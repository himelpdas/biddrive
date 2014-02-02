def index():
	return dict()
	
def auction_requests():
	auction_requests = db(db.auction_request.id>0).select()
	return dict(auction_requests=auction_requests)