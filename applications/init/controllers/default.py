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
	response.flash = T("%s is under heavy construction!"%APP_NAME.capitalize() )
	brands_list=('Acura', 'Audi', 'BMW', 'Buick', 'Cadillac', 'Chevrolet', 'Chrysler', 'Dodge', 'FIAT', 'Ford', 'GMC', 'Honda', 'Hyundai', 'Infiniti', 'Jaguar', 'Jeep', 'Kia', 'Land Rover', 'Lexus', 'Lincoln', 'Mazda', 'Mercedes-Benz', 'MINI', 'Mitsubishi', 'Nissan', 'Porsche', 'Ram', 'Scion', 'Smart', 'Subaru', 'Toyota', 'Volkswagen', 'Volvo')
	bg_images = db(db.index_bg_image.id > 0).select()
	hero_images = db(db.index_hero_image.id > 0).select()
	
	return dict(brands_list=brands_list, bg_images=bg_images, hero_images=hero_images)
	
def request_by_make():
	if not request.args:
		session.flash('Invalid Request!')
		redirect(URL())
	year = request.args[0]
	make = request.args[1]
	model = request.args[2]
	
	response.title="Request an auction"
	response.subtitle="for a %s %s %s."%(year, make, model)

	#put in class
	styles_URI = '/api/vehicle/v2/%s/%s/%s/styles'%(make, model, year)
	model_styles = ed_cache(
		styles_URI,
		lambda: ed.make_call(styles_URI),
	)
	
	return dict(args=request.args, model_styles=model_styles)

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
