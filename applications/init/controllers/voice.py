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
	intro =  "Hello! Welcome to the bid drive dot com automated auction validation system."
	gather = "Please %sdial your 12 digit winner code now."% ('re' if bool(message or skip_message) else '',)
	if not skip_message:
		resp.say(message or intro)
	with resp.gather(numDigits=12, action="handle_key.xml", method="POST") as g: #with is like try finally that automatically closes the file via calling __exit__()
		g.say(gather)
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
			g.say("You dialed %s. If this is correct, press 1. Otherwise, press 2 and try again."%(str(list(digit_pressed)).strip('[').strip(']'),))
		
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
			resp.say("Thank you. I will now connect you to your winning dealer. Please hold.")
			winning_offer = db(db.auction_request_offer.id == winner_code_exists.auction_request_offer).select().last()
			winning_dealer = db(db.dealership_info.owner_id == winning_offer.owner_id).select().last()
			#contact_made = winning_offer.update_record(contact_made=True)
			auction_request = db(db.auction_request.id == winning_offer.auction_request).select().last()
			color_names = dict(map(lambda id,name: [id,name], auction_request.color_preference, auction_request.simple_color_names))
			auction_request_vehicle = dict(color = color_names[winning_offer.color], year = auction_request.year, make = auction_request.make, model = auction_request.model, id=auction_request.id) #trim = auction_request.trim_name)
			winning_dealer_phone_number = "+"+''.join(winning_dealer.phone.split("-"))#http://goo.gl/JhE2V
			screen_for_machine_url = URL("screen_for_machine.xml", vars = auction_request_vehicle, scheme=True, host=True)#.split('/')[-1] #url MUST BE absolute, action can be absolute or relative!
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
	message = "This is the bid drive dot com automatic validation system. Press any key to skip this message. Hello. You are the winning bidder of auction ID {id}, for a {color} {year} {make} {model}. The buyer initiated this call and is waiting on the line. Please press any key to connect to the buyer now. ".format(**request.vars)
	with resp.gather(numDigits=1, action="screen_complete.xml", method="POST") as g: #if he pressed something go to a new function.
		g.say(message*3)
	resp.hangup() #hang up if no gather
	return dict(resp=str(resp))
	
def screen_complete():
	#no need to test gather as any key is good
	resp = twiml.Response()
	resp.say("Connecting.")
	return dict(resp=str(resp))
	