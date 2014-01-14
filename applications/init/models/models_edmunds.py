#do caching and db stuff here!

def vehicle(spec, **kwargs):
	URI = 'https://api.edmunds.com/api/vehicle/v2/%s?'%spec
	for key,value in kwargs.items():
		URI += "%s=%s&"%(key,value)
	URI = URI[:-1] #remove the trailing &
	response = cache.ram(
		URI, #to make sure the same URI doesn't get called twice
		lambda: json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()
		time_expire=60*60*24,
	)
	return response