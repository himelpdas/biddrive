def index():
	return dict()

@auth.requires_membership('dealers')
def auction_requests():
	if not "sortby" in request.vars:
		redirect(URL(vars=dict(sortby='newest')))
	"""
	It is also possible to build queries using in-place logical operators:
	>>> query = db.person.name!='Alex'
	>>> query &= db.person.id>3
	>>> query |= db.person.name=='John'
	"""
	query = (db.auction_request.id>0) & (db.auction_request.expires >= request.now) #WITHIN TIME AND RADIUS ONLY
	#####filtering#####
	make = request.vars['make']
	if make:
		query &= db.auction_request.make==make
	model = request.vars['model']
	if model:
		query &= db.auction_request.model==model
	year = request.vars['year']
	if year:
		query &= db.auction_request.year==year #move top
	color = request.vars['color']
	if color:
		query &= db.auction_request.color_preference.contains(color)
	#####sorting#####
	sortby = request.vars['sortby']
	orderby = ~db.auction_request.expires #TEMP
	if sortby == "id-up":
		orderby = db.auction_request.id
	if sortby == "id-down":
		orderby = ~db.auction_request.id
	if sortby == "make-up":
		orderby = db.auction_request.make
	if sortby == "make-down":
		orderby = ~db.auction_request.make
	if sortby == "model-up":
		orderby = db.auction_request.model
	if sortby == "model-down":
		orderby = ~db.auction_request.model
	if sortby == "trim-up":
		orderby = db.auction_request.trim_name
	if sortby == "trim-down":
		orderby = ~db.auction_request.trim_name
	if sortby == "newest":
		orderby = ~db.auction_request.expires
	if sortby == "oldest":
		orderby = db.auction_request.expires #not using ID because expires can be changed by admin
		
	auction_requests = db(query).select(orderby=orderby)
	
	#####in memory sorting#####
	if sortby == "colors-most" or sortby == "colors-least":
		reverse = False
		if sortby == "colors-least":
			reverse = True
		auction_requests = auction_requests.sort(lambda row: len(row.color_preference), reverse=reverse)#the sort function takes a rows object and applies a function with each row as the argument. Then it compares the returned numerical value of each row and sorts it 
	
	if sortby == 'closest' or sortby == 'farthest':
		def nearest_requests(row): # move to virtual field
			#my_zip = db(db.dealership_info.owner_id == auth.user_id).select().first().zip_code #todo- how move to computated field any table that has zip code #infact move edmunds shit to custom model validators
			auction_request  = row
			#my_coordinates = db(db.zipgeo.zip_code==my_zip).select().first()
			my_info = db(db.dealership_info.owner_id == auth.user_id).select().first()
			#auction_request_coordinates =  db(db.zipgeo.zip_code==auction_request_zip).select().first()
			#return calcDist(my_coordinates.latitude, my_coordinates.longitude, row.latitude, row.longitude)
			return calcDist(my_info.latitude, my_info.longitude, row.latitude, row.longitude)
		reverse = False
		if sortby == "farthest":
			reverse = True
		auction_requests = auction_requests.sort(nearest_requests, reverse=reverse) #returns new
	
	columns = [ #keep len 12
		[
			'Auction#', 
			['id-up','id-down'], #[caret up, caret down
			1
		],
		[
			'Year', 
			['year-up','year-down'],
			1
		],
		[
			'Make', 
			['make-up','make-down'],
			1
		],
		[
			'Model', 
			['model-up','model-down'],
			1
		],
		[
			'Trim', 
			['trim-up','trim-down'],
			2
		],
		[
			'Colors', #sort by number of colors 
			['colors-most','colors-least'],
			2
		],
		[
			'Zip Code', 
			['closest','farthest'],
			1
		],
		[
			'Ends In', 
			['oldest','newest'],
			1
		],
		[
			'Bids', 
			['most','least'],
			1
		],
		[
			'Best $', 
			['lowest','highest'],
			1
		],
	]

	response.title = "Auction requests"
	response.subtitle = "showing %s results."%len(auction_requests)
	return dict(auction_requests=auction_requests, columns = columns)