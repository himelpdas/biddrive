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
		requires = IS_EMPTY_OR(CRYPT(key='sha512:thisisthekey') )
	),	
	Field('login_2',
		requires = IS_EMPTY_OR(CRYPT(key='sha512:thisisthekey') )
	),	
	Field('login_3',
		requires = IS_EMPTY_OR(CRYPT(key='sha512:thisisthekey') )
	),	
	Field('login_4',
		requires = IS_EMPTY_OR(CRYPT(key='sha512:thisisthekey') )
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