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
	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_memberships():
	user_id = request.args(0) or redirect(URL('admin','list_users'))
	db.auth_membership.user_id.default = int(user_id)
	db.auth_membership.user_id.writable = False
	form = SQLFORM.grid(db.auth_membership.user_id == user_id,
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
	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_users():
	form = SQLFORM.grid(db.auth_user, links = [
		dict(header='Auctions',body=lambda row: A('Show all',_href=URL('admin','manage_auctions', vars=dict(user_type='buyer'), args=[row.id] ) ) ), 
		dict(header='Memberships',body=lambda row: A('Show all',_href=URL('admin','manage_memberships', vars=dict(user_type='buyer'), args=[row.id] ) ) ), 
	],  user_signature=False)
	return dict(form=form)
	
def manage_dealers():	
	form = SQLFORM.grid(db.auth_user.id==db.dealership_info.owner_id, links = [
		dict(header='Auctions',body=lambda row: A('Show all%s'% (' auctions' if 'auth_user' in request.args else ''),_href=URL('admin','manage_auctions', vars=dict(user_type='dealer'), args=[row.id] ) ) ), 
		dict(header='Memberships',body=lambda row: A('Show all%s'% (' memberships' if 'auth_user' in request.args else ''),_href=URL('admin','manage_memberships', vars=dict(user_type='dealer'), args=[row.id] ) ) ), 
		dict(header='Dealership info',body=lambda row: A('Show %s'% (' dealership info' if 'auth_user' in request.args else ''),_href=URL('admin','manage_dealership_info', vars=dict(user_type='dealer'), args=[row.id] ) ) ), 
	], 
	fields=map(lambda each_field_string: db.auth_user[each_field_string], db.auth_user.fields()), #fields method returns strings of field names of a table #http://goo.gl/L9nONC
	user_signature=False)
	return dict(form=form)
	
def manage_auctions():
	for_user_type = request.vars['user_type']
	user_id = request.args(0)
	db.auction_request.must_haves.writable = False
	db.auction_request.color_preference.writable = False
	db.auction_request.trim_choices.writable = False	
	db.auction_request.must_haves.readable = False
	db.auction_request.color_preference.readable = False
	db.auction_request.trim_choices.readable = False
	db.auction_request.trim_name.readable = True
	db.auction_request.color_names.readable = True
	db.auction_request.year.readable = True
	if for_user_type == 'buyer':
		form = SQLFORM.grid(db.auction_request.owner_id == user_id, args=[user_id], create=False,user_signature=False)
	elif for_user_type == 'dealer':
		form = SQLFORM.grid(((db.auction_request.id == db.auction_request_offer.auction_request)&(db.auction_request_offer.owner_id==user_id)), args=[user_id], create=False,user_signature=False)
	else:
		db.auction_request.owner_id.readable = True
		form = SQLFORM.grid(db.auction_request, create=False,user_signature=False)
	return dict(form=form)
	