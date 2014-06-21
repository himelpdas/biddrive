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
	resp.say("Hello! Welcome to bid drive dot com.")
	with resp.gather(numDigits=10, action="handle_key.xml", method="POST") as g:
		g.say("Please dial your 10 digit winner code now.")
	return(
		dict(
			resp=str(resp) #XML() MOVED TO VIEW #By default web2py escapes string characters passed to view, use XML function to preserve escapable characters (ex < > & etc.)
		)
	)
	
def handle_key():
	"""Handle key press from a user."""
	
	# Get the digit pressed by the user
	digit_pressed = request.post_vars['Digits']
	if digit_pressed:
		resp = twiml.Response()
		# Dial (310) 555-1212 - connect that number to the incoming caller.
		#resp.dial("+13105551212")
		# If the dial fails:
		resp.say("You dialed %s. Is this correct?"%(str(list(digit_pressed)).strip('[').strip(']'),)) #change to csv so operator can say each number separate

		return dict(resp = str(resp))
 
	# If the caller pressed anything but 1, redirect them to the homepage.
	else:
		redirect(URL('init', 'voice', 'index.xml'))