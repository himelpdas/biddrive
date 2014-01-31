# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## This is a sample controller
## - index is the default action of any application
## - user is required for authentication and authorization
## - download is for downloading files uploaded in the db (does streaming)
## - call exposes all registered services (none by default)
#########################################################################

#test update 
def index():
	"""
	example action using the internationalization operator T and flash
	rendered by views/default/index.html or views/generic.html

	if you need a simple wiki simply replace the two lines below with:
	return auth.wiki()
	"""

	brands_list=('Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 'FIAT', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jaguar', 'Jeep', 'Kia', 'Land Rover', 'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'MINI', 'Mitsubishi', 'Nissan', 'Porsche', 'Ram', 'Scion', 'Smart', 'Subaru', 'Toyota', 'Volkswagen', 'Volvo')
	bg_images = db(db.index_bg_image.id > 0).select()
	hero_images = db(db.index_hero_image.id > 0).select()
		
	return dict(brands_list=brands_list, bg_images=bg_images, hero_images=hero_images)
	
def request_by_make():
	if not request.args:
		session.flash='Invalid Request!'
		redirect(URL('index/html'))
		
	year = request.args[0] 
	if not int(year) in range(datetime.date.today().year-1, datetime.date.today().year+2):
		session.flash='Invalid Year!'
		redirect(URL('index.html'))
	make = request.args[1] #VALIDATE
	model = request.args[2]
	db.auction_request.year.default=year
	db.auction_request.make.default=make
	db.auction_request.model.default=model
	
	db.auction_request.temp_id.default=session.guest_temp_id=repr(uuid.uuid4())

	#put in class
	styles_URI = STYLES_URI%(make, model, year)
	model_styles = ed_cache(
		styles_URI,
		lambda: ed.make_call(styles_URI),
	)
	trims = []
	for each_style in model_styles["styles"]:
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

	db.auction_request.color_preference.requires = [IS_IN_SET(style_color_codes, multiple=True, zero=None), IS_NOT_EMPTY()]
	db.auction_request.color_preference.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	form = SQLFORM(db.auction_request)
	if form.process().accepted: #change error message
		session.flash = 'form accepted'
		redirect(
			URL('my_auctions.html')
		)
		
	response.title="Request an auction"
	response.subtitle="for a %s %s %s."%(year, make, model)

	return dict(model_styles=model_styles, trims=trims, form=form)
	
@auth.requires_login()
def my_auctions():
	guest_auction_requests = db((db.auction_request.owner_id == None) & (db.auction_request.temp_id == session.guest_temp_id)).select()
	for each_guest_auction_request in guest_auction_requests:
		each_guest_auction_request.update_record(owner_id=auth.user_id) #link guest id to user id
	
	my_auctions = db(db.auction_request.owner_id == auth.user_id).select()
	response.title="My auctions"
	return dict(guest_temp_id=session.guest_temp_id, my_auctions=my_auctions)
	
@auth.requires_login()
def auction():
	response.title="Auction"
	return dict()

def how_it_works():
	return dict()
	
def hello_dealers():
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
