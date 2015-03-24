
#####GET ACCURATE COORDINATES COMPUTE FUNCTIONS#####

def get_coordinates_data(row): #geocoding allows one to turn an address into coordinates
	us = geocoders.GeocoderDotUS() #https://code.google.com/p/geopy/wiki/GettingStarted
	location = us.geocode("{str1} {str2} {city} {state} {zip_code}".format(str1 = row['address_line_1'], str2 = row['address_line_2'] or '', city = row['city'], state = row['state'], zip_code = row['zip_code']))
	place, coords = location or (None, None) #fixes latitude longitude compute error when geocoding fails
	return coords

def get_most_accurate_longitude_from_address(row):
	coords = get_coordinates_data(row)
	if coords: # (lat, lon)
		return coords[1]
	else: #fallback to zip code accuracy if geocoding fails
		return db(db.zipgeo.zip_code == row['zip_code']).select().first()["longitude"]

def get_most_accurate_latitude_from_address(row):
	coords = get_coordinates_data(row)
	if coords: # (lat, lon)
		return coords[0]
	else: #fallback to zip code accuracy if geocoding fails
		return db(db.zipgeo.zip_code == row['zip_code']).select().first()["latitude"]

####ON VALIDATE FOR BUYER AND DEALER VEHICLE####

def VALIDATE_VEHICLE(form, make, model, year, _table, _dealer=False): #these defaults need form vars, so must do it in onvalidation
	
	#initialize
	trim_data = GET_STYLES_BY_MAKE_MODEL_YEAR_STYLE_ID(make,model,year,form.vars.trim)
	
	#make model names
	form.vars.make_name = make_name = trim_data['make']['name']
	form.vars.model_name = model_name = trim_data['model']['name']
	
	#submodel
	form.vars.body = trim_data['submodel']['body']
	
	##trim stuff
	form.vars.trim_data = json.dumps(trim_data)
	form.vars.trim_name = trim_data['name']
	form.vars.trim_price = trim_data['price']['baseMSRP']
	
	##options stuff
	option_names_list = []
	option_msrps_list = []
	option_descriptions_list = []
	option_categories_list = []
	option_category_names_list = []
	for each_option_type in trim_data['options']:
		for each_option in each_option_type['options']:
			#logger.debug(each_option)
			if str(each_option['id']) in form.vars['options']:
				option_names_list.append(each_option['name'])
				option_msrps_list.append(each_option['price']['baseMSRP'] if ('price' in each_option and 'baseMSRP' in each_option['price']) else 0 )
				option_descriptions_list.append(each_option['description'] if 'description' in each_option else None) 
				option_categories_list.append(each_option_type['category'])
				option_category_names_list.append(each_option_type['category'].lower().replace(" ", "_"))
	
	#put them in db
	form.vars.option_names = option_names_list
	form.vars.option_msrps = option_msrps_list
	form.vars.option_descriptions = option_descriptions_list
	form.vars.option_categories = option_categories_list
	form.vars.option_category_names = option_category_names_list
	
	##exterior colors
	color_names_list = []
	color_msrps_list = []
	color_categories_list = []
	color_hexes_list = []
	color_category_names_list = []
	color_simple_names_list = []
	for each_color_type in trim_data['colors']:
		for each_color_option in each_color_type['options']:
			if each_color_option['id'] in form.vars['colors']:
				color_names_list.append(each_color_option['name'])
				color_msrps_list.append(int(float(each_color_option['price']['baseMSRP'])) if ('price' in each_color_option and 'baseMSRP' in each_color_option['price']) else 0)
				if 'colorChips' in each_color_option:
					color_hexes_list.append(each_color_option['colorChips']['primary']['hex'])
					color_simple_names_list.append(simplecolor.predict((each_color_option['colorChips']['primary']['r'],each_color_option['colorChips']['primary']['g'],each_color_option['colorChips']['primary']['b']), each_color_option['name'])[1]) #(0.06822856993575846, 'BROWN')
				else:
					color_hexes_list.append('ff00ff')
					color_simple_names_list.append('')
				color_categories_list.append(each_color_type['category'].lower().replace(" ", "_"))
				color_category_names_list.append(each_color_type['category'])
	
	#for to be determined (missing interior or exterior categories
	if any(map(lambda each: each in ['0','1'], form.vars['colors']) ):
		for missing_colors in ['0','1']:
			if missing_colors in form.vars['colors']:
				if missing_colors == '0':
					missing_category = "Interior"				
				if missing_colors == '1':
					missing_category = "Exterior"
				color_names_list.append('%s color to be determined'%missing_category)
				color_msrps_list.append(0)
				color_category_names_list.append(missing_category)
				color_hexes_list.append('ff00ff')
				color_categories_list.append(missing_category.lower().replace(" ", "_")) #id safe
				color_simple_names_list.append('N/A')
	#print map(lambda each: each in [0,1], form.vars['colors'])
	
	#if not ('interior' in color_categories_list and 'exterior' in color_categories_list): #make sure there is at least one interior and one exterior color, or raise form error
	if not set(['interior', 'exterior']).issubset(color_categories_list): #more flexible than above
		form.errors.colors = "Select %sone interior color and one exterior color!" % ("at least " if not _dealer else '') #will only show after built-in validations ex. zip code
	if _dealer:
		form.vars.owner_id = auth.user_id
		if len(color_categories_list) > len(set(color_categories_list)):
			form.errors.colors = "Cannot pick multiple colors for the same category!"
	
	#logger.debug(form.errors)
	form.vars.color_names = color_names_list
	form.vars.color_msrps = color_msrps_list
	form.vars.color_hexes = color_hexes_list
	form.vars.color_categories = color_categories_list
	form.vars.color_category_names = color_category_names_list
	form.vars.color_simple_names = color_simple_names_list

	
