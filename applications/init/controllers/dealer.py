def index():
	return dict()

@auth.requires_membership('dealers')
def auction_requests():
	if not "sortby" in request.vars:
		redirect(URL(vars=dict(sortby='newest')))
	"""
	It is also possible to build queries using in-place logical operators:
	>>> query = db.person.name!='Alex'
	>>> query &= db.person.id>3
	>>> query |= db.person.name=='John'
	"""
	query = (db.auction_request.id>0) & (db.auction_request.expires >= request.now) #WITHIN TIME AND RADIUS ONLY. RADIUS IN FILTERING BELOW
	#####filtering#####
	#build query and filter menu
	make = request.vars['make']
	models_list = {}
	if make in BRANDS_LIST:
		query &= db.auction_request.make==make
		for each_model in ed_call(MAKE_URI%(make, YEAR))['models']:
			models_list.update(
				{each_model ['niceName'] : each_model ['name'] }
			)
		models_list = OD(sorted(models_list.items(), key=lambda x: x[1])) #sort a dict by values #http://bit.ly/OhPhQr
	else:
		make = None #simpler for view
	#
	model = request.vars['model']
	model_styles = []
	styles_list = {}
	if model in models_list:
		query &= db.auction_request.model==model
		model_styles+=(ed_call( STYLES_URI%(make, model, YEAR))['styles'])
		for each_style in model_styles:
			styles_list.update(
				{str(each_style['id']) : each_style['name']} #json returns int but request.vars returns string, make them compatible
			)
		styles_list = OD(sorted(styles_list.items(), key=lambda x: x[1])) #what it does is it passes key, value tuple to sorted function, which determines the key to sort with a function that gets passed each element in the dict
	else:
		model = None
	#
	trim = str(request.vars['trim'])
	colors_list = {}
	if trim in styles_list:
		query &= db.auction_request.trim_choices==trim
		for each_style in model_styles:
			if trim == str(each_style['id']):
				for each_color in each_style['colors'][1]['options']:
						colors_list.update({str(each_color['id']) : each_color['name']})
		colors_list = OD(sorted(colors_list.items(), key=lambda x: x[1])) 
	else:
		trim = None
	#
	color = str(request.vars['color'])
	if color in colors_list:
		query &= db.auction_request.color_preference.contains(color)
	else:
		color = None
	#
	year = request.vars['year']
	if year:
		query &= db.auction_request.year==year #move top
	color = request.vars['color']
	#####sorting#####
	sortby = request.vars['sortby']
	orderby = ~db.auction_request.expires #TEMP
	if sortby == "id-up":
		orderby = db.auction_request.id
	if sortby == "id-down":
		orderby = ~db.auction_request.id
	if sortby == "make-up":
		orderby = db.auction_request.make
	if sortby == "make-down":
		orderby = ~db.auction_request.make
	if sortby == "model-up":
		orderby = db.auction_request.model
	if sortby == "model-down":
		orderby = ~db.auction_request.model
	if sortby == "trim-up":
		orderby = db.auction_request.trim_name
	if sortby == "trim-down":
		orderby = ~db.auction_request.trim_name
	if sortby == "newest":
		orderby = ~db.auction_request.expires
	if sortby == "oldest":
		orderby = db.auction_request.expires #not using ID because expires can be changed by admin
		
	auction_requests = db(query).select(orderby=orderby)
	#####in memory filterting#####
	my_info = db(db.dealership_info.owner_id == auth.user_id).select().first()
	auction_requests = auction_requests.exclude(lambda row: row['radius'] >= calcDist(my_info.latitude, my_info.longitude, row.latitude, row.longitude) )#remove requests not in range
	#####in memory sorting#####
	if sortby == "colors-most" or sortby == "colors-least":
		reverse = False
		if sortby == "colors-least":
			reverse = True
		auction_requests = auction_requests.sort(lambda row: len(row.color_preference), reverse=reverse)#the sort function takes a rows object and applies a function with each row as the argument. Then it compares the returned numerical value of each row and sorts it 
	
	if sortby == 'closest' or sortby == 'farthest':
		reverse = False
		if sortby == "farthest":
			reverse = True
		auction_requests = auction_requests.sort(lambda row: calcDist(my_info.latitude, my_info.longitude, row.latitude, row.longitude), reverse=reverse) #returns new
	
	columns = [ #keep len 12
		[
			'', #title
			['id-up','id-down'], #caret up, caret down
			1 #span
		],
		[
			'Year', 
			['year-up','year-down'],
			1
		],
		[
			'Make', 
			['make-up','make-down'],
			1
		],
		[
			'Model', 
			['model-up','model-down'],
			1
		],
		[
			'Trim', 
			['trim-up','trim-down'],
			2
		],
		[
			'Colors', #sort by number of colors 
			['colors-most','colors-least'],
			2
		],
		[
			'Area', 
			['closest','farthest'],
			1
		],
		[
			'Ends In', 
			['oldest','newest'],
			1
		],
		[
			'Bids', 
			['most','least'],
			1
		],
		[
			'Best $', 
			['lowest','highest'],
			1
		],
	]
	#
	response.title = "Auction requests"
	area=db(db.zipgeo.zip_code == db(db.dealership_info.owner_id == auth.user_id).select().first().zip_code).select().first() #OPT put in compute or virtual field
	city = area.city
	state = area.state_abbreviation
	number = len(auction_requests)
	plural = ''
	if not number or number > 1:
		plural = 's'
	response.subtitle = "Showing %s result%s within 250 miles of %s, %s."% (number, plural, city, state)
	#
	return dict(auction_requests=auction_requests, columns = columns, brands_list=BRANDS_LIST, model=model, sortby=sortby, models_list=models_list, make=make, color=color, colors_list=colors_list, trim=trim, styles_list=styles_list)
	
