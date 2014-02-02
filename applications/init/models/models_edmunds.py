#do caching and db stuff here!

from edmunds import Edmunds

ed = Edmunds(EDMUNDS_KEY)

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

def ed_cache(URI, function, time_expire=60*60*24):
	#will call ram >> disk >> API
	def disk():
		response = cache.disk(
			repr(URI), #<type 'exceptions.TypeError'> String or Integer object expected for key, unicode found
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
STYLES_URI = '/api/vehicle/v2/%s/%s/%s/styles?state=new&view=full'
	
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
			IS_MATCH(
				'^\d{5}(-\d{4})?$',
        		error_message='not a zip code'
			),
		]
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
	Field('trim_choices', 
		requires=IS_NOT_EMPTY(),
	),
	Field('color_preference', 
		requires=IS_NOT_EMPTY(), #IS_IN_SET in default controller completely overrides this, but leave here for admin
		#widget = SQLFORM.widgets.checkboxes.widget,
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
	Field('radius', 
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
	#Field user ID
	#Block dealers
)