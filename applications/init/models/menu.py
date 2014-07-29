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

response.menu = []

if not db(db.auth_group.role == "dealers").select().first(): #cache!!
	auth.add_group('dealers', 'only accounts that submitted an admin-verified dealership application may join this group.')

if not db(db.auth_group.role == "admins").select().first(): #cache!!
	auth.add_group('admins', 'has access to various non-public aspects of the database')
	
AUTH_ADMIN = auth.has_membership(user_id = auth.user_id, role = "admins")
AUTH_DEALER = auth.has_membership(user_id = auth.user_id, role = "dealers")

if AUTH_ADMIN:
	response.menu.append(
		(T('Admin Portal'), False, URL('admin', 'dealership_requests'), [
			(T('DB management'), False, URL('appadmin', 'index'), []),
			(T('Dealership requests'), False, URL('admin', 'dealership_requests'), []),
			(T('Manage auctions'), False, URL('admin', 'manage_auctions'), []),
			(T('Manage buyers'), False, URL('admin', 'manage_buyers'), []),
			(T('Manage dealers'), False, URL('admin', 'manage_dealers'), []),
		]),
	)
# if not session.last_auction_visited else URL('dealer', 'auction', args=[session.last_auction_visited]
dealer_portal_menu_list=[
		(XML('<i class="fa fa-fw fa-car"></i> Buyer requests'), False, URL('dealer', 'auction_requests'), []),
		(XML('<i class="fa fa-fw fa-info-circle"></i> Dealership info'), False, URL('dealer', 'dealer_info'), []),
		#(T('Messages'), False, URL('dealer', 'messages'), []),
		#(T('Manage alerts'), False, URL('dealer', 'reminders'), []),
		(XML('<i class="fa fa-fw fa-gavel"></i> Entered auctions'), False, URL('dealer', 'my_auctions'), []),
		(XML('<i class="fa fa-fw fa-btc"></i> Purchase credits'), False, URL('billing', 'buy_credits'), []),
	] if AUTH_DEALER else [
		(XML('<i class="fa fa-fw fa-caret-right"></i> Dealer login'), False, URL('default', 'user', args=["login"], vars=dict(custom_message="Dealer login")), []),
		(XML('<i class="fa fa-fw fa-caret-right"></i> Join us!'), False, URL('default', "dealership_form", args=["force_register", "dealer_registration"]), []),
	]

if (not auth.user) or (AUTH_DEALER or AUTH_ADMIN): #non-buyers and visitors only
	response.menu.append(
		(T( 'Dealer%s'%('s' if not auth.user else ' Portal') ), False, URL('dealer', 'auction_requests'), dealer_portal_menu_list),
	)
"""
if not auth.user:
	response.menu.append((XML(;<button class="btn btn-default btn-xs navbar-btn"><i class="fa fa-fw fa-star"></i> Register</button>'), False, URL('default', 'user', args=['register'] ), []))
"""