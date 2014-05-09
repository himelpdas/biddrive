USD_PER_CREDIT = 1.0

db.define_table("pending_transaction",
	Field("owner", db.auth_user,
		readable = False,
		writable = False,
	),
	Field('credits'),
	Field('amount', "double",
		compute = lambda row: USD_PER_CREDIT * row.credits
	),
	auth.signature,
)

db.define_table("confirmed_transaction",
	Field("owner", db.auth_user,
		readable = False,
		writable = False,
	),
	Field('credits'),
	Field('amount', "double",),
	auth.signature,
)

