from gluon.scheduler import Scheduler

#QUEUE_EXPIRES = datetime.timedelta(days=1)
#TROPO_VOICE_KEY = '251fe697c982b94db08a7203b77d239b0b35c254f2d77f7d76248b2a0f11da61c53950902773c41c15de4d7f'

from twilio.rest import TwilioRestClient
from twilio import twiml

TWILIO_SID = "AC2cec9db22d55360d41944cd2b953804a"
TWILIO_KEY = "34add1bda0569d8c32fa37e2b9a7200b" 
twilio_clinet = TwilioRestClient(TWILIO_SID, TWILIO_KEY)

#http://goo.gl/L05FHS
#http://goo.gl/An6V4P

#EMAIL_NEW_FAVORITE_OFFER_SUBJECT = """%s You're the new favorite! (Auction #%s)"""
				
def send_alert_task(type, contact, message, subject = None):
	if type == 'email':
		if not IS_EMAIL()(contact)[1]: #for admin stuff #save the api call/resources if false#no error message if its either a tel or email>>> IS_EMAIL()('a@b.com') >>>('a@b.com', None)
			sent = mail.send(
				to=contact,
				subject=subject,
				message=message,
				headers = {'Content-Type' : 'text/html'}, #http://goo.gl/h6N78b #otherwise text/plain
			)
			return sent
	#if phone or text
	##if text...
	return False
	
	
scheduler = Scheduler(db) #from gluon.scheduler import Scheduler

