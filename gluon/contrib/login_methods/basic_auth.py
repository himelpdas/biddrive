import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import base64


def basic_auth(server="http://127.0.0.1"):
    """
    to use basic login with a different server
    from gluon.contrib.login_methods.basic_auth import basic_auth
    auth.settings.login_methods.append(basic_auth('http://server'))
    """

    def basic_login_aux(username,
            password,
            server=server):
        key = base64.b64encode(username+':'+password)
        headers = {'Authorization': 'Basic ' + key}
        request = urllib.request.Request(server, None, headers)
        try:
            urllib.request.urlopen(request)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False
    return basic_login_aux

