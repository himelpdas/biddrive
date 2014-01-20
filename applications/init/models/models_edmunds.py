#do caching and db stuff here!

from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI, function, time_expire=60*60*24):
	#will call ram >> disk >> API
	def disk():
		response = cache.disk(
			URI,
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
	
#json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()

db.define_table('auction_request',
	Field('year', 
		#requires = IS_INT_IN_RANGE(2000, datetime.date.today().year+1, error_message='invalid year!')
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
		widget = SQLFORM.widgets.checkboxes.widget,
	),
	Field('color_preference', 
		requires=IS_IN_SET([
			['white', 'White'], ['black', 'Black'], ['silver', 'Silver'], ['blue', 'Blue'], ['gray', 'Gray'], ['red', 'Red'], ['beige', 'Beige / Brown'], ['green', 'Green'],  ['yellow', 'Yellow / Gold'], 
		], zero=None),
		widget = SQLFORM.widgets.checkboxes.widget,
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