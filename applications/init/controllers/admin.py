@auth.requires_membership('admins')
def index():
	response.title="Admin portal"
	return dict()

response.title=None
	
@auth.requires_membership('admins')
def dealership_requests():
	if not request.args:
		verification = "awaiting"
	else:
		verification=request.args[0]
	dealership_requests = db(db.dealership_info.verification == verification).select()
	
	response.title="%s dealership requests"%verification.capitalize()
	return dict(dealership_requests=dealership_requests, verification=verification)
	
@auth.requires_membership('admins')
def dealership_form():
	if not request.args:
		session.flash = "No form ID provided!"
		redirect(URL('admin', 'index.html'))
	record = db(db.dealership_info.id == request.args[0]).select().first()
	if not record:
		session.flash = "Invalid form ID!"
		redirect(URL('admin', 'index.html'))
	
	#expose fields for admin. Do this before sql form is created.
	db.dealership_info.verification.readable = True
	db.dealership_info.verification.writable = True
	#db.dealership_info.created_on.readable = True #done automatically via auth.signature
	#db.dealership_info.changed_on.readable = True
	#db.dealership_info.changed_by.readable = True
	db.dealership_info.owner_id.readable = True
	db.dealership_info.owner_id.writable = True
		
	form = SQLFORM(db.dealership_info, record)
	
	if form.process().accepted:
		membership = dict(user_id = form.vars.owner_id, role = "dealers") #user_id = form.vars.owner_id will not work unless writable set to True.
		if form.vars.verification == "approved":
			auth.add_membership(**membership) #unpack keyword args
		else:
			auth.del_membership(**membership)
		#alert user
		response.flash = 'Form updated!'
	
	response.title = 'Admin interface'
	response.subtitle = 'to modify dealership request #%s'%request.args[0]
	return dict(form = form)
	
"""
@auth.requires_membership("admins") # uncomment to enable security 
def list_users(): #http://goo.gl/PDylze
	btn = lambda row: A("Edit", _href=URL('admin', 'manage_user', args=row.auth_user.id))
	btn2 = lambda row: A("Edit", _href=URL('admin', 'manage_membership', args=row.auth_user.id))
	db.auth_user.edit_user = Field.Virtual(btn)
	db.auth_user.edit_membership = Field.Virtual(btn2)
	rows = db(db.auth_user).select()
	headers = ["ID", "Name", "Last Name", "Email", "User", "Membership"]
	fields = ['id', 'first_name', 'last_name', "email", "edit_user", "edit_membership"]
	table = TABLE(THEAD(TR(*[B(header) for header in headers])),
				  TBODY(*[TR(*[TD(row[field]) for field in fields]) \
						for row in rows]))
	table["_class"] = "table table-striped table-bordered table-condensed"
	return dict(table=table)
	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_user():
	user_id = request.args(0) or redirect(URL('admin','list_users'))
	form = SQLFORM(db.auth_user, user_id).process()
	return dict(form=form)
"""
	
if not request.function in ['dealership_requests', 'dealership_form']:
	response.view = 'admin/manage_generic.html'
	
@auth.requires_membership("admins") # uncomment to enable security 
@auth.requires(request.args(0))
def manage_memberships():
	user_id = request.args[0] #or redirect(URL('admin','list_users'))
	db.auth_membership.user_id.default = int(user_id)
	db.auth_membership.user_id.writable = False
	form = SQLFORM.grid(db.auth_membership.user_id == user_id, 
						buttons_placement = 'left', links_placement = 'left', 
						args=[user_id],
						searchable=True,
						editable=False,
						deletable=True,
						details=True,
						#left=db.auth_membership.on(db.auth_user.id==db.auth_membership.user_id), ##technically a left join, left joins preserve all the rows on the left table, even if right table doesn't #http://goo.gl/TSc6L
						selectable=False,
						csv=True,
						create=False,
						user_signature=False)  # change to True in production
	return dict(form=form)
	
