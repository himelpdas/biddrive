"""
#DEFUNCT TROPO TEST
response.view="generic.json"
def index():
	return(
		dict(
			tropo=[{"say":{"value":"Welcome to the Biddrive dot com call center. Testing pronunciation. Hello Neal, Paul, Zaki, Barret, Rob, Christy, and Himel."}}]
			)
	)
def result():
	return(
		dict(
			tropo=[{"hangup":{"value":"Goodbye."}}]
			)
	)
"""
def index():
	resp = twiml.Response()
	skip_message = request.vars['skip_message']
	message = request.vars['message']
	intro =  "Hello! Welcome to the bid drive dot com automatic auction validation system."
	gather = "Please %sdial your 12 digit winner code now."% ('re' if bool(message or skip_message) else '',)
	if not skip_message:
		resp.say(message or intro)
	with resp.gather(numDigits=12, action="handle_key.xml", method="POST") as g: #with is like try finally that automatically closes the file via calling __exit__()
		for each in range(3):
			g.say(gather) #g is gather obj
			g.pause(length=3)
	return(
		dict(
			resp=str(resp) #XML() MOVED TO VIEW #By default web2py escapes string characters passed to view, use XML function to preserve escapable characters (ex < > & etc.)
		)
	)
	
def handle_key():
	"""Handle key press from a user."""
	
	# Get the digit pressed by the user
	digit_pressed = request.post_vars['Digits']
	if len(digit_pressed) == 12:
		resp = twiml.Response()
		# Dial (310) 555-1212 - connect that number to the incoming caller.
		#resp.dial("+13105551212")
		# If the dial fails:
		with resp.gather(numDigits=1, action="handle_key_check.xml/%s"%digit_pressed, method="POST") as g: #change to csv so operator can say each number separate
			for each in range(3):
				g.say("You dialed %s. If this is correct, press 1. Otherwise, press 2 and try again."%(str(list(digit_pressed)).strip('[').strip(']'),))
				g.pause(length=3)
		return dict(resp = str(resp))
 
	# If the caller pressed anything but 1, redirect them to the homepage.
	redirect(URL('init', 'voice', 'index.xml', vars=dict(message="I'm sorry. It seems you incorrectly dialed your winner code.")))
		
def handle_key_check():
	digit_pressed = request.post_vars['Digits']
	winner_code = request.args(0)
	if digit_pressed == '1':
		resp = twiml.Response()
		winner_code_exists = db(db.auction_request_winning_offer.winner_code.contains(winner_code)).select().last() #http://goo.gl/GwI1xN
		if winner_code_exists:
			winning_offer = db(db.auction_request_offer.id == winner_code_exists.auction_request_offer).select().last()
			winning_dealer = db(db.dealership_info.owner_id == winning_offer.owner_id).select().last()
			#time stuff# see if dealer is open now at his location's time. if not open, say schedule
			today_datetime_for_dealer = datetime.datetime.now(timezone(winning_dealer.time_zone))
			weekday_for_dealer = today_datetime_for_dealer.strftime("%A").lower() #extract day of the week #http://goo.gl/dopxlP
			def twelve_to_24hr(time, am_pm):
				hour, minute = map(lambda t: int(t),time.split(':'))
				if am_pm == "AM" and hour == 12: #convert from 12hr to 24hr time. Here 12AM should be 0hr, every other AM is fine
					hour = 0
				elif am_pm == "PM" and hour != 12: #leave 12PM alone, as it is also 12 in 24hr time. Every other PM add 12 to it. Ex. 1PM = 13hr
					hour+=12
				return hour, minute
			opening_time=winning_dealer['%s_opening_time'%weekday_for_dealer]
			closing_time=winning_dealer['%s_closing_time'%weekday_for_dealer]
			is_business_day = closing_time and opening_time #means it has, is, or was open this day
			is_open_now = True
			if is_business_day: #if one if false it's closed
				opening_hour, opening_minute = twelve_to_24hr(*opening_time.split(' ')) #Get schedule for the day of the week at dealer's location. Returns something like ['12:30', 'AM'] for Monday or whatever day it is for dealer... note it could be Tuesday on server's time, but still Monday on dealer's time
				closing_hour, closing_minute = twelve_to_24hr(*closing_time.split(' ')) #Get schedule for the day of the week at dealer's location. Returns something like ['12:30', 'AM'] for Monday or whatever day it is for dealer... note it could be Tuesday on server's time, but still Monday on dealer's time
				opening_datetime_for_dealer = today_datetime_for_dealer.replace(hour=opening_hour, minute=opening_minute)
				closing_datetime_for_dealer = today_datetime_for_dealer.replace(hour=closing_hour, minute=closing_minute)
				if today_datetime_for_dealer < opening_datetime_for_dealer or closing_datetime_for_dealer < today_datetime_for_dealer:
					is_open_now = False
			else:
				is_open_now = False
			if not is_open_now: #means they're closed
				tz_country, tz_zone = winning_dealer.time_zone.split('/') 
				schedule = ''
				for each_day in days_of_the_week:
					opening_time = winning_dealer['%s_opening_time'%each_day]
					closing_time = winning_dealer['%s_closing_time'%each_day]
					if opening_time and closing_time:
						schedule+=" %s, %s through %s."%(each_day, opening_time, closing_time)
				for each in range(3):
					resp.say("I'm sorry. Your winning dealer is not accepting calls at this time. Please call back at the following days, %s %s time.%s Thank you and have a great day. "%(tz_country, tz_zone, schedule) )
					resp.pause(length=3)
			else: #make vehicle details to pass to dealer	and CALL the dealer
				resp.say("Thank you. I will now connect you to your winning dealer. Please hold for up to 5 minutes.")
				auction_request = db(db.auction_request.id == winning_offer.auction_request).select().last()
				color_simple_names = dict(zip(auction_request.colors, auction_request.color_simple_names)) #dict(map(lambda id,name: [id,name], auction_request.colors, auction_request.color_simple_names))
				auction_request_vehicle = dict(_color = color_simple_names[winning_offer.exterior_color], _year = auction_request.year, _make = auction_request.make, _model = auction_request.model, _id=auction_request.id) #trim = auction_request.trim_name)
				winning_dealer_phone_number = "+"+''.join(winning_dealer.phone.split("-"))#http://goo.gl/JhE2V
				screen_for_machine_url = URL("screen_for_machine.xml", args=[winning_offer.id, winner_code], vars = auction_request_vehicle, scheme=True, host=True)#.split('/')[-1] #url MUST BE absolute, action can be absolute or relative!
				dialer = resp.dial(callerId = TWILIO_NUMBER_CALLER_ID) #convert init/voice/screen_for_machine.xml?model=... into screen_for_machine.xml?model=...
				dialer.append(twiml.Number(winning_dealer_phone_number, url = screen_for_machine_url, method="POST")) #allows for interaction (ie. gather) with dealer before he enters the call.. must hang up explicitly if unresponsive or call will connect
				#TODO figure out a way to play music while ringing #dialer.append(twiml.Conference(winner_code, waitUrl=URL('static','audio/on_hold_music.mp3', scheme=True, host=True) ) ) #room name is first argument
				resp.say("The call failed, or the remote party hung up. Goodbye.")
			return dict(resp = str(resp))
		else:
			redirect(URL('init', 'voice', 'index.xml', vars=dict(message="I'm sorry. That code doesn't exist in our database.")))
	
	# If the caller pressed 2 or some other key
	redirect(URL('init', 'voice', 'index.xml', vars=dict(skip_message=True)))

