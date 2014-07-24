# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

response.logo = A(B(APP_NAME.capitalize() ),XML('&trade;&nbsp;'),
                  _class="brand",_href=URL('default', 'index.html') )
response.title = APP_NAME.capitalize() or request.application.replace('_',' ').title()
response.subtitle = ''

## read more at http://dev.w3.org/html5/markup/meta.name.html
response.meta.author = 'Your Name <you@example.com>'
response.meta.description = 'a cool new app'
response.meta.keywords = 'web2py, python, framework'
response.meta.generator = 'Web2py Web Framework'

## your http://google.com/analytics id
response.google_analytics_id = None

#########################################################################
## this is the main application menu add/remove items as required
#########################################################################

response.menu = [
    #(T('Used cars'), False, URL('default', 'index'), []),
	(T('Become a dealer'), False, URL('default', "dealership_form", args=["force_register"] ), []),
	(T('Register'), False, URL('default', "user", args=["register"] ), []),
] if not auth.user_id else [] #if not auth.has_membership(user_id = auth.user_id, role = "dealers") else []
