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


#http://goo.gl/L05FHS
#http://goo.gl/An6V4P

#EMAIL_NEW_FAVORITE_OFFER_SUBJECT = """%s You're the new favorite! (Auction #%s)"""

db.define_table('alert_setting',
	Field('owner_id', db.auth_user,
		readable=False,
		writable=False,
		#notnull=True,
		default=auth.user_id,
	),
	Field('SMS_enabled', 'boolean', default=True),
	Field('on_new_request', 'boolean', default=True),
	Field('on_new_offer', 'boolean', default=True),
	Field('on_new_bid', 'boolean', default=True),
	Field('on_recieve_message', 'boolean', default=True),
	Field('on_new_favorite', 'boolean', default=True),
	Field('on_new_winner', 'boolean', default=True),
)
			
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
	
	
scheduler = Scheduler(db) #from gluon.scheduler import Scheduler

def get_alert_setting_table_for_user(USER):
	user_alert_setting=db(db.alert_setting.owner_id==USER.id).select().last()
	if not user_alert_setting: #create the table for user
		new_alert_setting_id = db.alert_setting.insert(owner_id=USER.id)		
		user_alert_setting=db(db.alert_setting.id==new_alert_setting_id).select().last()
	return user_alert_setting
			
def SEND_ALERT_TO_QUEUE(CHECK=None, USER=None, MESSAGE_TYPE = None, **MESSAGE_VARS):
	"""
		#original DRY
		if "new_offer" in auction_request_user.alerts:
					scheduler.queue_task(
						send_alert_task,
						pargs=['email', auction_request_user.email, response.render('email_alert_template.html', dict(
							APPNAME=APP_NAME,
							NAME = auction_request_user.first_name.capitalize(), 
							MESSAGE = XML("%s joined your auction just moments ago! So what now?"%(my_initials,) ),
							MESSAGE_TITLE = "A dealer submitted a %s!"%(car, ),
							WHAT_NOW = "Say hello!",
							INSTRUCTIONS = "You can message this or any dealer at any time during the duration of this auction.",
							CLICK_HERE = "Go to auction",
							CLICK_HERE_URL = URL(args=request.args, host=True, scheme=True),
						)), "%s: A new dealer submitted a %s!"%(APP_NAME, car)],
						retry_failed = 10,
						period = 3, # run 5s after previous
						timeout = 30, # should take less than 30 seconds
					)
		"""
	MESSAGE_DATA = {
		"BUYER_on_new_request" : lambda: dict( #need to use lambda because not all {variables} will be available from the dealer, default, and admin controllers... a keyerror would occur
			SUBJECT  =  "{app}: You requested a {year} {make} {model} near you!".format(**MESSAGE_VARS), 
			MESSAGE =  "Within a {mile} mile radius of {zip}.".format(**MESSAGE_VARS), 
			MESSAGE_TITLE =  XML("You requested a <i>{year} <b>{make}</b> {model}</i>.".format(**MESSAGE_VARS) ),
			WHAT_NOW =  "Stay tuned for offers!", 
			INSTRUCTIONS =  "Dealers near you have been alerted about your request.", 
			CLICK_HERE =  "Go to auction!",
			CLICK_HERE_URL =  "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_request" : lambda: dict(
			SUBJECT  =  "{app}: New request for a {year} {make} {model} near your area.".format(**MESSAGE_VARS),
			MESSAGE =  XML("There is a new request for a <i>{year} <b>{make}</b> {model}</i>.".format(**MESSAGE_VARS) ),
			MESSAGE_TITLE = "{she} wants a new {make}!".format(**MESSAGE_VARS),
			WHAT_NOW = "Hurry! Other nearby dealers {make} have been alerted as well.".format(**MESSAGE_VARS),
			INSTRUCTIONS = "Submit your {make} {model} now to grab the buyer's attention first!".format(**MESSAGE_VARS),
			CLICK_HERE = "View auction requests",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_approved_dealership" : lambda: dict(
			SUBJECT  =  "{app}: You have been approved!".format(**MESSAGE_VARS),
			MESSAGE =  "Your request to join the {app} dealer network was approved! So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = "Congratulations! You are now an approved dealer!",
			WHAT_NOW = "Click the button below to look for potential buyers.",
			INSTRUCTIONS = "We'll also alert you when we see new {specialize} requests near your area.".format(**MESSAGE_VARS),
			CLICK_HERE = "See buyer requests!",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_offer" : lambda: dict(
			SUBJECT  =  "{app}: {you_or_he} submitted a {car} in auction {aid}!".format(**MESSAGE_VARS),
			MESSAGE =  "{you_or_he} joined auction {aid} just moments ago! So what now?".format(**MESSAGE_VARS),
			MESSAGE_TITLE = XML("{you_or_he} submitted a <i>{car}</i>!".format(**MESSAGE_VARS)),
			WHAT_NOW = "Compare offers from other dealers and adjust your price!",
			INSTRUCTIONS = "Don't worry, we will alert you when offer prices change.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"BUYER_on_new_offer" : lambda: dict(
			SUBJECT  =  "{app}: A new dealer ({dealer_name}) just submitted a %s!".format(**MESSAGE_VARS),
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
			WHAT_NOW = "This was the dealer's final bid!" if MESSAGE_VARS['is_final_bid'] else "Let other dealers know if you like it!",
			INSTRUCTIONS = 'You can buy this car now! Just press the "buy it now" button for this offer in the auction page.' if MESSAGE_VARS['is_final_bid'] else "If you like this bid, go to the auction page and choose this price as your favorite. You can also message other dealers to bargain for better prices.",
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
			MESSAGE_TITLE = "{buyer} picked a new favorite!",
			WHAT_NOW = "Act fast!" if not MESSAGE_VARS['is_favorite'] else 'Keep it up!',
			INSTRUCTIONS = "Make a better offer to convince the buyer that your vehicle is the best deal!" if not MESSAGE_VARS['is_favorite'] else 'But stay alert for competing offers that may convince the buyer to have a change of mind!',
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
			SUBJECT  =  "{app}: A winner was chosen for a {car}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("The buyer for a <i>{car}</i> picked <b>{you_or_him}</b> as the winner! So what now?".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "{buyer} picked a new winner!",
			WHAT_NOW = "Try again! You'll have better luck next time." if not MESSAGE_VARS['is_winning_offer'] else "Wait for the buyer's call!",
			INSTRUCTIONS = "Tip: Look out for new buyer requests and bid quickly! Having the early attention of a buyer goes a long way." if not is_winning_offer else "The buyer will call you soon via our automatic validation system within your business hours!",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
		"DEALER_on_new_bid" : lambda: dict(
			SUBJECT  =  "{app}: {dealer} lowered the {car}'s bid price to ${price}!".format(**MESSAGE_VARS),
			MESSAGE =  XML("A dealer lowered the price for the <i>{car}</i>!".format(**MESSAGE_VARS)),
			MESSAGE_TITLE = "{dealer} lowered the {car}'s bid price to ${price}!".format(**MESSAGE_VARS),
			WHAT_NOW = "Other dealers have been alerted as well!",
			INSTRUCTIONS = "Make sure you look at other offers and adjust your bid price carefully.",
			CLICK_HERE = "Go to auction",
			CLICK_HERE_URL = "{url}".format(**MESSAGE_VARS),
		),
	}
	user_alert_setting=get_alert_setting_table_for_user(USER)
	if user_alert_setting and (CHECK=="force" or user_alert_setting[CHECK]):
		scheduler.queue_task(
			send_email_task,
			pargs=[USER.email, response.render(
				'email_alert_template.html', dict(
					APPNAME=APP_NAME,
					NAME = USER.first_name.capitalize(), 
					**MESSAGE_DATA[MESSAGE_TYPE]()
					)
				), MESSAGE_DATA[MESSAGE_TYPE]()["SUBJECT"]
			],
			retry_failed = 10,
			period = 3, # run 5s after previous
			timeout = 30, # should take less than 30 seconds
		)
