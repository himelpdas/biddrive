#!/usr/bin/python
# -*- coding: utf-8 -*-

# default_application, default_controller, default_function
# are used when the respective element is missing from the
# (possibly rewritten) incoming URL
#
default_application = 'init'    # ordinarily set in base routes.py
default_controller = 'default'  # ordinarily set in app-specific routes.py
default_function = 'index'      # ordinarily set in app-specific routes.py

# routes_app is a tuple of tuples.  The first item in each is a regexp that will
# be used to match the incoming request URL. The second item in the tuple is
# an applicationname.  This mechanism allows you to specify the use of an
# app-specific routes.py. This entry is meaningful only in the base routes.py.
#
# Example: support welcome, admin, app and myapp, with myapp the default:


routes_app = ((r'/(?P<app>welcome|admin|app)\b.*', r'\g<app>'),
              (r'(.*)', r'myapp'),
              (r'/?(.*)', r'myapp'))

# routes_in is a tuple of tuples.  The first item in each is a regexp that will
# be used to match the incoming request URL. The second item in the tuple is
# what it will be replaced with.  This mechanism allows you to redirect incoming
# routes to different web2py locations
#
# Example: If you wish for your entire website to use init's static directory:
#
#   routes_in=( (r'/static/(?P<file>[\w./-]+)', r'/init/static/\g<file>') )
#

routes_in = ((r'.*:/favicon.ico', r'/examples/static/favicon.ico'),
             (r'.*:/robots.txt', r'/examples/static/robots.txt'),
             ((r'.*http://otherdomain.com.* (?P<any>.*)', r'/app/ctr\g<any>')))

# routes_out, like routes_in translates URL paths created with the web2py URL()
# function in the same manner that route_in translates inbound URL paths.
#

routes_out = ((r'.*http://otherdomain.com.* /app/ctr(?P<any>.*)', r'\g<any>'),
              (r'/app(?P<any>.*)', r'\g<any>'))

# Error-handling redirects all HTTP errors (status codes >= 400) to a specified
# path.  If you wish to use error-handling redirects, uncomment the tuple
# below.  You can customize responses by adding a tuple entry with the first
# value in 'appName/HTTPstatusCode' format. ( Only HTTP codes >= 400 are
# routed. ) and the value as a path to redirect the user to.  You may also use
# '*' as a wildcard.
#
# The error handling page is also passed the error code and ticket as
# variables.  Traceback information will be stored in the ticket.
#
# routes_onerror = [
#     (r'init/400', r'/init/default/login')
#    ,(r'init/*', r'/init/static/fail.html')
#    ,(r'*/404', r'/init/static/cantfind.html')
#    ,(r'*/*', r'/init/error/index')
# ]

# specify action in charge of error handling
#
# error_handler = dict(application='error',
#                      controller='default',
#                      function='index')

# In the event that the error-handling page itself returns an error, web2py will
# fall back to its old static responses.  You can customize them here.
# ErrorMessageTicket takes a string format dictionary containing (only) the
# "ticket" key.

# error_message = '<html><body><h1>Invalid request</h1></body></html>'
# error_message_ticket = '<html><body><h1>Internal error</h1>Ticket issued: <a href="/admin/default/ticket/%(ticket)s" target="_blank">%(ticket)s</a></body></html>'

# specify a list of apps that bypass args-checking and use request.raw_args
#
#routes_apps_raw=['myapp']
#routes_apps_raw=['myapp', 'myotherapp']

def __routes_doctest():
    '''
    Dummy function for doctesting routes.py.

    Use filter_url() to test incoming or outgoing routes;
    filter_err() for error redirection.

    filter_url() accepts overrides for method and remote host:
        filter_url(url, method='get', remote='0.0.0.0', out=False)

    filter_err() accepts overrides for application and ticket:
        filter_err(status, application='app', ticket='tkt')

    >>> import os
    >>> import gluon.main
    >>> from gluon.rewrite import regex_select, load, filter_url, regex_filter_out, filter_err, compile_regex
    >>> regex_select()
    >>> load(routes=os.path.basename(__file__))

    >>> filter_url('http://domain.com/favicon.ico')
    'http://domain.com/examples/static/favicon.ico'
    >>> filter_url('https://domain.com/robots.txt')
    'https://domain.com/examples/static/robots.txt'
    >>> filter_url('http://domain.com/app/ctr/fcn')
    'http://domain.com/app/ctr/fcn'
    >>> filter_url('HTTP://DOMAIN.COM/app/ctr/fcn')
    'http://domain.com/app/ctr/fcn'
    >>> filter_url('http://domain.com/app/ctr/fcn?query')
    'http://domain.com/app/ctr/fcn?query'
    >>> filter_url('http://otherdomain.com/fcn')
    'http://otherdomain.com/app/ctr/fcn'
    >>> regex_filter_out('/app/ctr/fcn')
    '/ctr/fcn'
    >>> filter_url('https://otherdomain.com/app/ctr/fcn', out=True)
    '/ctr/fcn'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn', out=True)
    '/fcn'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn?query', out=True)
    '/fcn?query'
    >>> filter_url('http://otherdomain.com/app/ctr/fcn#anchor', out=True)
    '/fcn#anchor'
    >>> filter_err(200)
    200
    >>> filter_err(399)
    399
    >>> filter_err(400)
    400
    >>> filter_url('http://domain.com/welcome', app=True)
    'welcome'
    >>> filter_url('http://domain.com/', app=True)
    'myapp'
    >>> filter_url('http://domain.com', app=True)
    'myapp'
    >>> compile_regex('.*http://otherdomain.com.* (?P<any>.*)', '/app/ctr\g<any>')[0].pattern
    '^.*http://otherdomain.com.* (?P<any>.*)$'
    >>> compile_regex('.*http://otherdomain.com.* (?P<any>.*)', '/app/ctr\g<any>')[1]
    '/app/ctr\\\\g<any>'
    >>> compile_regex('/$c/$f', '/init/$c/$f')[0].pattern
    '^.*?:https?://[^:/]+:[a-z]+ /(?P<c>\\\\w+)/(?P<f>\\\\w+)$'
    >>> compile_regex('/$c/$f', '/init/$c/$f')[1]
    '/init/\\\\g<c>/\\\\g<f>'
    '''
    pass

if __name__ == '__main__':
    import doctest
    doctest.testmod()
