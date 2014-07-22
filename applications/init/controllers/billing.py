@auth.requires_membership('dealers')
def buy_credits():
	buy_credits_urls = dict(
		tier_1 = URL('billing','paypal', args=['1']),
		tier_2 = URL('billing','paypal', args=['2']),
		tier_3 = URL('billing','paypal', args=['3']),
		tier_4 = URL('billing','paypal', args=['4']),
	)
	my_credits_row = db(db.credits.owner == auth.user_id).select().first()
	my_credits = my_credits_row['credits'] if my_credits_row else 0
	return dict(buy_credits_urls=buy_credits_urls, my_credits=my_credits)

#visit https://github.com/paypal/rest-api-sdk-python/tree/master/samples

@auth.requires_membership('dealers')	
def paypal_return():
	if not session.purchase:
		session.message2 = "!Session expired!"
	elif request.args(0) == 'cancel':
		session.message2 = '!Payment canceled!'
	elif not request.vars['PayerID']:
		session.message2 = "!Buy something first!"
	else:
		#ID of the payment. This ID is provided when creating payment.
		payment = Paypal.Payment.find(session.purchase['payment_id'])

		# PayerID is required to approve the payment.
		if payment.execute({"payer_id": request.vars['PayerID'] }):  # return True or False
			sale_id = payment['transactions'][0]['related_resources'][0]['sale']['id']
			db.credit_orders.insert(owner = auth.user_id,payment_executed = request.now, payer_id = request.vars['PayerID'], sale_id = sale_id, **session.purchase)
			my_credits = db(db.credits.owner == auth.user_id).select().first()
			if not my_credits: #credits row for dealer doesn't exist for some reason
				db.credits.insert(owner=auth.user_id, credits = session.purchase['credits'])
			else:
				my_credits.update_record(credits = my_credits['credits'] + session.purchase['credits'])
			session.purchase = None #successful payment so remove purchase session
			session.message2 = "$Payment[%s] made successfully"%(payment.id)
		else:
			session.message2 = "!%s: %s"%(payment.error['name'], payment.error['details'])
	redirect(URL('billing','buy_credits'))

@auth.requires_membership('dealers')	
def paypal():
	tier = request.args(0)
	if not tier or int(tier) > 4:
		session.message = "Invalid order request!"
		redirect(URL('billing','buy_credits'))
	price=credits=0
	tier = int(tier)
	if tier == 1:
		credits = 200
		price = credits*1.0
	if tier == 2:
		credits = 400 
		price = credits* 0.75
	if tier == 3:
		credits = 1200
		price = credits * 0.50
	if tier == 4:
		credits = 4800
		price = credits * 0.25
	price = int(price)
	payment = Paypal.Payment({
		"intent":	"sale",

		# ###Payer
		# A resource representing a Payer that funds a payment
		# Payment Method as 'paypal'
		"payer":	{
			"payment_method":	"paypal" },

		# ###Redirect URLs
		"redirect_urls": {
			"return_url": URL('billing','paypal_return', scheme=True, host=True),
			"cancel_url": URL('billing','paypal_return',args=['cancel'], scheme=True, host=True),
		},

		# ###Transaction
		# A transaction defines the contract of a
		# payment - what is the payment for and who
		# is fulfilling it.
		"transactions":	[ {

			# ### ItemList
		#	"item_list": {
		#		"items": [{
		#			"name": "item",
		#			"sku": "item",
		#			"price": "5.00",
		#			"currency": "USD",
		#			"quantity": 1 }]},

			# ###Amount
			# Let's you specify a payment amount.
			"amount":	{
				"total":	str(price),
				"currency":	"USD" },
			"description":	"%s - %s credits for $%s deal."%(APP_NAME,credits,price) } 
		] 
	})

	# Create Payment and return status
	if payment.create():
		#session.message="Payment[%s] created successfully"%(payment.id)
		# Redirect the user to given approval url
		for link in payment['links']:
			if link['method'] == "REDIRECT":
				redirect_url = link['href']
				session.purchase = dict(payment_id = payment.id, price = price, credits = credits, payment_created=request.now)
				redirect(redirect_url)
				#print("Redirect for approval: %s"%(redirect_url))
	else:
		session.message = "Error while creating payment!"
		session.message2 = "%s: %s"%(payment.error['name'], payment.error['details'])
		redirect(URL('default','index'))