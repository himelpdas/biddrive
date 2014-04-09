def vehicle_content():
	if not request.args:
		return dict() #maybe 404
	#get_vehicle_make
	#get stupid fucking styleid
	#finally get bitch ass pics
	year = datetime.date.today().year
	if request.args(1):
		year = request.args[1]
	
	make_details = ed_call(MAKE_URI%(request.args[0], year))
	make_photos = {}
	for each_model in make_details['models']:
		first_image="http://placehold.it/150x100&text=Image%20Unavailable"
		try:
			model_styles = ed_call(STYLES_URI%(request.args[0], each_model['niceName'], year))
			style_id = model_styles["styles"][0]["id"]
			#
			model_photos = findPhotosByStyleID(style_id) #style is not important so call it model
			photo = model_photos[0]['photoSrcs'][-1] #get any photo
			for each_photo in model_photos[0]['photoSrcs']:
				if each_photo.split('.')[-2].split('_')[-1] == '150':  #but change to proper ratio if found
					photo = each_photo
			first_image = 'http://media.ed.edmunds-media.com'+photo  #errors will not be cached! :)
		except (IndexError, KeyError, TypeError): #indexError
			pass
		finally:
			make_photos.update({each_model['niceName']:first_image})

	return dict(make_details=make_details, make_photos=make_photos, year=year)
	
def color_preference(): #TODO get all data from single call make/model/year
	if not request.args:
		return dict() #maybe 404
	style = getStyleByMakeModelYearStyleID(request.args[0], request.args[1], request.args[2], request.args[3])
	style_colors=style['colors']#[1]['options']
	#make sure color data is safe for the multiselect form submission in request_by_make
	"""
	for each_color in style_colors:#replacced with colorChipsErrorFix()
		if each_color['category'] == 'Exterior':
			counter=0#USE ENUMERATE
			for each_option in each_color['options']:
				if not 'colorChips' in each_option:
					del each_color['options'][counter]
				counter+=1
	"""
	colorChipsErrorFix(style_colors)
	style_colors = style['colors'][1]['options']
	style_color_codes = []
	for each_color in style_colors:
		style_color_codes.append([
			each_color['id'],
			each_color['name']
		])
	session.style_color_codes = style_color_codes
	return dict(style_colors=style_colors)
	
def style_details(): #OLD#getting details by style id rather than parsing through make/model/year makes it harder for hackers to fake get values
	make = request.args[0]
	model = request.args[1]
	year = request.args[2] 
	style_id = request.args[3]
	style = getStyleByMakeModelYearStyleID(make, model, year, style_id)
	style_colors = color_preference()
	colors=[]
	for each_color in style_colors['style_colors']:
		colors.append([each_color['name'], each_color['colorChips']['primary']['hex']])
	stats = dict(
		mpg_city = ['MPG city' , style['MPG']['city'] if 'MPG' in style and 'city' in style['MPG'] else 'N/A'],
		mpg_hwy = ['MPG highway' , style['MPG']['highway'] if 'MPG' in style and 'highway' in style['MPG'] else 'N/A'], #do this for rest!
		fuel_type = ['Fuel type' , style['engine']['fuelType'].capitalize()],
		hp = ['Engine horsepower' , style['engine']['horsepower'] if 'engine' in style and 'horsepower' in style['engine'] else 'N/A'],
		torque = ['Engine torque' , style['engine']['torque'] if 'engine' in style and 'torque' in style['engine'] else 'N/A'],
		v =  ['Engine cylinders' , style['engine']['cylinder']],
		drive = ['Wheel drive' , style['drivenWheels'].capitalize()],
		body = ['Vehicle type' , style['submodel']['body']],
		trans = ['Transmission type' , style['transmission']['transmissionType'].capitalize().replace('_', ' ')],
		speed = ['Transmission speed' , str(style['transmission']['numberOfSpeeds']).capitalize()],
		base_msrp = ['Base MSRP', '$%0.0f'%style['price']['baseMSRP']],
		estimate = ['%s estimate'%APP_NAME.replace('(Alpha)', ''), '$%0.0f'%(int(style['price']['baseMSRP'])-random.randrange(3000,6000),)],
		colors=['Color options', colors],
		manufacturer_code = ['Code', style['manufacturerCode'] if 'manufacturerCode' in style else 'N/A'],
		fuel = ['Fuel', style['engine']['type'].capitalize()],
		doors = ['Vehicle doors' , style['numOfDoors']],
	)
	stats=OD(sorted(stats.items(), key=lambda t: t[1][0])) #sort by 'Cylinders' not 'v'
	return dict(stats = stats, make = make, model = model, year = year, style_id = style_id)

def reviews():
	reviews = ed_call(REVIEWS_URI%request.args[0])
	if reviews and 'reviews' in reviews:
		return dict(reviews = reviews['reviews'])
	else:
		return dict(reviews = {})
		
def style_photos():
	style_id = request.args[0]
	style_photos = findPhotosByStyleID(style_id) or [] #some models doesn't return an image ex. 2014 Kia cadenza.
	photos = []
	for each_photo_set in style_photos:
		for each_photo in each_photo_set['photoSrcs']:
			if each_photo.split('.')[-2].split('_')[-1] == '815': #get the desired ratio
				photos.append(IMG_PREFIX + each_photo)
	if not photos:
		photos.append("http://placehold.it/815x543&text=Image%20Unavailable")
	return dict(photos=photos)
	
#auth requires dealer or buyer or admin
@auth.requires(request.args(0))
@auth.requires_login()
def auction_request_offer_messages():
	auction_request_offer_id = request.args[0]
	join = db.auth_user.on(db.auction_request_offer_message.owner_id==db.auth_user.id) #for some reason [db.auth_user.on...] didn't work here. Maybe it only works for multiple joins.
	messages = db(db.auction_request_offer_message.auction_request_offer == auction_request_offer_id).select(join=join)
	for each_message in messages:
		if each_message.auction_request_offer_message.owner_id == auth.user.id:
			each_message['is_owner'] = True
		else:
			each_message['is_owner'] = False
	#set defaults before form is generated, though it could probably be set even after SQLFORM creation
	db.auction_request_offer_message.auction_request_offer.default = auction_request_offer_id
	db.auction_request_offer_message.owner_id.default = auth.user.id
	#form
	message_form = SQLFORM(db.auction_request_offer_message, _class="form-horizontal")
	if message_form.process().accepted:
		pass
	return dict(messages=messages, message_form=message_form)