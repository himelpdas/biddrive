# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

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
		
	response.message2="!%s is currently under development"%APP_NAME
		
	return dict(brands_list=getBrandsList(year))

@auth.requires(not auth.has_membership(role='dealers'), requires_login=False) #allowing two roles in the auction page will lead to weird results
@auth.requires(URL.verify(request, hmac_key = str(session.salt), hash_vars=[request.args(0),request.args(1),request.args(2)]),  requires_login=False)
def request_by_make():
	year = request.args[0] 
	make = request.args[1] #VALIDATE #done via digitally signed url
	model = request.args[2]
	db.auction_request.year.default=year
	db.auction_request.make.default=make
	db.auction_request.model.default=model
	#db.auction_request.created_on.default=request.now #moved to model
	
	model_styles = getStylesByMakeModelYear(make, model, year)
	
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
	
	style_color_codes = option_codes= [] #needed for SQLFORM to create proper IS_IN_SET widget
	if not request.post_vars: #if get: needed to prevent use of incorrect style_color_codes
		session.style_color_codes = []
		session.option_codes
	if session.style_color_codes: #generated by ajax/exterior_colors
		style_color_codes = session.style_color_codes #this is to update IS_IN_SET to the changes returned by the ajax function (stored in session so it can be used cross site), which is called every time user changes trim choices field
		option_codes = session.option_codes
	
	#making sure child-inputs are enforced if parent-inputs are selected
	if request.post_vars['funding_source'] != 'cash':  #cash 
		db.auction_request.expected_down_payment.requires = expected_down_payment_requires
	else: #is paying in full
		request.post_vars['financing'] = None #so erase other crap
		request.post_vars['expected_down_payment'] = None
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
	
	if request.post_vars['funding_source'] == 'lease': #lease
		db.auction_request.lease_term.requires = lease_term_requires #force a choice if taking a lease
		db.auction_request.lease_mileage.requires = lease_mileage_requires #TODO MAKE LESS DRY
		request.post_vars['financing'] = None #disable others
		
	if request.post_vars['funding_source'] == 'loan': #loan
		db.auction_request.financing.requires = financing_requires
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
		
	if request.post_vars['trading_in']:
		db.auction_request.describe_trade_in.requires = IS_NOT_EMPTY()
	else:
		request.post_vars['describe_trade_in'] = None 
		
	db.auction_request.exterior_colors.requires = [IS_IN_SET(style_color_codes, multiple=True, zero=None), IS_NOT_EMPTY(error_message='pick at least one color')]
	db.auction_request.exterior_colors.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	#db.auction_request.must_haves.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	db.auction_request.must_haves.requires = [IS_IN_SET(option_codes, multiple=True)]
	db.auction_request.must_haves.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	form = SQLFORM(db.auction_request, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY

	"""
	#moved to forms onvalidation, instead of using unvaidated post_vars! http://goo.gl/00Urs6
	#form dependant values
	if request.post_vars: #doesn't matter if values are un-validated here, since arguments here used the same variables in the forms, if a variable is weird from create won't succeed.
		trim_data = getStyleByMakeModelYearStyleID(make,model,year,request.post_vars.trim) 
		db.auction_request.trim_data.default = json.dumps(trim_data)
		db.auction_request.trim_name.default = trim_data['name'] 
		db.auction_request.color_names.default = [ each_color['name'] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.exterior_colors ] #make a list of color names based on ids in exterior_colors field
		db.auction_request.simple_exterior_color_names.default = [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.exterior_colors ]
	"""
	
	#make model names
	db.auction_request.make_name.default = make_name = model_styles[0]['make']['name']
	db.auction_request.model_name.default = model_name = model_styles[0]['model']['name']
	#
	def computations(form): #these defaults need form vars, so must do it in onvalidation
		trim_data = getStyleByMakeModelYearStyleID(make,model,year,form.vars.trim)
		colorChipsErrorFix(trim_data['colors']) #make sure all db entries are safe. protect trim_data from this error
		db.auction_request.trim_data.default = json.dumps(trim_data)
		db.auction_request.trim_name.default = trim_data['name'] 
		db.auction_request.color_names.default = [ each_color['name'] for each_color in trim_data['colors'] [[each['category']=='Exterior' for each in trim_data['colors']].index(True)] ['options'] if each_color['id'] in form.vars.exterior_colors ] #make a list of color names based on ids in exterior_colors field
		db.auction_request.simple_exterior_color_names.default = [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in trim_data['colors'] [[each['category']=='Exterior' for each in trim_data['colors']].index(True)] ['options'] if each_color['id'] in form.vars.exterior_colors ]
		
	if form.process(onvalidation=computations, hideerror=True, message_onfailure="@Errors in form. Please check it out.").accepted: #hideerror = True to hide default error elements #change error message via form.custom
		guest_msg = '! Register or login to view it.'
		msg_color = '$'
		pre_auction_id = [form.vars.id]
		if request.post_vars['password'] or request.post_vars['email']: #can't use form.vars for some reason, probably because process removed non SQLFORM vars like email and password
			if not auth.login_bare(request.post_vars['email'],request.post_vars['password']): #will login automatically if true
				guest_msg = ', but your email or password was incorrect. Try again!' 
				msg_color = "!"
		else: #user didn't login so force registration, use "force_register" arg in URL redirect to modify default behaviour in user.html
			pre_auction_id.append('force_register')
		if auth.user_id:
			guest_msg='! Dealers have been notified.' #user is logged in no need for guest msg
		session.message = msg_color + 'Auction submitted%s' % guest_msg
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
		if "new_request" in each_dealership.auth_user.alerts:
			scheduler.queue_task(
				send_alert_task,
				pargs=['email', each_dealership.auth_user.email, response.render('email_alert_template.html', 
					dict(
						APPNAME=APP_NAME,
						NAME = each_dealership.auth_user.first_name.capitalize(), 
						MESSAGE =  XML("There is a new request for a <i>%s <b>%s</b> %s</i> near your area."%(auction_request.auction_request.year, auction_request.auction_request.make_name, auction_request.auction_request.model_name ) ),
						MESSAGE_TITLE = "%s wants a new %s!"%("%s %s."%(auction_request.auth_user.first_name.capitalize(), auction_request.auth_user.last_name[:1].capitalize()), auction_request.auction_request.make_name),
						WHAT_NOW = "Hurry! Other nearby dealers %s have been alerted as well."%auction_request.auction_request.make_name,
						INSTRUCTIONS = "Submit your %s vehicle now to grab the buyer's attention first!"%auction_request.auction_request.make_name,
						CLICK_HERE = "View auction requests",
						CLICK_HERE_URL = URL('dealer', 'auction_requests', host=True, scheme=True),
					)
				), 
					"%s: New request for a %s %s %s near your area."%(APP_NAME, auction_request.auction_request.year, auction_request.auction_request.make_name, auction_request.auction_request.model_name),
				],
				retry_failed = 10,
				period = 3, # run 5s after previous
				timeout = 30, # should take less than 30 seconds
			)
	########
	#send email to owner reminding him he created an auction
	if "new_request" in auth.user.alerts:
		scheduler.queue_task(
			send_alert_task,
			pargs=['email', auth.user.email, response.render('email_alert_template.html', 
				dict(
					APPNAME=APP_NAME,
					NAME = auth.user.first_name.capitalize(), 
					MESSAGE_TITLE =  XML("You requested a <i>{year} <b>{make}</b> {model}</i>.".format(year=auction_request.auction_request.year, make=auction_request.auction_request.make_name, model=auction_request.auction_request.model_name ) ),
					MESSAGE = "Within a {mile} mile radius of {zip}.".format(mile = auction_request.auction_request.radius, zip=auction_request.auction_request.zip_code),
					WHAT_NOW = "Stay tuned for offers!",
					INSTRUCTIONS = "Dealers near you have been alerted about your request.",
					CLICK_HERE = "Go to auction!",
					CLICK_HERE_URL = URL('default', 'auction', args=[auction_request_id], host=True, scheme=True),
				)
			), 
				"{app}: You requested a {year} {make} {model} near you!".format(app=APP_NAME, year=auction_request.auction_request.year, make=auction_request.auction_request.make_name, model=auction_request.auction_request.model_name),
			],
			retry_failed = 10,
			period = 3, # run 5s after previous
			timeout = 30, # should take less than 30 seconds
		)
	redirect(
		URL('dealer','auction.html', args=auction_request_id) #http://goo.gl/twPSTK
	)
	
@auth.requires_login()
def my_auctions(): #FIX GUEST AUCTIONS
	guest_auction_requests = db((db.auction_request.owner_id == None) & (db.auction_request.temp_id == session.guest_temp_id)).select()
	for each_guest_auction_request in guest_auction_requests:
		each_guest_auction_request.update_record(owner_id=auth.user_id) #link guest id to user id
	
	my_auctions = db(db.auction_request.owner_id == auth.user_id).select()
	response.title="My auctions"
	return dict(guest_temp_id=session.guest_temp_id, my_auctions=my_auctions)

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
			db.credits.insert(owner=auth.user_id, credits = INTRODUCTORY_CREDITS) #create a record for this dealers credit balance
			db.credits_history.insert(change= INTRODUCTORY_CREDITS, owner_id=auth.user_id, reason="Welcome :)")
			response.message = '$Form accepted. Please wait a few days for our response!'
	else:
		response.message = "!You already submitted a request! Please contact us if you've waited longer than 3 weeks."
	
	response.title = 'Become our partner!'
	response.subtitle = 'Sell your cars on our website'
	return dict(form = form, heading="Become a %s partnering dealer"%APP_NAME)
	
def faq():
	return dict()

@auth.requires_login()
def after_login_portal():
	session.message = "!Successfully logged in. Welcome %s!"%auth.user.first_name.capitalize()
	if AUTH_DEALER:
		redirect(URL('dealer', 'auction_requests'))
	if AUTH_ADMIN:
		redirect(URL('admin', 'dealership_requests'))
	redirect(URL('index'))
	
@auth.requires(not auth.has_membership(role='dealers'))
def auction_history():
	my_auctions = db(db.auction_request.owner_id == auth.user_id).select(orderby=~db.auction_request.id)
	response.title = heading = "Auction history for %s" % auth.user.first_name.capitalize()
	for each_request in my_auctions:
		#####unread message logic#####
		has_unread_messages = False #buyer is interested in all messages from all dealers, rather than in dealers case where he is interested in only his own offer's messages. that's why this scans through auction_requests
		highest_message_for_this_auction = db(db.auction_request_offer_message.auction_request == each_request.id).select().last()
		my_highest_message_for_this_auction = db((db.unread_auction_messages.auction_request == each_request.id)&(db.unread_auction_messages.owner_id == auth.user_id)).select().last()
		if my_highest_message_for_this_auction and highest_message_for_this_auction: #maybe no messages
			if my_highest_message_for_this_auction.highest_id < highest_message_for_this_auction.id:
				has_unread_messages = True
		each_request['has_unread_messages'] = has_unread_messages
		#####ended logic#####
		a_winning_offer = db(db.auction_request_winning_offer.auction_request == each_request.id).select().last()
		auction_is_completed = (a_winning_offer or each_request.offer_expired())
		ends_in_human=False
		if not auction_is_completed:
			ends_in_human = human(each_request.offer_expires - request.now, precision=3, past_tense='{}', future_tense='{}')
		#ends_in_human = ends_in_human if ends_in_human else "Auction ended" #COMMENT OUT IF HANDLED IN VIEW
		each_request['ends_in_human'] = ends_in_human
		each_request['auction_url']=URL('dealer','auction', args=[each_request.id])
		#colors logic
		trim_data= json.loads(each_request['trim_data'])
		each_request['color_names_and_codes'] = []
		#last bid logic
		last_bid = db(db.auction_request_offer_bid.auction_request == each_request.id).select().last()
		last_bid_price = '$%s'%last_bid.bid if last_bid else "No Bids!"
		each_request['last_bid_price'] = last_bid_price
		last_bid_time = human(request.now-last_bid.created_on, precision=2, past_tense='{}', future_tense='{}') if last_bid else None
		each_request['last_bid_time'] = last_bid_time
		#how auction ended
		how_auction_ended = False
		if db(db.auction_request_winning_offer.auction_request == each_request['id']).select().last():
			how_auction_ended = 'You picked a winner!' 
		elif not ends_in_human: #that means time ran out so auction ended but no winner chosen
			how_auction_ended = "No winner was chosen"
		each_request['how_auction_ended'] = how_auction_ended
		#color stuff
		for each_color in each_request['color_names']:
			each_request['color_names_and_codes'].append([each_color, getColorHexByNameOrID(each_color, trim_data)])
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
