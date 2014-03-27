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
		first_image="http://placehold.it/162x81&text=Image%20Unavailable"
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
	try:
		style_colors=style['colors'][1]['options']
	except IndexError: 
		style_colors = {}
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
	stats = dict(
		mpg_city = ['MPG City' , style['MPG']['city'] if 'MPG' in style and 'city' in style['MPG'] else 'N/A'],
		mpg_hwy = ['MPG Highway' , style['MPG']['highway'] if 'MPG' in style and 'highway' in style['MPG'] else 'N/A'], #do this for rest!
		fuel = ['Fuel Type' , style['engine']['fuelType'].capitalize()],
		hp = ['Horsepower' , style['engine']['horsepower']],
		torque = ['Torque' , style['engine']['torque']],
		v =  ['Cylinders' , style['engine']['cylinder']],
		drive = ['Drive' , style['drivenWheels'].capitalize()],
		body = ['Body type' , style['submodel']['body']],
		trans = ['Transmission type' , style['transmission']['transmissionType'].capitalize().replace('_', ' ')],
		speed = ['Transmission speed' , style['transmission']['numberOfSpeeds']],
		base_msrp = ['Base MSRP ($)' , style['price']['baseMSRP']],
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
	style_photos = findPhotosByStyleID(style_id)
	photos = []
	for each_photo_set in style_photos:
		for each_photo in each_photo_set['photoSrcs']:
			if each_photo.split('.')[-2].split('_')[-1] == '815': #get the desired ratio
				photos.append(IMG_PREFIX + each_photo)
	if not photos:
		photos.append("http://placehold.it/815x543&text=Image%20Unavailable")
	return dict(photos=photos)