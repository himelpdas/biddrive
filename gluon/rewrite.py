#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import os
import re
import logging
import traceback
import threading
import urllib
from storage import Storage, List
from http import HTTP
from fileutils import abspath

regex_at = re.compile(r'(?<!\\)\$[a-zA-Z]\w*')
regex_anything = re.compile(r'(?<!\\)\$anything')
regex_iter = re.compile(r'.*code=(?P<code>\d+)&ticket=(?P<ticket>.+).*')

logger = logging.getLogger('web2py.rewrite')

thread = threading.local()  # thread-local storage for routing parameters

def _router_default():
    "return new copy of default router"
    router = Storage(
        default_application = 'init',
            applications = 'ALL',
        default_controller = 'default',
            controllers = 'DEFAULT',
        default_function = 'index',
        root_static = ['favicon.ico', 'robots.txt'],
        map_domain = dict(),
        languages = [],
        default_language = None,
        check_args = True,
        map_hyphen = True,
        acfe_match = r'\w+$',              # legal app/ctlr/fcn/ext
        file_match = r'(\w+[-=./]?)+$',    # legal file (path) name
        args_match = r'([\w@ -]+[=.]?)+$', # legal arg in args
    )
    return router

_router_defaults = _router_default() # static copy for access to default values
_router_defaults._acfe_match = re.compile(_router_defaults.acfe_match)
_router_defaults._file_match = re.compile(_router_defaults.file_match)
_router_defaults._args_match = re.compile(_router_defaults.args_match)
_router_defaults.applications = []
_router_defaults.controllers = []

def _params_default(app=None):
    "return new copy of default parameters"
    p = Storage()
    p.name = app or "BASE"
    p.default_application = app or "init"
    p.default_controller = "default"
    p.default_function = "index"
    p.routes_app = []
    p.routes_in = []
    p.routes_out = []
    p.routes_onerror = []
    p.routes_apps_raw = []
    p.error_handler = None
    p.error_message = '<html><body><h1>%s</h1></body></html>'
    p.error_message_ticket = \
        '<html><body><h1>Internal error</h1>Ticket issued: <a href="/admin/default/ticket/%(ticket)s" target="_blank">%(ticket)s</a></body><!-- this is junk text else IE does not display the page: '+('x'*512)+' //--></html>'
    p.router = Storage()
    p.router.active = False
    return p

params_apps = dict()
params = _params_default(app=None)  # base (and legacy) rewrite parameters
thread.routes = params # default to base rewrite parameters

def compile_re(k, v):
    """
    Preprocess and compile the regular expressions in routes_app/in/out

    The resulting regex will match a pattern of the form:

        [remote address]:[protocol]://[host]:[method] [path]

    We allow abbreviated regexes on input; here we try to complete them.
    """
    k0 = k  # original k for error reporting
    # bracket regex in ^...$ if not already done
    if not k[0] == '^':
        k = '^%s' % k
    if not k[-1] == '$':
        k = '%s$' % k
    # if there are no :-separated parts, prepend a catch-all for the IP address
    if k.find(':') < 0:
        # k = '^.*?:%s' % k[1:]
        k = '^.*?:https?://[^:/]+:[a-z]+ %s' % k[1:]
    # if there's no ://, provide a catch-all for the protocol, host & method
    if k.find('://') < 0:
        i = k.find(':/')
        if i < 0:
            raise SyntaxError, "routes pattern syntax error: path needs leading '/' [%s]" % k0
        k = r'%s:https?://[^:/]+:[a-z]+ %s' % (k[:i], k[i+1:])
    # $anything -> ?P<anything>.*
    for item in regex_anything.findall(k):
        k = k.replace(item, '(?P<anything>.*)')
    # $a (etc) -> ?P<a>\w+
    for item in regex_at.findall(k):
        k = k.replace(item, r'(?P<%s>\w+)' % item[1:])
    # same for replacement pattern, but with \g
    for item in regex_at.findall(v):
        v = v.replace(item, r'\g<%s>' % item[1:])
    return (re.compile(k, re.DOTALL), v)

