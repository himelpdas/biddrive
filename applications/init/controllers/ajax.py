import hmac
import logging
logger = logging.getLogger("web2py.app.biddrive")
logger.setLevel(logging.DEBUG)

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
		except Exception, e:
			logger.exception(e)
		finally:
			make_photos.update({each_model['niceName']:first_image})

	return dict(make_details=make_details, make_photos=make_photos, year=year)
	
def options_content(): #TODO get all data from single call make/model/year
	server_side_digest = hmac.new(str(hash(session.salt)), '%s%s%s%s'%(request.args[0], request.args[1], request.args[2], request.args[3])).hexdigest() #http://goo.gl/BtlcAZ #Make, Model, Year, StyleID, 4 = SESSION_ID #hmac.new("Secret Passphrase", Message);
	client_side_digest = request.args[-1]
	logger.debug("sEC:%s"%server_side_digest); logger.debug("cEC:%s"%client_side_digest)
	if not server_side_digest == client_side_digest:
		raise HTTP(404)
	style = getStyleByMakeModelYearStyleID(request.args[0], request.args[1], request.args[2], request.args[3]) #TODO DIGITALLY SIGN!!
	(make, model, year, style_id) = (request.args[0], request.args[1], request.args[2],  request.args[3])
	def __colors__():
		style_colors=style['colors']#[1]['options']
		#make sure color data is safe for the multiselect form submission in request_by_make
		"""
		for each_color in style_colors:#replaced with colorChipsErrorFix()
			if each_color['category'] == 'Exterior':
				counter=0#USE ENUMERATE
				for each_option in each_color['options']:
					if not 'colorChips' in each_option:
						del each_color['options'][counter]
					counter+=1
		"""
		#colorChipsErrorFix(style_colors)
		#style_colors = style['colors'] [[each['category']=='Exterior' for each in style['colors']].index(True)] ['options']
		color_codes = []
		for each_color in style_colors:
			if  each_color['category'] in ['Interior', 'Exterior']:
				for each_option in each_color['options']:
					color_codes.append(  [  each_option['id'], each_option['name'], each_option['colorChips']['primary']['hex'] if 'colorChips' in each_option else "fffff", each_color['category'] , each_color['category'].lower().replace(" ", "_")  ]  ) #["200466570", "17\" Alloy", "17\" x 7.0\" alloy wheels with 215/45R17 tires", "Exterior", "exterior"]
					#TODO - Use rare color hex to hack a "question mark" icon over a swatch of unknown color
		#color_codes.sort(key=lambda x: x[1])
		session.color_codes = color_codes
		return dict(color_codes=color_codes)
		
	def __options__():
		#each_request["digitally_signed_pre_auction_url"] = URL('dealer','pre_auction', args=[each_request.id], hmac_key=each_request.temp_id, hash_vars=[each_request.id]) #temp_id is a uuid # hmac key, hash_vars and salt all gets hashed together to generate a hash string, and must match with string of the same arguments passed through a hash function. #Note, the digital signature is verified via the URL.verify function. URL.verify also takes the hmac_key, salt, and hash_vars arguments described above, and their values must match the values that were passed to the URL function when the digital signature was created in order to verify the URL.
		#arg 0,1,2,3 is year make model and style id, make hmac key style id, even though it doesn't matter what is used as style id, as long as they're hashed together. salt is a hidden random string defined in _imports.py
		#if not URL.verify(request, hmac_key=request.args[3], salt = session.salt, hash_vars=[request.args[0], request.args[1], request.args[2]): #verifys all args (or ones specified) in a url
		#	return dict()
		trim_data = getStyleByMakeModelYearStyleID(request.args[0], request.args[1], request.args[2], request.args[3]) #TODO DIGITALLY SIGN!!
		options = trim_data['options']
		
		option_codes = []

		for each_option_type in options:
			if each_option_type['category'] in ['Interior', 'Exterior', 'Roof', 'Interior Trim', 'Mechanical','Package', 'Safety', 'Other']:
				for each_option in each_option_type['options']:
					option_codes.append(  [  each_option['id'], each_option['name'], each_option['description'] if 'description' in each_option else None, each_option_type['category'], each_option_type['category'].lower().replace(" ", "_")  ]  ) #["200466570", "17\" Alloy", "17\" x 7.0\" alloy wheels with 215/45R17 tires", "Exterior", "exterior"]
		
		#session.option_codes = map(lambda each_option: [each_option[0],  each_option[1]], option_codes) #requires in default function needs id, names
		session.option_codes = option_codes #requires in default function needs id, names
		
		return dict(option_codes = option_codes)
		
	def __style_details__(): #OLD#getting details by style id rather than parsing through make/model/year makes it harder for hackers to fake get values# FIXED WITH DIGITALLY SIGNED URLS
		#NO NEED TO HMAC VERIFY IT IS DONE IN colors AND options, ONLY DO IN CLIENT VIEW #DRY?
		style_colors = __colors__()
		colors=style_colors['color_codes'][:]
		
		options_descriptions = []
		for each_option in __options__()['option_codes']:
			if each_option[2] and each_option[2] != each_option[1]:
				options_descriptions.append([each_option[1],each_option[2]]) #append name and description

		msrp = int(style['price']['baseMSRP'])
		biddrive_estimate = int(int(style['price']['baseMSRP'])-random.randrange(3000,6000))

		stats = dict(
			base_msrp = ['Base MSRP', "${:,.0f}".format(msrp)],
			estimate = ['%s price (est.)'%APP_NAME.replace('(Alpha)', ''), "${:,.0f}".format(biddrive_estimate)],
			savings = ["Savings (est.)", "${:,.0f}".format(msrp - biddrive_estimate)],
		)
		stats=OD(sorted(stats.items(), key=lambda t: t[1][0])) #sort by 'Cylinders' not 'v'

		details = dict(
			mpg_city = ['MPG city, hwy' , '%s, %s'%(style['MPG']['city'] if 'MPG' in style and 'city' in style['MPG'] else 'N/A', style['MPG']['highway'] if 'MPG' in style and 'highway' in style['MPG'] else 'N/A')],
			#mpg_city = ['MPG city' , style['MPG']['city'] if 'MPG' in style and 'city' in style['MPG'] else 'N/A'],
			#mpg_hwy = ['MPG highway' , style['MPG']['highway'] if 'MPG' in style and 'highway' in style['MPG'] else 'N/A'], #do this for rest!
			#fuel_type = ['Fuel type' , style['engine']['fuelType'].capitalize()],
			hp = ['Motor' , '%s, V%s, %s hp'%(style['engine']['type'].capitalize(), style['engine']['cylinder'] , style['engine']['horsepower'] if 'engine' in style and 'horsepower' in style['engine'] else 'N/A')],
			#torque = ['Engine torque' , style['engine']['torque'] if 'engine' in style and 'torque' in style['engine'] else 'N/A'],
			#v =  ['Cylinders' , style['engine']['cylinder']],
			drive = ['Driven wheels' , style['drivenWheels'].capitalize()],
			body = ['Body type' , '%s door %s'%(style['numOfDoors'],style['submodel']['body'])],
			trans = ['Transmission' ,'%s speed %s'%(str(style['transmission']['numberOfSpeeds']).capitalize(), style['transmission']['transmissionType'].lower().replace('_', ' '))],
			#trans = ['Transmission type' , style['transmission']['transmissionType'].capitalize().replace('_', ' ')],
			#speed = ['Transmission speed' , str(style['transmission']['numberOfSpeeds']).capitalize()],
			colors=['Colors', colors],
			#manufacturer_code = ['Code', style['manufacturerCode'] if 'manufacturerCode' in style else 'N/A'],
			#fuel = ['Fuel type', style['engine']['type'].capitalize()],
			#doors = ['Doors' , style['numOfDoors']],
		)

		return dict(stats = stats, details=details, options_descriptions=options_descriptions, make = make, model = model, year = year, style_id = style_id)
	
	return dict(
		color_codes=__colors__()['color_codes'], option_codes = __options__()['option_codes'], style_details_html_string=XML(response.render('ajax/style_details.html', __style_details__() ) ),
	)