def GET_COLOR_CODES(style):
	style_colors=style['colors']
	color_codes = []
	for each_color in style_colors:
		if each_color['category'] in ['Interior', 'Exterior', 'Roof']:
			for each_option in each_color['options']:
				color_codes.append(  [  each_option['id'], each_option['name'], each_option['colorChips']['primary']['hex'] if 'colorChips' in each_option else "ff00ff", each_color['category'] , each_color['category'].lower().replace(" ", "_")  ]  ) #["200466570", "17\" Alloy", "17\" x 7.0\" alloy wheels with 215/45R17 tires", "Exterior", "exterior"]
				#TODO - Use rare color hex to hack a "question mark" icon over a swatch of unknown color# DONE- ff00ff magenta
	all_color_categories = map(lambda each: each[3], color_codes) 
	if not 'Interior' in all_color_categories:
		color_codes.append(  [  0, 'Interior color to be determined', "ff00ff", 'Interior' , 'interior'  ]  )
	if not 'Exterior' in all_color_categories:
		color_codes.append(  [  1, 'Exterior color to be determined', "ff00ff", 'Exterior' , 'exterior'  ]  )
	#color_codes.sort(key=lambda x: x[1])
	session.color_codes = color_codes
	#print color_codes
	return dict(color_codes=color_codes)
	
def GET_OPTION_CODES(style):
	options = style['options']
	
	option_codes = []

	for each_option_type in options:
		if each_option_type['category'] in OPTION_CATEGORIES: #['Interior', 'Exterior', 'Roof', 'Interior Trim', 'Mechanical','Package', 'Safety', 'Other']:
			for each_option in each_option_type['options']:
				option_codes.append(  [  each_option['id'], each_option['name'], each_option['description'] if 'description' in each_option else None, each_option_type['category'], each_option_type['category'].lower().replace(" ", "_")  ]  ) #["200466570", "17\" Alloy", "17\" x 7.0\" alloy wheels with 215/45R17 tires", "Exterior", "exterior"]
	
	#session.option_codes = map(lambda each_option: [each_option[0],  each_option[1]], option_codes) #requires in default function needs id, names
	session.option_codes = option_codes #requires in default function needs id, names
	
	return dict(option_codes = option_codes)
	

	
EXPECTED_DOWN_PMT_REQUIRES = IS_INT_IN_RANGE(0, 100000)

FINANCING_REQUIRES = IS_IN_SET(sorted(['Through the dealership or manufacturer', 'Self-finance (bank, credit union, etc.)']), multiple=False, zero="Choose one") #put in default controller

LEASE_MILEAGE_REQUIRES = IS_IN_SET(sorted(['12,000', '15,000', '18,000']), multiple=False, zero="Choose one")

LEASE_TERM_REQUIRES = IS_IN_SET(sorted(["24 months", "36 months", "39 months", "42 months", "48 months", "Lowest payments"]), multiple=False, zero="Choose one")