def load(routes='routes.py', app=None):
    """
    load: read and parse routes.py
    (called from main.py at web2py initialization time)
    store results in params
    """
    if app is None:
        path = abspath(routes)
    else:
        path = abspath('applications', app, routes)
    if not os.path.exists(path):
        return

    symbols = {}
    try:
        routesfp = open(path, 'r')
        exec routesfp.read().replace('\r\n','\n') in symbols
        routesfp.close()
    except SyntaxError, e:
        routesfp.close()
        logger.error(
            '%s has a syntax error and will not be loaded\n' % path
            + traceback.format_exc())
        raise e

    p = _params_default(app)

    for sym in ('routes_app', 'routes_in', 'routes_out'):
        if sym in symbols:
            for (k, v) in symbols[sym]:
                p[sym].append(compile_re(k, v))
    for sym in ('routes_onerror', 'routes_apps_raw',
                'error_handler','error_message', 'error_message_ticket',
                'default_application','default_controller', 'default_function'):
        if sym in symbols:
            p[sym] = symbols[sym]
    if 'router' in symbols:
        p.router = Storage(symbols['router'])
        p.router.active = True

    router = None
    if app is None:
        global params
        params = p  # install base rewrite parameters
        if params.router.active:
            router = _router_default()
            router.update(params.router)
            params.router = router
        for appname in os.listdir(abspath('applications')):
            if os.path.exists(abspath('applications', appname, routes)):
                load(routes, appname)
    else:
        if params.router.active or p.router.active:
            router = Storage(params.router)  # new copy of base router
            router.update(p.router)
            router.default_application = app # local default app
            p.router = router
        params_apps[app] = p
    if router is not None:
        router._acfe_match = re.compile(router.acfe_match)
        router._file_match = re.compile(router.file_match)
        router._args_match = re.compile(router.args_match)
        if isinstance(router.applications, str) and router.applications == 'ALL':
            router.applications = []
            for aname in os.listdir(abspath('applications')):
                if os.path.isdir(abspath('applications', aname)):
                    router.applications.append(aname)
        if isinstance(router.controllers, str):
            aname = router.controllers
            if aname == 'DEFAULT':
                if app is None:
                    aname = router.default_application
                else:
                    aname = app
            router.controllers = []
            if os.path.isdir(abspath('applications', aname)):
                cpath = abspath('applications', aname, 'controllers')
                for cname in os.listdir(cpath):
                    if os.path.isfile(abspath(cpath, cname)) and cname.endswith('.py'):
                        router.controllers.append(cname[:-3])
                router.controllers.append('static')

    logger.debug('URL rewrite is on. configuration in %s' % path)

def filter_uri(e, regexes, tag, default=None):
    "filter incoming URI against a list of regexes"
    query = e.get('QUERY_STRING', None)
    path = e['PATH_INFO']
    host = e.get('HTTP_HOST', 'localhost').lower()
    original_uri = path + (query and '?'+query or '')
    i = host.find(':')
    if i > 0:
        host = host[:i]
    key = '%s:%s://%s:%s %s' % \
        (e.get('REMOTE_ADDR','localhost'),
         e.get('WSGI_URL_SCHEME', 'http').lower(), host,
         e.get('REQUEST_METHOD', 'get').lower(), path)
    for (regex, value) in regexes:
        if regex.match(key):
            rewritten = regex.sub(value, key)
            logger.debug('%s: [%s] [%s] -> %s' % (tag, key, value, rewritten))
            return (rewritten, query, original_uri)
    logger.debug('%s: [%s] -> %s (not rewritten)' % (tag, key, default))
    return (default, query, original_uri)

def select(env=None, app=None, request=None):
    """
    select a set of rewrite params for the current request
    called from main.wsgibase before any URL rewriting
    """
    if app:
        thread.routes = params_apps.get(app, params)
    elif env and params.routes_app:
        if params.router.active:
            app = map_url_in(request, env, app=True)
        else:
            (app, q, u) = filter_uri(env, params.routes_app, "routes_app")
        thread.routes = params_apps.get(app, params)
    else:
        thread.routes = params # default to base rewrite parameters
    logger.debug("select routing parameters: %s" % thread.routes.name)
    return app  # for doctest

def filter_in(e):
    "called from main.wsgibase to rewrite incoming URL"
    if thread.routes.routes_in:
        (path, query, original_uri) = filter_uri(e, thread.routes.routes_in, "routes_in", e['PATH_INFO'])
        if path.find('?') < 0:
            e['PATH_INFO'] = path
        else:
            if query:
                path = path+'&'+query
            e['PATH_INFO'] = ''
            e['REQUEST_URI'] = path
            e['WEB2PY_ORIGINAL_URI'] = original_uri
    return e

