@auth.requires_membership('admins')
def index():
	response.title="Admin portal"
	return dict()

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
	db.dealership_info.created_on.readable = True
	db.dealership_info.changed_on.readable = True
	db.dealership_info.changed_by.readable = True
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