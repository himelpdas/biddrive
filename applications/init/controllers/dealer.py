def index():
	redirect(URL('my_auctions.html'))

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
	query = (db.auction_request.id > 0) & (db.auction_request.auction_expires >= request.now) #NON-COMPLETE AUCTIONS WITHIN TIME AND RADIUS ONLY. RADIUS IN FILTERING BELOW
	#query = (db.auction_request.id != db.auction_request_winning_offer.auction_request) & (db.auction_request.auction_expires >= request.now) #This doesn't work for some fucking reason, so filter in memory instead
	#####filtering#####
	#build query and filter menu
	#year
	
	my_info = db(db.dealership_info.owner_id == auth.user_id).select().first()
	
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
	#dealer_specialty = my_info.specialty
	#brands_list = dict([[each_niceName , brands_list[each_niceName]] for each_niceName in dealer_specialty]) #niceName, name #HACK - limit the brandslist to only whats in the dealer's speciality
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
				safe_style_colors = each_style['colors']
				colorChipsErrorFix(safe_style_colors)
				for each_color in safe_style_colors[1]['options']:
					colors_list.update( {str(each_color['id']) : [each_color['name'], each_color['colorChips']['primary']['hex'] ],} )
		colors_list = OD(sorted(colors_list.items(), key=lambda x: x[1])) #FIXED#TODO: ADD LOGIC TO PREVENT STUPID COLORCHIPS ERROR 
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
	orderby = ~db.auction_request.auction_expires #TEMP
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
		orderby = ~db.auction_request.auction_expires
	if sortby == "oldest":
		orderby = db.auction_request.auction_expires #not using ID because expires can be changed by admin
		
	auction_requests = db(query & (db.auction_request.owner_id==db.auth_user.id)).select(orderby=orderby)
	#####in memory filterting#####
	#location
	auction_requests = auction_requests.exclude(lambda row: row.auction_request['radius'] >= calcDist(my_info.latitude, my_info.longitude, row.auction_request.latitude, row.auction_request.longitude) )#remove requests not in range
	#winning
	auction_requests =auction_requests.exclude(lambda row: not db(db.auction_request_winning_offer.auction_request == row.auction_request['id']).select().first())
	#####DIGITALLY SIGNED URL##### #to prevent a malicious dealer from submitting an offer to a completely different auction id, than what was originally clicked in auction requests. First solution was to use RBAC, but hacker can simply loop through all the ids in the auction request and visit the RBAC url
	for each_request in auction_requests:
		each_request["digitally_signed_pre_auction_url"] = URL('dealer','pre_auction', args=[each_request.auction_request.id], hmac_key=each_request.auction_request.temp_id, hash_vars=[each_request.auction_request.id]) #temp_id is a uuid # hmac key, hash_vars and salt all gets hashed together to generate a hash string, and must match with string of the same arguments passed through a hash function. #Note, the digital signature is verified via the URL.verify function. URL.verify also takes the hmac_key, salt, and hash_vars arguments described above, and their values must match the values that were passed to the URL function when the digital signature was created in order to verify the URL.
	#####in memory sorting#####
	if sortby == "colors-most" or sortby == "colors-least":
		reverse = False
		if sortby == "colors-least":
			reverse = True
		auction_requests = auction_requests.sort(lambda row: len(row.auction_request.color_preference), reverse=reverse)#the sort function takes a rows object and applies a function with each row as the argument. Then it compares the returned numerical value of each row and sorts it 
	
	if sortby == 'closest' or sortby == 'farthest':
		reverse = False
		if sortby == "farthest":
			reverse = True
		auction_requests = auction_requests.sort(lambda row: calcDist(my_info.latitude, my_info.longitude, row.auction_request.latitude, row.auction_request.longitude), reverse=reverse) #returns new
	"""	
	if sortby == 'highest' or sortby == 'lowest':
		reverse = True
		def lowest_offer(row): #prevents multiple queries via Field.Method calls in lambda
			offer = row.auction_request.lowest_offer()
			if offer: 
				return offer.bid
			return 0
		if sortby == 'lowest':
			reverse = False
		auction_requests = auction_requests.sort(lowest_offer, reverse = reverse)
	"""	
	if sortby == 'most' or sortby == 'least':
		reverse = True
		if sortby == 'most':
			reverse = False
		auction_requests = auction_requests.sort(lambda row: row.auction_request.number_of_bids(), reverse=reverse)
		
	#
		
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
		#[
		#	'Best $', 
		#	['lowest','highest'],
		#	1
		#],
	]
	
	#
	response.title = "Auction requests"
	name=" ".join(map(lambda word: word.capitalize(), my_info.dealership_name.split(' '))) # converts bobs kia to Bobs Kia
	area=db(db.zipgeo.zip_code == my_info.zip_code).select().first() #OPT put in compute or virtual field
	city = area.city
	state = area.state_abbreviation
	number = len(auction_requests)
	plural = ''
	verb = 'is'
	if not number or number > 1:
		plural = 's'
		verb = 'are'
		car = brands_list[make] if make else 'car'
	response.message = 'Showing %s %s buyer%s who %s near "%s" in %s, %s.'% (number, car ,plural, verb, name, city, state)
	#
	return dict(auction_requests=auction_requests, columns = columns, years_list = year_range_string, brands_list=brands_list, year=year, model=model, sortby=sortby, models_list=models_list, make=make, color=color, colors_list=colors_list, trim=trim, styles_list=styles_list)

