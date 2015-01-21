##to alert users that auction has ended IF the auction was not ended short

##inspired by http://www.web2py.com/books/default/chapter/29/08/emails-and-sms#Sending-messages-using-a-background-task
##Finally, as described in Chapter 4, we need to run the mail_queue.py script as if it were inside a controller in our app:
##python web2py.py -S init -M -R applications/init/private/delayed_auction_alerts.py

##DO NOT use with sqlite, as there will be long locks 

import time, datetime

class delayed_alert_send():
	
	def __init__(self, auction_request): #is defined in self not global
		self.auction_request = auction_request
		self.url = URL('dealer', 'auction', args=[auction_request.id])
		self.vehicle = '%s %s %s (ID:%s)' % (auction_request['year'], auction_request['make_name'], auction_request['model_name'], auction_request['id'])
		
		self.buyer = db(db.auth_user.id == auction_request.owner_id).select().last()
		self.dealers = db(db.auction_request_offer.auction_request == auction_request.id).select(left=db.auth_user.on(db.auth_user.id == db.auction_request_offer.owner_id)) 
		
	def send_auction_ended_now(self):
		self.message_type = 'auction_ended_now'
		#buyer send
		self.contact = self.buyer.email
		self.name = self.buyer.first_name.capitalize()
		self.pronoun = 'You'
		self.instructions = 'In the auction, press the red "buy it now" button to pick the offer that is best for you! After that follow the insructions to connect with the dealer!'
		self.try_email()
		#self.try_sms
		
		#dealer send
		self.pronoun='The buyer'
		self.instructions = 'If you win, we will let you know. After that, the auction the buyer will call you (via our automated hotline) during your business hours. You will be charged a success fee only if you answer the call.'
		for each_dealer in self.dealers:
			self.contact = each_dealer.auth_user.email
			self.name = each_dealer.auth_user.first_name.capitalize()
			
			self.try_email()
			#self.try_sms

	def send_auction_ending_soon(self):
		self.message_type = 'auction_ending_soon'
		#buyer send
		self.contact = self.buyer.email
		self.name = self.buyer.first_name.capitalize()
		self.pronoun = 'the dealers'
		self.instructions = XML('Communicate with the dealers now to get the best possible price. Remember, you have <b>no obligation</b> to buy anything if it is not to your liking!')
		
		self.try_email()
		#self.try_sms
		
		#dealer send
		self.pronoun='the buyer and lower your price'
		self.instructions = XML('Try to convince the buyer in these final hours that <b>you</b> have the vehicle he/she wants. Lowering your price just a bit and communicating the buyer can make all the difference.')
		for each_dealer in self.dealers:
			self.contact = each_dealer.auth_user.email
			self.name = each_dealer.auth_user.first_name.capitalize()
			
			self.try_email()
			#self.try_sms
		
	def try_email(self, number=5, timeout=5):
		for each_attempt in range(number):
			if self.send_email():
				break
			time.sleep(timeout)

	def send_email(self):
		message_type_vars = self.get_message_type_vars()
		return mail.send(
			to=self.contact,
			subject=message_type_vars["SUBJECT"],
			message=response.render(
				'email_alert_template.html', 
				dict(
					APP=APP_NAME,
					**message_type_vars
				)
			),
			headers = {'Content-Type' : 'text/html'}, #http://goo.gl/h6N78b #otherwise text/plain
		)

	def get_message_type_vars(self):
		rendered = {
			"auction_ended_now" : dict(
				NAME = self.name,
				SUBJECT  =  "{app}: The auction for {vehicle} has ended!".format(app=APP_NAME, vehicle=self.vehicle),
				MESSAGE_TITLE =  "The auction for {vehicle} has just ended moments ago!".format(name = self.name, vehicle=self.vehicle),
				MESSAGE = "Dealers can no longer bid on this auction.",
				WHAT_NOW = "{pronoun} will have 24 hours to pick a winner.".format(pronoun=self.pronoun),
				INSTRUCTIONS = "{instructions}".format(instructions = self.instructions),
				CLICK_HERE = "Go to auction",
				CLICK_HERE_URL = "{url}".format(url = self.url),
			),
			"auction_ending_soon" : dict(
				NAME = self.name,
				SUBJECT  =  "{app}: The auction for {vehicle} is ending soon!".format(app=APP_NAME, vehicle=self.vehicle),
				MESSAGE_TITLE =  "The auction for {vehicle} will end very soon!".format(name = self.name, vehicle=self.vehicle),
				MESSAGE = "After the auction ends, dealers will no longer be able to lower their prices!",
				WHAT_NOW = "Message {pronoun}!".format(pronoun=self.pronoun),
				INSTRUCTIONS = "{instructions}".format(instructions = self.instructions),
				CLICK_HERE = "Go to auction",
				CLICK_HERE_URL = "{url}".format(url = self.url),
			),
		}
		return rendered[self.message_type]
		
while True:
	try:
		non_completed_auctions = db( #auctions where buyer can pick a winner
			db.auction_request.offer_expires > request.now #exclude auctions where offers expired (completed)
		).select().exclude(
			lambda row: not bool( db(db.auction_request_winning_offer.auction_request == row.id).select() ) #exclude auctions that has a winning offer (completed)
		) #note each row found will require another db call (via exclude), this can affect performance negatively when there are many auctions
		
		#print len(non_completed_auctions)
		
		for each_auction in non_completed_auctions:
			alert_queue = db(db.delayed_auction_alert_queue.auction_request==each_auction.id).select()
			
			if not alert_queue:
				alert_queue_new_id = db.delayed_auction_alert_queue.insert(auction_request=each_auction.id)
				alert_queue = dict(auction_request = alert_queue_new_id , sent_auction_ending_soon = False, sent_auction_ended_now = False) #fake record to save from a commit
			
			change = False
			
			if each_auction.auction_expired():
				
				delayed_alert_send(each_auction).send_auction_ended_now()
				
				alert_queue['sent_auction_ended_now'] = change = True
			
			elif request.now > each_auction.auction_expires - datetime.timedelta(hours = 6): #if it's now 6 hours or more before auction expires
				
				delayed_alert_send(each_auction).send_auction_ending_soon()
				
				alert_queue['sent_auction_ending_soon'] = change =  True
			
			else:
				pass
			
			if change:
				pass
				db(db.delayed_auction_alert_queue.auction_request==each_auction.id).update(sent_auction_ended_now = alert_queue['sent_auction_ended_now'], sent_auction_ending_soon = alert_queue['sent_auction_ending_soon'] ) #update the records
				db.commit() #No create, drop, insert, truncate, delete, or update operation is actually committed until web2py issues the commit command. In models, views and controllers, web2py does this for you, but in modules you are required to do the commit.
		
	except Exception,e: 
		mail.send(
			to="himeldas@live.com", #TODO change to "admin@biddrive.com"
			subject="Error in delayed_auction_alerts.py",
			message=str(e)
		)

	finally:
		db.commit() #will leave SQLITE locked if exception, not sure about MYSQL

	time.sleep(60*30) # check every 0.5 hour