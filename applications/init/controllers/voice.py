response.view="generic.json"
def index():
	return(
		dict(
			tropo=[{"say":{"value":"BidDrive is the greatest ever. TrueCar can kiss my ass."}}]
			)
	)
def result():
	return(
		dict(
			tropo=[{"hangup":{"value":"Goodbye."}}]
			)
	)