#@auth.requires_login() #make dealer only
@auth.requires(request.args(0))
#@auth.requires(auth.has_membership(role='request_by_make_authorized_dealers_#%s'%request.args(0))) #use request.args(0) instead of [0] to return None if no args
#@auth.requires(not db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == request.args(0))).select()) #make sure dealer did not make an offer already
@auth.requires_membership('dealers')
def pre_auction():
	auction_request_id = request.args[0]
	if db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == auction_request_id)).select(): #make sure dealer did not make an offer already... if so redirect him to auction
		redirect(URL('auction',args=[auction_request_id]))
	#if not request.args:  #make decorator http://bit.ly/1i2wbHz
	#	session.message='No request ID!'
	#	redirect(URL('my_auctions.html'))
	auction_request = db(db.auction_request.id == auction_request_id).select().last() #ALWAYS verify existence of vars/args in database.
	if not auction_request:
		session.message='@Invalid request ID!'
		redirect(URL('my_auctions'))
	if not URL.verify(request, hmac_key=auction_request.temp_id, hash_vars=[auction_request.id]): #verifys all args (or ones specified) in a url
		session.message='@You are attempting to tamper with BidDrive! You have been reported.'
		redirect(URL('my_auctions'))
	
	db.auction_request_offer.auction_request.default = auction_request_id
	db.auction_request_offer.owner_id.default = auth.user_id
	db.auction_request_offer.owner_id.readable = False
	db.auction_request_offer.owner_id.writable = False
	
	car=dict(year=auction_request.year,
	make=auction_request.make,
	model=auction_request.model,
	trim=auction_request.trim_name)
	
	trim_data = json.loads(auction_request.trim_data)
	options = trim_data['options']
	#return dict(form=None, options=options) #uncomment for testing
	interior_options = []
	exterior_options = []
	mechanical_options = []
	package_options = []
	fees_options = []
	safety_options = []
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
		if each_option_type['category'] == 'Safety':
			safety_options = each_option_type['options']
	#return dict(form=None, options=options, interior_options=interior_options, mechanical_options=mechanical_options) #uncomment for testing
	#USEFUL #interior_options = options.get('interior') or [] #returns None, but get blank [] instead
	interior_options_names = []
	exterior_options_names = []
	mechanical_options_names = []
	package_options_names = []
	fees_options_names = []
	safety_options_names = []
	
	msrp_by_id = {'base':trim_data['price']['baseMSRP']}

	for each_option in interior_options:
		if 'price' in each_option and 'baseMSRP' in each_option['price']:
			interior_options_names.append([each_option['id'],each_option['name']]) ##never safe to use names in forms stick to standard ids
			msrp_by_id[each_option['name']] = each_option['price']['baseMSRP'] 
			
	interior_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.interior_options.requires = IS_IN_SET(interior_options_names, multiple=True)
	db.auction_request_offer.interior_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	#now make a price dict for calculation
	for each_option in exterior_options: #FIXED front and rear splash guard 2014 buick enclave has no msrp and causes page to fail. so if price doesn't exist don't add it#NVM JUST MAKE IT $0 LIKE HAGGLEDADDY
		#if 'price' in each_option and 'baseMSRP' in each_option['price']:
		exterior_options_names.append([each_option['id'],each_option['name']])
		msrp_by_id[each_option['name']] = each_option['price']['baseMSRP'] if 'price' in each_option and 'baseMSRP' in each_option['price'] else 0

		#TODO CHANGE TO $0 here N/A via ajax in view
	exterior_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.exterior_options.requires = IS_IN_SET(exterior_options_names, multiple=True)
	db.auction_request_offer.exterior_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in mechanical_options:
		if 'price' in each_option and 'baseMSRP' in each_option['price']:
			mechanical_options_names.append([each_option['id'],each_option['name']])
			msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	mechanical_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.mechanical_options.requires = IS_IN_SET(mechanical_options_names, multiple=True)
	db.auction_request_offer.mechanical_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in package_options:
		if 'price' in each_option and 'baseMSRP' in each_option['price']: 
			package_options_names.append([each_option['id'],each_option['name']])
			msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	package_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.package_options.requires = IS_IN_SET(package_options_names, multiple=True)
	db.auction_request_offer.package_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in fees_options:
		if 'price' in each_option and 'baseMSRP' in each_option['price']: 
			fees_options_names.append([each_option['id'],each_option['name']])
			msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	fees_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.fees_options.requires = IS_IN_SET(fees_options_names, multiple=True)
	db.auction_request_offer.fees_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	for each_option in safety_options:
		if 'price' in each_option and 'baseMSRP' in each_option['price']: 
			safety_options_names.append([each_option['id'],each_option['name']])
			msrp_by_id[each_option['name']] = each_option['price']['baseMSRP']  
	safety_options_names.sort(key=lambda each:each[1])
	db.auction_request_offer.safety_options.requires = IS_IN_SET(safety_options_names, multiple=True)
	db.auction_request_offer.safety_options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	colors = zip(auction_request.color_preference, auction_request.color_names) #color_preference means color_ids please do sitewide replace
	colors.sort(key = lambda each: each[1])
	
	db.auction_request_offer.color.requires = IS_IN_SET(colors, zero=None)
	
	form = SQLFORM(db.auction_request_offer, _class="form-horizontal", hideerror=True) #to add class to form #http://goo.gl/g5EMrY
				
	def computations(form):
		codes_to_names = dict(interior_options_names+
			exterior_options_names+
			mechanical_options_names+
			package_options_names+
			fees_options_names+
			safety_options_names
		)
		codes_to_colors = dict(colors)
		options_prefixes = ['interior', 'exterior', 'mechanical', 'package', 'fees', 'safety']
		for each_prefix in options_prefixes:
			db.auction_request_offer['%s_options_names'%each_prefix].default = [ codes_to_names[each_option_code] for each_option_code in form.vars["%s_options"%each_prefix] ]
		db.auction_request_offer.color_name.default = codes_to_colors[form.vars["color"]]

	if form.process(onvalidation=computations, hideerror = False, message_onfailure="@Errors in form. Please check it out.").accepted: #hideerror = True to hide default error elements #change error message via form.custom
		if request.args and db((db.auction_request.id == auction_request_id) & (db.auction_request.auction_expires > request.now )).select(): #since we're dealing with money here use all means to prevent false charges. ex. make sure auction is not expired!
			my_piggy = db(db.credits.owner==auth.user_id).select().last()
			my_piggy.update_record( credits = my_piggy.credits - CREDITS_PER_AUCTION) #remove one credit
			auth.add_membership('dealers_in_auction_%s'%auction_request_id, auth.user_id) #instead of form.vars.id in default/request_by_make use request.args[0]
		session.message = '$Your vehicle was submitted!'
		redirect(
			URL('auction', args=[auction_request_id])
		)

	auction_request_area = db(db.zipgeo.zip_code == auction_request.zip_code).select().first()
	auction_request_user = db(db.auth_user.id == auction_request.owner_id).select().first() 

	auction_request_info = dict(
		id = str(auction_request.id),
		auction_requests_user_entered = len(db(db.auction_request.owner_id == auction_request_user.id).select()),
		first_name =auction_request_user.first_name,
		last_init =auction_request_user.last_name.capitalize()[:1]+'.',
		year = auction_request.year,
		make = auction_request.make,
		model = auction_request.model,
		is_lease = auction_request.funding_source == 'lease',
		trim_name = auction_request.trim_name,
		trim_data = trim_data,
		auction_request=auction_request,
		colors = colors,
		city = auction_request_area.city,
		state = auction_request_area.state_abbreviation,
		zip_code =  auction_request_area.zip_code,
	)
	
	return dict(form = form, options=options,msrp_by_id=msrp_by_id, auction_request_id=auction_request_id,auction_request_info=auction_request_info, **car)

