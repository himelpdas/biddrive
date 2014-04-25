from gluon.scheduler import Scheduler

QUEUE_EXPIRES = datetime.timedelta(days=1)
TROPO_VOICE_KEY = '251fe697c982b94db08a7203b77d239b0b35c254f2d77f7d76248b2a0f11da61c53950902773c41c15de4d7f'


EMAIL_NEW_FAVORITE_OFFER_MESSAGE = """Hello %s! The buyer for auction ID: %s picked %s as the favorite! Check your auctions page"""
EMAIL_NEW_FAVORITE_OFFER_SUBJECT = """%s You're the new favorite! (Auction #%s)"""
				
def send_alert_task(type, contact, message, subject = None):
	if type == 'email':
		if not IS_EMAIL()(contact)[1]: #for admin stuff #save the api call/resources if false#no error message if its either a tel or email>>> IS_EMAIL()('a@b.com') >>>('a@b.com', None)
			sent = mail.send(
				to=contact,
				subject=subject,
				message=message,
			)
			return sent
	#if phone or text
	##if text...
	return False
	
	
scheduler = Scheduler(db) #from gluon.scheduler import Scheduler

'''
class trash():
	db.define_table('send_email_queue',
		Field('recipient', db.auth_user, requires=IS_NOT_EMPTY()),
		Field('subject'),
		Field('message', 'text', requires=IS_NOT_EMPTY()),
		Field('type', requires=IS_IN_SET(['email','text','phone'])),
		Field('contact', requires=IS_NOT_EMPTY()),
		Field('contact_check', required=True, #true or false
			compute=lambda row: not IS_EMAIL()(row['contact'])[1] or not IS_MATCH(REGEX_TELEPHONE)[1], #no error message if its either a tel or email>>> IS_EMAIL()('a@b.com') >>>('a@b.com', None)
		),
		Field('sent', 'boolean',
			default=False,
		),
		Field('trys', 'integer',
			default=0,
		),
		Field('expires', 'datetime', #keep trying to send this email for one day
			default=request.now+QUEUE_EXPIRES,
			#readable=False,
			writable=False,
		),	
		Field('created_on', 'datetime', 
			default=request.now,
			#readable=False,
			writable=False,
		),
		Field('changed_on', 'datetime', 
			update=request.now,
			#readable=False,
			writable=False,
		),
		Field('created_by', db.auth_user, 
			default=auth.user_id, #DO NOT CONFUSE auth.user_id with db.auth_user #<type 'exceptions.TypeError'> long() argument must be a string or a number, not 'Table'
			readable=False,
			writable=False,
		),
		Field('changed_by', db.auth_user,
			update=auth.user_id,
			readable=False,
			writable=False,
		)
	)#if created/changed_by = None then changed_on can be considered the time when the message was created, and _by when the message was sent

	#timed events
		#next_to_send = db((db.send_email_queue.id>0)&(db.send_email_queue.expires>request.now)&(db.send_email_queue.trys<5)).select().first()
	#TROPO OR TWILIO
	class alert():
		templates = dict(
			for_dealer_favorite_offer_gained = [
				"You're the new favorite!",
				"""
					The buyer has chosen your bid for the %s (Auction ID: %s) as the favorite! Keep up the good work!
				""".replace('	',''),
			],
		)
		def __init__(self, template, auth_id, *formats):
			user = db(db.auth_user.id == auth_id).select().last()
			if template in templates:
				if user:
					email = user.email
					self.success = db.send_email_queue.insert(
						recipient = auth_id,
						email=email,
						subject=self.templates[template][0],
						message=self.templates[template][1]%formats
					)

	scheduler.queue_task(
		send_alert_task,
		pargs=[],
		pvars={},
		repeats = 0, #10, # run 10 times
		period = 5, # every 5S
		timeout = 5, # should take less than 30 seconds
		)
'''