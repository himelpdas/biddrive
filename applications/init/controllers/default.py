# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

INDEX_MAX_RECENT_VEHICLES = 24

def index():
	"""
	example action using the internationalization operator T and flash
	rendered by views/default/index.html or views/generic.html

	if you need a simple wiki simply replace the two lines below with:
	return auth.wiki()
	"""

	year = datetime.date.today().year
	if request.args(0):
		year = request.args[0]
		
	#response.message2="@%s is currently under development"%APP_NAME
	
	def recently_sold():
		recent_requests = db((db.auction_request.id > 0) & (db.auction_request_winning_offer.id != None)).select(left = db.auction_request_winning_offer.on(db.auction_request_winning_offer.auction_request == db.auction_request.id), orderby=~db.auction_request.id, limitby=(0, 100)) #dont need the entire list, so limitby
		
		if len(recent_requests) < 12: #show unsold vehicles if sold vehicles too few
			recent_requests = db((db.auction_request.id > 0) & (db.auction_request_winning_offer.id == None)).select(left = db.auction_request_winning_offer.on(db.auction_request_winning_offer.auction_request == db.auction_request.id), orderby=~db.auction_request.id, limitby=(0, 100))
		
		recent_vehicles_json = set([])
			
		for each_request in recent_requests:
			first_image=None
			try:
				model_photos = FIND_PHOTOS_BY_STYLE_ID(each_request.auction_request.trim)
				photo = model_photos[0]['photoSrcs'][-1] #get any photo
				for each_photo in model_photos[0]['photoSrcs']:
					if each_photo.split('.')[-2].split('_')[-1] == '815':  #but change to proper ratio if found
						photo = each_photo
				first_image = 'http://media.ed.edmunds-media.com'+photo  #errors will not be cached! :)
			except Exception, e:
				logger.exception(e)
				pass
			if first_image: #only show if image available
				recent_vehicles_json.add(json.dumps(dict( #must dump to json as set does not support dicts
					image = first_image,
					year = each_request.auction_request.year, 
					make = each_request.auction_request.make ,
					make_name = each_request.auction_request.make_name ,
					model = each_request.auction_request.model,
					model_name = each_request.auction_request.model_name,
					body = each_request.auction_request.body,
				)))
			
			
		recent_vehicles = map(lambda each: json.loads(each),recent_vehicles_json)[:INDEX_MAX_RECENT_VEHICLES] #turn back to dict

		recent_vehicles_bodies = set(map(lambda each: each['body'],recent_vehicles))
		
		return recent_vehicles, recent_vehicles_bodies
	
	recent_data = cache.disk('index_recently_sold', recently_sold, time_expire=60*15 )
	
	return dict(brands_list=GET_BRANDS_LIST(year), cars = recent_data[0], bodies=recent_data[1]) #cars=GET_FEATURED_CARS())

'''
def index_old():
	"""
	example action using the internationalization operator T and flash
	rendered by views/default/index.html or views/generic.html

	if you need a simple wiki simply replace the two lines below with:
	return auth.wiki()
	"""

	year = datetime.date.today().year
	if request.args(0):
		year = request.args[0]

	response.message2="!%s is currently under development"%APP_NAME

	return dict(brands_list=GET_BRANDS_LIST(year))
'''

