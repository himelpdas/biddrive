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

	bg_images = db(db.index_bg_image.id > 0).select()
	hero_images = db(db.index_hero_image.id > 0).select()
	
	year = datetime.date.today().year
	if request.args(0):
		year = request.args[0]
		
	return dict(brands_list=getBrandsList(year), bg_images=bg_images, hero_images=hero_images)

@auth.requires(not auth.has_membership(role='dealers'), requires_login=False) #allowing two roles in the auction page will lead to weird results
def request_by_make():
	if not request.args:
		session.message='Invalid request!'
		redirect(URL('index.html'))
		
	year = request.args[0] 
	make = request.args[1] #VALIDATE
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
	db.auction_request.trim_choices.requires = IS_IN_SET(trims, zero=None)
	
	style_color_codes = [] #needed for SQLFORM to create proper IS_IN_SET widget
	if not request.post_vars: #if get: needed to prevent use of incorrect style_color_codes
		session.style_color_codes = None
	if session.style_color_codes: #generated by ajax/color_preference
		style_color_codes = session.style_color_codes #this is to update IS_IN_SET to the changes returned by the ajax function (stored in session so it can be used cross site), which is called every time user changes trim choices field

	
	#making sure child-inputs are enforced if parent-inputs are selected
	if request.post_vars['funding_source'] != "Paying in full":
		db.auction_request.expected_down_payment.requires = IS_INT_IN_RANGE(0, 100000)
	else: #is paying in full
		request.post_vars['financing'] = None #so erase other crap
		request.post_vars['expected_down_payment'] = None
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
	
	if request.post_vars['funding_source'] == "Taking a lease":
		db.auction_request.lease_term.requires = IS_IN_SET(sorted(["24 months", "36 months", "39 months", "42 months", "48 months", "Lowest payments"]), multiple=False, zero="Choose one") #force a choice if taking a lease
		db.auction_request.lease_mileage.requires = IS_IN_SET(sorted(['12,000', '15,000', '18,000']), multiple=False, zero="Choose one") #TODO MAKE LESS DRY
		request.post_vars['financing'] = None #disable others
		
	if request.post_vars['funding_source'] == "Taking a loan":
		db.auction_request.financing.requires = IS_IN_SET(sorted(['Through the manufacturer', 'Self-finance (your bank, credit union, etc.)']), multiple=False, zero="Choose one")
		request.post_vars['lease_term'] = None
		request.post_vars['lease_mileage'] = None
		
	if request.post_vars['trading_in']:
		db.auction_request.describe_trade_in.requires = IS_NOT_EMPTY()
	else:
		request.post_vars['describe_trade_in'] = None 
		
	db.auction_request.color_preference.requires = [IS_IN_SET(style_color_codes, multiple=True, zero=None), IS_NOT_EMPTY(error_message='pick at least one color')]
	db.auction_request.color_preference.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	#db.auction_request.must_haves.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	form = SQLFORM(db.auction_request, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY

	"""
	#moved to forms onvalidation, instead of using unvaidated post_vars! http://goo.gl/00Urs6
	#form dependant values
	if request.post_vars: #doesn't matter if values are un-validated here, since arguments here used the same variables in the forms, if a variable is weird from create won't succeed.
		trim_data = getStyleByMakeModelYearStyleID(make,model,year,request.post_vars.trim_choices) 
		db.auction_request.trim_data.default = json.dumps(trim_data)
		db.auction_request.trim_name.default = trim_data['name'] 
		db.auction_request.color_names.default = [ each_color['name'] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.color_preference ] #make a list of color names based on ids in color_preference field
		db.auction_request.simple_color_names.default = [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in request.post_vars.color_preference ]
	"""
	
	def computations(form):
		trim_data = getStyleByMakeModelYearStyleID(make,model,year,form.vars.trim_choices)
		colorChipsErrorFix(trim_data['colors']) #make sure all db entries are safe. protect trim_data from this error
		db.auction_request.trim_data.default = json.dumps(trim_data)
		db.auction_request.trim_name.default = trim_data['name'] 
		db.auction_request.color_names.default = [ each_color['name'] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in form.vars.color_preference ] #make a list of color names based on ids in color_preference field
		db.auction_request.simple_color_names.default = [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in trim_data['colors'][1]['options'] if each_color['id'] in form.vars.color_preference ]
	
	if form.process(onvalidation=computations, hideerror=True).accepted: #hideerror = True to hide default error elements #change error message via form.custom
		guest_msg = ' Register or login to view it.'
		if auth.user_id:
			guest_msg=' Dealers have been notified!' #user is logged in no need for guest msg
		session.message = '$Auction submitted!%s' % guest_msg
		auth.add_group('request_by_make_authorized_dealers_#%s'%form.vars.id, 'The group of dealers that entered a particular request_by_make auction by agreeing to its terms and charges.')
		redirect(
			URL('default','pre_auction.html', args=form.vars.id) #http://goo.gl/twPSTK
		)
		
	response.title="Request an auction"
	response.subtitle="for a %s %s %s."%(year, make, model)

	return dict(model_styles=model_styles, trims=trims, form=form, year=year, make=make, model=model)
	
@auth.requires(not auth.has_membership(role='dealers')) #make sure dealers can't get anonymous auction requests attached to their name
@auth.requires(request.args(0))
def pre_auction():
	auction_id = request.args[0]
	guest_auction_requests = db((db.auction_request.owner_id == None) & (db.auction_request.temp_id == session.guest_temp_id)).select() #guest temp id is unique for each auction request, so it's safe to query up with this value... but make sure it's empty so that update doesn't keep running on this function
	for each_guest_auction_request in guest_auction_requests:
		each_guest_auction_request.update_record(owner_id=auth.user_id) #link guest id to user id
	redirect(
		URL('dealer','auction.html', args=auction_id) #http://goo.gl/twPSTK
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
	
	form = SQLFORM(db.dealership_info)
	
	if form.process().accepted:
		#email alert to admin
		response.message = '$Form accepted. Please wait a few days for our response!'
	
	response.title = 'Become our partner!'
	response.subtitle = 'Sell your cars on our website'
	return dict(form = form)
	
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

	if request.args:
		if request.args[0] == "register":
			response.title = "Join us"
		if request.args[0] == "login":
			response.title = "Welcome back"
		if request.args[0] == "request_reset_password":
			response.title = "Forgot something?"
	if auth.is_logged_in():
		response.title='Hey, %s!' % auth.user.first_name



	return dict(form=auth())

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
