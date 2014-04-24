response.view="generic.json"
def index():
	return(
		dict(
			tropo=[{"say":{"value":"Guess what?"}}]
			)
	)
def result():
	return(
		dict(
			tropo=[{"hangup":{"value":"Goodbye."}}]
			)
	)