"""
@auth.requires(request.args(0))
def authorize_auction_for_dealer(): #add permission and charge entry fee upon dealer agreement of terms and fees
	auction_request_id = request.args[0]
	if request.args and db((db.auction_request.id == auction_request_id) & (db.auction_request.auction_expires > request.now )).select(): #since we're dealing with money here use all means to prevent false charges. ex. make sure auction is not expired!
		auth.add_membership('request_by_make_authorized_dealers_#%s'%auction_request_id, auth.user_id) #instead of form.vars.id in default/request_by_make use request.args[0]
		redirect(URL('pre_auction.html', args=[auction_request_id]))
	session.message='@Invalid request ID!'
	redirect(URL('auction_requests'))
"""

	
#@auth.requires_login() #make dealer only
@auth.requires(request.args(0))
#auth requires is admin or is part of this auction
def __auction_validator__():
	auction_request_id = request.args[0]
	auction_request = db(db.auction_request.id == auction_request_id).select().first()
	if not auction_request:
		session.message="!Invalid auction ID!"
		redirect(URL('my_auctions'))
	
	#get vehicle data
	trim_data = json.loads(auction_request.trim_data)
	
	auction_request_ends = auction_request.auction_expires
	auction_request_expired = auction_request.auction_expired() #auction_request.auction_expires < request.now
	auction_ended_offer_ends = auction_request.offer_expires #auction_request.auction_expires + datetime.timedelta(days = 1) 
	auction_ended_offer_expired = auction_request.offer_expired() #auction_ended_offer_ends < request.now 

	is_owner = auction_request.owner_id == auth.user.id #TODO add restriction that prevents dealers from creating an auction
	is_dealer_with_offer = db((db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request == auction_request_id)).select().first() #where dealer owns this bid of this auction_request
	is_authorized_dealer = auth.has_membership(role='dealers_in_auction_%s'%auction_request_id) #will need authorized dealers but may have to move redirect function that controls this
	is_authorized_buyer = auth.has_membership(role='owner_of_auction_%s'%auction_request_id) #can remove at admin
	
	is_participant = is_authorized_dealer_with_offer =is_dealer_and_with_final_bid= False
	if is_owner and is_authorized_buyer:
		is_participant = True
	if is_dealer_with_offer and is_authorized_dealer:
		is_authorized_dealer_with_offer = True
		is_participant = True
		if 0 >= db(db.credits.owner==auth.user_id).select().last().credits: #do not allow negative balance dealers to participate, instead make them buy more credits.
			session.message2="@You have a negative balance! You must purchase more credits to participate in auctions."
			redirect(URL('billing', 'buy_credits'))
		if db((db.auction_request_offer_bid.owner_id == auth.user_id) & (db.auction_request_offer_bid.auction_request==auction_request_id) & (db.auction_request_offer_bid.final_bid != None)).select().first():
			is_dealer_and_with_final_bid = True
	if not is_participant: #somehow he never made an offer
		session.message="@You are not a part of this auction!"
		redirect(URL('default','index'))
		
	#session.last_auction_visited = auction_request_id #for instant access to last auction visited when portal button pressed
	#tested above if this user is worth using resources for, now do all the required queries for the logic below
	auction_request_offers = db((db.auction_request_offer.auction_request == auction_request_id)&(db.auction_request_offer.owner_id==db.auth_user.id)&(db.auction_request_offer.owner_id == db.dealership_info.owner_id)&(db.auction_request_offer.owner_id == db.auth_user.id)).select()#This is a multi-join versus the single join in my_auctions. join auth_table and dealership_info too since we need the first name and lat/long of dealer, instead of having to make two db queries
	last_favorite_choice = db(db.auction_request_favorite_choice.auction_request == auction_request_id).select().last()  #no need for further testing aside from auction_request_id because of previous if/else
	a_winning_offer = db(db.auction_request_winning_offer.auction_request == auction_request_id).select().last()
	
	auction_is_completed = (a_winning_offer or auction_ended_offer_expired)

	#auction request info
	auction_request_area = db(db.zipgeo.zip_code == auction_request.zip_code).select().first()
	auction_request_user = db(db.auth_user.id == auction_request.owner_id).select().first() 
	
	colors=[]
	color_names = dict(map(lambda id,name: [id,name], auction_request.color_preference, auction_request.color_names)) #dual purpose: make color names dict that each_offer below can map color-id to #since the dealers color must've been in the choices in the auction request, it is safe to use the auction request data as a reference rather than the API
	color_names = OD(sorted(color_names.items(), key=lambda x: x[1])) #color_names.sort()
	for id, each_name in color_names.items(): #just get names here for auction_request_info
		color_hex=getColorHexByNameOrID(each_name, trim_data) #don't forget color hex
		colors.append([each_name, color_hex])
		
	is_lease = auction_request.funding_source == 'lease'
	
	return dict(auction_request_id=auction_request_id, 
		auction_request=auction_request, 
		trim_data=trim_data,
		auction_request_ends=auction_request_ends,
		auction_request_expired=auction_request_expired,
		auction_ended_offer_ends=auction_ended_offer_ends,
		auction_ended_offer_expired=auction_ended_offer_expired,
		is_owner=is_owner,
		is_dealer_with_offer=is_dealer_with_offer,
		is_authorized_dealer=is_authorized_dealer,
		is_participant=is_participant,
		is_authorized_dealer_with_offer=is_authorized_dealer_with_offer,
		is_dealer_and_with_final_bid=is_dealer_and_with_final_bid,
		auction_request_offers = auction_request_offers,
		last_favorite_choice = last_favorite_choice,
		a_winning_offer = a_winning_offer,
		auction_is_completed = auction_is_completed,
		auction_request_area=auction_request_area,
		auction_request_user=auction_request_user,
		colors=colors,
		is_lease=is_lease,
		color_names=color_names,)

