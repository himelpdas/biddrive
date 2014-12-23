"""
@auth.requires_membership('admins')
def index():
	response.title="Admin portal"
	return dict()
"""
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
	record_owner = db(db.auth_user.id == record.owner_id).select().last()
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
	#db.dealership_info.owner_id.writable = True
	form = SQLFORM(db.dealership_info, record)
	if form.process().accepted:
		#form.vars.owner_id returns None for some reason maybe after web2py upgrade, will use ID from record instead
		membership = dict(user_id = record.owner_id, role = "dealers") #user_id = form.vars.owner_id will not work unless writable set to True.
		if form.vars.verification == "approved":
			membership_id = auth.add_membership(**membership) #unpack keyword args
			#quickRaise(form.vars.owner_id) #testing for reason why add membership fails, turns out form.vars.owner_id stopped working possibly after web2py upgrade. Now form.vars appears to work only if writable=True.
			#alert new dealer
			SEND_ALERT_TO_QUEUE(OVERRIDE_ALERT_SETTING=True, USER=record_owner, MESSAGE_TEMPLATE = "DEALER_approved_dealership", **dict(app=APP_NAME, specialize=' '.join(record.specialty) , url=URL('dealer', 'auction_requests', host=True, scheme=True) ) )
		else:
			auth.del_membership(**membership)
		#alert user
		response.flash = 'Form updated!'
	
	response.title = 'Admin interface'
	response.subtitle = 'to modify dealership request #%s'%request.args[0]
	return dict(form = form)

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
						#create=False,
						user_signature=False,
						orderby=~db.auth_membership.id)  # change to True in production
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
	user_signature=False, 
	orderby=~db.auth_user.id)
	return dict(form=form)
	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_dealers():	
	db.dealership_info.verification.readable = True
	form = SQLFORM.grid(db.auth_user.id==db.dealership_info.owner_id, links = [
		dict(header='Auctions',body=lambda row: A('Show all%s'% (' auctions' if 'auth_user' in request.args else ''),_href=URL('admin','manage_auctions', vars=dict(user_type='dealer'), args=[row.id] ) ) ), 
		dict(header='Memberships',body=lambda row: A('Show all%s'% (' memberships' if 'auth_user' in request.args else ''),_href=URL('admin','manage_memberships', args=[row.id] ) ) ), 
		dict(header='Credits',body=lambda row: A('Show%s'% (' credits' if 'auth_user' in request.args else ''),_href=URL('admin','manage_credits', args=[row.id] ) ) ), 
		dict(header='Orders',body=lambda row: A('Show all%s'% (' orders' if 'auth_user' in request.args else ''),_href=URL('admin','manage_orders', args=[row.id] ) ) ), 
		dict(header='Dealership info',body=lambda row: A('Show %s'% (' dealership info' if 'auth_user' in request.args else ''),_href=URL('admin','manage_dealership_info', args=[row.id] ) ) ), 
	], 
	fields=map(lambda each_field_string: db.auth_user[each_field_string], db.auth_user.fields()), #fields method returns list of strings of field names of a table #http://goo.gl/L9nONC
	buttons_placement = 'left', links_placement = 'left', 
	create=False,
	user_signature=False,
	orderby=~db.auth_user.id)
	return dict(form=form)
	
@auth.requires_membership("admins") # uncomment to enable security 
@auth.requires(request.args(0))
def manage_dealership_info():
	user_id =request.args[0]
	form = SQLFORM.grid(db.dealership_info.owner_id==user_id, buttons_placement = 'left', links_placement = 'left', create=False, user_signature=False,
	orderby=~db.dealership_info.id)
	return dict(form=form)

@auth.requires_membership("admins") # uncomment to enable security 	
def manage_auctions():
	for_user_type = request.vars['user_type']
	identifier = request.args(0)
	db.auction_request.options.writable = False
	db.auction_request.colors.writable = False
	db.auction_request.trim.writable = False	
	db.auction_request.options.readable = False
	db.auction_request.colors.readable = False
	db.auction_request.trim.readable = False
	db.auction_request.trim_name.readable = True
	db.auction_request.color_names.readable = True
	db.auction_request.year.readable = True
	db.auction_request.make_name.readable = True
	db.auction_request.model_name.readable = True
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
		form = SQLFORM.grid(query, create=False, buttons_placement = 'left', links=links, links_placement = 'left', 
		user_signature=False,
		orderby=~db.auction_request.id)
	return dict(form=form)

@auth.requires_membership("admins") # uncomment to enable security 	
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
		user_signature=False,
		orderby=~db.auction_request_winning_offer.id
	)
	return dict(form=form)
	
