#do caching and db stuff here!

if not db(db.auth_group.role == "dealers").select().first(): #cache!!
	auth.add_group('dealers', 'only accounts that submitted an admin-verified dealership application may join this group.')

if not db(db.auth_group.role == "admins").select().first(): #cache!!
	auth.add_group('admins', 'has access to various non-public aspects of the database')
	
if auth.user_id:
	if auth.has_membership(user_id = auth.user_id, role = "admins"):
		response.menu.append(
			(T('Admin Portal'), False, URL('admin', 'index.html'), [
				(T('Dealership Requests'), False, URL('admin', 'dealership_requests.html'), []),
				(T('User Management'), False, URL('admin', 'user_management.html'), []),
			]),
		)
	if auth.has_membership(user_id = auth.user_id, role = "dealers"):
		response.menu.append(
			(T('Dealer Portal'), False, URL('dealer', 'index.html'), [
				(T('Auction Requests'), False, URL('dealer', 'auction_requests.html'), []),
			]),
		)

#json.loads(fetch(URI)), #equivalent to urllib.urlopen(URI).read()

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
	Field('phone',
		requires = IS_MATCH(
			'^1?((-)\d{3}-?|\(\d{3}\))\d{3}-?\d{4}$',
			error_message='not a phone number',
		),
	),
	Field('address_line_1',
		requires=IS_NOT_EMPTY(),
	),
	Field('address_line_2'),	
	Field('city',
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
	Field('longitude', 'double',
		compute=lambda row: db(db.zipgeo.zip_code == row['zip_code']).select().first().longitude,
	),
	Field('latitude', 'double',
		compute=lambda row: db(db.zipgeo.zip_code == row['zip_code']).select().first().latitude,
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
	Field('created_on', 'datetime', 
		default=request.now,
		readable=False,
		writable=False,
	),
	Field('changed_on', 'datetime', 
		update=request.now,
		readable=False,
		writable=False,
	),
	Field('changed_by', db.auth_user, 
		update=auth.user_id,
		readable=False,
		writable=False,
	),
)

db.define_table('auction_request',
	Field('owner_id', db.auth_user,
		readable=False,
		writable=False,
		#notnull=True,
		default=auth.user_id,
	),
	Field('temp_id',
		readable=False,
		writable=False,
	),
	Field('year', #default value in controller for validation
		readable=False,
		writable=False,
	),
	Field('make', 
		readable=False,
		writable=False,
	),
	Field('model', 
		readable=False,
		writable=False,
	),
	Field('trim_choices', #change to trim_choice #trim and style are the same
		requires=IS_NOT_EMPTY(),
	),	
	Field('trim_data', #maybe get rid of this field.
		required=True, #prevents None insertions! since compute is runned on insertion/update it may be possible that a failed update will result in a None. This can happen when edmunds cache fails and returns None
		readable=False,
		writable=False,
		compute = lambda row: json.dumps(getStyleByMakeModelYearStyleID(row['make'],row['model'],row['year'],row['trim_choices'])), #FIX compute in controller only!! Since compute runs on update as well edmunds may not return data during UUID to ID conversion #no need to error check because subsequent compute fields will raise native exceptions
	),#move compute to controller to prevent updating of error json returned by edmunds
	Field('trim_name',
		required=True,
		readable=False,
		writable=False,
		compute = lambda row: json.loads(row['trim_data'])['name'], 
	),
	Field('color_preference', 'list:string', #otherwise queries will return string not list!
		requires=IS_NOT_EMPTY(), #IS_IN_SET in default controller completely overrides this, but leave here for admin
		#widget = SQLFORM.widgets.checkboxes.widget,
	),	
	Field('color_names', 'list:string',
		required=True, #tells the DAL that no insert should be allowed on this table if a value for this field is not explicitly specified.
		readable=False,
		writable=False,
		compute = lambda row: [ each_color['name'] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['color_preference'] ], #make a list of color names based on ids in color_preference field
	),
	Field('simple_color_names','list:string',
		required=True,
		readable=False,
		writable =False,
		compute = lambda row: [ simplecolor.predict( (each_color['colorChips']['primary']['r'],each_color['colorChips']['primary']['g'],each_color['colorChips']['primary']['b']), each_color['name'])[1] for each_color in json.loads(row['trim_data'])['colors'][1]['options'] if each_color['id'] in row['color_preference'] ], 
	), #FIXED WITH required=True #WARNING COMPUTE FIELD WILL NOT BREAK INSERTION ON ERROR! COMMON ERROR: KeyError colorChips #WILL RESULT IN FAILURE IN LATER VIEWS
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
	Field('created_on', 'datetime', 
		default=request.now,
		readable=False,
		writable=False,
	),
	Field('changed_on', 'datetime', 
		update=request.now,
		readable=False,
		writable=False,
	),
	Field('expires', 'datetime',
		default = request.now + datetime.timedelta(days = AUCTION_DAYS_EXPIRE),
		readable=False,
		writable=False,
	),
	#virtual fields are not sortable in db use #EDIT USE METHOD INSTESD, which is calculated on demand instead of on on select in queries
	Field.Method('lowest_offer',
		lambda row: db(db.auction_request_offer.auction_request == row.auction_request.id).select(orderby = ~db.auction_request_offer.bid).last()
	),
	Field.Method('number_of_bids',
		lambda row: len(db(db.auction_request_offer.auction_request == row.auction_request.id).select())
	),
	#Field user ID
	#Block dealers
)
"""
	Field('image_limit', 'integer', #returns no such column error #need to add column because migrate issues #SQLITE makes it hard to add/rm columns #SQLITE DATABASE BROWSER #http://goo.gl/SbdnfH #http://goo.gl/Qua42R #ALTER TABLE auction_request ADD COLUMN image_limit INTEGER # UPDATE auction_request SET image_limit = 5
		required = True,
		readable=False,
		writable=False,
		default = 5, #raise limit when purchase made
"""	
db.define_table('auction_request_offer',
	Field('auction_request', db.auction_request,
		readable=False,
		writable=False,
		required=True,
	), 
	Field('owner_id', db.auth_user,
		requires = IS_IN_DB(db, 'dealership_info.owner_id', '%(dealership_name)s',)
	),
	Field('bid', 'double',
		requires = IS_NOT_EMPTY(),
	),
	Field('color',
		requires=IS_NOT_EMPTY(),
	),
	Field('interior_options', 'list:string',
		#requires is_in_set like trim above
		requires=IS_NOT_EMPTY(),
	),
	Field('exterior_options', 'list:string',
		#requires is_in_set like trim above
		requires=IS_NOT_EMPTY(),
	),
	Field('mechanical_options', 'list:string',
		#requires is_in_set like trim above
		requires=IS_NOT_EMPTY(),
	),
	Field('package_options', 'list:string',
		#requires is_in_set like trim above
		requires=IS_NOT_EMPTY(),
	),
	Field('fees_options', 'list:string',
		#requires is_in_set like trim above
		requires=IS_NOT_EMPTY(),
	),
	Field('summary', 'text',
		requires=IS_NOT_EMPTY(),
	),
	Field('exterior_image', 'upload',
		requires=[IS_NOT_EMPTY(), IS_IMAGE()] #change message
	), 
	Field('interior_image', 'upload',
		requires=[IS_NOT_EMPTY(), IS_IMAGE()]
	), 
	#ext
	Field('front_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('rear_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('tire_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	#int
	Field('dashboard_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('passenger_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('trunk_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	#misc
	Field('underhood_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('roof_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	), 
	Field('other_image', 'upload',
		requires=IS_EMPTY_OR(IS_IMAGE())
	),
)

#continue work here
db.define_table('auction_request_offer_image',
	Field('auction_request_offer', 'reference auction_request'), #use temp ID in URL to mask id number# USE HAS PERMISSION INSTEAD
	Field('file', 'upload',
		required=True,
	), 
	Field('description',
		requires=IS_NOT_EMPTY(),
		#can be None so required unnecessary
	),
	Field('type',
		requires = IS_IN_SET(
			['Vehicle', 'Exterior', 'Interior', 'Accessories', 'Imperfection'],
			zero=None
		),
	),
)