def auction():
	auction_validator = __auction_validator__()
	auction_request_id=auction_validator['auction_request_id']
	auction_request=auction_validator['auction_request']
	trim_data=auction_validator['trim_data']
	auction_request_ends=auction_validator['auction_request_ends']
	auction_request_expired=auction_validator['auction_request_expired']
	auction_ended_offer_ends=auction_validator['auction_ended_offer_ends']
	auction_ended_offer_expired=auction_validator['auction_ended_offer_expired']
	is_owner=auction_validator['is_owner']
	is_dealer_with_offer=auction_validator['is_dealer_with_offer']
	is_authorized_dealer=auction_validator['is_authorized_dealer']
	is_participant=auction_validator['is_participant']
	is_authorized_dealer_with_offer=auction_validator['is_authorized_dealer_with_offer']
	is_dealer_and_with_final_bid=auction_validator['is_dealer_and_with_final_bid']
	auction_request_offers=auction_validator['auction_request_offers']
	last_favorite_choice=auction_validator['last_favorite_choice']
	a_winning_offer=auction_validator['a_winning_offer']
	auction_is_completed=auction_validator['auction_is_completed']
	auction_is_completed = auction_validator['auction_is_completed']
	auction_request_area=auction_validator['auction_request_area']
	auction_request_user=auction_validator['auction_request_user']
	colors=auction_validator['colors']
	color_names=auction_validator['color_names']
	is_lease=auction_validator['is_lease']
	car = '%s %s %s (ID:%s)' % (auction_request['year'], auction_request['make'].upper(), auction_request['model'].upper(), auction_request['id'])
	
	#only allow form functionality to show for dealers as long as auction is active
	bid_form = my_message_form_dealer = my_auction_request_offer_id = is_final_bid = None
	if not a_winning_offer and not auction_request_expired: #do not allow any insertions for expired or winning
		#create offer form
		if is_authorized_dealer_with_offer and not is_dealer_and_with_final_bid:
			#see if final offer
			final_message = None
			is_final_bid = request.vars['final_bid']
			if is_final_bid:
				db.auction_request_offer_bid.end_sooner_in_hours.requires = IS_INT_IN_RANGE(1, (auction_request_ends-request.now).total_seconds()/3600.0)
				final_message = "@This was your final bid! The buyer has been notified."
			#make sure new bid can't be higher than previous
			my_previous_bid = db((db.auction_request_offer_bid.owner_id == auth.user_id) & (db.auction_request_offer_bid.auction_request == auction_request_id)).select().last()
			highest_bid_allowed = my_previous_bid.bid if my_previous_bid else (5000 if is_lease else 1000000)
			db.auction_request_offer_bid.bid.requires = [IS_NOT_EMPTY(),IS_INT_IN_RANGE(49 if is_lease else 999, highest_bid_allowed)]
			#bid form
			my_auction_request_offer_id = is_dealer_with_offer.id
			db.auction_request_offer_bid.auction_request.default = auction_request_id
			db.auction_request_offer_bid.auction_request_offer.default = my_auction_request_offer_id
			db.auction_request_offer_bid.owner_id.default = auth.user_id
			bid_form = SQLFORM(db.auction_request_offer_bid ,_class="form-horizontal") #update form!! #to add class to form #http://goo.gl/g5EMrY

			#message form
			db.auction_request_offer_message.auction_request_offer.default = my_auction_request_offer_id #make sure the message form has the dealers offer_id for submission
			db.auction_request_offer_message.auction_request.default = auction_request_id
			db.auction_request_offer_message.owner_id.default = auth.user.id
			my_message_form_dealer = SQLFORM(db.auction_request_offer_message, _class="form-horizontal") #the message form to show if user is dealer
			
			#dealer bid process
			if bid_form.process(hideerror = True).accepted:
				response.message = '$Your new bid is $%s.'%"{:,}".format(bid_form.vars.bid) #redirect not needed since we're dealing with POST
				if final_message:
					session.message2 = final_message
					redirect(URL(args=request.args))
			elif bid_form.errors:
				response.message = '!Bid not submitted! Please check for mistakes in form.'
			
			#dealer message process
			if my_message_form_dealer.process().accepted:
				response.message = '$Your message was submitted to the buyer.'
				your = auth.user
				_buyer = auction_request_user
				scheduler.queue_task(
					send_alert_task,
					pargs=['email', _buyer.email, response.render('email_alert_template.html', dict(
						APPNAME=APP_NAME,
						NAME = _buyer.first_name.capitalize(), 
						MESSAGE =  XML("A dealer for a <i>%s</i> sent <b>%s</b> a message."%(car, 'you')),
						MESSAGE_TITLE = "You have a new message!",
						WHAT_NOW = "%s said:"%your.first_name.capitalize(),
						INSTRUCTIONS = my_message_form_dealer.vars.message,
						CLICK_HERE = "Go to auction",
						CLICK_HERE_URL = URL(args=request.args),
					)), "You have a new message about the %s at %s"%(car,APP_NAME)],
					#pvars={},
					#repeats = 10, # run 10 times
					period = 5, # run 5s after previous
					timeout = 30, # should take less than 30 seconds
				)
				
			elif my_message_form_dealer.errors:
				response.message = '!Your message had errors. Please fix!'
	
	##################
	lowest_offer_row = auction_request.lowest_offer() #one db call instead of two like above
	lowest_price = None
	if lowest_offer_row:
		lowest_price = '$%s'%int(lowest_offer_row.bid)
	##auction request offers (rows) #FIX - somehow duplicates can appear you must fix. must have to do with similar id numbers# FIXED used ordered dict for auction_request_offers_info instead of list
	##auction_request_offers = db((db.auction_request_offer.auction_request == auction_request_id)&(db.auction_request_offer.owner_id==db.auth_user.id)&(db.auction_request_offer.owner_id == db.dealership_info.owner_id)).select()#This is a multi-join versus the single join in my_auctions. join auth_table and dealership_info too since we need the first name and lat/long of dealer, instead of having to make two db queries
	##################
	#favorite stuff
	favorite_price = None
	if last_favorite_choice:
		last_favorite_choice_bid = db(db.auction_request_offer_bid.auction_request_offer == last_favorite_choice.auction_request_offer).select().last()
		if last_favorite_choice_bid: #it guaranteed exists, but do if then in case anyway
			favorite_price='$%s'%last_favorite_choice_bid.bid
	##################
	#auction requests info
	auction_ended_offer_expires = (auction_request.auction_expires - request.now).total_seconds() if not auction_ended_offer_expired and not a_winning_offer else 0 #set a timer for offer expire, but only if there is no winner and not auction_ended_offer_expired
	bidding_ended = auction_request_expired
	auction_request_info = dict(
		id = str(auction_request.id),
		auction_requests_user_entered = len(db(db.auction_request.owner_id == auction_request_user.id).select()),
		first_name =auction_request_user.first_name,
		last_init =auction_request_user.last_name[:1]+'.',
		year = auction_request.year,
		make = auction_request.make,
		model = auction_request.model,
		is_lease = is_lease,
		trim_name = auction_request.trim_name,
		trim_data = trim_data,
		auction_request=auction_request,
		colors = colors,
		city = auction_request_area.city,
		state = auction_request_area.state_abbreviation,
		zip_code =  auction_request_area.zip_code,
		ends_on = str(auction_request.auction_expires),
		ends_in_seconds = (auction_request.auction_expires - request.now).total_seconds() if not bidding_ended else 0, #if bidding ended you'll end up with negative number will fuck up auction page
		bidding_ended = bidding_ended,
		auction_completed = not auction_ended_offer_expires, #auction is finito if buyer chose a winner or offer time ran out
		auction_ended_offer_expires = auction_ended_offer_expires,
		#ends_in_human = human(auction_request.auction_expires - request.now, precision=2, past_tense='{}', future_tense='{}'),
		number_of_bids = auction_request.number_of_bids(),
		number_of_dealers = len(auction_request_offers),
		lowest_price = lowest_price,
		favorite_price = favorite_price,
		view_certificate_url = URL('dealer','winner', args=[auction_request_id], hmac_key=str(auth.user_id), hash_vars=[auction_request_id], salt=str(session.salt)) #hash_vars is like message in hmac function #temp_id is a uuid # hmac key, hash_vars and salt all gets hashed together to generate a hash string, and must match with string of the same arguments passed through a hash function. #Note, the digital signature is verified via the URL.verify function. URL.verify also takes the hmac_key, salt, and hash_vars arguments described above, and their values must match the values that were passed to the URL function when the digital signature was created in order to verify the URL.
	)

	#in memory sorting	
	sortby = request.vars['sortby']
	sortlist = []
	
	#Price
	pricechoices = ["bid_price-up", "bid_price-down"]; sortlist.extend(pricechoices)
	if sortby in pricechoices:
		reverse = False
		if sortby == "bid_price-down":
			reverse = True
		auction_request_offers = auction_request_offers.sort(lambda row: row.auction_request_offer.latest_bid(), reverse=reverse)
		
	#MSRP
	msrpchoices = ["retail_price-up", "retail_price-down"]; sortlist.extend(msrpchoices)
	if sortby in msrpchoices:
		reverse = False
		if sortby == "retail_price-down":
			reverse = True
		auction_request_offers = auction_request_offers.sort(lambda row: row.auction_request_offer.MSRP(), reverse=reverse)
		
	#Discount (%off)
	if not is_lease:
		discountchoices = ["discount-up", "discount-down"]; sortlist.extend(discountchoices)
		if sortby in discountchoices:
			reverse = False
			if sortby == "discount-down":
				reverse = True
			def msrp_discount(row):
				latest_bid = row.auction_request_offer.latest_bid()
				if latest_bid:
					return latest_bid.MSRP_discount()
				return 0
			auction_request_offers = auction_request_offers.sort(msrp_discount, reverse=reverse)
	
	#Distance
	distancechoices = ["distance-up", "distance-down"]; sortlist.extend(distancechoices)
	
	def distance_to_auction_request(row): #will reuse so keep outside of if statement #CACHE this using db.dealership_info.id and row.owner_id 
		#offer_owner_info = db(db.dealership_info.id == row.owner_id).select().last()
		return calcDist(row.dealership_info.latitude, row.dealership_info.longitude, auction_request.latitude, auction_request.longitude)
		
	if sortby in distancechoices:
		reverse = False
		if sortby == "distance-down":
			reverse = True
		auction_request_offers = auction_request_offers.sort(distance_to_auction_request, reverse=reverse) #returns new
		
	###########END SORTING#############
	"""
	response.view = 'generic.html'
	return dict(auction_request_info = auction_request_info['trim_data'])
	"""
	
	auction_request_offers_info = OD()
	#trim_data = json.loads(auction_request_info['trim_data'])
	for each_offer in auction_request_offers:
		offer_id = each_offer.auction_request_offer.id

		#options
		interior_options = []
		exterior_options = []
		mechanical_options = []
		package_options = []
		fees_options = []
		safety_options =[]
		
		for each_option in each_offer.auction_request_offer.interior_options:
			interior_options.append(getOption(trim_data, 'Interior', each_option))
		for each_option in each_offer.auction_request_offer.exterior_options:
			exterior_options.append(getOption(trim_data, 'Exterior', each_option))
		for each_option in each_offer.auction_request_offer.mechanical_options:
			mechanical_options.append(getOption(trim_data, 'Mechanical', each_option))
		for each_option in each_offer.auction_request_offer.package_options:
			package_options.append(getOption(trim_data, 'Package', each_option))
		for each_option in each_offer.auction_request_offer.safety_options:
			safety_options.append(getOption(trim_data, 'Safety', each_option))
		for each_option in each_offer.auction_request_offer.fees_options:
			fees_options.append(getOption(trim_data, 'Additional Fees', each_option))

		#pricing stuff
		bids = db((db.auction_request_offer_bid.owner_id == each_offer.auction_request_offer.owner_id) & (db.auction_request_offer_bid.auction_request == auction_request_id)).select()
		number_of_bids = len(bids)
		msrp = each_offer.auction_request_offer.MSRP()
		last_bid = bids.last() #already have bids objects no need to run twice with auction_request.last_bid()
		#last_bid_price = is_not_awaiting_offer = last_bid.bid if last_bid else None; is_awaiting_offer = not is_not_awaiting_offer
		last_bid_price = is_not_awaiting_offer = bid_is_final = final_bid_ends_on = final_bid_ended = None
		if last_bid:
			last_bid_price = is_not_awaiting_offer = last_bid.bid  #last bid means latest
			#final bid
			bid_is_final=final_bid_ends_on = last_bid.final_bid
			final_bid_ended = (request.now > final_bid_ends_on) if bid_is_final else None #DO NOT USE ALONE OR ONLY TEST TRUE
			bid_is_final_and_not_ended = bid_is_final and not final_bid_ended
		is_awaiting_offer = not is_not_awaiting_offer
		
		#favorite and winning checks
		is_winning_offer=False
		if a_winning_offer:
			is_winning_offer = a_winning_offer.auction_request_offer == offer_id
		is_favorite = None		
		if last_favorite_choice:
			if last_favorite_choice.auction_request_offer == offer_id: #see if the fave is this offer
				if bid_is_final: #DO NOT ALLOW FINAL OR EXPIRED BIDS
					is_favorite = last_favorite_choice = auction_request_info['favorite_price']= None
				else:
					is_favorite = True #all good
		
		#stuff to do if this offer is owned by viewing dealer
		is_my_offer = each_offer.auction_request_offer.owner_id == auth.user.id #i'm a dealer
		if is_my_offer and is_awaiting_offer and not auction_request_expired:
			response.message2 = "!Please make a bid now!"
		
		#mark all messages as read
		if is_my_offer:
			highest_message_in_this_offer = db(db.auction_request_offer_message.auction_request_offer == each_offer.auction_request_offer.id).select().last()
			if highest_message_in_this_offer:
				all_messages_read = db.unread_auction_messages.insert(highest_id = highest_message_in_this_offer.id, auction_request = auction_request_id, auction_request_offer = each_offer.auction_request_offer.id)
	
		#dealer stuff
		#this_dealer = db(db.auth_user.id == each_offer.owner_id ).select().first() or quickRaise("this_dealer not found!") #no need for further validation, assume all dealers here are real due to previous RBAC decorators and functions
		this_dealer_distance = distance_to_auction_request(each_offer)
		
		#color stuff
		this_color = color_names[each_offer.auction_request_offer.color]#since the pictures will have colors, no need to add a color square, so just map id to name
			
		#message stuff buyer
		my_message_form_buyer = ''
		has_message_from_buyer = None
		if is_owner:
			#message stuff
			if not a_winning_offer and not auction_request_expired: #do not allow any insertions for expired or winning
				db.auction_request_offer_message.auction_request_offer.default = offer_id #my_auction_request_offer_id meant for the dealer viewing this page, offer_id means the one in this loop 
				db.auction_request_offer_message.owner_id.default = auth.user.id
				db.auction_request_offer_message.auction_request.default = auction_request_id
				my_message_form_buyer = SQLFORM(db.auction_request_offer_message, _class="form-horizontal") #the message form to show if user is dealer
				if my_message_form_buyer.process(formname="buyer_message_form_%s"%offer_id).accepted: #The hidden field called "_formname" is generated by web2py as a name for the form, but the name can be overridden. This field is necessary to allow pages that contain and process multiple forms. web2py distinguishes the different submitted forms by their names. http://goo.gl/gTct7C
					response.message = '$Your message was submitted to the dealer.'
					your = auth.user
					_dealer = each_offer.auth_user
					scheduler.queue_task(
						send_alert_task,
						pargs=['email', _dealer.email, response.render('email_alert_template.html', dict(
							APPNAME=APP_NAME,
							NAME = _dealer.first_name.capitalize(), 
							MESSAGE =  XML("The buyer for a <i>%s</i> sent <b>%s</b> a message."%(car, 'you')),
							MESSAGE_TITLE = "You have a new message!",
							WHAT_NOW = "%s said:"%your.first_name.capitalize(),
							INSTRUCTIONS = my_message_form_buyer.vars.message,
							CLICK_HERE = "Go to auction",
							CLICK_HERE_URL = URL(args=request.args),
						)), "You have a new message about the %s at %s"%(car,APP_NAME)],
						#pvars={},
						#repeats = 10, # run 10 times
						period = 5, # run 5s after previous
						timeout = 30, # should take less than 30 seconds
					)
				elif my_message_form_buyer.errors:
					response.message = '!Your message had errors. Please fix!'
			#winner insert stuff
			winning_choice=int(request.vars['winner'] or 0)
			if each_offer.auction_request_offer['id'] == winning_choice and not a_winning_offer and not auction_ended_offer_expired:
				if is_not_awaiting_offer and not final_bid_ended:
					digits = 999999999999 #12 digits
					winner_code = str(random.randint(0, digits + 1)).zfill(len(str(digits))) #http://goo.gl/2IkFe #up to but not including 10 trillion. zero fill to 12 places. #ONE IN 9.999... TRILLION CHANCE FOR CONFLICT, SO NEED UNIQUE=TRUE TO CAUSE INTERNAL ERROR
					a_winning_offer = db.auction_request_winning_offer.insert(auction_request = auction_request_id, owner_id = is_owner, auction_request_offer = winning_choice, winner_code=winner_code)#insert new winner
					is_winning_offer=True #now make it true
					session.BROADCAST_WINNER_ALERT=True
					#session.BROADCAST_WINNER_ALERT = True
					#session.message = "$All dealers will be alerted about your new favorite!"
				else:
					session.message = "!Awaiting or expired bids cannot be chosen as a winner."
				redirect(URL(args=request.args)) #get rid of vars
			if a_winning_offer:
				response.message = "$You picked a winner! Click the green button below to view your certificate!" #keep as response.message so it always shows
			#blinking new message stuff
			highest_message_in_this_offer = db(db.auction_request_offer_message.auction_request_offer == offer_id).select().last()
			highest_message_id_that_owner_read = db(db.unread_auction_messages.auction_request == auction_request_id).select().last()
			if highest_message_id_that_owner_read and highest_message_in_this_offer:
				if highest_message_id_that_owner_read.highest_id <= highest_message_in_this_offer.id and highest_message_in_this_offer.owner_id!=auth.user_id :
					has_message_from_buyer =True
			
			#favorite insert stuff
			new_favorite_choice = int(request.vars['favorite'] or 0)
			if each_offer.auction_request_offer['id'] == new_favorite_choice and not a_winning_offer and not auction_ended_offer_expired:
				if last_favorite_choice and last_favorite_choice.not_until > request.now: #make sure is real favorite, make sure buyer can't constantly change favorite choice, make sure new favorite choice = old one, make sure auction hasn't expired, make sure the favorite is not an awaiting bid
					session.message = "!Dealers not alerted! You can't change your favorite until %s."%human(last_favorite_choice.not_until - request.now, precision=2, past_tense='{}', future_tense='{}')
				elif is_awaiting_offer or bid_is_final:
					session.message = "!You cannot choose an this bid as your favorite." #and change the message for the owner.
				elif final_bid_ended:
					session.message = "!You cannot choose an expired bid as your favorite." #and change the message for the owner.
				elif is_not_awaiting_offer and not final_bid_ended:
					last_favorite_choice = db.auction_request_favorite_choice.insert(auction_request = auction_request_id, owner_id = is_owner, auction_request_offer=new_favorite_choice) #no need for further testing because of previous if/else
					#send message
					session.BROADCAST_FAVORITE_ALERT = True
					session.message = "$All dealers will be alerted about your new favorite!"
				redirect(URL(args=request.args)) #get rid of vars
		#response messaging stuff
		if not is_owner and is_my_offer:#if you don't do this check, since each_offer loops for buyer as well, eventually is_winning_offer will be true and message below will show for buyer. do same with dealer via is_my_offer
			if auction_request_info['auction_completed']: 
				if is_winning_offer:
					response.message3 = "$You are the winner! We will connect you to the buyer when the buyer contacts us."
				elif not is_winning_offer and a_winning_offer: #make sure that there is a winner before making the following claim
					response.message3 = "@Buyer picked a winner, but you did not win. Sorry :-("
				elif not is_winning_offer and not a_winning_offer:
					response.message3 = "@Buyer did not pick a winner."
				
		#message stuff dealer, keep below SQLFORM so that new messages show on submission
		offer_messages = db(db.auction_request_offer_message.auction_request_offer == offer_id).select(orderby=~db.auction_request_offer_message.id)
		for each_message in offer_messages:
			if each_message.owner_id == auction_request.owner_id:
				each_message.is_auction_requester = True
			else: each_message.is_auction_requester = False

		#MESSAGE QUEUES #GOTTA DO IT LIKE THIS BECAUSE LET'S SAY OFFER[7] IS WINNER, ONLY OFFERS > 7 WILL GET ALERTED, SO IT'S NECESSARY TO RELOAD THE PAGE (STORING A COMMAND TO SEND ALERTS IN SESSION) SO THAT OFFERS > 0 WILL BE ALERTED.
		your = each_offer.auth_user
		if session.BROADCAST_FAVORITE_ALERT:
			_buyer = auction_request_user
			scheduler.queue_task(
				send_alert_task,
				pargs=['email', your.email, response.render('email_alert_template.html', dict(
					APPNAME=APP_NAME,
					NAME = your.first_name.capitalize(), 
					MESSAGE =  XML("The buyer for a <i>%s</i> picked <b>%s</b> as the favorite! So what now?"%(car, 'you' if is_favorite else 'another dealer')),
					MESSAGE_TITLE = "%s picked a new favorite!"%_buyer.first_name.capitalize(),
					WHAT_NOW = "Act fast!" if not is_favorite else 'Keep it up!',
					INSTRUCTIONS = "Make a better offer to convince the buyer that your vehicle is the best deal!" if not is_favorite else 'But stay alert for competing offers that may convince the buyer to have a change of mind!',
					CLICK_HERE = "Go to auction",
					CLICK_HERE_URL = URL(args=request.args),
				)), "New favorite was chosen for %s auction for a %s"%(APP_NAME,car)],
				#pvars={},
				#repeats = 10, # run 10 times
				period = 5, # run 5s after previous
				timeout = 30, # should take less than 30 seconds
			)
		if session.BROADCAST_WINNER_ALERT: 
			_buyer = auction_request_user
			scheduler.queue_task(
				send_alert_task,
				pargs=['email', your.email, response.render('email_alert_template.html', dict(
					APPNAME=APP_NAME,
					NAME = your.first_name.capitalize(), 
					MESSAGE =  XML("The buyer for a <i>%s</i> picked <b>%s</b> as the winner! So what now?"%(car, 'you' if is_winning_offer else 'another dealer')),
					MESSAGE_TITLE = "%s picked a winner!"%_buyer.first_name.capitalize(),
					WHAT_NOW = "Try again! You'll have better luck next time." if not is_winning_offer else "Wait for the buyer's call!",
					INSTRUCTIONS = "Tip: Look out for new buyer requests and bid quickly! Having attention of the buyer early on goes a long way." if not is_winning_offer else "The buyer will call you soon via our automatic validation system within your business hours!",
					CLICK_HERE = "Go to auction",
					CLICK_HERE_URL = URL(args=request.args),
				)), "A winner was chosen for %s auction for a %s"%(APP_NAME,car)],
				#pvars={},
				#repeats = 10, # run 10 times
				period = 5, # run 5s after previous
				timeout = 30, # should take less than 30 seconds
			)

		each_offer_dict = {
			'id' : offer_id,
			'has_message_from_buyer' : has_message_from_buyer,
			'is_winning_offer' :is_winning_offer,
			'is_my_offer': is_my_offer,
			'additional_info':each_offer.auction_request_offer['fineprint'],
			'about_us':each_offer.dealership_info['mission_statement'],
			'bid_is_final': bool(bid_is_final),
			'final_bid_ends_in_hours': (final_bid_ends_on - request.now).total_seconds()/3600 if bid_is_final else None,
			'final_bid_ended': final_bid_ended,
			'show_buy_now_btn': True if is_owner and not auction_request_info['auction_completed'] and not auction_request_info['bidding_ended'] and is_not_awaiting_offer and not a_winning_offer and bid_is_final_and_not_ended else False,
			'is_favorite': is_favorite,
			'offer_messages' : offer_messages,
			'my_message_form_dealer': my_message_form_dealer if my_auction_request_offer_id == offer_id else '', #add message form to this bid cell, only one needed hence why logic is outside this loop
			'my_message_form_buyer': my_message_form_buyer,
			'dealer_first_name':each_offer.auth_user.first_name,
			'dealer_area':'%s, %s'%(each_offer.dealership_info.city.capitalize(), each_offer.dealership_info.state),
			'dealer_id' : each_offer.auction_request_offer.owner_id,
			'show_winner_btn': True if is_owner and not auction_request_info['auction_completed'] and auction_request_info['bidding_ended'] and is_not_awaiting_offer and not a_winning_offer and not bid_is_final else False,
			'is_not_awaiting_offer':is_not_awaiting_offer,
			'is_awaiting_offer': not is_not_awaiting_offer,
			'last_bid_price' : last_bid_price,
			'dealer_rating':'N/A',
			'number_of_bids' : number_of_bids,
			'color' : this_color,
			'summary' : each_offer.auction_request_offer.summary,
			'interior_options' : interior_options,
			'exterior_options' : exterior_options,
			'mechanical_options' : mechanical_options,
			'package_options' : package_options,
			'fees_options' : fees_options,
			'safety_options':safety_options,
			#'exterior_image' : each_offer.auction_request_offer.exterior_image,
			#'interior_image' : each_offer.auction_request_offer.interior_image,
			'exterior_images' : each_offer.auction_request_offer.exterior_image_compressed,
			'interior_images' : each_offer.auction_request_offer.interior_image_compressed,
			#'front_image' : each_offer.auction_request_offer.front_image,
			'front_images' : each_offer.auction_request_offer.front_image_compressed,
			#'rear_image' : each_offer.auction_request_offer.rear_image,
			'rear_images' : each_offer.auction_request_offer.rear_image_compressed,
			#'tire_image' : each_offer.auction_request_offer.tire_image,
			'tire_images' : each_offer.auction_request_offer.tire_image_compressed,
			#'dashboard_image' : each_offer.auction_request_offer.dashboard_image,
			'dashboard_images' : each_offer.auction_request_offer.dashboard_image_compressed,
			#'passenger_image' : each_offer.auction_request_offer.passenger_image,
			'passenger_images' : each_offer.auction_request_offer.passenger_image_compressed,
			#'trunk_image' : each_offer.auction_request_offer.trunk_image,
			'trunk_images' : each_offer.auction_request_offer.trunk_image_compressed,
			#'underhood_image' : each_offer.auction_request_offer.underhood_image,
			'underhood_images' : each_offer.auction_request_offer.underhood_image_compressed,
			#'roof_image' : each_offer.auction_request_offer.roof_image,
			'roof_images' : each_offer.auction_request_offer.roof_image_compressed,
			#'other_image' : each_offer.auction_request_offer.other_image,
			'other_images' : each_offer.auction_request_offer.other_image_compressed,
			'msrp': '$%s'%msrp,
			'offer_distance_to_auction_request': '%0.2f'%this_dealer_distance,
			'msrp_discount_percent': '%0.2f%%'% (last_bid.MSRP_discount(each_offer) if last_bid else 0.00,) ,#(100-(last_bid_price)/float(msrp)*100) #http://goo.gl/2qp8lh #http://goo.gl/6ngwCd
			'msrp_discount_dollars':'$%s'%(int(msrp) - int(msrp if not last_bid_price else last_bid_price),),
		}
		#auction_request_offers_info.append(each_offer_dict)
		auction_request_offers_info.update({offer_id:each_offer_dict}) #FIXED used ordered dictionary to prevent duplicates from query appearing in auction
	
	#MARK ALL MESSAGES AS READ FOR USER. unread message stuff# keep below each offer to prevent new message icon from showing to owner when owner submits a message
	if is_owner:
		highest_message_in_this_auction = db(db.auction_request_offer_message.auction_request == auction_request_id).select().last()
		if highest_message_in_this_auction:
			marked_as_read = db.unread_auction_messages.insert(highest_id = highest_message_in_this_auction.id, auction_request = auction_request_id)
	
	auction_request_offers_info = auction_request_offers_info.values() #convert back to list to be compatible with current view
	
	session.BROADCAST_FAVORITE_ALERT = session.BROADCAST_WINNER_ALERT = False #make sure send alert
	
	#title stuff
	response.title="Auction"
	response.subtitle="for %s's new %s %s %s" % (auth.user.first_name, auction_request.year, auction_request.make, auction_request.model)
	return dict(auction_request_info=auction_request_info, auction_request_offers_info=auction_request_offers_info, is_dealer = is_dealer_with_offer, is_owner=is_owner, bid_form=bid_form, sortlist=sortlist, auction_is_completed=auction_is_completed, auction_request_expired=auction_request_expired, auction_ended_offer_expired=auction_ended_offer_expired, a_winning_offer=a_winning_offer, is_final_bid=is_final_bid)
	
