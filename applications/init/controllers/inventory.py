#CONTROLLER

null_defaults = {}
for each_field in db.auction_request_offer.fields[1:]:
	null_defaults.update({each_field:None})
	
root_directory = os.path.normpath(request.folder)
upload_folder =  os.path.normpath('/uploads')
upload_directory =  root_directory + upload_folder

@auth.requires_membership('dealers')
def index():
	
	paging = PAGINATE(request.args(0),request.vars['view'])
	
	sortby = request.vars['sortby']
	sorting = [["make-up", "make-down"], ["model-up", "model-down"], ["trim-up", "trim-down"], ["year-up", "year-down"] ]
	orderby = ~db.auction_request_offer.modified_on
	#DB LEVEL SORTING 
	if sortby == "make-up":
		orderby = db.auction_request_offer.make #this query causes referencing of two tables, so a join has occured
	if sortby == "make-down":
		orderby = ~db.auction_request_offer.make
	if sortby == "model-up":
		orderby = db.auction_request_offer.model
	if sortby == "model-down":
		orderby = ~db.auction_request_offer.model
	if sortby == "trim-up":
		orderby = db.auction_request_offer.trim_name
	if sortby == "trim-down":
		orderby = ~db.auction_request_offer.trim_name
	if sortby == "year-up":
		orderby = db.auction_request_offer.year
	if sortby == "year-down":
		orderby = ~db.auction_request_offer.year
		
	show = request.vars['show']
	if not show or not show in map(lambda each_pair: each_pair[0], VEHICLE_STATES):
		show = "all"
	show_list = sorted( map(lambda x: x[0],VEHICLE_STATES) + ["all"])
	query = (db.auction_request_offer.id > 0) & (db.auction_request_offer.owner_id == auth.user_id) #must
	#left = db.auction_request.on(db.auction_request_offer.auction_request == db.auction_request.id)
	if (not show == "all") and (show in show_list[:2]): #all is inert
		query &= db.auction_request_offer.status.contains(show)
	else:
		query &= ~db.auction_request_offer.status.contains('archived') #don't show archived by default

	my_inventory = db(query).select(
		#left=left, 
		limitby = paging['limitby'],
		orderby = orderby
	)
	
	for each_vehicle in my_inventory:
		int_ext_colors = GET_OFFER_ROW_INT_EXT_COLORS(each_vehicle)
		each_vehicle['interior_color'] = int_ext_colors[0]
		each_vehicle['exterior_color'] = int_ext_colors[1]
	
	scrape_form = SPIDER_FORM_FACTORY
	
	def onvalidation(form):
		spider_class = form.vars['site']
		spider = VIEW_SPIDER_FIELD_INFO[spider_class]
		for each_field_letter in spider:
			each_field = spider[each_field_letter]
			if each_field:
				if each_field['requires']:
					validator = globals()[each_field['requires']]
					run_validator = validator()(form.vars["field_%s"%each_field_letter])
					error_message = run_validator[1]
					if error_message:
						form.errors["field_%s"%each_field_letter] = error_message #>>> IS_NOT_EMPTY()("") returns ('', 'Enter a value') ### >>> IS_NOT_EMPTY()("test") returns ('test', None)
					
	if scrape_form.process(keepvalues=True, onvalidation=onvalidation, hide_error=True, message_onfailure="@Errors in form. Please check it out.").accepted:
		try: #REMOVE FOR TESTING
			with automanager.AutoManager(
					userid=auth.user_id, 
					savedir=upload_directory,
					field_a=scrape_form.vars['field_a'],
					field_b=scrape_form.vars['field_b'],
					field_c=scrape_form.vars['field_c'],
					field_d=scrape_form.vars['field_d'],
					field_e=scrape_form.vars['field_e'],
				) as spider:
					image_updates = {}
					defaults = {}
					defaults.update(null_defaults)
					
					for i, each_photo_file in enumerate(spider.photos[ : VEHICLE_IMAGE_NUMBERS[-1]-1]): #or else will get: Field image_compressed_11 does not belong to the table
						field_number = i+1
						image_upload = db.auction_request_offer['image_%s'%field_number].store(each_photo_file, str(uuid.uuid4()))
						del defaults["image_compressed_%s"%field_number] #can't be None defaults for compute fields to run
						image_updates.update({"image_%s"%field_number:image_upload})

					defaults.update(image_updates)
					defaults.update({'summary' : spider.description, 'status' : ['unsold','new'], 'mileage':spider.mileage, 'additional_costs':0})
					new_vehicle = db.auction_request_offer.insert(**defaults) #create a new offer, with some elements already pre-filled. Will not show up in views until form submit is executed, since onvalidation changes owner_id from None to auth_user.id
		except:
			session.flash = "@Failed to import vehicle! Please double-check your information or try again later."
			redirect(URL('inventory', 'index'))
				
		session.flash = "$Inserted %s!"%new_vehicle
		redirect(URL("inventory","vin_decode", args=[spider.VIN, new_vehicle]))
	
	response.title="My inventory" + (": %s vehicles"%show.capitalize().replace("_", " ") if show else "")
	
	return dict(my_inventory=my_inventory, sorting=sorting, show_list=show_list, scrape_form=scrape_form, **paging)
	
