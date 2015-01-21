from gluon.scheduler import Scheduler

#QUEUE_EXPIRES = datetime.timedelta(days=1)
#TROPO_VOICE_KEY = '251fe697c982b94db08a7203b77d239b0b35c254f2d77f7d76248b2a0f11da61c53950902773c41c15de4d7f'

from twilio.rest import TwilioRestClient
from twilio import twiml

TWILIO_SID = "AC2cec9db22d55360d41944cd2b953804a"
TWILIO_KEY = "34add1bda0569d8c32fa37e2b9a7200b" 
TWILIO_NUMBER = "(857) 453-8317"
TWILIO_NUMBER_CALLER_ID = "1-857-453-8317"
twilio_client = TwilioRestClient(TWILIO_SID, TWILIO_KEY)

"""
Example SMS
sms = twilio_client.sms.messages.create(body="Jenny please?! I love you <3",
    to="+14159352345",
    from=TWILIO_NUMBER_CALLER_ID)
"""

#http://goo.gl/L05FHS
#http://goo.gl/An6V4P
			
def send_email_task(contact, message, subject = None):
	if not IS_EMAIL()(contact)[1]: #for admin stuff #save the api call/resources if false#no error message if its either a tel or email>>> IS_EMAIL()('a@b.com') >>>('a@b.com', None)
		sent = mail.send(
			to=contact,
			subject=subject,
			message=message,
			headers = {'Content-Type' : 'text/html'}, #http://goo.gl/h6N78b #otherwise text/plain
		)
		return sent
	return False
	
def send_sms_task(contact, shortmessage):
	if not IS_MATCH('^1?((-)\d{3}-?|\(\d{3}\))\d{3}-?\d{4}$',)(contact)[1]: #check if phone number
		sms = twilio_client.sms.messages.create(body=shortmessage,
		to=contact,
		from_=TWILIO_NUMBER_CALLER_ID)
	return False
	
	
scheduler = Scheduler(db) #from gluon.scheduler import Scheduler
			
