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
	#year
	year = request.vars['year']
	year_range_string = map(lambda each_year: str(each_year),YEAR_RANGE) #vars come back as strings, so make YEAR_RANGE strings for easy comparison
	if not year in year_range_string: #get all years and makes if year not specified
		year=None
		brands_list = OD() #TEMP
		for each_year in year_range_string:
			brands_list.update(getBrandsList(each_year)) #doesn't matter if each_year is int or str because getBrandsList uses string formatting
		year_list = year_range_string #USE YEAR_LIST INSTEAD OF YEAR
	else:
		brands_list = getBrandsList(year)
		year_list = [year]
	brands_list = OD(sorted(brands_list.items(), key=lambda x: x[1])) #sort a dict by values #http://bit.ly/OhPhQr
		
	make = request.vars['make']
	models_list = {}
	if make in brands_list: #TEMP
		query &= db.auction_request.make==make
		for each_year in year_list:
			for each_model in ed_call(MAKE_URI%(make, each_year))['models']:
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
		for each_year in year_list:
			model_styles+=(ed_call( STYLES_URI%(make, model, each_year))['styles'])
		for each_style in model_styles:
			styles_list.update(
				{str(each_style['id']) : '%s (%s)'%(each_style['name'], each_style['year']['year']) if not year else each_style['name']} #json returns int but request.vars returns string, make them compatible
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
		query &= ((db.auction_request.year>=year_list[0]) & (db.auction_request.year<=year_list[-1]))#move top
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
	if sortby == "year-up":
		orderby = db.auction_request.year
	if sortby == "year-down":
		orderby = ~db.auction_request.year
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
		
	if sortby == 'highest' or sortby == 'lowest':
		reverse = True
		def lowest_offer(row): #prevents multiple queries via Field.Method calls in lambda
			offer = row.lowest_offer()
			if offer: 
				return offer.bid
			return 0
		if sortby == 'lowest':
			reverse = False
		auction_requests = auction_requests.sort(lowest_offer, reverse = reverse)
		
	if sortby == 'most' or sortby == 'least':
		reverse = True
		if sortby == 'most':
			reverse = False
		auction_requests = auction_requests.sort(lambda row: row.number_of_bids(), reverse=reverse)
		
	#sort virtual fields http://goo.gl/skbNJ6
	
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
	return dict(auction_requests=auction_requests, columns = columns, years_list = year_range_string, brands_list=brands_list, year=year, model=model, sortby=sortby, models_list=models_list, make=make, color=color, colors_list=colors_list, trim=trim, styles_list=styles_list)
	
@auth.requires(request.args(0))
def authorize_auction_for_dealer(): #add permission and charge entry fee upon dealer agreement of terms and fees
	auction_request_id = request.args[0]
	if request.args and db((db.auction_request.id == auction_request_id) & (db.auction_request.expires > request.now )).select(): #since we're dealing with money here use all means to prevent false charges. ex. make sure auction is not expired!
		auth.add_membership('request_by_make_authorized_dealers_#%s'%auction_request_id, auth.user_id) #instead of form.vars.id in default/request_by_make use request.args[0]
		redirect(URL('pre_auction.html', args=[auction_request_id]))
	raise HTTP(404 , "Invalid auction request!")

@auth.requires_login() #make dealer only
@auth.requires(request.args(0))
@auth.requires(auth.has_membership(role='request_by_make_authorized_dealers_#%s'%request.args(0))) #use request.args(0) instead of [0] to return None if no args
#@auth.requires(not db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == request.args(0))).select()) #make sure dealer did not make an offer already
def pre_auction():
	auction_request_id = request.args[0]
	if db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == auction_request_id)).select(): #make sure dealer did not make an offer already... if so redirect him to auction
		redirect(URL('auction',args=[auction_request_id]))
	#if not request.args:  #make decorator http://bit.ly/1i2wbHz
	#	session.flash='No request ID!'
	#	redirect(URL('my_auctions.html'))
	auction_request_rows = db(db.auction_request.id == auction_request_id).select() #ALWAYS verify existence of vars/args in database.
	if not auction_request_rows:
		session.flash='Invalid request ID!'
		redirect(URL('my_auctions.html'))
	
	db.auction_request_offer.auction_request.default = auction_request_id
	db.auction_request_offer.owner_id.default = auth.user_id
	db.auction_request_offer.owner_id.readable = False
	db.auction_request_offer.owner_id.writable = False
	
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
	
	colors = zip(auction_request.color_preference, auction_request.color_names) #color_preference means color_ids please do sitewide replace
	colors.sort(key = lambda each: each[1])
	
	db.auction_request_offer.color.requires = IS_IN_SET(colors, zero=None)
	
	offer_form = SQLFORM(db.auction_request_offer, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY
	
	if offer_form.process(hideerror = False).accepted: #hideerror = True to hide default error elements #change error message via form.custom
		session.flash = 'success!'
		redirect(
			URL('auction.html', args=[auction_request_id])
		)
	
	return dict(offer_form = offer_form, options=options,msrp_by_id=msrp_by_id, auction_request_id=auction_request_id)
	
	
def __get_option_from_ID(trim_data, option_type, option_id):
	options_data = trim_data['options']
	options = []
	for each_option_type in options_data:
		if each_option_type['category'] == option_type:
			options = each_option_type['options']
	for each_option in options:
		if int(each_option['id']) == int(option_id):
			return each_option 
	
@auth.requires_login() #make dealer only
@auth.requires(request.args(0))
#auth requires is admin or is part of this auction
def auction():
	auction_request_id = request.args[0]
	auction_request = db(db.auction_request.id == auction_request_id).select().first()
	if not auction_request:
		session.flash="Invalid request ID!"
		redirect(URL('default','index.html'))
	
	auction_request_expired = auction_request.expires < request.now

	#create offer form
	is_owner = auction_request.owner_id == auth.user.id #TODO add restriction that prevents dealers from creating an auction
	my_offer = db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == auction_request_id)).select().first() #where dealer owns this bid of this auction_request
	
	is_participant = False
	if my_offer:
		is_participant = True
	if is_owner:
		is_participant = True
	if not is_participant: #somehow he never made an offer
		session.flash="You are not a part of this auction!"
		redirect(URL('default','index.html'))

	#only allow form functionality to show for dealers as long as auction is active
	bid_form = None
	authorized_dealer = auth.has_membership(role='request_by_make_authorized_dealers_#%s'%auction_request_id)
	if authorized_dealer and not auction_request_expired: 
		if authorized_dealer:
			my_auction_request_offer_id = my_offer.id
			db.auction_request_offer_bid.auction_request.default = auction_request_id
			db.auction_request_offer_bid.auction_request_offer.default = my_auction_request_offer_id
			db.auction_request_offer_bid.owner_id.default = auth.user_id

			bid_form = SQLFORM(db.auction_request_offer_bid ,_class="form-horizontal") #update form!! #to add class to form #http://goo.gl/g5EMrY

		if bid_form.process(hideerror = False).accepted:
			response.flash = 'Your new bid is %s!'%bid_form.vars.bid

	#auction request info
	auction_request_area = db(db.zipgeo.zip_code == auction_request.zip_code).select().first()
	auction_request_user = db(db.auth_user.id == auction_request.owner_id).select().first() 
	
	colors=[]
	color_names=auction_request.color_names
	color_names.sort()
	for each_name in color_names:
		for each_color in json.loads(auction_request.trim_data)['colors'][1]['options']:
			if each_color['name'] == each_name:
				color_hex = each_color['colorChips']['primary']['hex']
				colors.append([each_name, color_hex])
	
	lowest_offer_row = auction_request.lowest_offer() #one db call instead of two like above
	lowest_offer = "No bids!"
	if lowest_offer_row:
		lowest_offer = '$%s'%int(lowest_offer_row.bid)
	
	#auction request offers (rows)
	auction_request_offers = db(db.auction_request_offer.auction_request == auction_request_id).select()
	
	#auction requests info
	auction_request_info = dict(
		id = str(auction_request.id),
		first_name =auction_request_user.first_name,
		last_init =auction_request_user.last_name[:1]+'.',
		year = auction_request.year,
		make = auction_request.make,
		model = auction_request.model,
		trim_name = auction_request.trim_name,
		trim_data = auction_request.trim_data,
		colors = colors,
		city = auction_request_area.city,
		state = auction_request_area.state_abbreviation,
		zip_code =  auction_request_area.zip_code,
		ends_on = str(auction_request.expires),
		ends_in_seconds = (auction_request.expires - request.now).total_seconds(),
		ends_in_human = human(auction_request.expires - request.now, precision=2, past_tense='{}', future_tense='{}'),
		number_of_bids = auction_request.number_of_bids(),
		number_of_dealers = len(auction_request_offers),
		best_price = lowest_offer,
	)

	#in memory sorting	
	sortby = request.vars['sortby']
	sortlist = []
	#Price
	pricechoices = ["price-up", "price-down"]; sortlist.extend(pricechoices)
	if sortby in pricechoices:
		reverse = False
		if sortby == "price-down":
			reverse = True
		auction_request_offers = auction_request_offers.sort(lambda row: row.latest_bid(), reverse=reverse)
	#MSRP
	msrpchoices = ["retail-price-up", "retail-price-down"]; sortlist.extend(msrpchoices)
	if sortby in msrpchoices:
		reverse = False
		if sortby == "retail-price-down":
			reverse = True
		auction_request_offers = auction_request_offers.sort(lambda row: row.MSRP(), reverse=reverse)
	#Discount (%off)
	discountchoices = ["discount-up", "discount-down"]; sortlist.extend(discountchoices)
	if sortby in discountchoices:
		reverse = False
		if sortby == "discount-down":
			reverse = True
		def msrp_discount(row):
			latest_bid = row.latest_bid()
			if latest_bid:
				return latest_bid.MSRP_discount()
			return 0
		auction_request_offers = auction_request_offers.sort(msrp_discount, reverse=reverse)
	
	#Distance
	distancechoices = ["distance-up", "distance-down"]; sortlist.extend(distancechoices)
	if sortby in distancechoices:
		reverse = False
		if sortby == "distance-down":
			reverse = True
		def distance_to_auction_request(row):
			offer_owner_info = db(db.dealership_info.id == row.owner_id).select().last()
			return calcDist(offer_owner_info.latitude, offer_owner_info.longitude, auction_request.latitude, auction_request.longitude)
			
		auction_request_offers = auction_request_offers.sort(distance_to_auction_request, reverse=reverse) #returns new
	
	"""
	response.view = 'generic.html'
	return dict(auction_request_info = auction_request_info['trim_data'])
	"""
	
	auction_request_offers_info = []
	trim_data = json.loads(auction_request_info['trim_data'])
	for each_offer in auction_request_offers:
		#options
		interior_options = []
		exterior_options = []
		mechanical_options = []
		package_options = []
		fees_options = []
		
		for each_option in each_offer.interior_options:
			interior_options.append(__get_option_from_ID(trim_data, 'Interior', each_option))
		for each_option in each_offer.exterior_options:
			exterior_options.append(__get_option_from_ID(trim_data, 'Exterior', each_option))
		for each_option in each_offer.mechanical_options:
			mechanical_options.append(__get_option_from_ID(trim_data, 'Mechanical', each_option))
		for each_option in each_offer.package_options:
			package_options.append(__get_option_from_ID(trim_data, 'Package', each_option))
		for each_option in each_offer.fees_options:
			fees_options.append(__get_option_from_ID(trim_data, 'Additional Fees', each_option))
			
		bids = db((db.auction_request_offer_bid.owner_id == each_offer.owner_id) & (db.auction_request_offer_bid.auction_request == auction_request_id)).select()
		number_of_bids = len(bids)
		msrp = each_offer.MSRP()
		last_bid = bids.last()
		
		each_offer_dict = {
			'id' : each_offer.id,
			'last_bid_price' : '$%s'%last_bid.bid if last_bid else "No Bids!",
			'number_of_bids' : number_of_bids,
			'color' : each_offer.color,
			'summary' : each_offer.summary,
			'interior_options' : interior_options,
			'exterior_options' : exterior_options,
			'mechanical_options' : mechanical_options,
			'package_options' : package_options,
			'fees_options' : fees_options,
			'exterior_image' : each_offer.exterior_image,
			'interior_image' : each_offer.interior_image,
			'front_image' : each_offer.front_image,
			'rear_image' : each_offer.rear_image,
			'tire_image' : each_offer.tire_image,
			'dashboard_image' : each_offer.dashboard_image,
			'passenger_image' : each_offer.passenger_image,
			'trunk_image' : each_offer.trunk_image,
			'underhood_image' : each_offer.underhood_image,
			'roof_image' : each_offer.roof_image,
			'other_image' : each_offer.other_image,
			'msrp': '$%s'%msrp,
			'msrp_discount': '%0.2f%%'% (last_bid.MSRP_discount(each_offer) if last_bid else 0.00,) #(100-(last_bid_price)/float(msrp)*100) #http://goo.gl/2qp8lh #http://goo.gl/6ngwCd
		}
		auction_request_offers_info.append(each_offer_dict)

	#title stuff
	response.title="Auction"
	response.subtitle="for %s's new %s %s %s" % (auth.user.first_name, auction_request.year, auction_request.make, auction_request.model)
	return dict(auction_request_info=auction_request_info, auction_request_offers_info=auction_request_offers_info, is_owner=is_owner, bid_form=bid_form, sortlist=sortlist, auction_request_expired=auction_request_expired)
	
@auth.requires_membership('dealers')
def my_auctions():
	my_offers = db(db.auction_request_offer.owner_id == auth.user_id).select()
	my_offer_summaries = []
	for each_offer in my_offers:
		auction_request = db(db.auction_request.id == each_offer.auction_request).select().first()
		color_names = dict(map(lambda id,name: [id,name], auction_request.color_preference, auction_request.color_names)) #since the dealers color must've been in the choices in the auction request, it is safe to use the auction request data as a reference rather than the API
		each_offer_dict = {
			'year':auction_request.year,
			'make':auction_request.make,
			'model':auction_request.model,
			'trim':auction_request.trim_name,
			'color':color_names[each_offer.color],
			'best_price': 'N/A',
		}
		my_offer_summaries.append(each_offer_dict)
	return dict(my_offer_summaries = my_offer_summaries)