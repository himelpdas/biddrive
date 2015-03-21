#MODEL

db.define_table('scrape',
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),	
	Field('temp_id',
		default=str(uuid.uuid4()),
		readable=True,
		writable=False,
	),
	Field('site', 
		required=True,
		requires=IS_IN_SET([["AutoManager","Automanager.com"]], zero=None),
	),
	Field('stock_id', 
		required=True,
	),
	Field('login_1',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('25f36ee9-a785-450e-a091-c7d8718f21e7') )
	),	
	Field('login_2',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('a644ae8f-759f-43ab-985c-0d20a7bf1e80') )
	),	
	Field('login_3',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('c0be32ba-a49e-47ca-927f-2a03cd90b364') )
	),	
	Field('login_4',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('3a78d1be-6ed8-4706-9ca4-38cae1d3cd71') )
	),
	Field('percent', 'integer', 
		default = 0,
		readable=True,
		writable=False,
	),
	Field('success', 'boolean',
		readable=True,
		writable=False,
	),
	Field('reason',
		readable=True,
		writable=False,
	),	
	auth.signature,
)

VIEW_SPIDER_LABELS = XML(json.dumps(
	{
		"AutoManager":{'1':'Username','2':'Password','3':'Client ID','4':None}
	}
))