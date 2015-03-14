
db.define_table('scrape',
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),
	Field('site', 
		required=True,
	),
	Field('stock_id', 
		required=True,
	),
	Field('percent', 'integer', 
		default = 0,
	),
	Field('success', 'boolean', 
	),
	Field('reason',
	),	
	Field('cancel', 'boolean',
		default = False
	),
	auth.signature,
)