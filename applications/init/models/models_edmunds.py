#do caching and db stuff here!

from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI):
	response = cache.ram(
		URI, #to make sure the same URI doesn't get called twice
		lambda: ed,
		time_expire=60*60*24,
	)
	return response
	
#json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()