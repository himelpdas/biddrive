#!/usr/bin/python
# -*- coding: utf-8 -*-

#  router is a dictionary of URL routing parameters.
#
#  For each request, the effective router is the default router (below),
#  updated by the base router (if any) from routes.py,
#  updated by the relevant application-specific router (if any)
#  from applications/app/routes.py.
#
#  Optional members of base router:
#
#  default_application: default application name
#  applications: list of all recognized applications, or 'ALL' to use all currently installed applications
#      Names in applications are always treated as an application names when they appear first in an incoming URL.
#  domains: dict used to map domain names to application names
#
#  These values may be overridden by app-specific routers:
#
#  default_controller: name of default controller
#  default_function: name of default function (all controllers)
#  root_static: list of static files accessed from root
#       (mapped to the selected application's static/ directory)
#
#
#  Optional members of application-specific router:
#
#  These values override those in the base router:
#
#  default_controller
#  default_function
#  root_static
#
#  When these appear in the base router, they apply to the default application only:
#
#  domain: the domain that maps to this application (alternative to using domains in the base router)
#  languages: list of all supported languages
#      Names in controllers are always treated as language names when they appear in an incoming URL after
#      the (optional) application name. 
#  controllers: list of valid controllers in selected app
#       or "DEFAULT" to use all controllers in the selected app plus 'static'
#       or [] to disable controller-name omission
#      Names in controllers are always treated as controller names when they appear in an incoming URL after
#      the (optional) application and language names. 
#  default_language
#       The language code (for example: en, it-it) optionally appears in the URL following
#       the application (which may be omitted). For incoming URLs, the code is copied to
#       request.language; for outgoing URLs it is taken from request.language.
#       If languages=[], language support is disabled.
#       The default_language, if any, is omitted from the URL.
#  check_args: set to False to suppress arg checking
#       request.raw_args always contains a list of raw args from the URL, not unquoted
#       request.args are the same values, unquoted
#       By default (check_args=True), args are required to match args_match.
#  acfe_match: regex for valid application, controller, function, extension /a/c/f.e
#  file_match: regex for valid file (used for static file names)
#  args_match: regex for valid args (see also check_args flag)
#
#
#  The built-in default routers supply default values (undefined members are None):
#
#     base_router = dict(
#         default_application = 'init',
#             applications = 'ALL',
#         root_static = ['favicon.ico', 'robots.txt'],
#         domains = dict(),
#         acfe_match = r'\w+$',              # legal app/ctlr/fcn/ext
#         file_match = r'(\w+[-=./]?)+$',    # legal file (path) name
#     )
#
#     default_router = dict(
#         default_controller = 'default',
#             controllers = 'DEFAULT',
#         default_function = 'index',
#         languages = [],
#         default_language = None,
#         check_args = True,
#         map_hyphen = True,
#         args_match = r'([\w@ -]+[=.]?)+$', # legal arg in args
#     )
#
#  See rewrite.map_url_in() and rewrite.map_url_out() for implementation details.


#  This simple router set overrides only the default application name,
#  but provides full rewrite functionality.

routers = dict(

    # base router
    BASE = dict(
        default_application = 'welcome',
    ),

    # default application router
    DEFAULT = dict(),
)


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

def __routes_doctest():
    '''
    Dummy function for doctesting routes.py.

    Use filter_url() to test incoming or outgoing routes;
    filter_err() for error redirection.

    filter_url() accepts overrides for method and remote host:
        filter_url(url, method='get', remote='0.0.0.0', out=False)

    filter_err() accepts overrides for application and ticket:
        filter_err(status, application='app', ticket='tkt')

    >>> filter_url('http://domain.com/abc', router='app')
    'welcome'
    >>> filter_url('http://domain.com/welcome', router='app')
    'welcome'
    >>> filter_url('http://domain.com/favicon.ico')
    '/applications/welcome/static/favicon.ico'
    >>> filter_url('http://domain.com/abc')
    '/welcome/default/abc'
    >>> filter_url('http://domain.com/index/abc')
    "/welcome/default/index ['abc']"
    >>> filter_url('http://domain.com/default/abc.css')
    '/welcome/default/abc.css'
    >>> filter_url('http://domain.com/default/index/abc')
    "/welcome/default/index ['abc']"
    >>> filter_url('http://domain.com/default/index/a%20bc')
    "/welcome/default/index ['a bc']"
    >>> filter_url('http://domain.com/bad!ctl')
    Traceback (most recent call last):
    ...
    HTTP
    >>> filter_url('http://domain.com/ctl/bad!fcn')
    Traceback (most recent call last):
    ...
    HTTP
    >>> filter_url('http://domain.com/ctl/fcn.bad!ext')
    Traceback (most recent call last):
    ...
    HTTP
    >>> filter_url('http://domain.com/ctl/fcn/bad!arg')
    Traceback (most recent call last):
    ...
    HTTP

    >>> filter_url('https://domain.com/app/ctr/fcn', out=True)
    '/app/ctr/fcn'
    >>> filter_url('https://domain.com/welcome/ctr/fcn', out=True)
    '/ctr/fcn'
    >>> filter_url('https://domain.com/welcome/default/fcn', out=True)
    '/fcn'
    >>> filter_url('https://domain.com/welcome/default/index', out=True)
    '/'
    >>> filter_url('https://domain.com/welcome/appadmin/index', out=True)
    '/appadmin'
    >>> filter_url('http://domain.com/welcome/default/fcn?query', out=True)
    '/fcn?query'
    >>> filter_url('http://domain.com/welcome/default/fcn#anchor', out=True)
    '/fcn#anchor'
    >>> filter_url('http://domain.com/welcome/default/fcn?query#anchor', out=True)
    '/fcn?query#anchor'

    >>> filter_url('http://domain.com/appadmin/fcn-1')
    '/welcome/appadmin/fcn_1'
    >>> filter_url('http://domain.com/welcome/appadmin/fcn_1', out=True)
    '/appadmin/fcn-1'
    >>> filter_url('http://domain.com/examples/appadmin/fcn-1')
    '/examples/appadmin/fcn_1'
    >>> filter_url('http://domain.com/examples/appadmin/fcn_1', out=True)
    '/examples/appadmin/fcn-1'
    >>> filter_url('http://domain.com/app/static/filename-with_underscore', out=True)
    '/app/static/filename-with_underscore'
    >>> filter_url('http://domain.com/admin/static/filename-with_underscore')
    '/applications/admin/static/filename-with_underscore'
    
    >>> get_effective_router('welcome').default_application
    'welcome'
    >>> get_effective_router('welcome').default_controller
    'default'
    >>> get_effective_router('welcome').controllers
    ['appadmin', 'default', 'static']
    >>> get_effective_router('admin').controllers
    ['appadmin', 'default', 'gae', 'mercurial', 'shell', 'wizard', 'static']

    >>> filter_err(200)
    200
    >>> filter_err(399)
    399
    >>> filter_err(400)
    400
    '''
    pass

if __name__ == '__main__':
    import os
    import gluon.main
    import doctest
    from gluon.rewrite import load, filter_url, filter_out, filter_err, get_effective_router
    load(routes=os.path.basename(__file__))
    doctest.testmod()
