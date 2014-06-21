from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI, function, time_expire=60*60*24): #ed cache flawed make sure data is ok
	#will call ram >> disk >> API
	URI = repr(URI)
	def disk():
		backup_cache = cache.disk
		if '127.0.0.1' in request.env.http_host: #disk cache doesn't play well across all local development environments
			backup_cache = cache.ram #just use ram cache longer on localhosts
		#response = cache.disk(
		response = backup_cache(	
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
	
YEAR_RANGE=range(datetime.date.today().year-1, datetime.date.today().year+2) #minus 1 more year if it's the first 7 days of the year, so auction active requests don't disappear in searches in the new year
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

def getBrandsList(year):
	brands_list = OD()
	map(lambda model: brands_list.update({model['niceName']:model['name']}),ed_call(MAKES_URI%year)['makes']) #FIXED#TEMP HACK, should be ID:NAME but it was reversed to preserve compatibility with later code
	return brands_list
	
def findPhotosByStyleID(style_id):
	findphotosbystyleid_URI = '/v1/api/vehiclephoto/service/findphotosbystyleid'
	return ed_cache( #cannot use ed_call
		'photos'+str(style_id), #must be unique for each corresponding image 
		lambda: ed.make_call(findphotosbystyleid_URI, comparator='simple', styleId=style_id)  #errors will not be cached! :)
	)

def getStylesByMakeModelYear(make, model, year):
	if int(year) in YEAR_RANGE:
		return ed_call(STYLES_URI%(make, model, year))['styles'] #(make, model, year)

def getStyleByMakeModelYearStyleID(make, model, year, style_id):
	styles = getStylesByMakeModelYear(make, model, year)
	for each_style in styles:
		if int(each_style['id']) == int(style_id):
			return each_style
			#else None
			
def getOption(trim_data, option_type, option_id):
	options_data = trim_data['options']
	options = []
	for each_option_type in options_data:
		if each_option_type['category'] == option_type:
			options = each_option_type['options']
	for each_option in options:
		if int(each_option['id']) == int(option_id):
			return each_option
			
			
def getMsrp(trim_data, option_ids={}):
	trim_data = json.loads(trim_data)
	price = int(trim_data['price']['baseMSRP'])
	options_data = trim_data['options']
	for each_option_key in option_ids:
		options = []
		for each_option_type in options_data:
			if each_option_type['category'] == each_option_key:
				options = each_option_type['options']
		for each_choice in option_ids[each_option_key]:
			for each_option in options:
				if int(each_option['id']) == int(each_choice):
					price+=int(each_option['price']['baseMSRP'] if 'price' in each_option else 0)
	return price
	
def colorChipsErrorFix(style_colors): #experimental
	for each_color in style_colors:
		if each_color['category'] == 'Exterior':
			for counter,each_option in enumerate(each_color['options']):
				if not 'colorChips' in each_option:
					del each_color['options'][counter]
					
def getColorHexByNameOrID(identifier, trim_data):
	name_or_id="id"
	try: int(identifier)
	except ValueError:
		name_or_id="name"
	try:
		trim_data = json.loads(trim_data)
	except TypeError:
		try: trim_data.keys()
		except: raise Exception("Trim_data variable corrupt!")
	color_hex=None
	for each_color in trim_data['colors'][1]['options']:
		if each_color[name_or_id] == identifier:
			color_hex = each_color['colorChips']['primary']['hex']
			break
	if not color_hex:
		raise Exception("Couldn't find color hex by name or ID!")
	return color_hex