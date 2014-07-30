INTRODUCTORY_CREDITS = 50
CREDITS_PER_AUCTION = 10
CREDITS_PER_SUCCESS = 100

paypal_state =IS_IN_SET(['created', 'approved', 'failed', 'canceled', 'expired',], zero=None)


import paypalrestsdk as Paypal #pip install paypalrestsdk

Paypal.configure({
  "mode": "sandbox", # sandbox or live
  "client_id": "EBWKjlELKMYqRNQ6sYvFo64FtaRLRR5BdHEESmha49TM",
  "client_secret": "EO422dn3gQLgDbuwqTjzrFgFtaRLRR5BdHEESmha49TM" })

db.define_table("credits",
	Field("owner_id", db.auth_user,),
	Field('credits', "integer",),
	Field("latest_reason",), #default="Administrative"),#will not work onvalidation because default is done on insertion
	auth.signature,
)

db.define_table("credit_orders",
	Field("owner_id", db.auth_user,
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
	Field('payment_refunded', 'datetime', default=None),
	auth.signature,
)

db.define_table('credits_history',
	Field("change", 'integer',
		required=True,
	),	
	Field("reason",
		required=True,
	),
	Field("owner_id", db.auth_user,
		required=True,
	),
	auth.signature,
)