def screen_for_machine():
	resp = twiml.Response()
	winning_offer_id = request.args(0)
	winner_code = request.args(1)
	if set(['_color', '_year', '_make', '_model', '_id']).issubset(request.vars): #test is list values in list w/o comprehensions #http://goo.gl/mxqfX1 #this will NOT run on self redirect because vehicle vars will not be in url, thus it can proceed to db insertion
		message = "This is the bid drive dot com automatic auction validation system. Press any key to skip the following message. Congratulations! You are the winning bidder of auction number {_id}, for a {_color} {_year} {_make} {_model}. The buyer initiated this call and is waiting on the line. Please press any key to connect to the buyer now. ".format(**request.vars)
		hmac_url = URL('voice', 'screen_for_machine.xml', args=[winning_offer_id, winner_code, "screen_complete"], hmac_key=str(winning_offer_id), salt = str(winner_code) ) #need some kinda random number to ensure winner_code is safe... since there is no session to store a uuid, the winner_code is random and private enough
		with resp.gather(numDigits=1, action=hmac_url, method="POST") as g: #if he pressed something go to a new function. #action would be screen_for_machine.xml/screen_complete
			for each in range(3):
				g.say(message)
				g.pause(length=3)
	if "screen_complete" in request.args and URL.verify(request, hmac_key=winning_offer_id, salt = winner_code): #HMAC PROTECT HERE!! Can do it manually too http://goo.gl/SLXU3d
		winning_offer = db(db.auction_request_winning_offer.auction_request_offer == winning_offer_id).select().last()
		contact_made = winning_offer.update_record(contact_made=True)
		#collect money
		winners_piggy = db(db.credits.owner_id==winning_offer.owner_id).select().last()
		winners_piggy.update_record( credits = winners_piggy.credits - CREDITS_PER_SUCCESS) #remove one credit
		db.credits_history.insert(change= -CREDITS_PER_SUCCESS, owner_id=winning_offer.owner_id, reason="Success fee", modified_by=winning_offer.owner_id)
		resp.say("Connecting. ")
	else:
		resp.say("Goodbye. ") #IF POUND PRESSED ACTION WILL NOT BE CALLED!
		resp.hangup() #hang up if no gather
	return dict(resp=str(resp))

"""
def screen_complete(): #IF POOR VOIP PHONE IS BEING CALLED, THE KEY PRESS WILL NOT BE REGISTERED AND THIS ACTION WILL NOT BE CALLED!!! TWILIO PROBABLY REGISTERS IT AS A # PRESS!!!
	#no need to test gather as any key is good
	winning_offer_id = request.args(0)
	winning_offer = db(db.auction_request_offer.id == winning_offer_id).select().last()
	contact_made = winning_offer.update_record(contact_made=True)
	resp = twiml.Response()
	resp.say("Connecting. ")
	return dict(resp=str(resp))
"""
	