@auth.requires_membership('dealers')
def my_auctions():
	def paginate(page, view): #adapted from web2py book
		"""	{{#in view}}
			{{for i,row in enumerate(rows):}}
				{{if i==items_per_page: break}}
				{{=row.value}}<br />
			{{pass}}
			{{#main}}
			{{if page:}}
				<a href="{{=URL(args=[page-1])}}">previous</a>
			{{pass}}

			{{if len(rows)>items_per_page:}}
				<a href="{{=URL(args=[page+1])}}">next</a>
			{{pass}}
		"""
		limits_list = [5,10,15,25,40,60]
		if page: page=int(page)
		else: page=0
		items_per_page=limits_list[0] if not view else int(view)
		limitby=(page*items_per_page,(page+1)*items_per_page+1)
		return dict(page=page,items_per_page=items_per_page, limitby=limitby, limits_list=limits_list)
	
	paging = paginate(request.args(0),request.vars['view'])
	
	sortby = request.vars['sortby']
	sorting = [["make-up", "make-down"], ["model-up", "model-down"], ["trim-up", "trim-down"], ["year-up", "year-down"], ["expiration-up", "expiration-down"]]
	orderby = ~db.auction_request.auction_expires
	#DB LEVEL SORTING 
	if sortby == "make-up":
		orderby = db.auction_request.make #this query causes referencing of two tables, so a join has occured
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
	if sortby == "expiration-up":
		orderby = ~db.auction_request.id
	if sortby == "expiration-down":
		orderby = db.auction_request.id #not using ID because expires can be changed by admin
	
	#OLD METHOD OF JOINS A#join =db.auction_request.on(db.auction_request_offer.auction_request==db.auction_request.id) #[db.auction_request.on(db.auction_request_offer.auction_request==db.auction_request.id)] #about joins http://goo.gl/iuQp6P #joins are much faster than sorting. Instead of two separate queries, join them and access their variables at once
	#in a join if a row from tableA doesn't match with a row from tableB, the join is skipped. To force this to happen you must use a left join. (use left instead of join argument) 

	show = request.vars['show']
	show_list = sorted(['won', 'lost', 'live', 'all'])
	query = (db.auction_request_offer.owner_id == auth.user_id) & (db.auction_request_offer.auction_request==db.auction_request.id) #must
	left=None
	if show == "won":
		query &= db.auction_request_winning_offer.auction_request_offer == db.auction_request_offer.id #can assume auction ended
	elif show == "lost": #lost also means expired and not won
		#query &= (db.auction_request_winning_offer.auction_request_offer != db.auction_request_offer.id) & (db.auction_request.offer_expires < request.now) #THIS WON'T WORK BECAUSE != WILL NOT CAUSE A JOIN, THEREFORE IT IS IGNORED AND BOTH WIN AND LOSE AUCTIONS WILL SHOW
		query &= (db.auction_request_winning_offer.auction_request_offer == None) & (db.auction_request.offer_expires < request.now) #for this to succeed a field cannot be None or incompatible with > == < #QUERY DOENS'T WORK WINNING OFFERS STILL SHOW
		left = db.auction_request_winning_offer.on(db.auction_request_offer.id == db.auction_request_winning_offer.auction_request_offer) #left join forces auction_request_winning_offer to be joined to query even though not all auction_request_offers have a corresponding auction_request_winning_offer, therefore it will be None instead and can be queried. # IF you intend to select on persons (whether they have things or not) and their things (if they have any), then you need to perform a LEFT OUTER JOIN. # 
	elif show == "live": #show is_active only
		query &= db.auction_request.auction_expires > request.now
	
	#OLD METHOD OF JOINS B#my_offers = db(query).select(join=join, orderby=orderby,limitby=paging['limitby']) #do a select where, join, and orderby all at once.
	my_offers = db(query).select(orderby=orderby,limitby=paging['limitby'], left=left) #do a select where, join, and orderby all at once.
	my_offer_summaries = []
	for each_offer in my_offers:
		#auction_request = db(db.auction_request.id == each_offer.auction_request).select().first() don't needed #make sure not abandoned or expired!
		#auction_request.expired()
		color_names = dict(map(lambda id,name: [id,name], each_offer.auction_request.color_preference, each_offer.auction_request.color_names)) #since the dealers color must've been in the choices in the auction request, it is safe to use the auction request data as a reference rather than the API
		#get this dealers last bid on this auction
		my_last_bid = each_offer.auction_request_offer.latest_bid()
		my_last_bid_price = '$%s'%my_last_bid.bid if my_last_bid else "No Bids!"
		my_last_bid_time = human(request.now-my_last_bid.created_on, precision=2, past_tense='{}', future_tense='{}') if my_last_bid else None
		#get the best price for this auction
		auction_best_bid = each_offer.auction_request.lowest_offer()
		auction_best_price = '$%s'%auction_best_bid.bid if auction_best_bid else "No Bids!"
		
		a_winning_offer = db(db.auction_request_winning_offer.auction_request == each_offer.auction_request.id).select().last()
		auction_is_completed = (a_winning_offer or each_offer.auction_request.offer_expired())
		ends_in_human=False
		if not auction_is_completed:
			ends_in_human = human(each_offer.auction_request.offer_expires - request.now, precision=3, past_tense='{}', future_tense='{}')
		
		has_unread_messages = False
		highest_message_for_this_offer = db(db.auction_request_offer_message.auction_request_offer == each_offer.auction_request_offer.id).select().last()
		my_highest_message_for_this_offer = db((db.unread_auction_messages.auction_request_offer == each_offer.auction_request_offer.id)&(db.unread_auction_messages.owner_id == auth.user_id)).select().last()
		if my_highest_message_for_this_offer and highest_message_for_this_offer: #maybe no messages
			if my_highest_message_for_this_offer.highest_id < highest_message_for_this_offer.id:
				has_unread_messages = True
				
		how_auction_ended = False
		if a_winning_offer and a_winning_offer['auction_request_offer'] in db((db.auction_request_offer.auction_request == each_offer.auction_request.id)&(db.auction_request_offer.owner_id == auth.user_id)).select(): #see if logged in dealer has a winning offer in this auction request. #OLD- Make sure you turn None into [] or in test will fail
			how_auction_ended = 'You are the winner!' 
		elif db(db.auction_request_winning_offer.auction_request == each_offer.auction_request.id).select():
			how_auction_ended = 'A winner was chosen'
		elif not ends_in_human: #that means time ran out so auction ended but no winner chosen
			how_auction_ended = "There are no winners"

		#each_request['how_auction_ended'] = how_auction_ended

		each_offer_dict = {
			'how_auction_ended':how_auction_ended,
			'has_unread_messages':has_unread_messages,
			'ends_in_human': ends_in_human if ends_in_human else "Auction ended",
			'year':each_offer.auction_request.year,
			'make':each_offer.auction_request.make,
			'model':each_offer.auction_request.model,
			'trim':each_offer.auction_request.trim_name,
			'vin':each_offer.auction_request_offer.vin_number,
			'color': color_names[each_offer.auction_request_offer.color],
			'offer_expires':each_offer.auction_request.offer_expires,
			'auction_best_price': auction_best_price,
			'my_last_bid_price': my_last_bid_price,
			'my_last_bid_time': my_last_bid_time,
			'auction_bids':each_offer.auction_request.number_of_bids(),
			'number_of_bids':each_offer.auction_request_offer.number_of_bids(),
			'auction_id':each_offer.auction_request.id,
			'my_offer_id':each_offer.auction_request_offer.id,
			'new_messages':0,
			'auction_url':URL('auction', args=[each_offer.auction_request.id]),
		}
		my_offer_summaries.append(each_offer_dict)
	#IN MEMORY SORTING is considered safe because we have limitby'd the offers to maximum of 60 
	return dict(my_offer_summaries = my_offer_summaries, sorting=sorting, show_list=show_list, **paging)
	
