import httplib, urllib
def signup(email):
    
    params = urllib.urlencode({'EMAIL': email, 'subscribe': 'Subscribe'})
    headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}
    conn = httplib.HTTPConnection("op97.us2.list-manage2.com:80")
    conn.request("POST", "/subscribe/post?u=4fd72c69819f5a370cdcb08b2&id=492d9585cd", params, headers)
    response = conn.getresponse()
    try:
        data = response.read()
        if 'Almost finished' in data: return True
    except:
        pass
    return False