def reviews():
	#leave as is, no need to protect because no vals go into db
	reviews = ed_call(REVIEWS_URI%request.args[0])
	if reviews and 'reviews' in reviews:
		return dict(reviews = reviews['reviews'])
	else:
		return dict(reviews = {})
		
def style_photos():
	#leave as is, no need to protect because no vals go into db
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
	
def dealer_radius_map(): #CACHE CACHE CACHE!!
	#leave as is, no need to protect because no vals go into db
	zipcode = request.args(2)
	radius = request.args[1]
	make = request.args[0]
	error_img = "http://placehold.it/600x400&text=%s"
	urls = [error_img%"Error loading map."]
	dealers = []
	if not zipcode:
		urls=[error_img%"Enter a zip code."]
	elif int(radius) in [10, 25, 50, 85, 130, 185, 250]: #validate
		if not IS_MATCH('^\d{5}(-\d{4})?$')(zipcode)[1]: 
			urls=[error_img%"Wrong zip code."]
			zip_info = db(db.zipgeo.zip_code == zipcode).select().first()
			if zip_info:
				urls=[]
				dealers = db(db.dealership_info.specialty.contains(make)).select()
				dealers = dealers.exclude(lambda row: int(radius) >= calcDist(zip_info.latitude, zip_info.longitude, row.latitude, row.longitude) )#remove requests not in range
				dmap = DecoratedMap()
				dmap.add_marker(AddressMarker(zipcode,label='0',color="green")) #http://goo.gl/vwQIDN Motionless
				for counter, each_dealer in enumerate(dealers):
					#dmap.add_marker(AddressMarker('%s,%s,%s,%s'%(each_dealer.address_line_1, each_dealer.city, each_dealer.state, each_dealer.zip_code),label=str(counter+1)))
					dmap.add_marker(LatLonMarker(lat=each_dealer.latitude,lon=each_dealer.longitude, label=str(counter+1))) #latlon marker not documented had to check source of motionless.py #BIG DIFFERENCE, SHORTER URL FOR MORE POINTERS AND MORE "HIDDEN" -- http://maps.google.com/maps/api/staticmap?maptype=roadmap&format=png&size=600x400&sensor=false&markers=|color:green|label:0|11106&markers=|label:1|3518%2033rd%20st%2CAstoria%2CNY%2C11106 --VS-- http://maps.google.com/maps/api/staticmap?maptype=roadmap&format=png&size=600x400&sensor=false&markers=|label:1|40.757096,-73.927133&markers=|color:green|label:0|11106
				urls.append(dmap.generate_url().replace('400x400', '600x400'))
		else:
			urls=[error_img%"Not a zip code."]

	return dict(urls=urls, make_name=all_brands_list[make], dealer_count=len(dealers))
	
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
	
def contact_made():
	winner_code = request.args(0)
	winning_choice = db(db.auction_request_winning_offer.winner_code == winner_code).select().last()
	status = 'pending'
	if winning_choice and winning_choice.contact_made:
		status = 'success'
	return dict(status=status)