MATCHING_CATEGORIES = [['body', "Body type (E.g. SUV, Sedan, Compact, etc.)"], ['year','Year'], ['make','Make (E.g. Ford, Honda, Toyota, etc.)'], ['model','Model (E.g. Accord, Fusion, Grand Cherokee, etc.)'], ['trim','Trim (E.g. EX, LX, Sport, etc.)'], ['colors','Colors'], ['options','Options']]

VEHICLE_STATES = [['unsold','Unsold'], ['sold','Sold'], ['new','New'], ['used','Used'], ['archived','Archived']]

class VEHICLE_STATES_VALIDATOR(object): #http://brunorocha.org/python/web2py/custom-validator-for-web2py-forms.html
	def __init__(self, error_message="Can't be %s and %s!"):
		self.error_message = error_message

	def __call__(self, value):
		error = None
		# CONDITION COMES HERE
		#print value
		if "new" in value and "used" in value:
			error = self.error_message%("new", "used")
		if "sold" in value and "unsold" in value:
			error = self.error_message%("sold", "unsold")
		# IF error != None - value is invalid 
		return (value, error)
		
class AES_ENCRYPTION_VALIDATOR(object): #http://stackoverflow.com/questions/4095339/what-is-the-best-way-to-encrypt-stored-data-in-web2py
    def __init__(self,key): self.key=key
    def __call__(self,value):
        secret = m2secret.Secret() #http://stackoverflow.com/questions/17477394/m2crypto-error-installing-on-windows
        secret.encrypt(value, self.key)
        return secret.serialize()
    def formatter(self,value):
        secret = m2secret.Secret()
        secret.deserialize(value)
        return (secret.decrypt(self.key),None)

		
VEHICLE_IMAGE_NUMBERS = map(lambda x: x+1, range(10))

TIMES_OF_THE_DAY = ['12:00 AM', '12:15 AM', '12:30 AM', '12:45 AM', '1:00 AM', '1:15 AM', '1:30 AM', '1:45 AM', '2:00 AM', '2:15 AM', '2:30 AM', '2:45 AM', '3:00 AM', '3:15 AM', '3:30 AM', '3:45 AM', '4:00 AM', '4:15 AM', '4:30 AM', '4:45 AM', '5:00 AM', '5:15 AM', '5:30 AM', '5:45 AM', '6:00 AM', '6:15 AM', '6:30 AM', '6:45 AM', '7:00 AM', '7:15 AM', '7:30 AM', '7:45 AM', '8:00 AM', '8:15 AM', '8:30 AM', '8:45 AM', '9:00 AM', '9:15 AM', '9:30 AM', '9:45 AM', '10:00 AM', '10:15 AM', '10:30 AM', '10:45 AM', '11:00 AM', '11:15 AM', '11:30 AM', '11:45 AM', '12:00 PM', '12:15 PM', '12:30 PM', '12:45 PM', '1:00 PM', '1:15 PM', '1:30 PM', '1:45 PM', '2:00 PM', '2:15 PM', '2:30 PM', '2:45 PM', '3:00 PM', '3:15 PM', '3:30 PM', '3:45 PM', '4:00 PM', '4:15 PM', '4:30 PM', '4:45 PM', '5:00 PM', '5:15 PM', '5:30 PM', '5:45 PM', '6:00 PM', '6:15 PM', '6:30 PM', '6:45 PM', '7:00 PM', '7:15 PM', '7:30 PM', '7:45 PM', '8:00 PM', '8:15 PM', '8:30 PM', '8:45 PM', '9:00 PM', '9:15 PM', '9:30 PM', '9:45 PM', '10:00 PM', '10:15 PM', '10:30 PM', '10:45 PM', '11:00 PM', '11:15 PM', '11:30 PM', '11:45 PM']

DAYS_OF_THE_WEEK = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

ALL_BRANDS_LIST = OD() #Generate Brands list

for each_year in YEAR_RANGE:
	ALL_BRANDS_LIST.update(GET_BRANDS_LIST(each_year)) #doesn't matter if each_year is int or str because GET_BRANDS_LIST uses string formatting
	
ALL_BRANDS_LIST_NAME_PAIRS_SORTED = sorted(ALL_BRANDS_LIST.items(), key=lambda x: x[1]) #niceName, name