def filter_out(url, e=None):
    "called from html.URL to rewrite outgoing URL"
    if not hasattr(thread, 'routes'):
        select()    # ensure thread.routes is set (for application threads)
    if thread.routes.router.active:
        return url  # already filtered
    if thread.routes.routes_out:
        items = url.split('?', 1)
        if e:
            host = e.get('http_host', 'localhost').lower()
            i = host.find(':')
            if i > 0:
                host = host[:i]
            items[0] = '%s:%s://%s:%s %s' % \
                 (e.get('remote_addr', ''),
                  e.get('wsgi_url_scheme', 'http').lower(), host,
                  e.get('request_method', 'get').lower(), items[0])
        else:
            items[0] = ':http://localhost:get %s' % items[0]
        for (regex, value) in thread.routes.routes_out:
            if regex.match(items[0]):
                rewritten = '?'.join([regex.sub(value, items[0])] + items[1:])
                logger.debug('routes_out: [%s] -> %s' % (url, rewritten))
                return rewritten
    logger.debug('routes_out: [%s] not rewritten' % url)
    return url


def try_redirect_on_error(http_object, request, ticket=None):
    "called from main.wsgibase to rewrite the http response"
    status = int(str(http_object.status).split()[0])
    if status>399 and thread.routes.routes_onerror:
        keys=set(('%s/%s' % (request.application, status),
                  '%s/*' % (request.application),
                  '*/%s' % (status),
                  '*/*'))
        for (key,redir) in thread.routes.routes_onerror:
            if key in keys:
                if redir == '!':
                    break
                elif '?' in redir:
                    url = '%s&code=%s&ticket=%s&requested_uri=%s&request_url=%s' % \
                        (redir,status,ticket,request.env.request_uri,request.url)
                else:
                    url = '%s?code=%s&ticket=%s&requested_uri=%s&request_url=%s' % \
                        (redir,status,ticket,request.env.request_uri,request.url)
                return HTTP(303,
                            'You are being redirected <a href="%s">here</a>' % url,
                            Location=url)
    return http_object

def filter_url(url, method='get', remote='0.0.0.0', out=False, app=False, router=False, lang=None):
    "doctest interface to filter_in() and filter_out()"
    regex_url = re.compile(r'^(?P<scheme>http|https|HTTP|HTTPS)\://(?P<host>[^/]+)(?P<uri>\S*)')
    match = regex_url.match(url)
    scheme = match.group('scheme').lower()
    host = match.group('host').lower()
    uri = match.group('uri')
    k = uri.find('?')
    if k < 0:
        k = len(uri)
    (path_info, query_string) = (uri[:k], uri[k+1:])
    e = {
         'REMOTE_ADDR': remote,
         'REQUEST_METHOD': method,
         'WSGI_URL_SCHEME': scheme,
         'HTTP_HOST': host,
         'REQUEST_URI': uri,
         'PATH_INFO': path_info,
         'QUERY_STRING': query_string,
         #for filter_out request.env use lowercase
         'remote_addr': remote,
         'request_method': method,
         'wsgi_url_scheme': scheme,
         'http_host': host
    }
    if router:
        request = Storage()
        e["applications_parent"] = '/'
        request.env = Storage(e)
        request.language = lang
        if out:
            items = path_info.strip('/').split('/')
            a = items.pop(0)
            c = items.pop(0)
            f = items.pop(0)
            acf = map_url_out(a, c, f, items, lang)
            if items:
                url = '%s/%s' % (acf, '/'.join(items))
            else:
                url = acf
            if query_string:
                url += '?' + query_string
            return url
        if router == "app":
            return map_url_in(request, e, app=True)
        (static, e) = map_url_in(request, e)
        if static:
            return static
        result = "/%s/%s/%s" % (request.application, request.controller, request.function)
        if request.extension and request.extension != 'html':
            result += ".%s" % request.extension
        if request.args:
            result += " %s" % request.args
        if request.language:
            result += " (%s)" % request.language
        return result
    elif out:
        return filter_out(uri, e)
    elif app:
        return select(e)
    else:
        select(app=select(e))
        e = filter_in(e)
        if e.get('PATH_INFO','') == '':
            path = e['REQUEST_URI']
        elif query_string:
            path = e['PATH_INFO'] + '?' + query_string
        else:
            path = e['PATH_INFO']
    return scheme + '://' + host + path

