# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
	if platform.system() in ["Darwin", "Windows"]:
		db = DAL('sqlite://storage18.sqlite',pool_size=1, adapter_args=dict(foreign_keys=False), check_reserved=['mysql']) #check_reserved=['all']) #http://bit.ly/1fkDk3w
	else: #db = DAL('mysql://<mysql_user>:<mysql_password>@localhost/<mysql_database>')
		db = DAL('mysql://himdas:ekFh2E4t4VKF@mysql.biddrive.com/db_0', check_reserved=['mysql']) #always check for reserved keywords in future possible DBs. #http://goo.gl/g7cXti #PROBLEMS FIXED by making new db, erase inside /database folder, reload... Also clear cache on browser to remove previous login
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'
## (optional) static assets folder versioning
# response.static_version = '0.0.0'
#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
auth = Auth(db)
crud, service, plugins = Crud(db), Service(), PluginManager()

##############EXTRA SETTINGS###############
auth.settings.register_onaccept += [
	lambda form: SEND_ALERT_TO_QUEUE(OVERRIDE_ALERT_SETTING=True, USER=db(db.auth_user.id==form.vars.id).select().last(), MESSAGE_TEMPLATE = "GENERIC_welcome_to_biddrive", **dict(first_name=form.vars.first_name) ) ,
	#lambda form: get_alert_setting_table_for_user(form.vars.id) #no longer needed since email alert settings were simplified, and now resides in db.auth_user
]

force_default_on_register = False if not auth.is_logged_in() else True  #since auth doesn't allow changing fields after db.define_tables(auth), default can be forced here
auth.settings.extra_fields['auth_user']= [
	Field('mobile_phone',
		requires = IS_MATCH(
			REGEX_TELEPHONE,
			error_message='not a phone number',
		)
	),
	Field('enable_email_alerts', 'boolean', default = True, readable = force_default_on_register, writable = force_default_on_register),
	Field('enable_sms_alerts', 'boolean', default = False, readable = force_default_on_register, writable=force_default_on_register),
]

############################################

## create all tables needed by auth if not custom tables
auth.define_tables(username=False, signature=False)
auth.messages.email_sent = '$Email sent!'
## configure email
mail = auth.settings.mailer
mail.settings.server = 'in-v3.mailjet.com:587' #some hosts block port 25 #'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'noreply@biddrive.com' #'Your Name <you@gmail.com>' #http://goo.gl/FNosX9
mail.settings.login = '7d01f433ff459980e1ab595decc7ba34:3fdf22c6fde649e46391c5a4e8bec77c' #'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################

## after defining tables, uncomment below to enable auditing

auth.enable_record_versioning(db)

#########################################################################
## Add color changing symbol for global error message div in layout.html
auth.messages.invalid_login = '!Invalid login'
