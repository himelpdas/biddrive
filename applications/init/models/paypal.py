USD_PER_CREDIT = 1.0
INTRODUCTORY_CREDITS = 1000.0
CREDITS_PER_AUCTION = 1.0

paypal_state =IS_IN_SET(['created', 'approved', 'failed', 'canceled', 'expired',], zero=None)


import paypalrestsdk as Paypal #pip install paypalrestsdk

Paypal.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": "EBWKjlELKMYqRNQ6sYvFo64FtaRLRR5BdHEESmha49TM",
  "client_secret": "EO422dn3gQLgDbuwqTjzrFgFtaRLRR5BdHEESmha49TM" })

db.define_table("credits",
	Field("owner", db.auth_user),
	Field('credits', "integer",),
	auth.signature,
)

db.define_table("credit_orders",
	Field("owner", db.auth_user,
		readable = False,
		writable = False,
	),
	Field('payment_id',
		required=True
	),	
	Field('sale_id',
		required=True
	),
	Field('payer_id',
		required=True
	),
	Field('credits', "integer",
		required=True
	),
	Field('price', "integer",
		required=True
	),	
	Field('refunded', "boolean",
		default=False
	),
	Field('payment_created', 'datetime'),
	Field('payment_executed', 'datetime'),
	auth.signature,
)