def filter_err(status, application='app', ticket='tkt'):
    "doctest interface to routes_onerror"
    if status > 399 and thread.routes.routes_onerror:
        keys = set(('%s/%s' % (application, status),
                  '%s/*' % (application),
                  '*/%s' % (status),
                  '*/*'))
        for (key,redir) in thread.routes.routes_onerror:
            if key in keys:
                if redir == '!':
                    break
                elif '?' in redir:
                    url = redir + '&' + 'code=%s&ticket=%s' % (status,ticket)
                else:
                    url = redir + '?' + 'code=%s&ticket=%s' % (status,ticket)
                return url # redirection
    return status # no action

#  router support
#
#  TODO
#    hook for user logic? (routes.py or in controller if app-specific)
#    router doctest: supply app-specific router as argument?

class MapUrlIn(object):
    "logic for mapping incoming URLs"

    def __init__(self, request=None, env=None):
        "initialize a map-in object"
        self.request = request
        self.env = env

        self.base_router = params.router
        self.router = params.router
        self.application = None
        self.language = None
        self.controller = None
        self.function = None
        self.extension = 'html'

        self.controllers = []
        self.languages = []
        self.default_language = None
        self.check_args = True
        self.map_hyphen = True

        self.path = self.env['PATH_INFO']
        self.query = self.env.get('QUERY_STRING', None)
        self.env['REQUEST_URI'] = self.path + (self.query and ('?' + self.query) or '')
        if '#' in self.query:
            self.query, self.anchor = self.query.split('#', 1)
        elif '#' in self.path:
            self.path, self.anchor = self.path.split('#', 1)
        else:
            self.anchor = None
        self.path = self.path.strip('/')
        self.env['PATH_INFO'] = '/' + self.path

        self.raw_args = List(self.path and self.path.split('/') or [])
        self.args = List([urllib.unquote(arg) for arg in self.raw_args])
        self.host = self.env.get('HTTP_HOST', 'localhost').lower()
        i = self.host.find(':')
        if i > 0:
            self.host = self.host[:i]
        self.remote_addr = self.env.get('REMOTE_ADDR','localhost')
        self.scheme = self.env.get('WSGI_URL_SCHEME', 'http').lower()
        self.method = self.env.get('REQUEST_METHOD', 'get').lower()

    def map_app(self):
        "determine application name"
        router = self.base_router
        arg0 = self.harg0
        if arg0 in router.applications:
            self.application = arg0
        elif self.host in router.map_domain:
            self.application = router.map_domain[self.host]
        elif arg0 and not router.applications:
            self.application = arg0
        else:
            self.application = router.default_application
        self.pop_arg_if(self.application == arg0)
    
        if not router._acfe_match.match(self.application):
            raise HTTP(400, thread.routes.error_message % 'invalid request',
                       web2py_error='invalid application')

        #  set the application-specific router, if any
        #
        thread.routes = params_apps.get(self.application, params)
        logger.debug("select application=%s and router=%s" % (self.application, thread.routes.name))
        self.request.application = self.application
        self.router = thread.routes.router   # possibly switch to app-specific router

    def map_defaults(self):
        '''
        If this is the base router, certain values apply only to the default application;
        other applications get the default values.
        '''
        if self.application == self.router.default_application:
            r = self.router
        else:
            r = _router_defaults
        self.controllers = r.controllers
        self.languages = r.languages
        self.default_language = r.default_language
        self.check_args = r.check_args
        self.map_hyphen = r.map_hyphen
        self._acfe_match = r._acfe_match
        self._file_match = r._file_match
        self._args_match = r._args_match

    def map_root_static(self):
        "handle root-static files (no hyphen mapping)"
        if len(self.args) == 1 and self.arg0 in self.router.root_static:   
            self.controller = self.request.controller = 'static'
            root_static_file = os.path.join(self.request.env.applications_parent,
                                   'applications', self.application,
                                   self.controller, self.arg0)
            logger.debug("route: root static=%s" % root_static_file)
            return root_static_file
        return None

    def map_language(self):
        "handle language (no hyphen mapping)"
        arg0 = self.arg0  # no hyphen mapping
        if arg0 and arg0 in self.languages:
            self.language = arg0
        else:
            self.language = self.default_language
        if self.language:
            logger.debug("route: language=%s" % self.language)
            self.pop_arg_if(self.language == arg0)
            arg0 = self.arg0

    def map_controller(self):
        "identify controller"
        #  handle controller
        #
        arg0 = self.harg0    # map hyphens
        if not arg0 or (self.controllers and arg0 not in self.controllers):
            self.controller = self.router.default_controller
        else:
            self.controller = arg0
            self.pop_arg_if(True)
        logger.debug("route: controller=%s" % self.controller)
        if not self._acfe_match.match(self.controller):
            raise HTTP(400, thread.routes.error_message % 'invalid request',
                       web2py_error='invalid controller')

    def map_static(self):
        '''
        handle static files
        file_match but no hyphen mapping
        '''
        if self.controller != "static":
            return None
        file = '/'.join(self.args)
        if not self._file_match.match(file):
            raise HTTP(400, thread.routes.error_message % 'invalid request',
                       web2py_error='invalid static file')
        #
        #  support language-specific static subdirectories,
        #  eg /appname/en/static/filename => applications/appname/static/en/filename
        #  if language-specific file doesn't exist, try same file in static
        #
        if self.language:
            static_file = os.path.join(self.request.env.applications_parent,
                                   'applications', self.application,
                                   'static', self.language, file)
        if not self.language or not os.path.isfile(static_file):
            static_file = os.path.join(self.request.env.applications_parent,
                                   'applications', self.application,
                                   'static', file)
        logger.debug("route: static=%s" % static_file)
        return static_file

    def map_function(self):
        "handle function.extension"
        arg0 = self.harg0    # map hyphens
        if arg0:
            func_ext = arg0.split('.')
            if len(func_ext) > 1:
                self.function = func_ext[0]
                self.extension = func_ext[-1]
            else:
                self.function = arg0
            self.pop_arg_if(True)
        else:
            self.function = self.router.default_function
        logger.debug("route: function.ext=%s.%s" % (self.function, self.extension))
    
        if not self._acfe_match.match(self.function):
            raise HTTP(400, thread.routes.error_message % 'invalid request',
                       web2py_error='invalid function')
        if self.extension and not self._acfe_match.match(self.extension):
            raise HTTP(400, thread.routes.error_message % 'invalid request',
                       web2py_error='invalid extension')

    def validate_args(self):
        '''
        validate args if check_args flag is set
        else replace each invalid arg with None, leaving raw_args alone
        '''
        if self.check_args:
            for arg in self.args:
                if not self._args_match.match(arg):
                    raise HTTP(400, thread.routes.error_message % 'invalid request',
                               web2py_error='invalid args')
        else:
            args = []
            for arg in self.args:
                if self._args_match.match(arg):
                    args.append(arg)
                else:
                    args.append(None)
            self.args = args

    def update_request(self):
        "update request from self"
        self.request.application = self.application
        self.request.controller = self.controller
        self.request.function = self.function
        self.request.extension = self.extension
        self.request.anchor = self.anchor
        self.request.args = self.args
        self.request.raw_args = self.raw_args
        if self.language:
            self.request.language = self.language
        for (key, value) in self.env.items():
            self.request.env[key.lower().replace('.', '_')] = value

    @property
    def arg0(self):
        "return first arg"
        return self.args(0)

    @property
    def harg0(self):
        "return first arg with optional hyphen mapping"
        if self.map_hyphen and self.args(0):
            return self.args(0).replace('-', '_')
        return self.args(0)

    def pop_arg_if(self, dopop):
        "conditionally remove first arg and return new first arg"
        if dopop:
            self.args.pop(0)
            self.raw_args.pop(0)

