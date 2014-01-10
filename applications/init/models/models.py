db.define_table('index_bg_image',
	Field('title', unique=True),
	Field('image', 'upload', requires=IS_IMAGE() ),
	format = '%(title)s')

db.define_table('index_hero_image',
	Field('description', unique=True),
	Field('author'),
	Field('URL', requires=IS_URL() ),
	Field('image', 'upload', requires=IS_IMAGE() ),
	format = '%(description)s')

#TODO- implement auto image cropper virtual field