@auth.requires(URL.verify(request, hmac_key=str(auth.user_id), salt = str(session.salt), hash_vars=[request.args(0)])) #guarantees that user clicked from auction page if this passes
def winner():
	response.title="Certificate"
	#get valuable data and validate this page
	auction_validator = __auction_validator__()

	#get the color chart
	colors=auction_validator['color_names']
	
	#get the auction request
	auction_request=auction_validator['auction_request']
	
	#get the winner
	winner = auction_validator['a_winning_offer'] #must be True because this link would be active if there is a winner
	
	#details about trim
	trim_data=auction_validator['trim_data']
	#details about offer
	auction_request_offer = db(db.auction_request_offer.id == winner.auction_request_offer).select().last()
	#get the image urls
	list_of_image_types = ['exterior', 'interior', 'front', 'rear', 'tire', 'dashboard', 'passenger', 'trunk', 'underhood', 'roof', 'other']
	image_urls = {}
	for each_image_type in list_of_image_types:
		image_filename_pair = auction_request_offer['%s_image_compressed'%each_image_type]
		image_s = image_filename_pair[0] if image_filename_pair else None
		if image_s:
			image_urls.update({
				'%s_image_url'%each_image_type : URL('static', 'thumbnails/%s'%image_s)
			})
	#color stuff
	color = colors[auction_request_offer.color]
	#options stuff
	options =  {
		'Interior':auction_request_offer.interior_options,
		'Exterior':auction_request_offer.exterior_options,
		'Mechanical':auction_request_offer.mechanical_options,
		'Package':auction_request_offer.package_options,
		'Additional Fees':auction_request_offer.fees_options,
		'Safety':auction_request_offer.safety_options,
	}
	option_names = []
	for each_option_type in options:
		for each_option in options[each_option_type]:
			option_names.append(getOption(trim_data, each_option_type, each_option)['name'])
			
	#prices stuff
	last_bid = auction_request_offer.latest_bid()
	last_bid_price = ('$%s'%last_bid.bid) if not auction_validator['is_lease'] else ('$%s per month'%last_bid.bid)
	
	#vin number
	vin = auction_request_offer.vin_number
	
	#dealership info stuff
	dealer = db(db.auth_user.id == auction_request_offer.owner_id).select().last()
	dealership = db(db.dealership_info.owner_id == auction_request_offer.owner_id).select().last()
	
	#winner code for call verification and certificate
	winner_code=winner.winner_code
	#make the winner code look nice
	winner_code_spaced = ' '.join([winner_code[i:i+3] for i in range(0,len(winner_code),3)]) #http://goo.gl/0ra6oM
	
	#map stuff
	dmap = DecoratedMap()
	dmap.add_marker(AddressMarker('%s,%s,%s,%s'%(dealership.address_line_1, dealership.city, dealership.state, dealership.zip_code),label='D'))
	map_url = dmap.generate_url().replace('400x400', '600x400')
	
	#was call verification complete and buyer/dealer talked?
	contact_made=winner.contact_made
	
	return dict(
		auction_id = auction_validator['auction_request_id'], 
		winner_code_spaced=winner_code_spaced, 
		contact_made=contact_made, 
		winner_code=winner_code,
		auction_request_id = auction_request.id,
		auction_request = auction_request,
		trade_in = auction_request.trading_in,
		year=auction_request.year, 
		trim = auction_request.trim_name,
		make = auction_request.make, 
		model = auction_request.model, 
		color = color,
		option_names= option_names,
		dealer=dealer,
		dealership = dealership,
		is_lease = auction_validator['is_lease'],
		map_url=map_url,
		vin=vin,
		last_bid_price=last_bid_price,
		list_of_image_types=list_of_image_types,
		image_urls=image_urls,
	)
	