class MapUrlOut(object):
    "logic for mapping outgoing URLs"

    def __init__(self, application, controller, function, args, lang):
        "initialize a map-out object"
        if not hasattr(thread, 'routes'):
            thread.routes = params  # default to base rewrite parameters
        self.router = thread.routes.router
        self.base_router = params.router

        self.application = application
        self.controller = controller
        self.function = function
        self.args = args

        #  If this is the base router, certain values apply only to the default application;
        #  other applications get the default values.
        #
        if self.application == self.router.default_application:
            r = self.router
        else:
            r = _router_defaults
        self.controllers = r.controllers
        self.languages = r.languages
        self.default_language = r.default_language
        self.map_hyphen = r.map_hyphen

        if lang and lang in self.languages:
            self.language = lang
        else:
            self.language = None

        self._acf = ''
        self.omit_application = False
        self.omit_language = False
        self.omit_controller = False
        self.omit_function = False

    def active(self):
        "do we have an active router?"
        return self.router is not None and self.router.active

    @property
    def base_default_application(self):
        "default_application from base router"
        return self.base_router.default_application

    def omit_lang(self):
        "omit language if possible"

        if not self.language or self.language == self.default_language:
            self.omit_language = True
    
    def omit_acf(self):
        "omit what we can of a/c/f"

        router = self.router

        #  Handle the easy no-args case of tail-defaults: /a/c  /a  /
        #
        if not self.args and self.function == router.default_function:
            self.omit_function = True
            if self.controller == router.default_controller:
                self.omit_controller = True
                if self.application == self.base_default_application:
                    self.omit_application = True
    
        #  omit the base default application
        #  omit applications in the domain map
        #
        if self.application == self.base_default_application or self.application in router.map_domain.values():
            self.omit_application = True
    
        #  omit controller if default controller for default app
        #
        if self.application == router.default_application and self.controller == router.default_controller:
            self.omit_controller = True
    
        #  prohibit ambiguous cases
        #
        #  because we presume the lang string to be unambiguous, its presence protects application omission
        #
        if self.omit_language:
            if not router.applications or self.controller in router.applications:
                self.omit_application = False
            if not router.applications or self.function in router.applications:
                self.omit_controller = False
        if not self.controllers or self.function in self.controllers:
            self.omit_controller = False

    def build_acf(self):
        "build acf from components"
        if self.map_hyphen:
            self.application = self.application.replace('_', '-')
            self.controller = self.controller.replace('_', '-')
            if self.controller != 'static':
                self.function = self.function.replace('_', '-')
        if not self.omit_application:
            self._acf += '/' + self.application
        if not self.omit_language:
            self._acf += '/' + self.language
        if not self.omit_controller:
            self._acf += '/' + self.controller
        if not self.omit_function:
            self._acf += '/' + self.function
        return self._acf or '/'

    def acf(self):
        "convert components to /app/lang/controller/function"

        if not self.active():
            return None         # use regex filter
        self.omit_lang()        # try to omit language
        self.omit_acf()         # try to omit a/c/f
        return self.build_acf() # build and return the /a/lang/c/f string