@auth.requires_membership("admins") # uncomment to enable security 
def manage_offers():
	auction_id = request.args(0)
	query = db.auction_request_offer
	links = [		
		dict(header='Auction',body=lambda row: A('Show%s'% (' auction' if 'auction_request_offer' in request.args else ''),_href=URL('admin','manage_auctions', args=[row.auction_request] ) ) ), 
		dict(header='Winning offer',body=lambda row: A('Show%s'% (' winning offer' if 'auction_request_offer' in request.args else ''),_href=URL('admin','manage_winning_offer', args=[row.auction_request] ) ) ), 
	]
	
	#options_prefixes = ['interior', 'exterior', 'mechanical', 'package', 'fees', 'safety']
	db.auction_request_offer['option_names'].readable = True
	db.auction_request_offer['option_names'].writable = False #even though it's handled in models_edmunds do it again anyway
	db.auction_request_offer['options'].readable = False
	db.auction_request_offer['options'].writable = False
	db.auction_request_offer.exterior_color.readable = False
	db.auction_request_offer.exterior_color.writable = False
	db.auction_request_offer.exterior_color_name.readable = True
	db.auction_request_offer.exterior_color_name.writable = False

	if auction_id:
		query = db.auction_request_offer.auction_request == auction_id
	form =  SQLFORM.grid(query,
		buttons_placement = 'left', links=links, links_placement = 'left', 
		create=False,
		user_signature=False,
		orderby=~db.auction_request_offer.id
	)
	return dict(form=form)
	
@auth.requires_membership("admins") # uncomment to enable security 
@auth.requires(request.args(0))
def manage_credits():
	user_id = request.args[0]
	query = db.credits.owner_id == user_id
	links=[]
	def onvalidation(form): #this will document changes made by an admin to the dealers credits history 
		credits_now = db(query).select().last()
		credits_new = form.vars.credits
		changed = credits_new - credits_now.credits
		reason = form.vars.latest_reason or "Administrative"
		db.credits_history.insert(reason=reason, changed=changed, owner_id=user_id)
		#form.errors= True  #this prevents the submission from completing

	form =  SQLFORM.grid(query,  args=[user_id],
		buttons_placement = 'left', links=links, links_placement = 'left', 
		editable=True,
		searchable=False,
		create=False,
		deletable=False,
		onvalidation=onvalidation,
		user_signature=False,
		orderby=~db.credits.id
	)
	return dict(form=form)
	
@auth.requires_membership("admins") # uncomment to enable security 
@auth.requires(request.args(0))
def manage_orders():
	user_id = request.args[0]
	query = db.credit_orders.owner_id == user_id
	links=[
		dict(header='Refund',body=lambda row: A('Issue%s'% (' refund' if 'credit_orders' in request.args else ''),_href=URL('admin','issue_refund', args=[row.id] ), _onclick="return confirm('Are you sure you want to issue a refund?')" ) ) #http://goo.gl/h6vOEE
	]
	form =  SQLFORM.grid(query, args=[user_id],
		buttons_placement = 'left', links=links, links_placement = 'left', 
		editable=False,
		create=False,
		deletable=False,
		user_signature=False,
		orderby=~db.credit_orders.id
	)
	return dict(form=form)
	
#from paypalrestsdk import Sale, Payment
@auth.requires_membership("admins") # uncomment to enable security 
#@auth.requires_membership("accountants") # uncomment to enable security 
@auth.requires(request.args(0))
def issue_refund(): #how to refund via sale id http://goo.gl/zVzjE7 #where the sale id is http://goo.gl/QwJjfe
	order_id = request.args[0]
	order = db(db.credit_orders.id == order_id).select().last()
	sale = Paypal.Sale.find(order.sale_id)

	# Make Refund API call
	# Set amount only if the refund is partial
	refund = sale.refund({
	  "amount": {
		"total" : str(order.price), #"total": "0.01",
		"currency": "USD" } 
	})

	# Check refund status
	if refund.success():
		#print("Refund[%s] Success"%(refund.id))
		my_credits = db(db.credits.owner_id == order.owner_id).select().first()
		order.update_record(refunded=True, payment_refunded=request.now)
		my_credits.update_record(credits = int(my_credits.credits) - int(order.credits))
		db.credits_history.insert(changed = -int(order.credits), owner_id=auth.user_id, reason="Refund")
		session.message2 = "$Payment %s successfully refunded!" % order.payment_id
	else:
		#print("Unable to Refund")
		#print(refund.error)
		session.message2 = "@%s: %s!" % (refund.error['name'],refund.error['message'])
		session.message = "!Sorry, payment %s could not be refunded!" % order.payment_id
	redirect(URL('admin','manage_orders', args=[order.owner_id]))