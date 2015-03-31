#MODEL
from webspiders import *

SPIDER_CLASSES_AND_SITES = ["AutoManager","Automanager.com"]

SPIDER_FORM_FACTORY = SQLFORM.factory(
	Field('site', 
		required=True,
		requires=IS_IN_SET([SPIDER_CLASSES_AND_SITES], zero=None),
	),
	Field('field_a'),
	Field('field_b'),
	Field('field_c'),
	Field('field_d'),
	Field('field_e'),
	Field('remember', 'boolean', default=False),
	_class="form-horizontal",
)

VIEW_SPIDER_FIELD_INFO = {

		"AutoManager":OD(
			a={
					'name':'Client ID',
					'requires': "IS_NOT_EMPTY",
				},
			b={
					'name':'Username',
					'requires': "IS_NOT_EMPTY", #OR NONE IF NO REQURES
				},
			c={
					'name':'Password',
					'requires': "IS_NOT_EMPTY", #must keep string so JSON can serialize
				},
			d={
					'name':'Stock ID',
					'requires': "IS_NOT_EMPTY",
				},
			e = None,
		)

	}
"""
db.define_table('scrape',
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),	
	Field('site', 
		required=True,
		requires=IS_IN_SET([SPIDER_CLASSES_AND_SITES], zero=None),
	),
	Field('field_a',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('25f36ee9-a785-450e-a091-c7d8718f21e7') )
	),	
	Field('field_b',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('a644ae8f-759f-43ab-985c-0d20a7bf1e80') )
	),	
	Field('field_c',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('c0be32ba-a49e-47ca-927f-2a03cd90b364') )
	),	
	Field('field_d',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('3a78d1be-6ed8-4706-9ca4-38cae1d3cd71') )
	),
	Field('field_e',
		requires = IS_EMPTY_OR(AES_ENCRYPTION_VALIDATOR('774dc102-f32d-4473-89f8-edc310d0ede2') )
	),
	auth.signature,
)
"""