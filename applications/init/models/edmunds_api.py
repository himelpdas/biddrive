from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

def ed_cache(URI, function, time_expire=60*60*24): #ed cache flawed make sure data is ok
	#will call ram >> disk >> API
	URI = repr(URI)
	def disk():
		backup_cache = cache.disk
		if platform.system() in ["Darwin", "Windows"]: #disable disk cache on Macs #disk cache doesn't play well across all local development environments, particularly macs #http://stackoverflow.com/questions/1854/python-what-os-am-i-running-on #Problems with windows too on 2.9.11
			backup_cache = cache.ram #so just use ram cache longer instead
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

#color swatch
COLOR_SWATCH = lambda hex, title='': XML('<i class="fa {fa} fa-fw" style="color:#{hex}; text-shadow : -1px 0 black, 0 1px black, 1px 0 black, 0 -1px black;" title="{title}"></i>'.format(hex=hex,title=title, fa="fa-square" if not hex == "ff00ff" else "fa-minus-square") ) #add border so that whites can show #http://goo.gl/2j2bP #http://goo.gl/R9EI3h
BULLET=XML('&nbsp;<i class="fa fa-shield fa-rotate-270"></i>&nbsp;&nbsp;')
OPTION_CATEGORIES = sorted(['Interior', 'Exterior', 'Roof', 'Interior Trim', 'Mechanical','Package', 'Safety', 'Fees', 'Other'])
def CATEGORIZED_OPTIONS(auction_request):
	ar = auction_request
	options_database = zip(ar.options, ar.option_names, ar.option_msrps, ar.option_descriptions, ar.option_categories, ar.option_category_names)
	options_dictionary = OD(map(lambda each_category: [each_category , [] ], OPTION_CATEGORIES)) #make an ordered dict (option_categories already sorted) with all the option categories holding a blank list 
	for each_option in options_database:
		options_dictionary[each_option[4]].append(each_option)
	#print options_dictionary
	return options_dictionary

def getBrandsList(year):
	brands_list = OD()
	makes_this_year = ed_call(MAKES_URI%year)
	map(lambda model: brands_list.update({model['niceName']:model['name']}),makes_this_year['makes'] if makes_this_year else {}) #fixed Nonetype has no attribute __getitem__ #FIXED#TEMP HACK, should be ID:NAME but it was reversed to preserve compatibility with later code
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
	#for each_color in trim_data['colors'][1]['options']: #check instead to find exterior's index, since lambo doesn't have interior color, and therefore exterior is index 0, not 1... thus causing error
	for each_color in trim_data['colors'] [[each['category']=='Exterior' for each in trim_data['colors']].index(True)] ['options']:
		if each_color[name_or_id] == identifier:
			color_hex = each_color['colorChips']['primary']['hex']
			break
	if not color_hex:
		#raise Exception("Couldn't find color hex by name or ID!")
		color_hex="000" #Some how, generic "Blue" (instead of Blu Mediterraneo) label was inputed into a maserati gt convertible auction request database causing an exception to be raised. A temporary fix by removing the raise and returning white worked, however investigate this further. Possible reason is Edmunds API returned Blue. Another reason could be a mix up of color_simple_names with color_pref in auction request, but this is unlikely.
	return color_hex



def getFeaturedCars():
     cars = []
     cars.append({
        'year' :  u'2014',
        'make' :  u'honda',
        'model' : u'accord',
        'types' : u'sedan',
        'image' : u'2014_honda_accord_sedan_ex-l-v-6-wnavigation_fq_oem_2_300.jpg'
     })
     cars.append({
        'year' :  u'2014',
        'make' :  u'ford',
        'model' : u'fusion',
        'types' : u'sedan hybrid',
        'image' : u'2014_ford_fusion_sedan_se_fq_oem_2_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'jeep',
        'model' : u'cherokee',
        'types' : u'suv',
        'image' : u'2014_jeep_cherokee_4dr-suv_trailhawk_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'ford',
        'model' : u'f-150',
        'types' : u'pickup',
        'image' : u'2015_ford_f-150_crew-cab-pickup_platinum_fq_oem_2_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'mazda',
        'model' : u'cx-5',
        'types' : u'suv',
        'image' : u'2014_mazda_cx-5_4dr-suv_grand-touring_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'tesla',
        'model' : u'model-s',
        'types' : u'hybrid sedan sporty',
        'image' : u'2014_tesla_model-s_sedan_p85_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'toyota',
        'model' : u'venza',
        'types' : u'suv',
        'image' : u'2013_toyota_venza_wagon_limited_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'subaru',
        'model' : u'forester',
        'types' : u'suv',
        'image' : u'2014_subaru_forester_4dr-suv_25i-premium-pzev_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'bmw',
        'model' : u'3-series',
        'types' : u'sedan',
        'image' : u'2014_bmw_3-series_sedan_320i_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'toyota',
        'model' : u'sienna',
        'types' : u'minivan',
        'image' : u'2015_toyota_sienna_passenger-minivan_limited-premium-7-passenger_fq_oem_1_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'chrysler',
        'model' : u'town-and-country',
        'types' : u'minivan',
        'image' : u'2013_chrysler_town-and-country_passenger-minivan_limited_fq_oem_2_815.jpg'
     })
     cars.append({
        'year' :  u'2015',
        'make' :  u'nissan',
        'model' : u'370z',
        'types' : u'sporty',
        'image' : u'2013_nissan_370z_coupe_touring_fq_oem_2_815.jpg'
     })
     return cars

"""
OD([(u'acura', u'Acura'), (u'aston-martin', u'Aston Martin'), (u'audi',
 u'Audi'), (u'bmw', u'BMW'), (u'bentley', u'Bentley'), (u'buick', u'Buick'), (u'cadillac', u'Cadillac'), (u'chevrolet', u'Chevrolet'), (u'chrysler', u'Chrysler'
), (u'dodge', u'Dodge'), (u'fiat', u'FIAT'), (u'ford', u'Ford'), (u'gmc', u'GMC'
), (u'honda', u'Honda'), (u'hyundai', u'Hyundai'), (u'infiniti', u'Infiniti'), (
u'jaguar', u'Jaguar'), (u'jeep', u'Jeep'), (u'kia', u'Kia'), (u'lamborghini', u'Lamborghini'), (u'land-rover', u'Land Rover'), (u'lexus', u'Lexus'), (u'lincoln'
, u'Lincoln'), (u'lotus', u'Lotus'), (u'mini', u'MINI'), (u'maserati', u'Maserati'), (u'mazda', u'Mazda'), (u'mclaren', u'McLaren'), (u'mercedes-benz', u'Mercedes-Benz'), (u'mitsubishi', u'Mitsubishi'), (u'nissan', u'Nissan'), (u'porsche',
u'Porsche'), (u'ram', u'Ram'), (u'rolls-royce', u'Rolls-Royce'), (u'scion', u'Scion'), (u'subaru', u'Subaru'), (u'suzuki', u'Suzuki'), (u'tesla', u'Tesla'), (u'toyota', u'Toyota'), (u'volkswagen', u'Volkswagen'), (u'volvo', u'Volvo'), (u'smart', u'smart')])
#if then in case ed_call fails
"""