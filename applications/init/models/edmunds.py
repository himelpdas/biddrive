from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI, function, time_expire=60*60*24): #ed cache flawed make sure data is ok
	#will call ram >> disk >> API
	URI = repr(URI)
	def disk():
		response = cache.disk(
			URI, #<type 'exceptions.TypeError'> String or Integer object expected for key, unicode found
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

	if not response or 'error' in response or 'status' in response or 'errorType' in response:
		cache.ram(URI, None)
		cache.disk(URI, None)
		return None
		#raise HTTP(response['code'], response['message']) 

	return response

def ed_call(URI):
	"""fewer arguments than ed_cache"""
	return ed_cache(URI, lambda: ed.make_call(URI))
	
YEAR='2013'
MAKES_URI = '/api/vehicle/v2/makes?state=new&year=%s&view=full'
MAKE_URI = '/api/vehicle/v2/%s?state=new&year=%s'
STYLES_URI = '/api/vehicle/v2/%s/%s/%s/styles?state=new&view=full'
STYLE_URI = "/api/vehicle/v2/styles/%s?view=full&fmt=json"
COLORS_URI = '/api/vehicle/v2/styles/%s/colors?category=Exterior&fmt=json'
COLOR_URI = "/api/vehicle/v2/colors/%s?fmt=json"
REVIEWS_URI = "/api/vehiclereviews/v2/styles/%s?sortby=created:ADESC&pagenum=1&pagesize=10"
IMG_PREFIX = "http://media.ed.edmunds-media.com/"

OD([(u'acura', u'Acura'), (u'aston-martin', u'Aston Martin'), (u'audi',
 u'Audi'), (u'bmw', u'BMW'), (u'bentley', u'Bentley'), (u'buick', u'Buick'), (u'cadillac', u'Cadillac'), (u'chevrolet', u'Chevrolet'), (u'chrysler', u'Chrysler'
), (u'dodge', u'Dodge'), (u'fiat', u'FIAT'), (u'ford', u'Ford'), (u'gmc', u'GMC'
), (u'honda', u'Honda'), (u'hyundai', u'Hyundai'), (u'infiniti', u'Infiniti'), (
u'jaguar', u'Jaguar'), (u'jeep', u'Jeep'), (u'kia', u'Kia'), (u'lamborghini', u'Lamborghini'), (u'land-rover', u'Land Rover'), (u'lexus', u'Lexus'), (u'lincoln'
, u'Lincoln'), (u'lotus', u'Lotus'), (u'mini', u'MINI'), (u'maserati', u'Maserati'), (u'mazda', u'Mazda'), (u'mclaren', u'McLaren'), (u'mercedes-benz', u'Mercedes-Benz'), (u'mitsubishi', u'Mitsubishi'), (u'nissan', u'Nissan'), (u'porsche',
u'Porsche'), (u'ram', u'Ram'), (u'rolls-royce', u'Rolls-Royce'), (u'scion', u'Scion'), (u'subaru', u'Subaru'), (u'suzuki', u'Suzuki'), (u'tesla', u'Tesla'), (u'toyota', u'Toyota'), (u'volkswagen', u'Volkswagen'), (u'volvo', u'Volvo'), (u'smart', u'smart')])
#if then in case ed_call fails
BRANDS_LIST = OD()
map(lambda model: BRANDS_LIST.update({model['niceName']:model['name']}),ed_call(MAKES_URI%YEAR)['makes']) #FIXED#TEMP HACK, should be ID:NAME but it was reversed to preserve compatibility with later code

def findPhotosByStyleID(style_id):
	findphotosbystyleid_URI = '/v1/api/vehiclephoto/service/findphotosbystyleid'
	return ed_cache( #cannot use ed_call
		'photos'+str(style_id), #must be unique for each corresponding image 
		lambda: ed.make_call(findphotosbystyleid_URI, comparator='simple', styleId=style_id)  #errors will not be cached! :)
	)

def getStylesByMakeModelYear(make, model, year):
	if int(year) in range(datetime.date.today().year-1, datetime.date.today().year+2):
		return ed_call(STYLES_URI%(make, model, year))['styles'] #(make, model, year)

def getStyleByMakeModelYearStyleID(make, model, year, style_id):
	styles = getStylesByMakeModelYear(make, model, year)
	for each_style in styles:
		if int(each_style['id']) == int(style_id):
			return each_style
			#else None