def map_url_in(request, env, app=False):
    "route incoming URL"

    #  initialize router-url object
    #
    map = MapUrlIn(request=request, env=env)
    map.map_app()     # determine application
    if app:
        return map.application
    map.map_defaults()    # adjust defaults if not default application
    root_static_file = map.map_root_static() # handle root-static files
    if root_static_file:
        return (root_static_file, map.env)
    map.map_language()
    map.map_controller()
    static_file = map.map_static()
    if static_file:
        return (static_file, map.env)
    map.map_function()
    map.validate_args()
    map.update_request()
    return (None, map.env)

def map_url_out(application, controller, function, args, lang=None):
    '''
    supply /a/c/f (or /a/lang/c/f) portion of outgoing url

    The basic rule is that we can only make transformations
    that map_url_in can reverse.

    Suppose that the incoming arguments are a,c,f,args,lang
    and that the router defaults are da, dc, df, dl.

    We can perform these transformations trivially if args=[] and lang=None or dl:

    /da/dc/df => /
    /a/dc/df => /a
    /a/c/df => /a/c

    We would also like to be able to strip the default application or application/controller
    from URLs with function/args present, thus:

        /da/c/f/args  => /c/f/args
        /da/dc/f/args => /f/args

    We use [applications] and [controllers] to suppress ambiguous omissions.

    We assume that language names do not collide with a/c/f names.
    '''
    map = MapUrlOut(application, controller, function, args, lang)
    return map.acf()

def get_effective_router(appname):
    "return a read-only copy of the effective router for the specified application"
    if not thread.routes.router.active:
        return None
    router = Storage(thread.routes.router)  # return a copy
    #
    #  If this is the base router, adjust values for non-default application
    #
    if router.default_application != appname:
        router.controllers = _router_defaults.controllers
        router.languages = _router_defaults.languages
        router.default_language = _router_defaults.default_language
        router.check_args = _router_defaults.check_args
        router.map_hyphen = _router_defaults.map_hyphen
        router._acfe_match = _router_defaults._acfe_match
        router._file_match = _router_defaults._file_match
        router._args_match = _router_defaults._args_match
    router.base_router = params.router
    return router