@auth.requires(request.args(0))
@auth.requires_membership('dealers')
def vin_decode():
	clean_vin = "".join(request.args[0].split()).replace("_","") #odd behavior: %20KNDJT2A56C7438499 gets passed as _KNDJT2A56C7438499 in request.args, so replace '_' with '' as quickfix #http://stackoverflow.com/questions/3739909/how-to-strip-all-whitespace-from-string
	#print clean_vin
	vin_info = EDMUNDS_CALL(VIN_DECODE_URI % clean_vin)
	is_imported = request.args(1)
	if vin_info:
		make = vin_info['make']['niceName']
		model = vin_info['model']['niceName']
		year = vin_info['years'][0]['year']
		#print year, make, model
		if is_imported:
			vehicle = db(db.auction_request_offer.id == int(is_imported) ).select().last()
			vehicle.update_record(make = make, model = model, year=year, vin_number = clean_vin)
			vehicle_id = vehicle.id
		else:
			defaults = {}
			defaults.update(null_defaults)
			defaults.update(dict(make = make, model = model, year=year, vin_number = clean_vin, status=['unsold','new'], additional_costs=0))
			vehicle_id = db.auction_request_offer.insert( **defaults)
		redirect(URL('inventory', 'vehicle', args=[vehicle_id]) )

	session.flash = "@Failed to decode VIN number! Please double-check VIN and try again."
	redirect(URL('inventory', 'index'))
	
@auth.requires(request.args(0))
@auth.requires_membership('dealers')
@auth.requires(URL.verify(request, hmac_key = HMAC_KEY, hash_vars=[request.args(0)], salt=str(session.salt)))
def del_vehicle():
	id = request.args[0]
	record = db(db.auction_request_offer.id==int(id)).select().last()
	compressed_image_path = root_directory + os.path.normpath("/static/thumbnails")
	for each_number in VEHICLE_IMAGE_NUMBERS:
		try:
			each_image = os.path.normpath("/"+record["image_%s"%each_number])
			os.remove(upload_directory + each_image)
			for each_image_name in record["image_compressed_%s"%each_number]:
				each_compressed_image = os.path.normpath("/"+each_image_name)
				os.remove(compressed_image_path + each_compressed_image)
		except:
			pass
		finally:
			record.delete_record()
	session.flash = "$Deleted vehicle record ID %s."%id
	redirect(URL('inventory', 'index'))
	
@auth.requires(request.args(0))
@auth.requires_membership('dealers')
def vehicle():

	vehicle_id = int(request.args[0])
	vehicle = db(db.auction_request_offer.id == int(vehicle_id) ).select().last()
	
	year = vehicle.year
	make = vehicle.make
	model = vehicle.model
	
	db.auction_request_offer.year.default=year
	db.auction_request_offer.make.default=make
	db.auction_request_offer.model.default=model
	#db.auction_request_offer.created_on.default=request.now #moved to model
	
	edit_record = db(db.auction_request_offer.id == vehicle_id).select().last() #can't have none ID so it's safe to use request.args
	editable = bool(edit_record.trim_data)
	
	model_styles = EDMUNDS_CALL(STYLES_URI%(make, model, year))['styles'] #GET_STYLES_BY_MAKE_MODEL_YEAR instead to limit years
	
	#print model_styles
	
	if not model_styles:
		session.message='@Invalid Year!'
		redirect(URL('index.html'))
		
	trims = []
	for each_style in model_styles:
		trims.append(
			[each_style['id'], each_style['name']]
		)	
	trims.sort()

	db.auction_request_offer.trim.requires = IS_IN_SET(trims, zero=None)
	#trim_data = json.loads(auction_request_offer.trim_data)
	
	color_codes = []
	option_codes= [] #needed for SQLFORM to create proper IS_IN_SET widget
	if not request.post_vars: #if get: needed to prevent use of incorrect color_codes
		if editable:
			GET_COLOR_CODES(json.loads(edit_record['trim_data'])) #session.color_codes needed to prefill edit form data. Also make sure this isn't done in form submit, because trim_data might be different from the previous record.
			GET_OPTION_CODES(json.loads(edit_record['trim_data']))
		else:
			session.color_codes = []
			session.option_codes = []
		
	if session.color_codes: #generated by ajax/colors
		color_codes = session.color_codes #this is to update IS_IN_SET to the changes returned by the ajax function (stored in session so it can be used cross site), which is called every time user changes trim choices field
	if session.option_codes:
		option_codes = session.option_codes #["200466570", "17\" Alloy", "17\" x 7.0\" alloy wheels with 215/45R17 tires", "Exterior", "exterior"]
	
	db.auction_request_offer.colors.requires = [IS_IN_SET( map(lambda each_color: [each_color[0],  each_color[1]], color_codes), multiple=True)] #OLD [IS_IN_SET(color_codes, multiple=True, zero=None), IS_NOT_EMPTY(error_message='pick at least one color')]
	db.auction_request_offer.colors.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	#db.auction_request_offer.options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
		
	db.auction_request_offer.options.requires = [IS_IN_SET( map(lambda each_option: [each_option[0],  each_option[1]], option_codes), multiple=True)] #requires needs [id, name]'s
	db.auction_request_offer.options.widget=SQLFORM.widgets.multiple.widget #multiple widget will not appear when IS_IN_SET is combined with other validators
	
	db.auction_request_offer.auction_request.default = None
	db.auction_request_offer.owner_id.default = auth.user_id
	
	form = SQLFORM(db.auction_request_offer, record = edit_record.id, _class="form-horizontal") #to add class to form #http://goo.gl/g5EMrY
	
	if form.process(keepvalues=True, onvalidation=lambda form:VALIDATE_VEHICLE(form, make, model, year, 'auction_request_offer', _dealer=True), hideerror=True, message_onfailure="@Errors in form. Please check it out.").accepted: #hideerror = True to hide default error elements #change error message via form.custom
		redirect(URL("inventory","index"))
		
	response.title="Add a vehicle to your inventory"
	return dict(form = form, year=year, make=make, model=model, editable=editable, edit_record=edit_record) #options=options, option_codes=option_codes,) #msrp_by_id=msrp_by_id, )
