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
	
YEAR='2012'
	
#json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()