def SEND_ALERT_TO_QUEUE(OVERRIDE_ALERT_SETTING=False, USER=None, MESSAGE_TEMPLATE = None, **MESSAGE_VARS): #setting OVERRIDE_ALERT_SETTING to false means check USERs alert settings before sending
	MESSAGE_DATA = {
		"GENERIC_welcome_to_biddrive": lambda: dict(
			SUBJECT="Welcome to BidDrive, {first_name}!".format(**MESSAGE_VARS),
			MESSAGE="The most efficient way to buy a car!",
			MESSAGE_TITLE=XML("Welcome to <a href='http://www.biddrive.com'>BidDrive.com</a>"),
			WHAT_NOW="What are you waiting for? Submit a request for the car of your dreams!",
			INSTRUCTIONS=XML("If you're a dealer join our team <a href='http://www.biddrive.com/init/default/dealership_form/'>here</a>"),
			CLICK_HERE="Start here!",
			CLICK_HERE_URL="http://www.biddrive.com/",
		),
		"BUYER_on_new_request" : lambda: dict( #need to use lambda because not all {variables} will be available from the dealer, default, and admin controllers... a keyerror would occur
			SUBJECT  =  "{app}: You requested a {year} {make} {model} near your area!".format(**MESSAGE_VARS), 
			MESSAGE =  "Within a {mile} mile radius of {zip}.".format(**MESSAGE_VARS), 
			MESSAGE_TITLE =  XML("You requested a <i>{year} <b>{make}</b> {model}</i>.".format(**MESSAGE_VARS) ),
			WHAT_NOW =  "Stay tuned for offers!", 
			INSTRUCTIONS =  "Dealers near you have been alerted about your request.", 
			CLICK_HERE =  "Go to auction!",
			CLICK_HERE_URL =  "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_request" : lambda: dict(
			SUBJECT  =  "{app}: {she} requested a {year} {make} {model} near your area.".format(**MESSAGE_VARS),
			MESSAGE =  XML("There is a new request for a <i>{year} <b>{make}</b> {model}</i>.".format(**MESSAGE_VARS) ),
			MESSAGE_TITLE = "{she} wants a new {make}!".format(**MESSAGE_VARS),
			WHAT_NOW = "Hurry! Other nearby dealers {make} have been alerted as well.".format(**MESSAGE_VARS),
			INSTRUCTIONS = "Submit your {make} {model} now to grab the buyer's attention first!".format(**MESSAGE_VARS),
			CLICK_HERE = "View auction requests",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_approved_dealership" : lambda: dict(
			SUBJECT  =  "{app}: Your application has just been approved!".format(**MESSAGE_VARS),
			MESSAGE =  "Your request to join the {app} dealer network was approved! So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = "Congratulations! You are now an approved dealer!",
			WHAT_NOW = "Click the button below to look for potential buyers.",
			INSTRUCTIONS = "We'll also alert you when we see new {specialize} requests near your area.".format(**MESSAGE_VARS),
			CLICK_HERE = "See buyer requests!",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_offer" : lambda: dict(
			SUBJECT  =  "{app}: {you_or_he} submitted a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  "{you_or_he} joined auction {aid} just moments ago! So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = XML("{you_or_he} submitted a <i>{car}</i>!".format(**MESSAGE_VARS)),
			WHAT_NOW = "Compare offers from other dealers and adjust your price!",
			INSTRUCTIONS = "Don't worry, we will alert you when offer prices change.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"BUYER_on_new_offer" : lambda: dict(
			SUBJECT  =  "{app}: A new dealer ({dealer_name}) just submitted a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  "{dealer_name} joined your auction just moments ago! So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = "A dealer submitted a {car}!".format(**MESSAGE_VARS),
			WHAT_NOW = "Say hello!",
			INSTRUCTIONS = "You can message this or any other dealer at any time during the duration of this auction.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"BUYER_on_new_bid" : lambda: dict(
			SUBJECT  =  "{app}: {dealer_name} {change} the {car} price to {price}!".format(**MESSAGE_VARS),
			MESSAGE =  "{dealer_name} {change} the price to {price}. So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = "A dealer {change} the price for the <i>{car}</i>!".format(**MESSAGE_VARS),
			WHAT_NOW = "This was the dealer's final bid!" if MESSAGE_VARS['form_is_final_bid'] else "Let other dealers know if you like it!",
			INSTRUCTIONS = 'You can buy this car now! Just press the "buy it now" button for this offer in the auction page.' if MESSAGE_VARS['form_is_final_bid'] else "If you like this bid, go to the auction page and choose this price as your favorite. You can also message other dealers to bargain for better prices.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"BUYER_on_recieve_message" : lambda: dict(
			SUBJECT  =  "{app}: You have a new message about the {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("A dealer for a <i>{car}</i> sent <b>you</b> a message.".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "You have a new message!",
			WHAT_NOW = "{he} wrote:".format(**MESSAGE_VARS),
			INSTRUCTIONS = "{message}:".format(**MESSAGE_VARS),
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_recieve_message" : lambda: dict(
			SUBJECT  =  "{app}: You have a new message about the {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("The buyer for a <i>{car}</i> sent <b>you</b> a message.".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "You have a new message!",
			WHAT_NOW = "{he} wrote:".format(**MESSAGE_VARS),
			INSTRUCTIONS = "{message}:".format(**MESSAGE_VARS),
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),		
		"BUYER_on_new_favorite" : lambda: dict(
			SUBJECT  =  "{app}: A new favorite was chosen for a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("Dealers in your auction were alerted about your favorite <i>{car}</i> offer. So what now?".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "You picked a new favorite!",
			WHAT_NOW = "Dealers have been alerted!",
			INSTRUCTIONS = "Now that dealers know which offer you like the most, they may lower their prices!",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),		
		"DEALER_on_new_favorite" : lambda: dict(
			SUBJECT  =  "{app}: A new favorite was chosen for a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("The buyer for a <i>{car}</i> picked <b>{you_or_him}</b> as the favorite! So what now?".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "{buyer} picked a new favorite!".format(**MESSAGE_VARS),
			WHAT_NOW = "Act fast!" if not MESSAGE_VARS['each_is_favorite'] else 'Keep it up!',
			INSTRUCTIONS = "Make a better offer to convince the buyer that your vehicle is the best deal!" if not MESSAGE_VARS['each_is_favorite'] else 'But stay alert for competing offers that may convince the buyer to have a change of mind!',
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"BUYER_on_new_winner" : lambda: dict(
			SUBJECT  =  "{app}: A winner was chosen for a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("You chose a winning {car}! So what now?".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "You picked a winner!",
			WHAT_NOW = "Connect with the dealer to get your certificate.",
			INSTRUCTIONS = "Click the button below and follow the instructions on the auction page.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_winner" : lambda: dict(
			SUBJECT  =  "{app}: {buyer} picked {you_or_him} as the winner for a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("The buyer for a <i>{car}</i> picked <b>{you_or_him}</b> as the winner! So what now?".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "{buyer} picked a new winner!".format(**MESSAGE_VARS),
			WHAT_NOW = "Try again! You'll have better luck next time." if not MESSAGE_VARS['each_is_winning_offer'] else "Wait for the buyer's call!",
			INSTRUCTIONS = "Tip: Look out for new buyer requests and bid quickly! Having the early attention of a buyer goes a long way." if not MESSAGE_VARS['each_is_winning_offer'] else "The buyer will call you soon via our automatic validation system within your business hours!",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_bid" : lambda: dict(
			SUBJECT  =  "{app}: {dealer} {change} the {car} bid price to ${price}!".format(**MESSAGE_VARS),
			MESSAGE_TITLE =  "{dealer} {change} the price for the {car}!".format(**MESSAGE_VARS),
			MESSAGE = XML("The price was {change} to <b>${price}!</b>".format(**MESSAGE_VARS)),
			WHAT_NOW = "Other dealers have been alerted as well!",
			INSTRUCTIONS = "Make sure you continue to follow other offers and adjust your bid price carefully.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
	}

	if OVERRIDE_ALERT_SETTING or USER.enable_email_alerts:
		scheduler.queue_task(
			send_email_task,
			pargs=[USER.email, response.render(
				'email_alert_template.html', dict(
					APPNAME=APP_NAME,
					NAME = USER.first_name.capitalize(), 
					**MESSAGE_DATA[MESSAGE_TEMPLATE]()
					)
				), MESSAGE_DATA[MESSAGE_TEMPLATE]()["SUBJECT"]
			],
			retry_failed = 10,
			period = 3, # run 5s after previous
			timeout = 30, # should take less than 30 seconds
		)
	if USER.enable_sms_alerts: #since user can be charged, do not allow OVERRIDE_ALERT_SETTING, only explicitly determined by enable_sms_alerts
		tel_number = USER.mobile_phone
		scheduler.queue_task(
			send_sms_task,
			pargs=[tel_number, MESSAGE_DATA[MESSAGE_TEMPLATE]()["SUBJECT"]],
			retry_failed = 5, period = 2, timeout = 10, #less important
		)

db.define_table('delayed_auction_alert_queue',
	Field('auction_request', db.auction_request),
	Field('sent_auction_ending_soon', 'boolean', default = False),
	Field('sent_auction_ended_now', 'boolean', default = False),
	auth.signature,
)