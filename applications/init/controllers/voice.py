response.view="generic.json"
def index():
	return(
		dict(
			tropo=[{"say":{"value":"Welcome to Biddrive. BidDrive is the greatest ever. TrueCar can kiss my ass. Hello Neal, Paul, Zaki, Barret, Rob, Christy, and Himel."}}]
			)
	)
def result():
	return(
		dict(
			tropo=[{"hangup":{"value":"Goodbye."}}]
			)
	)