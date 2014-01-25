def vehicle_content():
	if not request.args:
		return dict() #maybe 404
	#get_vehicle_make
	#get stupid fucking styleid
	#finally get bitch ass pics
	make_URI = '/api/vehicle/v2/%s?state=new&year=%s'%(request.args[0], YEAR)
	make_details = ed_cache(
		make_URI,
		lambda: ed.make_call(make_URI),
	)
	make_photos = {}
	for each_model in make_details['models']:
		first_image="http://placehold.it/162x81&text=Image%20Unavailable"
		try:
			styles_URI = STYLES_URI%(request.args[0], each_model['niceName'], YEAR)
			model_styles = ed_cache(
				styles_URI,
				lambda: ed.make_call(styles_URI),
			)
			style_id = model_styles["styles"][0]["id"]
			#
			findphotosbystyleid_URI = '/v1/api/vehiclephoto/service/findphotosbystyleid'
			model_photos = ed.make_call(findphotosbystyleid_URI, comparator='simple', styleId=style_id)
			photo = model_photos[0]['photoSrcs'][-1]
			for each_photo in model_photos[0]['photoSrcs']:
				if each_photo.split('.')[-2].split('_')[-1] == '150':
					photo = each_photo
			first_image = ed_cache(
				style_id, #must be unique for each corresponding image 
			 	lambda:  'http://media.ed.edmunds-media.com'+photo,  #errors will not be cached! :)
			)
		except (IndexError, KeyError): #indexError
			pass
		finally:
			make_photos.update({each_model['niceName']:first_image})

	return dict(make_details=make_details, make_photos=make_photos)
	
def color_preference():
	if not request.args:
		return dict() #maybe 404
	colors_URI = '/api/vehicle/v2/styles/%s/colors?category=Exterior&fmt=json'%request.args[0]
	style_colors = ed_cache(
		colors_URI,
		lambda: ed.make_call(colors_URI),
	)
	style_color_codes = []
	for each_color in style_colors['colors']:
		style_color_codes.append(each_color['name'])
	session.style_color_codes = style_color_codes
	return dict(style_colors=style_colors)
	