@auth.requires(not auth.has_membership(role='dealers'), requires_login=False) #allowing two roles in the auction page will lead to weird results
@auth.requires(URL.verify(request, hmac_key = HMAC_KEY, salt = str(session.salt), hash_vars=[request.args(0),request.args(1),request.args(2)]),  requires_login=False)
def request_by_make():
	year = request.args[0] 
	make = request.args[1] #VALIDATE #done via digitally signed url
	model = request.args[2]
	db.auction_request.year.default=year
	db.auction_request.make.default=make
	db.auction_request.model.default=model
	#db.auction_request.created_on.default=request.now #moved to model
	
	model_styles = GET_STYLES_BY_MAKE_MODEL_YEAR(make, model, year, enforce_years = True)
	
	make_name = model_styles[0]['make']['name']
	model_name = model_styles[0]['model']['name']
	
	if not model_styles:
		session.message='Invalid Year!'
		redirect(URL('index.html'))
	
	db.auction_request.temp_id.default=session.guest_temp_id=repr(uuid.uuid4()) #needed to save non logged in users form submission
	
	trims = []
	for each_style in model_styles:
		trims.append(
			[each_style['id'], each_style['name']]
		)	
	trims.sort()
	db.auction_request.trim.requires = IS_IN_SET(trims, zero=None)
	
	color_codes = []
	option_codes= [] #needed for SQLFORM to create proper IS_IN_SET widget
	if not request.post_vars: #if get: needed to prevent use of incorrect color_codes
		session.color_codes = []
		session.option_codes = []
	if session.color_codes: #generated by ajax/colors
		color_codes = session.color_codes #this is to update IS_IN_SET to the changes returned by the ajax function (stored in session so it can be used cross site), which is called every time user changes trim choices field
	if session.option_codes:
		option_codes = session.option_codes
	
	#making sure child-inputs are enforced if parent-inputs are selected
	if request.post_vars['funding_source'] != 'cash':  #cash 
		db.auction_request.expected_down_payment.requires = EXPECTED_DOWN_PMT_REQUIRES
	else: #is paying in full
		request.post_vars['financing'] = None #so erase other crap
		request.post_vars['expected_down_payment'] = None
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
	
	if request.post_vars['funding_source'] == 'lease': #lease
		db.auction_request.lease_term.requires = LEASE_TERM_REQUIRES #force a choice if taking a lease
		db.auction_request.lease_mileage.requires = LEASE_MILEAGE_REQUIRES #TODO MAKE LESS DRY
		request.post_vars['financing'] = None #disable others
		
	if request.post_vars['funding_source'] == 'loan': #loan
		db.auction_request.financing.requires = FINANCING_REQUIRES
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
		
	if request.post_vars['trading_in']:
		db.auction_request.describe_trade_in.requires = IS_NOT_EMPTY()
	else:
		request.post_vars['describe_trade_in'] = None 
		
	db.auction_request.colors.requires = [IS_IN_SET( map(lambda each_color: [each_color[0],  each_color[1]], color_codes), multiple=True)] #OLD [IS_IN_SET(color_codes, multiple=True, zero=None), IS_NOT_EMPTY(error_message='pick at least one color')]
	db.auction_request.colors.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	#db.auction_request.options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	db.auction_request.options.requires = [IS_IN_SET( map(lambda each_option: [each_option[0],  each_option[1]], option_codes), multiple=True)] #requires needs [id, name]'s
	db.auction_request.options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	form = SQLFORM(db.auction_request, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY

	"""
	#moved to forms onvalidation, instead of using unvaidated post_vars! http://goo.gl/00Urs6
	#form dependant values
	if request.post_vars: #doesn't matter if values are un-validated here, since arguments here used the same variables in the forms, if a variable is weird from create won't succeed.
		trim_data = GET_STYLES_BY_MAKE_MODEL_YEAR_STYLE_ID(make,model,year,request.post_vars.trim) 
		db.auction_request.trim_data.default = json.dumps(trim_data)
		db.auction_request.trim_name.default = trim_data['name'] 
		db.auction_request.color_names.default = [ each_color['name'] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.colors ] #make a list of color names based on ids in colors field
		db.auction_request.color_simple_names.default = [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.colors ]
	"""

	if form.process(keepvalues=True, onvalidation=lambda form:VALIDATE_VEHICLE(form, make, model, year, 'auction_request'), hideerror=True, message_onfailure="@Errors in form. Please check it out.").accepted: #hideerror = True to hide default error elements #change error message via form.custom
		pre_auction_id = [form.vars.id]
		if request.post_vars['password'] or request.post_vars['email']: #can't use form.vars for some reason, probably because process removed non SQLFORM vars like email and password
			if not auth.login_bare(request.post_vars['email'],request.post_vars['password']): #will login automatically if true
				session.message = '!Your request was submitted, but your email or password was incorrect! Please try again.' 
		else: #user didn't login so force registration, use "force_register" arg in URL redirect to modify default behaviour in user.html
			pre_auction_id.append('force_register')
		auth.add_group('dealers_in_auction_%s'%form.vars.id, 'The group of dealers that entered a particular auction by agreeing to its terms and charges.')
		auth.add_group('owner_of_auction_%s'%form.vars.id, 'The owner of a particular auction who made the initial request.')
		redirect(
			URL('default','pre_auction', args=pre_auction_id) #http://goo.gl/twPSTK
		)
		
	response.title="Request an auction"
	response.subtitle="for a %s %s %s."%(year, make_name, model_name)

	return dict(model_styles=model_styles, trims=trims, form=form, year=year, make=make, model=model, make_name=make_name, model_name=model_name)
	
@auth.requires(not auth.has_membership(role='dealers')) #make sure dealers can't get anonymous auction requests attached to their name
@auth.requires(request.args(0)) #login true
def pre_auction():
	auction_request_id = request.args[0]
	guest_auction_requests = db((db.auction_request.owner_id == None) & (db.auction_request.temp_id == session.guest_temp_id)).select() #guest temp id is unique for each auction request, so it's safe to query up with this value... but make sure it's empty so that update doesn't keep running on this function
	for each_guest_auction_request in guest_auction_requests:
		each_guest_auction_request.update_record(owner_id=auth.user_id) #link guest id to user id
	auth.add_membership('owner_of_auction_%s'%auction_request_id, auth.user_id)
	####alert dealers nearby####
	auction_request = db((db.auction_request.id == auction_request_id)&(db.auth_user.id == db.auction_request.owner_id)#join auth_user, make sure he owns this auction
		&(db.auth_user.id == auth.user_id) #temp id should have been attached to a real auth_user by now
	).select().last()
	all_specialty_dealerships = db((db.dealership_info.verification == "approved")&(db.dealership_info.specialty.contains(auction_request.auction_request.make))&(db.auth_user.id == db.dealership_info.owner_id)).select()
	#remove dealerships not in range
	all_specialty_dealerships_in_range_of_auction_request = all_specialty_dealerships.exclude(lambda row: auction_request.auction_request['radius'] >= calcDist(row.dealership_info.latitude, row.dealership_info.longitude, auction_request.auction_request.latitude, auction_request.auction_request.longitude) )
	for each_dealership in all_specialty_dealerships_in_range_of_auction_request:
		SEND_ALERT_TO_QUEUE( 
			USER=each_dealership.auth_user,
			MESSAGE_TEMPLATE= "DEALER_on_new_request",
			**dict(app=APP_NAME, 
				she="%s %s."%(auction_request.auth_user.first_name.capitalize(), auction_request.auth_user.last_name[:1].capitalize() ), 
				year=auction_request.auction_request.year, make=auction_request.auction_request.make_name, model=auction_request.auction_request.model_name, url=URL('dealer', 'auction_requests', host=True, scheme=True), )
		)
	#send email to owner reminding him he created an auction
	SEND_ALERT_TO_QUEUE(
		USER=auth.user,
		MESSAGE_TEMPLATE= "BUYER_on_new_request",
		**dict(app=APP_NAME, year=auction_request.auction_request.year, make=auction_request.auction_request.make_name, model=auction_request.auction_request.model_name, mile = auction_request.auction_request.radius, zip=auction_request.auction_request.zip_code, url=URL('dealer', 'auction', args=[auction_request_id], host=True, scheme=True), )
	)
	session.message="$Request completed! Dealers nearby were notified."
	redirect(
		URL('dealer','auction.html', args=auction_request_id) #http://goo.gl/twPSTK
	)

def how_it_works():
	return dict()
 
def hello_dealers():
 	return dict()
 
@auth.requires_login()
def dealership_form():
	#db.dealership_info.created_on.default=request.now #moved to model thanks to update argument
	
	city_field = request.post_vars['city']
	if city_field:
		request.post_vars['city'] = " ".join(map(lambda word: word.capitalize(), city_field.split(' ')))
	
	form = SQLFORM(db.dealership_info, _class="form-horizontal", hideerror=True)
	
	if not db(db.dealership_info.owner_id == auth.user_id).select():
		if form.process().accepted:
			#email alert to admin
			db.credits.insert(owner_id=auth.user_id, credits = INTRODUCTORY_CREDITS) #create a record for this dealers credit balance
			db.credits_history.insert(changed = INTRODUCTORY_CREDITS, owner_id=auth.user_id, reason="Welcome :)")
			response.message = '$Form accepted. Please wait a few days for our response!'
	elif AUTH_DEALER:
		redirect(URL('dealer','auction_requests'))
	else:
		response.message = "!You already submitted a request! Please contact us if you've waited longer than 3 weeks."
	
	response.title = 'Become our partner!'
	response.subtitle = 'Sell your cars on our website'
	return dict(form = form, heading="Become a %s partnering dealer"%APP_NAME)
	
def faq():
	return dict()

@auth.requires_login()
def after_login_portal():
	session.message = '!<i class="fa fa-fw fa-thumbs-up"></i> Successfully logged in. Welcome <b>%s</b>!'%auth.user.first_name.capitalize()
	if AUTH_DEALER:
		redirect(URL('dealer', 'auction_requests'))
	elif AUTH_ADMIN:
		redirect(URL('admin', 'dealership_requests'))
	else:
		redirect(URL('default', 'auction_history'))
	
@auth.requires(not auth.has_membership(role='dealers'))
def auction_history():
	my_auctions = db(db.auction_request.owner_id == auth.user_id).select(orderby=~db.auction_request.id)
	response.title = heading = "Auction history for %s" % auth.user.first_name.capitalize()
	for each_request in my_auctions:
		#####unread message logic#####
		has_unread_messages = False #buyer is interested in all messages from all dealers, rather than in dealers case where he is interested in only his own offer's messages. that's why this scans through auction_requests
		highest_message_for_this_auction = db(db.auction_request_offer_message.auction_request == each_request.id).select().last()
		my_highest_message_for_this_auction = db((db.auction_request_unread_messages.auction_request == each_request.id)&(db.auction_request_unread_messages.owner_id == auth.user_id)).select().last()
		if my_highest_message_for_this_auction and highest_message_for_this_auction: #maybe no messages
			if my_highest_message_for_this_auction.highest_id < highest_message_for_this_auction.id:
				has_unread_messages = True
		each_request['has_unread_messages'] = has_unread_messages

		#auction URL
		each_request['auction_url']=URL('dealer','auction', args=[each_request.id])

		#colors logic
		trim_data= json.loads(each_request['trim_data'])
		each_request['color_names_and_codes'] = []

		#last bid logic
		last_bid = db(db.auction_request_offer_bid.auction_request == each_request.id).select().last()
		last_bid_price = "${:,}".format(last_bid.bid) if last_bid else "No Bids!"
		each_request['last_bid_price'] = last_bid_price
		last_bid_time = "%s ago"%human(request.now-last_bid.created_on, precision=2, past_tense='{}', future_tense='{}') if last_bid else "--"
		each_request['last_bid_time'] = last_bid_time

		#how auction ended logic
		a_winning_offer = db(db.auction_request_winning_offer.auction_request == each_request.id).select().last()
		auction_is_completed = (a_winning_offer or each_request.offer_expired())
		how_auction_ended = XML("<i class='fa fa-fw fa-clock-o'></i> Awaiting your winner")
		if db(db.auction_request_winning_offer.auction_request == each_request['id']).select().last():
			how_auction_ended = XML("<i class='fa fa-fw fa-trophy'></i> You selected a winner!")
		elif auction_is_completed: #that means time ran out so auction ended but no winner chosen
			how_auction_ended = XML("<i class='fa fa-fw fa-thumbs-down'></i> You didn't pick a winner")
		each_request['how_auction_ended'] = how_auction_ended
		
		#time remaining logic
		bidding_has_ended = each_request.auction_expired()
		ends_in_human="Auction ended"
		if not bidding_has_ended:
			time_delta_remaining = each_request.auction_expires - request.now
			ends_in_human = human(time_delta_remaining, precision=3, past_tense='{}', future_tense='{}')
			#print ends_in_human, time_delta_remaining.total_seconds()
			ends_in_human = XML("<span class='%s'>%s</span>"%("text-danger" if (not auction_is_completed and time_delta_remaining.total_seconds() < 21600) else '',ends_in_human))
		each_request['ends_in_human'] = ends_in_human
		#color stuff done in view
	return dict(my_auctions=my_auctions,heading =heading)

def user():
	"""
	exposes:
	http://..../[app]/default/user/login
	http://..../[app]/default/user/logout
	http://..../[app]/default/user/register
	http://..../[app]/default/user/profile
	http://..../[app]/default/user/retrieve_password
	http://..../[app]/default/user/change_password
	http://..../[app]/default/user/manage_users (requires membership in
	use @auth.requires_login()
		@auth.requires_membership('group name')
		@auth.requires_permission('read','table name',record_id)
	to decorate functions that need access control
	"""
	form = auth()
	user_arg = request.args(0)
	if user_arg == "register":
		response.title = "Join us"
	if user_arg == "login":
		response.title = "Welcome back"
	if user_arg == "request_reset_password":
		response.title = "Forgot something?"
	if user_arg == "reset_password":
		response.title = "Create a new password"
		#form = auth.reset_password()
		#response.view = 'generic.html'
	if user_arg=="profile":
		response.title='Hey, %s!' % auth.user.first_name
		

	return dict(form=form)

@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
	"""
	http://..../[app]/default/data/tables
	http://..../[app]/default/data/create/[table]
	http://..../[app]/default/data/read/[table]/[id]
	http://..../[app]/default/data/update/[table]/[id]
	http://..../[app]/default/data/delete/[table]/[id]
	http://..../[app]/default/data/select/[table]
	http://..../[app]/default/data/search/[table]
	but URLs must be signed, i.e. linked with
	  A('table',_href=URL('data/tables',user_signature=True))
	or with the signed load operator
	  LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
	"""
	return dict(form=crud())

def about():
	return dict()

def careers():
	return dict()

def contact():
	return dict()

def sitemap():
	return dict()

def car_chooser():
	"""
	example action using the internationalization operator T and flash
	rendered by views/default/index.html or views/generic.html

	if you need a simple wiki simply replace the two lines below with:
	return auth.wiki()
	"""

	year = datetime.date.today().year
	if request.args(0):
		year = request.args[0]

	return dict(brands_list=GET_BRANDS_LIST(year))