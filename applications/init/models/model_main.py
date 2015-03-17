#MODEL

#####GENERATE BRANDSLIST#####

ALL_BRANDS_LIST = OD() #TEMP

for each_year in YEAR_RANGE:
	ALL_BRANDS_LIST.update(GET_BRANDS_LIST(each_year)) #doesn't matter if each_year is int or str because GET_BRANDS_LIST uses string formatting

#useful data structure

all_brands_list_sorted = sorted(ALL_BRANDS_LIST.items(), key=lambda x: x[1]) #niceName, name

times_of_the_day = ['12:00 AM', '12:15 AM', '12:30 AM', '12:45 AM', '1:00 AM', '1:15 AM', '1:30 AM', '1:45 AM', '2:00 AM', '2:15 AM', '2:30 AM', '2:45 AM', '3:00 AM', '3:15 AM', '3:30 AM', '3:45 AM', '4:00 AM', '4:15 AM', '4:30 AM', '4:45 AM', '5:00 AM', '5:15 AM', '5:30 AM', '5:45 AM', '6:00 AM', '6:15 AM', '6:30 AM', '6:45 AM', '7:00 AM', '7:15 AM', '7:30 AM', '7:45 AM', '8:00 AM', '8:15 AM', '8:30 AM', '8:45 AM', '9:00 AM', '9:15 AM', '9:30 AM', '9:45 AM', '10:00 AM', '10:15 AM', '10:30 AM', '10:45 AM', '11:00 AM', '11:15 AM', '11:30 AM', '11:45 AM', '12:00 PM', '12:15 PM', '12:30 PM', '12:45 PM', '1:00 PM', '1:15 PM', '1:30 PM', '1:45 PM', '2:00 PM', '2:15 PM', '2:30 PM', '2:45 PM', '3:00 PM', '3:15 PM', '3:30 PM', '3:45 PM', '4:00 PM', '4:15 PM', '4:30 PM', '4:45 PM', '5:00 PM', '5:15 PM', '5:30 PM', '5:45 PM', '6:00 PM', '6:15 PM', '6:30 PM', '6:45 PM', '7:00 PM', '7:15 PM', '7:30 PM', '7:45 PM', '8:00 PM', '8:15 PM', '8:30 PM', '8:45 PM', '9:00 PM', '9:15 PM', '9:30 PM', '9:45 PM', '10:00 PM', '10:15 PM', '10:30 PM', '10:45 PM', '11:00 PM', '11:15 PM', '11:30 PM', '11:45 PM']

days_of_the_week = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

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
	db[_table].make_name.default = make_name = trim_data['make']['name']
	db[_table].model_name.default = model_name = trim_data['model']['name']
	
	#submodel
	db[_table].body.default = trim_data['submodel']['body']
	
	##trim stuff
	db[_table].trim_data.default = json.dumps(trim_data)
	db[_table].trim_name.default = trim_data['name']
	db[_table].trim_price.default = trim_data['price']['baseMSRP']
	
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
	db[_table].option_names.default = option_names_list
	db[_table].option_msrps.default = option_msrps_list
	db[_table].option_descriptions.default = option_descriptions_list
	db[_table].option_categories.default = option_categories_list
	db[_table].option_category_names.default = option_category_names_list
	
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
		form.errors.colors = "Select %sone interior color and one exterior color!" % "at least " if not _dealer else '' #will only show after built-in validations ex. zip code
	if _dealer:
		if len(color_categories_list) > len(set(color_categories_list)):
			form.errors.colors = "Cannot pick multiple colors for the same category!"
	
	#logger.debug(form.errors)
	db[_table].color_names.default = color_names_list
	db[_table].color_msrps.default = color_msrps_list
	db[_table].color_hexes.default = color_hexes_list
	db[_table].color_categories.default = color_categories_list
	db[_table].color_category_names.default = color_category_names_list
	db[_table].color_simple_names.default = color_simple_names_list