db.auth_user.registration_key.readable = True
db.auth_user.registration_key.writable = True
db.auth_user.registration_key.requires = IS_EMPTY_OR(IS_IN_SET(['blocked', 'pending'], zero="allowed")) #this is a hack! remove this if email registration is enabled!

	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_buyers():
	#form = SQLFORM.grid(db.auth_user, links = [
	form = SQLFORM.grid( ((db.auth_user.id > 0) & (db.dealership_info.id == None) ), links = [
		dict(header='Auctions',body=lambda row: A('Show all%s'%(' auctions' if 'auth_user' in request.args else ''),_href=URL('admin','manage_auctions', vars=dict(user_type='buyer'), args=[row.auth_user.id if 'auth_user' in row else row.id] ) ) ), #MUST do this on joins 
		dict(header='Memberships',body=lambda row: A('Show all%s'%(' memberships' if 'auth_user' in request.args else ''),_href=URL('admin','manage_memberships', args=[row.auth_user.id if 'auth_user' in row else row.id] ) ) ), #args=[row.auth_user.id] #HACK BUT DONT USE-by forcing the fields argument to show only auth_user, the join is essentially gone and row.auth_user.id is unnecessary 
	],  
	buttons_placement = 'left', links_placement = 'left', 
	left=db.dealership_info.on(db.auth_user.id == db.dealership_info.owner_id), #technically a left join, left joins preserve all the rows on the left table, even if right table doesn't #http://goo.gl/TSc6L
	fields = map(lambda each_field_string: db.auth_user[each_field_string], db.auth_user.fields()), #show only auth_user fields
	user_signature=False)
	return dict(form=form)
	
def manage_dealers():	
	form = SQLFORM.grid(db.auth_user.id==db.dealership_info.owner_id, links = [
		dict(header='Auctions',body=lambda row: A('Show all%s'% (' auctions' if 'auth_user' in request.args else ''),_href=URL('admin','manage_auctions', vars=dict(user_type='dealer'), args=[row.id] ) ) ), 
		dict(header='Memberships',body=lambda row: A('Show all%s'% (' memberships' if 'auth_user' in request.args else ''),_href=URL('admin','manage_memberships', args=[row.id] ) ) ), 
		dict(header='Dealership info',body=lambda row: A('Show %s'% (' dealership info' if 'auth_user' in request.args else ''),_href=URL('admin','manage_dealership_info', args=[row.id] ) ) ), 
	], 
	fields=map(lambda each_field_string: db.auth_user[each_field_string], db.auth_user.fields()), #fields method returns list of strings of field names of a table #http://goo.gl/L9nONC
	buttons_placement = 'left', links_placement = 'left', 
	user_signature=False)
	return dict(form=form)
	
@auth.requires(request.args(0))
def manage_dealership_info():
	dealership_info_id =request.args[0]
	form = SQLFORM.grid(db.dealership_info.id==dealership_info_id, buttons_placement = 'left', links_placement = 'left', user_signature=False)
	return dict(form=form)
	
