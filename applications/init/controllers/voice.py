response.view="generic.json"
def index():
	return(
		dict(
			tropo=[{"say":{"value":"Guess what? http://www.phono.com/audio/troporocks.mp3"}}]
			)
	)
def result():
	return(
		dict(
			tropo=[{"hangup":{"value":"Goodbye."}}]
			)
	)