#####DEFINE TABLES#####
db.define_table('dealership_info',
	Field('owner_id', db.auth_user,
		readable=False,
		writable=False,
		#notnull=True,
		default=auth.user_id,
	),
	Field('verification',
		default='awaiting',
		requires=IS_IN_SET([
			'approved', 'awaiting', 'rejected'
		], zero=None),
		readable=False, #for admin change in admin controller
		writable=False,
	),
	Field('dealership_name',
		requires=IS_NOT_EMPTY(),
	),	
	Field('specialty', 'list:string',
		requires=[IS_IN_SET(all_brands_list_sorted, zero=None, multiple=True),IS_NOT_EMPTY(error_message="You must pick at least one brand"),],
		widget =SQLFORM.widgets.multiple.widget
	),	
	Field('mission_statement', 'text',
		requires = IS_NOT_EMPTY(),
	),
	Field('office_phone',
		requires = IS_MATCH(
			REGEX_TELEPHONE,
			error_message='not a phone number',
		),
	),
	Field('address_line_1',
		requires=IS_NOT_EMPTY(),
	),
	Field('address_line_2'),	
	Field('city',
		#requires=[IS_NOT_EMPTY(),IS_IN_DB(db,'zipgeo.city')],
		requires=IS_NOT_EMPTY(),
	),
	Field('state',
		requires=IS_IN_SET([
			'AA','AE','AP','AL','AK','AS','AZ','AR','CA','CO','CT','DE','DC','FM','FL','GA','GU','HI','ID','IL','IN','IA','KS','KY','LA','ME','MH','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','MP','OH','OK','OR','PW','PA','PR','RI','SC','SD','TN','TX','UT','VT','VI','VA','WA','WV','WI','WY'
		], zero=None)
	),
	Field('zip_code', 
		requires=[
			IS_NOT_EMPTY(),
			IS_IN_DB(db,'zipgeo.zip_code'),
		]
	),
	Field('time_zone',
		requires=IS_IN_SET(['US/Alaska', 'US/Arizona', 'US/Central', 'US/Eastern', 'US/Hawaii', 'US/Mountain', 'US/Pacific'], zero=None),
	),
	Field('monday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('monday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('tuesday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('tuesday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('wednesday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('wednesday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('thursday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('thursday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('friday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('friday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('saturday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('saturday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('sunday_opening_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),	
	Field('sunday_closing_time',
		requires=IS_EMPTY_OR(IS_IN_SET(times_of_the_day, zero="Unavailable")),
	),
	Field('longitude', 'double',
		required=True,
		compute=get_most_accurate_longitude_from_address,
	),
	Field('latitude', 'double',
		required=True, #make sure its guaranteed because it can mess things up later if geocoding fails
		compute=get_most_accurate_latitude_from_address,
	),
	Field('country',
		requires=IS_IN_SET([
			'United States'
		], zero=None)
	),
	Field('dealership_license', 'upload', 
		uploadfolder='%s/uploads/dealership/licenses'%request.application, 
		uploadseparate=True
	), #upload in separate folders because after 1000 files searches become slow.
	auth.signature,
)

EXPECTED_DOWN_PMT_REQUIRES = IS_INT_IN_RANGE(0, 100000)
FINANCING_REQUIRES = IS_IN_SET(sorted(['Through the dealership or manufacturer', 'Self-finance (bank, credit union, etc.)']), multiple=False, zero="Choose one") #put in default controller
LEASE_MILEAGE_REQUIRES = IS_IN_SET(sorted(['12,000', '15,000', '18,000']), multiple=False, zero="Choose one")
LEASE_TERM_REQUIRES = IS_IN_SET(sorted(["24 months", "36 months", "39 months", "42 months", "48 months", "Lowest payments"]), multiple=False, zero="Choose one")
MATCHING_CATEGORIES = [['body', "Body type (E.g. SUV, Sedan, Compact, etc.)"], ['year','Year'], ['make','Make (E.g. Ford, Honda, Toyota, etc.)'], ['model','Model (E.g. Accord, Fusion, Grand Cherokee, etc.)'], ['trim','Trim (E.g. EX, LX, Sport, etc.)'], ['colors','Colors'], ['options','Options']]
db.define_table('auction_request',
	Field('owner_id', db.auth_user,
		readable=False,
		writable=False,
		#notnull=True,
		default=auth.user_id,
	),
	Field('temp_id', #UUID4 used for guest users and                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            used for digitally signed URL
		readable=False,
		writable=False,
	),                                                   
	Field('matching', 'list:string',
		requires=IS_IN_SET(MATCHING_CATEGORIES, zero=None, multiple=True),
		default="trim",
	),
	Field('year', #default value in controller for validation
		readable=False,
		writable=False,
	),
	Field('make', 
		readable=False,
		writable=False,
	),	
	Field('make_name', 
		readable=False,
		writable=False,
	),
	Field('model', 
		readable=False,
		writable=False,
	),		
	Field('model_name', #needed for better representation instead of capitalizing niceName in make/model
		readable=False,
		writable=False,
	),
	Field('body', 
		readable=False,
		writable=False,
	),	
	Field('trim', #change to trim_choice #trim and style are the same
		requires=IS_NOT_EMPTY(),
	),	
	Field('trim_data', 'text', #Must be text or blob (65,535) or else 512 character limit in MYSQL (char). Don't use blob because padding error will occur if previous string data in row, blobs are good for binaries.
		required=True, #prevents None insertions! since compute is runned on insertion/update it may be possible that a failed update will result in a None. This can happen when edmunds cache fails and returns None
		readable=False,
		writable=False,
		#compute = lambda row: json.dumps(GET_STYLES_BY_MAKE_MODEL_YEAR_STYLE_ID(row['make'],row['model'],row['year'],row['trim'])), #FIX compute in controller only!! Since compute runs on update as well edmunds may not return data during UUID to ID conversion #no need to error check because subsequent compute fields will raise native exceptions
	),#move compute to controller to prevent updating of error json returned by edmunds
	Field('trim_name',
		required=True,
		readable=True,
		writable=False,
		#compute = lambda row: json.loads(row['trim_data'])['name'], 
	),
	Field('trim_price', 'integer',
		required=True,
		readable=True,
		writable=False,
	),
	Field('colors', 'list:string', #otherwise queries will return string not list!
		#requires=IS_NOT_EMPTY(), #IS_IN_SET in default controller completely overrides this, but leave here for admin
		#widget = SQLFORM.widgets.checkboxes.widget,
	),	
	Field('color_names', 'list:string',
		required=True, #tells the DAL that no insert should be allowed on this table if a value for this field is not explicitly specified.
		readable=False,
		writable=False,
		#compute = lambda row: [ each_color['name'] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['colors'] ], #make a list of color names based on ids in colors field
	),
	Field('color_categories', 'list:string',
		required=True,
		readable=False,
		writable=False
	),	
	Field('color_category_names', 'list:string',
		required=True,
		readable=True,
		writable=False
	),	
	Field('color_hexes', 'list:string',
		required=True,
		readable=True,
		writable=False
	),
	Field('color_msrps', 'list:integer',
		required=True, #tells the DAL that no insert should be allowed on this table if a value for this field is not explicitly specified.
		readable=True,
		writable=False,
	),
	Field('color_simple_names','list:string',
		required=True,
		readable=False,
		writable =False,
		#compute = lambda row: [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['colors'] ], 
	), #FIXED WITH required=True #WARNING COMPUTE FIELD WILL NOT BREAK INSERTION ON ERROR! COMMON ERROR: KeyError colorChips #WILL RESULT IN FAILURE IN LATER VIEWS
	Field('options', 'list:string',
		#requires = IS_IN_SET(sorted(['Sunroof', 'Leather', 'Navigation', 'Heated seats', 'Premium sound', 'Third row seating', 'Cruise Control', 'Video System', 'Bluetooth', 'Satellite Radio', 'Tow Hitch']), multiple=True, zero=None)
	),	
	Field('option_names', 'list:string',
		required=True,
		writable =False,
	),	
	Field('option_msrps', 'list:integer',
		required=True,
		writable =False,
	),	
	Field('option_descriptions', 'list:string',
		required=True,
		writable =False,
	),
	Field('option_categories', 'list:string',
		required=True,
		readable=False,
		writable=False
	),	
	Field('option_category_names', 'list:string',
		required=True,
		readable=True,
		writable=False
	),	
	#add description field
	Field('FICO_credit_score',
		requires = IS_EMPTY_OR(IS_IN_SET(sorted(['780+', '750-799', '720-749', '690-719', '670-689', '650-669', '621-649', '620 or less', ]), multiple=False, zero="I don't know")),
	),
	Field('funding_source',
		requires = IS_IN_SET([['cash',"I'm buying it (cash)"],['loan',"I'll take a loan"], ['lease','I want to lease']], multiple=False, zero=None) #TODO change to choose one
	),	
	Field('financing',
		requires = IS_EMPTY_OR(FINANCING_REQUIRES) #put in default controller but leave here for admin purposes
	),
	Field('expected_down_payment', 'integer',
		requires = IS_EMPTY_OR(EXPECTED_DOWN_PMT_REQUIRES) #leave here just in case even tho it's done in the controller
	),
	Field('lease_mileage', 
		requires = IS_EMPTY_OR(LEASE_MILEAGE_REQUIRES)
	),	
	Field('lease_term', 
		requires = IS_EMPTY_OR(LEASE_TERM_REQUIRES)
	),
	Field('trading_in', 'boolean',
	),	
	Field('describe_trade_in', 'text'
	),
	Field('zip_code', 
		requires=[
			IS_NOT_EMPTY(),
			IS_IN_DB(db,'zipgeo.zip_code'),
			#IS_MATCH(
			#	'^\d{5}(-\d{4})?$',
        	#	error_message='not a zip code'
			#),
		]
	),
	Field('longitude', 'double',
		compute=lambda row: db(db.zipgeo.zip_code == row['zip_code']).select().first().longitude,
	),
	Field('latitude', 'double',
		compute=lambda row: db(db.zipgeo.zip_code == row['zip_code']).select().first().latitude,
	),
	Field('radius', 'double', #must be float or haversine will fail
		requires=IS_IN_SET([
			[10, '10 miles'], [25, '25 miles'], [50, '50 miles'], [85, '85 miles'], [130, '130 miles'], [185, '185 miles'], [250, '250 miles'],  
		], zero=None)
	),	
	Field('auction_expires', 'datetime',
		default = request.now + datetime.timedelta(days = AUCTION_DAYS_EXPIRE),
		readable=False,
		writable=False,
	),	
	Field('offer_expires', 'datetime',
		compute = lambda row: row['auction_expires'] + datetime.timedelta(days = AUCTION_DAYS_OFFER_ENDS),
		readable=False,
		writable=False,
	),
	#virtual fields are not sortable in db use #EDIT USE METHOD INSTESD, which is calculated on demand instead of on on select in queries
	Field.Method('lowest_offer', #of all the bids find the lowest
		lambda row: db(db.auction_request_offer_bid.auction_request == row.auction_request.id).select(orderby = ~db.auction_request_offer_bid.bid).last()
	),
	#Field.Method('favorite_offer', #favorite offer fort this auction request
	#	lambda row: db((db.auction_request_favorite_choice.auction_request == row.auction_request.id)&(db.auction_request_favorite_choice.auction_request_offer == db.auction_request_offer_bid.auction_request_offer)).select().last()
	#),
	Field.Method('number_of_bids',
		lambda row: len(db(db.auction_request_offer_bid.auction_request  ==row.auction_request.id).select())
	),
	Field.Method('auction_expired',
		lambda row: row.auction_request.auction_expires < request.now
	),	
	Field.Method('offer_expired',
		lambda row: row.auction_request.offer_expires < request.now
	),
	Field.Method('estimation',
		lambda row:
			sum([sum(row.auction_request.option_msrps), row.auction_request.trim_price, sum(row.auction_request.color_msrps)])  #add up the base, the options, and the most expensive interior and exterior color choices
	),
	#Field user ID
	#Block dealers
	auth.signature #http://goo.gl/3u2l7r
)

"""
	Field('image_limit', 'integer', #returns no such column error #need to add column because migrate issues #SQLITE makes it hard to add/rm columns #SQLITE DATABASE BROWSER #http://goo.gl/SbdnfH #http://goo.gl/Qua42R #ALTER TABLE auction_request ADD COLUMN image_limit INTEGER # UPDATE auction_request SET image_limit = 5
		required = True,
		readable=False,
		writable=False,
		default = 5, #raise limit when purchase made
"""	
#pip install pillow
from smartthumb import * #http://goo.gl/tiSyz
import os
def resize_offer_image_upload(image, x=1080, y=720, center=True):
	os_slash = '\\' if os.name == 'nt' else '/'
	return SMARTHUMB(
		open(request.folder + '%suploads%s%s'%(os_slash,os_slash,image), 'rb' ), #MAKE SURE BINARY MODE http://goo.gl/Z36WjY #get the file that was just uploaded# make sure test for windows as windows use / vs \
		uuid.uuid4(),
		(x, y), #1080,720
		center,
	)
	

"""	
db.define_table('auction_request_offer',
	Field('auction_request', db.auction_request,
		readable=False,
		writable=False,
		required=True,
	), 
	Field('vin_number', #http://goo.gl/cKY06b
		#requires = IS_MATCH(
		#	"^(([a-h,A-H,j-n,J-N,p-z,P-Z,0-9]{9})([a-h,A-H,j-n,J-N,p,P,r-t,R-T,v-z,V-Z,0-9])([a-h,A-H,j-n,J-N,p-z,P-Z,0-9])(\d{6}))$",
		#	error_message = "Not a US VIN number!"
		#),
		requires=IS_NOT_EMPTY(), required=True
	),
	#Field(
	#	'remember_data_for_30_days', 'boolean', #http://goo.gl/Jx29vY
	#),
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),
	Field('exterior_color',
		requires=IS_NOT_EMPTY(), required=True
	),	
	Field('exterior_color_name', 
		readable=False, writable=False, required=True
	),	
	Field('interior_color',
		requires=IS_NOT_EMPTY(), required=True,
	),	
	Field('interior_color_name', 
		readable=False, writable=False, required=True
	),
	Field('options', 'list:string',
		#requires is_in_set like trim above
		#requires=IS_NOT_EMPTY(),
	),
	Field('option_names', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
		#requires is_in_set like trim above
		#requires=IS_NOT_EMPTY(),
	),	
	Field('option_descriptions', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_category_names', 'list:string', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_categories', 'list:string', readable=False, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),	
	Field('option_msrps', 'list:integer', readable=True, writable=False, #MUST PUT READABLE = WRITABLE = FALSE, BECAUSE CUSTOM FORM WITHOUT THESE FIELDS WILL SUMBIT NONE REGARDLESS OF DEFAULTS DEFINED HERE OR IN CONTROLLER
	),
	Field('summary', 'text',
		requires=IS_NOT_EMPTY(),
	),	
	Field('additional_costs', 'integer',
		requires=IS_INT_IN_RANGE(0,20000),
	),
	Field('additional_costs_details', 'text',
	),	
	Field('exterior_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)
	),	
    Field('exterior_image_compressed', 'list:string', compute = 
		#required = True, #or fails will be silent!! DEBUG IN SHELL
        lambda row: 
            [resize_offer_image_upload(row['exterior_image'],x=500,y=400),resize_offer_image_upload(row['exterior_image'],x=800,y=600)] if row['exterior_image'] else [] #[small, big] NOTE IF ROW.FIELD DOESN'T WORK, TRY ROW.TABLE.FIELD!
    ),
	Field('interior_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)
	), 
    Field('interior_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['interior_image'],x=500,y=400),resize_offer_image_upload(row['interior_image'],x=800,y=600)] if row['interior_image'] else []  #[small, big]
    ),
	#ext
	Field('front_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)
	),
    Field('front_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['front_image'],x=500,y=400),resize_offer_image_upload(row['front_image'],x=800,y=600)] if row['front_image'] else [] #[small, big]
    ),
	Field('rear_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)
	), 
    Field('rear_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['rear_image'],x=500,y=400),resize_offer_image_upload(row['rear_image'],x=800,y=600)] if row['rear_image'] else [] #[small, big]
    ),
	Field('tire_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('tire_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['tire_image'],x=500,y=400),resize_offer_image_upload(row['tire_image'],x=800,y=600)] if row['tire_image'] else [] #[small, big]
    ),
	#int
	Field('dashboard_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('dashboard_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['dashboard_image'],x=500,y=400),resize_offer_image_upload(row['dashboard_image'],x=800,y=600)] if row['dashboard_image'] else [] #[small, big]
    ),
	Field('passenger_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('passenger_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['passenger_image'],x=500,y=400),resize_offer_image_upload(row['passenger_image'],x=800,y=600)] if row['passenger_image'] else [] #[small, big]
    ),
	Field('trunk_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('trunk_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['trunk_image'],x=500,y=400),resize_offer_image_upload(row['trunk_image'],x=800,y=600)] if row['trunk_image'] else [] #[small, big]
    ),
	#misc
	Field('underhood_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('underhood_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['underhood_image'],x=500,y=400),resize_offer_image_upload(row['underhood_image'],x=800,y=600)] if row['underhood_image'] else [] #[small, big]
    ),
	Field('roof_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	), 
    Field('roof_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['roof_image'],x=500,y=400),resize_offer_image_upload(row['roof_image'],x=800,y=600)] if row[''] else [] #[small, big]
    ),
	Field('other_image', 'upload',
		requires=IS_EMPTY_OR(
			IS_IMAGE(
				maxsize=(10000, 10000),
				minsize=(800,600), #min HD
				error_message='Need an image of at least 800x600 pixels!', 
			)
		)	
	),
    Field('other_image_compressed', 'list:string', compute = 
        lambda row: 
            [resize_offer_image_upload(row['other_image'],x=500,y=400),resize_offer_image_upload(row['other_image'],x=800,y=600)] if row[''] else [] #[small, big]
    ),
	###################IMGS#####################
	Field.Method('latest_bid', #this offers latest bid
		lambda row: db((db.auction_request_offer_bid.auction_request == row.auction_request_offer.auction_request) & (row.auction_request_offer.id == db.auction_request_offer_bid.auction_request_offer)).select().first() #get the bid that has this auction request, and auction request offer
	),#continue
	Field.Method('estimation',
		lambda row:
			db(db.auction_request.id == row.auction_request_offer.auction_request).select().last()['trim_price'] + sum(row.auction_request_offer.option_msrps) + row.auction_request_offer.additional_costs
	), #CACHE QUERY
	Field.Method('number_of_bids',
		lambda row: len(db(db.auction_request_offer_bid.auction_request_offer == row.auction_request_offer.id).select())
	),
	auth.signature,
)
"""

VEHICLE_IMAGE_NUMBERS = map(lambda x: x+1, range(10))

auction_request_offer_image_fields = []	
for each in VEHICLE_IMAGE_NUMBERS:
	auction_request_offer_image_fields += [
		Field('image_%s'%each, 'upload',
			requires=IS_EMPTY_OR(
				IS_IMAGE(
					maxsize=(10000, 10000),
					minsize=(320,240), #min HD
					error_message='Need an image of at least 320x240 pixels!', 
				)
			)
		),
		Field('image_compressed_%s'%each, 'list:string', compute = 
			lambda row: 
				[resize_offer_image_upload(row['image_%s'],x=320,y=240),resize_offer_image_upload(row['image_%s'],x=800,y=600)] if row[''] else [] #[small, big]
		),
	]
	

	
db.define_table('auction_request_offer',
	Field('auction_request', db.auction_request,
		readable=False,
		writable=False,
		#required=True,
	), 
	Field('owner_id', 'reference auth_user',
		writable=False,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s')
	),
	Field('status',
		requires = IS_IN_SET(['unsold', 'sold']),
		default = 'unsold'
	),
	Field('vin_number',
		requires=IS_NOT_EMPTY(), required=True
	),
	Field('year', #default value in controller for validation
		readable=False,
		writable=False,
	),
	Field('make', 
		readable=False,
		writable=False,
	),	
	Field('make_name', 
		readable=False,
		writable=False,
	),
	Field('model', 
		readable=False,
		writable=False,
	),		
	Field('model_name', #needed for better representation instead of capitalizing niceName in make/model
		readable=False,
		writable=False,
	),
	Field('body', 
		readable=False,
		writable=False,
	),	
	Field('trim', #change to trim_choice #trim and style are the same
		requires=IS_NOT_EMPTY(),
	),	
	Field('trim_data', 'text', #Must be text or blob (65,535) or else 512 character limit in MYSQL (char). Don't use blob because padding error will occur if previous string data in row, blobs are good for binaries.
		required=True, #prevents None insertions! since compute is runned on insertion/update it may be possible that a failed update will result in a None. This can happen when edmunds cache fails and returns None
		readable=False,
		writable=False,
		#compute = lambda row: json.dumps(GET_STYLES_BY_MAKE_MODEL_YEAR_STYLE_ID(row['make'],row['model'],row['year'],row['trim'])), #FIX compute in controller only!! Since compute runs on update as well edmunds may not return data during UUID to ID conversion #no need to error check because subsequent compute fields will raise native exceptions
	),#move compute to controller to prevent updating of error json returned by edmunds
	Field('trim_name',
		required=True,
		readable=True,
		writable=False,
		#compute = lambda row: json.loads(row['trim_data'])['name'], 
	),
	Field('trim_price', 'integer',
		required=True,
		readable=True,
		writable=False,
	),
	Field('colors', 'list:string', #otherwise queries will return string not list!
		#requires=IS_NOT_EMPTY(), #IS_IN_SET in default controller completely overrides this, but leave here for admin
		#widget = SQLFORM.widgets.checkboxes.widget,
	),	
	Field('color_names', 'list:string',
		required=True, #tells the DAL that no insert should be allowed on this table if a value for this field is not explicitly specified.
		readable=False,
		writable=False,
		#compute = lambda row: [ each_color['name'] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['colors'] ], #make a list of color names based on ids in colors field
	),
	Field('color_categories', 'list:string',
		required=True,
		readable=False,
		writable=False
	),	
	Field('color_category_names', 'list:string',
		required=True,
		readable=True,
		writable=False
	),	
	Field('color_hexes', 'list:string',
		required=True,
		readable=True,
		writable=False
	),
	Field('color_msrps', 'list:integer',
		required=True, #tells the DAL that no insert should be allowed on this table if a value for this field is not explicitly specified.
		readable=True,
		writable=False,
	),
	Field('color_simple_names','list:string',
		required=True,
		readable=False,
		writable =False,
		#compute = lambda row: [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['colors'] ], 
	), #FIXED WITH required=True #WARNING COMPUTE FIELD WILL NOT BREAK INSERTION ON ERROR! COMMON ERROR: KeyError colorChips #WILL RESULT IN FAILURE IN LATER VIEWS
	Field('options', 'list:string',
		#requires = IS_IN_SET(sorted(['Sunroof', 'Leather', 'Navigation', 'Heated seats', 'Premium sound', 'Third row seating', 'Cruise Control', 'Video System', 'Bluetooth', 'Satellite Radio', 'Tow Hitch']), multiple=True, zero=None)
	),	
	Field('option_names', 'list:string',
		required=True,
		writable =False,
	),	
	Field('option_msrps', 'list:integer',
		required=True,
		writable =False,
	),	
	Field('option_descriptions', 'list:string',
		required=True,
		writable =False,
	),
	Field('option_categories', 'list:string',
		required=True,
		readable=False,
		writable=False
	),	
	Field('option_category_names', 'list:string',
		required=True,
		readable=True,
		writable=False
	),	
	Field('summary', 'text',
		requires=IS_NOT_EMPTY(),
	),	
	Field('additional_costs', 'integer',
		requires=IS_INT_IN_RANGE(0,30000),
	),
	Field('additional_costs_details', 'text',
	),	
	Field.Method('latest_bid', #this offers latest bid
		lambda row: db((db.auction_request_offer_bid.auction_request == row.auction_request_offer.auction_request) & (row.auction_request_offer.id == db.auction_request_offer_bid.auction_request_offer)).select().first() #get the bid that has this auction request, and auction request offer
	),#continue
	Field.Method('estimation',
		lambda row:
			sum([row.auction_request_offer.trim_price, sum(row.auction_request_offer.option_msrps), sum(row.auction_request_offer.color_msrps), row.auction_request_offer.additional_costs])
	), #CACHE QUERY
	Field.Method('number_of_bids',
		lambda row: len(db(db.auction_request_offer_bid.auction_request_offer == row.auction_request_offer.id).select())
	),
	auth.signature,
	*auction_request_offer_image_fields
)

#continue work here
db.define_table('auction_request_offer_bid', #MUST find bids by using minimum 2/3 of owner_id, auction_request, and/or auction_request_offer
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',),
		required = True,
		readable=False,
		writable=False,
	),
	Field('auction_request', 'reference auction_request',
		required = True,
		readable=False,
		writable=False,
	), #OLD #use temp ID in URL to mask id number# USE HAS PERMISSION INSTEAD
	Field('auction_request_offer', 'reference auction_request_offer',
		required = True,
		readable=False,
		writable=False,
	),
	Field('bid', 'integer',
		requires = [IS_NOT_EMPTY(),IS_INT_IN_RANGE(999, 1000000)]
	),
	Field('end_sooner_in_hours', 'integer',
		#requires = IS_EMPTY_OR(IS_INT_IN_RANGE(1, 72)) #hours #handle in controller
	),
	Field('final_bid', 'datetime',
		compute= lambda row: request.now+datetime.timedelta(hours = row['end_sooner_in_hours']) if row['end_sooner_in_hours'] else None,
	),
	Field.Method('estimation_discount',
		lambda row, offer=None: 100-(row.auction_request_offer_bid.bid)/float(offer.auction_request_offer.estimation() if offer else db(db.auction_request_offer.id == row.auction_request_offer_bid.auction_request_offer).select().last().estimation())*100,
	),
	auth.signature,
)

db.define_table('auction_request_offer_message',
	Field('auction_request_offer', 'reference auction_request_offer',
		required = True,
		readable = False,
		writable = False,
	),
	Field('auction_request', 'reference auction_request',
		required = True,
		readable=False,
		writable=False,
	),
	Field('owner_id', db.auth_user,
		required = True,
		readable = False,
		writable = False,
	),
	Field('message', 'text',
		required = True,
		requires = IS_NOT_EMPTY(),
	),
	auth.signature,
)

db.define_table('auction_request_favorite_choice',
	Field('auction_request_offer', 'reference auction_request_offer',
		required = True,
		readable = False,
		writable = False,
	),
	Field('auction_request', 'reference auction_request',
		required = True,
		readable=False,
		writable=False,
	),
	Field('owner_id', db.auth_user,
		required = True,
		readable = False,
		writable = False,
	),
	Field('not_until', 'datetime', 
		compute = lambda row: row.created_on + datetime.timedelta(hours=AUCTION_FAVS_EXPIRE),
		readable=False,
		writable=False,
	),
	auth.signature,
)

db.define_table('auction_request_winning_offer',
	Field('auction_request_offer', 'reference auction_request_offer',
		required = True,
		readable = False,
		writable = False,
	),
	Field('auction_request', 'reference auction_request',
		required = True,
		readable=False,
		writable=False,
	),
	Field('owner_id', db.auth_user,
		required = True,
		readable = False,
		writable = False,
	),
	Field('winner_code',
		readable=False,
		writable=False,
		unique = True, length=255, #length=255 needed in mysql #UNCOMMENT IN PRODUCTION
	),
	Field('contact_made', 'datetime',
		default=None,
	),
	auth.signature,
)

db.define_table('auction_request_unread_messages',
	Field('highest_id', 'reference auction_request_offer_message',
		readable=False,
		writable=False,
	),
	Field('auction_request_offer', 'reference auction_request_offer',
		readable = False,
		writable = False,
	),
	Field('auction_request', 'reference auction_request',
		required = True,
		readable=False,
		writable=False,
	),
	Field('owner_id', db.auth_user,
		default = auth.user_id,
		required = True,
		readable = False,
		writable = False,
	),
	auth.signature,
)