def authorize_auction_for_dealer(): #add permission and charge entry fee upon dealer agreement of terms and fees
	auction_request_id = request.args[0]
	if request.args and db((db.auction_request.id == auction_request_id) & (db.auction_request.expires > request.now )).select(): #since we're dealing with money here use all means to prevent false charges. ex. make sure auction is not expired!
		auth.add_membership('request_by_make_authorized_dealers_#%s'%auction_request_id, auth.user_id) #instead of form.vars.id in default/request_by_make use request.args[0]
		redirect(URL('pre_auction.html', args=[auction_request_id]))
	raise HTTP(404 , "Invalid auction request!")
	
@auth.requires_login() #make dealer only
@auth.requires(auth.has_membership(role='request_by_make_authorized_dealers_#%s'%request.args(0))) #use request.args(0) instead of [0] to return None if no args
def pre_auction():
	if not request.args:  #make decorator http://bit.ly/1i2wbHz
		session.flash='No request ID!'
		redirect(URL('my_auctions.html'))
	auction_request_id = request.args[0]
	auction_request_rows = db(db.auction_request.id == auction_request_id).select() #ALWAYS verify existence of vars/args in database.
	if not auction_request_rows:
		session.flash='Invalid request ID!'
		redirect(URL('my_auctions.html'))
	
	db.auction_request_offer.auction_request.default = auction_request_id
	
	auction_request = auction_request_rows.last()
	trim_data = json.loads(auction_request.trim_data)
	options = trim_data['options']
	#return dict(offer_form=None, options=options) #uncomment for testing
	interior_options = []
	exterior_options = []
	mechanical_options = []
	package_options = []
	fees_options = []
	for each_option_type in options:
		if each_option_type['category'] == 'Interior':
			interior_options = each_option_type['options']
		if each_option_type['category'] == 'Exterior':
			exterior_options = each_option_type['options']
		if each_option_type['category'] == 'Mechanical':
			mechanical_options = each_option_type['options']
		if each_option_type['category'] == 'Package':
			package_options = each_option_type['options']
		if each_option_type['category'] == 'Additional Fees':
			fees_options = each_option_type['options']
	#return dict(offer_form=None, options=options, interior_options=interior_options, mechanical_options=mechanical_options) #uncomment for testing
	#USEFUL #interior_options = options.get('interior') or [] #returns None, but get blank [] instead
	interior_options_names = []
	exterior_options_names = []
	mechanical_options_names = []
	package_options_names = []
	fees_options_names = []
	
	msrp_by_id = {'base':trim_data['price']['baseMSRP']}

	for each_option in interior_options:
		interior_options_names.append([each_option['id'],each_option['name']]) ##never safe to use names in forms stick to standard ids
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	interior_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.interior_options.requires = IS_IN_SET(interior_options_names, multiple=True)
	db.auction_request_offer.interior_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	
	for each_option in exterior_options:
		exterior_options_names.append([each_option['id'],each_option['name']])
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	exterior_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.exterior_options.requires = IS_IN_SET(exterior_options_names, multiple=True)
	db.auction_request_offer.exterior_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in mechanical_options:
		mechanical_options_names.append([each_option['id'],each_option['name']])
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	mechanical_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.mechanical_options.requires = IS_IN_SET(mechanical_options_names, multiple=True)
	db.auction_request_offer.mechanical_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in package_options:
		package_options_names.append([each_option['id'],each_option['name']])
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	package_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.package_options.requires = IS_IN_SET(package_options_names, multiple=True)
	db.auction_request_offer.package_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in fees_options:
		fees_options_names.append([each_option['id'],each_option['name']])
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	fees_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.fees_options.requires = IS_IN_SET(fees_options_names, multiple=True)
	db.auction_request_offer.fees_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	#db.auction_request_offer.
	
	offer_form = SQLFORM(db.auction_request_offer, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY
	
	if offer_form.process(hideerror = False).accepted: #hideerror = True to hide default error elements #change error message via form.custom
		session.flash = 'success!'
		redirect(
			URL('auction.html')
		)
	
	return dict(offer_form = offer_form, options=options,msrp_by_id=msrp_by_id, auction_request_id=auction_request_id)
	
@auth.requires_login() #make dealer only
def auction():
	if not request.args:  #make decorator http://bit.ly/1i2wbHz
		session.flash='No request ID!'
		redirect(URL('my_auctions.html'))
	
	auction_request_id = request.args[0]
	
	auction_request = db(db.auction_request.id == auction_request_id).select().first()
	if not auction_request:
		session.flash="Invalid request ID!"
		redirect(URL('my_auctions.html'))
	
	response.title="Auction"
	response.subtitle="for %s's new %s %s %s" %  (auth.user.first_name, auction_request.year, auction_request.make, auction_request.model)
	
	return dict()