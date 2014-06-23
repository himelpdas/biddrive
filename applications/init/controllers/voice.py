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
	intro =  "Hello! Welcome to the bid drive dot com automated auction verification service."
	gather = "Please %sdial your 10 digit winner code now."% 're' if bool(message or skip_message) else ''
	if not skip_message:
		resp.say(message or intro)
	with resp.gather(numDigits=10, action="handle_key.xml", method="POST") as g: #with is like try finally that automatically closes the file via calling __exit__()
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
	if len(digit_pressed) == 10:
		resp = twiml.Response()
		# Dial (310) 555-1212 - connect that number to the incoming caller.
		#resp.dial("+13105551212")
		# If the dial fails:
		with resp.gather(numDigits=1, action="handle_key_check.xml/%s"%digit_pressed, method="POST") as g: #change to csv so operator can say each number separate
			g.say("You dialed %s. If this is correct, press 1. Otherwise, press any other key."%(str(list(digit_pressed)).strip('[').strip(']'),))
		
		return dict(resp = str(resp))
 
	# If the caller pressed anything but 1, redirect them to the homepage.
	else:
		redirect(URL('init', 'voice', 'index.xml', vars=dict(message="I'm sorry. It seems you incorrectly dialed your winner code.")))
		
def handle_key_check():
	digit_pressed = request.post_vars['Digits']
	winner_code = request.args(0)
	if digit_pressed == '1':
		resp = twiml.Response()
		winner_code_exists = db.auction_request_winning_offer.winner_code.contains(digit_pressed) #http://goo.gl/GwI1xN
		if winner_code_exists:
			resp.say("Thank you. I will now connect you to your winning dealer. Please hold.")
			return dict(resp = str(resp))
		else:
			redirect(URL('init', 'voice', 'index.xml', vars=dict(message="I'm sorry. That code doesn't exist in our database.")))
	# If the caller pressed 2 or some other key
	else:
		redirect(URL('init', 'voice', 'index.xml', vars=dict(skip_message=True)))