#do caching and db stuff here!

from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI, function, time_expire=60*60*24):
	#will call ram >> disk >> API
	def disk():
		response = cache.disk(
			repr(URI), #<type 'exceptions.TypeError'> String or Integer object expected for key, unicode found
			function,
			time_expire*7,
		)
		return response
	#
	response = cache.ram(
		URI, #to make sure the same URI doesn't get called twice
		disk,
		time_expire,
	)
	return response
	
YEAR='2013'
STYLES_URI = '/api/vehicle/v2/%s/%s/%s/styles?state=new&view=full'
	
#json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()

db.define_table('auction_request',
	Field('owner_id', db.auth_user,
		readable=False,
		writable=False,
		notnull=True,
		default=auth.user_id,
	),
	Field('temp_id',
		readable=False,
		writable=False,
		notnull=True,
		default=auth.user_id, #none if not logged in
	),
	Field('year', 
		readable=False,
		writable=False,
		notnull=True
	),
	Field('make', 
		readable=False,
		writable=False,
		notnull=True
	),
	Field('model', 
		readable=False,
		writable=False,
		notnull=True
	),
	Field('trim_choices', 
		requires=IS_NOT_EMPTY(),
	),
	Field('color_preference', 
		requires=IS_NOT_EMPTY(),
		#widget = SQLFORM.widgets.checkboxes.widget,
	),	
	Field('zip_code', 
		requires=[
			IS_NOT_EMPTY(),
			IS_MATCH(
				'^\d{5}(-\d{4})?$',
        		error_message='not a zip code'
			),
		]
	),
	Field('radius', 
		requires=IS_IN_SET([
			[10, '10 miles'], [25, '25 miles'], [50, '50 miles'], [85, '85 miles'], [130, '130 miles'], [185, '185 miles'], [250, '250 miles'],  
		], zero=None)
	),	
	#Field user ID
	#Block dealers
)