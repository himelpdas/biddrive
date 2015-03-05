
db.define_table('scrape',
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),
	Field('site', required=True,
	),
	Field('stock_id', required=True,
	),
	Field('percent', 'integer', default = 0,
	),
	Field('success', 'boolean', 
	),
	Field('reason',
	),
	auth.signature,
)
	
db.define_table('stock',
	Field('vin_number', 
		requires=IS_NOT_EMPTY(), required=True
	),
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),
	Field('exterior_color',
		requires=IS_NOT_EMPTY(), required=True
	),	
	Field('exterior_color_name', 
		readable=False, writable=False, required=True
	),	
	Field('interior_color',
		requires=IS_NOT_EMPTY(), required=True,
	),	
	Field('interior_color_name', 
		readable=False, writable=False, required=True
	),
	Field('options', 'list:string',
	),
	Field('option_names', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_descriptions', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_category_names', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_categories', 'list:string', readable=False, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_msrps', 'list:integer', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),
	Field('summary', 'text',
		requires=IS_NOT_EMPTY(),
	),	
	Field('additional_costs', 'integer',
		requires=IS_INT_IN_RANGE(0,20000),
	),
	Field('additional_costs_details', 'text',
	),	
	auth.signature,
)