def manage_auctions():
	for_user_type = request.vars['user_type']
	identifier = request.args(0)
	db.auction_request.must_haves.writable = False
	db.auction_request.color_preference.writable = False
	db.auction_request.trim_choices.writable = False	
	db.auction_request.must_haves.readable = False
	db.auction_request.color_preference.readable = False
	db.auction_request.trim_choices.readable = False
	db.auction_request.trim_name.readable = True
	db.auction_request.color_names.readable = True
	db.auction_request.year.readable = True
	links = [		
		dict(header='Offers',body=lambda row: A('Show all%s'% (' offers' if 'auction_request' in request.args else ''), #this logic tests to see if its the grid or edit form and names the URL accordingly
			_href=URL('admin','manage_offers', args=[row.auction_request.id if 'auction_request' in row else row.id] ) ) ), 
		dict(header='Winning offer',body=lambda row: A('Show%s'% (' winning offer' if 'auction_request' in request.args else ''),_href=URL('admin','manage_winning_offer', args=[row.auction_request.id if 'auction_request' in row else row.id] ) ) ), 
	]
	user_id = identifier
	if for_user_type == 'buyer':
		form = SQLFORM.grid(db.auction_request.owner_id == user_id, args=[user_id], create=False, buttons_placement = 'left', links=links, links_placement = 'left', user_signature=False)
	elif for_user_type == 'dealer':
		form = SQLFORM.grid(((db.auction_request.id == db.auction_request_offer.auction_request)&(db.auction_request_offer.owner_id==user_id)), args=[user_id], create=False, buttons_placement = 'left', links_placement = 'left',
		fields=map(lambda each_field_string: db.auction_request[each_field_string], db.auction_request.fields()), #fields method returns list of strings of field names of a table #http://goo.gl/L9nONC
		links=links,
		field_id = db.auction_request.id, #http://goo.gl/OxMlTj
		user_signature=False)
	else:
		auction_id = identifier
		query = db.auction_request
		if auction_id:
			query = db.auction_request.id == auction_id
		db.auction_request.owner_id.readable = True
		form = SQLFORM.grid(query, create=False, buttons_placement = 'left', links=links, links_placement = 'left', user_signature=False)
	return dict(form=form)
	
@auth.requires(request.args(0))
def manage_winning_offer():
	#db.auction_request_winning_offer.auction_request.readable=True
	#db.auction_request_winning_offer.auction_request_offer.readable=True
	#db.dealership_info.id.readable=False
	auction_id = request.args[0]
	links = [		
		dict(header='Auction',body=lambda row: A('Show%s'% (' auction' if 'auction_request_winning_offer' in request.args else ''),_href=URL('admin','manage_auctions', args=[row.auction_request] ) ) ), 
		dict(header='Offer',body=lambda row: A('Show%s'% (' offer' if 'auction_request_winning_offer' in request.args else ''),_href=URL('admin','manage_offers', args=[row.auction_request_offer] ) ) ), 
	]
	form=SQLFORM.grid(db.auction_request_winning_offer.auction_request == auction_id,
		buttons_placement = 'left', links=links, links_placement = 'left', 
		searchable=False,
		editable=True,
		create=False,
		user_signature=False
	)
	return dict(form=form)
	
def manage_offers():
	auction_id = request.args(0)
	query = db.auction_request_offer
	links = [		
		dict(header='Auction',body=lambda row: A('Show%s'% (' auction' if 'auction_request_offer' in request.args else ''),_href=URL('admin','manage_auctions', args=[row.auction_request] ) ) ), 
		dict(header='Winning offer',body=lambda row: A('Show%s'% (' offer' if 'auction_request_offer' in request.args else ''),_href=URL('admin','manage_winning_offer', args=[row.auction_request] ) ) ), 
	]
	
	options_prefixes = ['interior', 'exterior', 'mechanical', 'package', 'fees', 'safety']
	for each_prefix in options_prefixes:
		db.auction_request_offer['%s_options_names'%each_prefix].readable = True
		db.auction_request_offer['%s_options_names'%each_prefix].writable = False #even though it's handled in models_edmunds do it again anyway
		db.auction_request_offer['%s_options'%each_prefix].readable = False
		db.auction_request_offer['%s_options'%each_prefix].writable = False
	db.auction_request_offer.color.readable = False
	db.auction_request_offer.color.writable = False
	db.auction_request_offer.color_name.readable = True
	db.auction_request_offer.color_name.writable = False

	if auction_id:
		query = db.auction_request_offer.auction_request == auction_id
	form =  SQLFORM.grid(query,
		buttons_placement = 'left', links=links, links_placement = 'left', 
		user_signature=False
	)
	return dict(form=form)