db.define_table('zipgeo',
	#id automatically created
	Field('zip_code'),
	Field('state_abbreviation'),
	Field('latitude', 'float'),
	Field('longitude', 'float'),
	Field('city'),
	Field('state'),
)