@auth.requires_membership('dealers')
def dealer_info():
	response.view = 'default/dealership_form.html'
	response.title=heading="Edit dealer's info"
	my_info =db(db.dealership_info.owner_id == auth.user_id).select().last()

	city_field = request.post_vars['city'] #make it look nice for auction page
	if city_field:
		request.post_vars['city'] = " ".join(map(lambda word: word.capitalize(), city_field.split(' ')))
		
	form=SQLFORM(db.dealership_info,my_info,_class="form-horizontal", hideerror=True)
	#4 ways to further validate: check post_vars (bad as nothing has been validated), on_validate and form.vars, custom validators, compute fields with required == True (will cause internal error instead)
	def make_sure_opening_and_closing_times_make_sense(form):
		x=-1; times_of_the_day_decimal=[]
		for n, each_time in enumerate(times_of_the_day): #times_of_the_day variable is from model_edmunds.py
			if n%4==0:
				x+=1
			times_of_the_day_decimal.append(float('%s.%s'%(x,each_time.split(':')[-1].split(' ')[0])))
		
		times_of_the_day_to_decimal = dict(zip(times_of_the_day,times_of_the_day_decimal))
		
		for each_day in days_of_the_week:
			submitted_opening_time = form.vars['%s_opening_time'%each_day]
			submitted_closing_time = form.vars['%s_closing_time'%each_day]
			if not (submitted_opening_time and submitted_closing_time): #if one is closed make both closed
				form.vars['%s_opening_time'%each_day] = form.vars['%s_closing_time'%each_day] = None
			elif times_of_the_day_to_decimal[submitted_opening_time] > times_of_the_day_to_decimal[submitted_closing_time]:
				submitted_opening_time = form.errors['%s_opening_time'%each_day] = "Opening time cannot be after closing time!"
				submitted_closing_time = form.errors['%s_closing_time'%each_day] = "Closing time cannot be before opening time!"
		
	if form.process(onvalidation=make_sure_opening_and_closing_times_make_sense).accepted:
		response.message="$Changes were saved!"
	return dict(heading=heading,form=form)