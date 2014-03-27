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
	
def request_by_make():
	if not request.args:
		session.flash='Invalid request!'
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
		session.flash='Invalid Year!'
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

	db.auction_request.color_preference.requires = [IS_IN_SET(style_color_codes, multiple=True, zero=None), IS_NOT_EMPTY(error_message='pick at least one color')]
	db.auction_request.color_preference.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	form = SQLFORM(db.auction_request, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY
	
	if form.process(hideerror=True).accepted: #hideerror = True to hide default error elements #change error message via form.custom
		guest_msg = ' Register or login to view it.'
		if auth.user_id:
			guest_msg='' #user is logged in no need for guest msg
		session.flash = 'Auction submitted!%s' % guest_msg
		auth.add_group('request_by_make_authorized_dealers_#%s'%form.vars.id, 'The group of dealers that entered a particular request_by_make auction by agreeing to its terms and charges.')
		redirect(
			URL('auction.html', args=form.vars.id) #http://goo.gl/twPSTK
		)
		
	response.title="Request an auction"
	response.subtitle="for a %s %s %s."%(year, make, model)

	return dict(model_styles=model_styles, trims=trims, form=form, year=year, make=make, model=model)
	
@auth.requires_login()
def my_auctions():
	guest_auction_requests = db((db.auction_request.owner_id == None) & (db.auction_request.temp_id == session.guest_temp_id)).select()
	for each_guest_auction_request in guest_auction_requests:
		each_guest_auction_request.update_record(owner_id=auth.user_id) #link guest id to user id
	
	my_auctions = db(db.auction_request.owner_id == auth.user_id).select()
	response.title="My auctions"
	return dict(guest_temp_id=session.guest_temp_id, my_auctions=my_auctions)
	
@auth.requires_login()
def auction(): #make sure only allow one active auction per user
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
	
	return dict(auction_request=auction_request)

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
		response.flash = 'Form accepted. Please wait a few days for our response!'
	
	response.title = 'Become our partner!'
	response.subtitle = 'Sell your cars on our website'
	return dict(form = form)
	
@auth.requires_membership('dealers')
def dealer_portal():
	return dict()

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
