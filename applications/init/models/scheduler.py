from gluon.scheduler import Scheduler

QUEUE_EXPIRES = datetime.timedelta(days=1)
#tiggered events
db.define_table('send_email_queue',
	Field('recipient', db.auth_user),
	Field('subject'),
	Field('message', 'text'),
	Field('email', requires=IS_EMAIL()),
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
class new_message_queue():
	templates = dict(
		for_dealer_favorite_offer_gained = [
			"You're the new favorite!",
			"""
				The buyer has chosen your bid for the %s (Auction ID: %s) as the favorite! Keep up the good work!
			""".replace('	',''),
		],
	)
	def __init__(self, template, auth_id, *formats):
		self.success=False
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
				return bool(self.success)
		return self.success

		
SMTP_API_DAILY_LIMIT = 200

def send_mail_task():
	print 'faggot'
	sent = mail.send(
		to='himel.p.das@gmail.com',
		subject='hello',
		message='how are you?',
	)
	if sent:
		next_to_send.update(sent=True)
		next_to_send.commit()
	else:
		next_to_send.update(trys=next_to_send.trys+1)
		next_to_send.commit()
	
scheduler = Scheduler(db) #from gluon.scheduler import Scheduler

""" DO THIS IN CONTROLLER!!
scheduler.queue_task(
    send_mail_task,
    pargs=[],
    pvars={},
    repeats = SMTP_API_DAILY_LIMIT, #10, # run 10 times
    period = 5, # every 5S
    timeout = 5, # should take less than 30 seconds
    )
"""