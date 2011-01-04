#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Contains:

- wsgibase: the gluon wsgi application

"""

import cgi
import cStringIO
import Cookie
import os
import re
import copy
import sys
import time
import thread
import datetime
import signal
import socket
import tempfile
import random
import string
from fileutils import abspath
from settings import global_settings
from admin import add_path_first, create_missing_folders, create_missing_app_folders

#  calling script has inserted path to script directory into sys.path
#  applications_parent (path to applications/, site-packages/ etc) defaults to that directory
#  set sys.path to ("", gluon_parent/site-packages, gluon_parent, ...)
#
#  this is wrong:
#  web2py_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#  because we do not want the path to this file which may be Library.zip
#
#  gluon_parent is the directory containing gluon, web2py.py, logging.conf and the handlers.
#  applications_parent (web2py_path) is the directory containing applications/ and routes.py
#  The two are identical unless web2py_path is changed via the web2py.py -f folder option
#  main.web2py_path is the same as applications_parent (for backward compatibility)
#
global_settings.gluon_parent = os.environ.get('web2py_path', os.getcwd())
global_settings.applications_parent = global_settings.gluon_parent
web2py_path = global_settings.applications_parent # backward compatibility
global_settings.app_folders = set()

create_missing_folders()

# set up logging for subsequent imports
import logging
import logging.config
logpath = abspath("logging.conf")
if os.path.exists(logpath):
    logging.config.fileConfig(abspath("logging.conf"))
else:
    logging.basicConfig()
logger = logging.getLogger("web2py")

from restricted import RestrictedError
from http import HTTP, redirect
from globals import Request, Response, Session
from compileapp import build_environment, run_models_in, \
    run_controller_in, run_view_in
from fileutils import copystream
from contenttype import contenttype
from sql import BaseAdapter
from settings import global_settings
from validators import CRYPT
from cache import Cache
from html import URL as Url
from storage import List
import newcron
import rewrite

__all__ = ['wsgibase', 'save_password', 'appfactory', 'HttpServer']

# Security Checks: validate URL and session_id here,
# accept_language is validated in languages

# pattern used to validate client address
regex_client = re.compile('[\w\-:]+(\.[\w\-]+)*\.?')  # ## to account for IPV6

version_info = open(abspath('VERSION'), 'r')
web2py_version = version_info.read()
version_info.close()

try:
    import rocket
except:
    if not global_settings.web2py_runtime_gae:
        logger.warn('unable to import Rocket')

rewrite.load()

def get_client(env):
    """
    guess the client address from the environment variables

    first tries 'http_x_forwarded_for', secondly 'remote_addr'
    if all fails assume '127.0.0.1' (running locally)
    """
    g = regex_client.search(env.get('http_x_forwarded_for', ''))
    if g:
        return g.group()
    g = regex_client.search(env.get('remote_addr', ''))
    if g:
        return g.group()
    return '127.0.0.1'

def copystream_progress(request, chunk_size= 10**5):
    """
    copies request.env.wsgi_input into request.body
    and stores progress upload status in cache.ram
    X-Progress-ID:length and X-Progress-ID:uploaded
    """
    if not request.env.content_length:
        return cStringIO.StringIO()
    source = request.env.wsgi_input
    size = int(request.env.content_length)
    dest = tempfile.TemporaryFile()
    if not 'X-Progress-ID' in request.vars:
        copystream(source, dest, size, chunk_size)
        return dest
    cache_key = 'X-Progress-ID:'+request.vars['X-Progress-ID']
    cache = Cache(request)
    cache.ram(cache_key+':length', lambda: size, 0)
    cache.ram(cache_key+':uploaded', lambda: 0, 0)
    while size > 0:
        if size < chunk_size:
            data = source.read(size)
            cache.ram.increment(cache_key+':uploaded', size)
        else:
            data = source.read(chunk_size)
            cache.ram.increment(cache_key+':uploaded', chunk_size)
        length = len(data)
        if length > size:
            (data, length) = (data[:size], size)
        size -= length
        if length == 0:
            break
        dest.write(data)
        if length < chunk_size:
            break
    dest.seek(0)
    cache.ram(cache_key+':length', None)
    cache.ram(cache_key+':uploaded', None)
    return dest


def serve_controller(request, response, session):
    """
    this function is used to generate a dynamic page.
    It first runs all models, then runs the function in the controller,
    and then tries to render the output using a view/template.
    this function must run from the [application] folder.
    A typical examples would be the call to the url
    /[application]/[controller]/[function] that would result in a call
    to [function]() in applications/[application]/[controller].py
    rendered by applications/[application]/[controller]/[view].html
    """

    # ##################################################
    # build environment for controller and view
    # ##################################################

    environment = build_environment(request, response, session)

    # set default view, controller can override it

    response.view = '%s/%s.%s' % (request.controller,
                                  request.function,
                                  request.extension)

    # also, make sure the flash is passed through
    # ##################################################
    # process models, controller and view (if required)
    # ##################################################

    run_models_in(environment)
    response._view_environment = copy.copy(environment)
    page = run_controller_in(request.controller, request.function, environment)
    if isinstance(page, dict):
        response._vars = page
        for key in page:
            response._view_environment[key] = page[key]
        run_view_in(response._view_environment)
        page = response.body.getvalue()
    raise HTTP(response.status, page, **response.headers)


def start_response_aux(status, headers, exc_info, response=None):
    """
    in controller you can use::

    - request.wsgi.environ
    - request.wsgi.start_response

    to call third party WSGI applications
    """
    response.status = str(status).split(' ',1)[0]
    response.headers = dict(headers)
    return lambda *args, **kargs: response.write(escape=False,*args,**kargs)


def middleware_aux(request, response, *middleware_apps):
    """
    In you controller use::

        @request.wsgi.middleware(middleware1, middleware2, ...)

    to decorate actions with WSGI middleware. actions must return strings.
    uses a simulated environment so it may have weird behavior in some cases
    """
    def middleware(f):
        def app(environ, start_response):
            data = f()
            start_response(response.status,response.headers.items())
            if isinstance(data,list):
                return data
            return [data]
        for item in middleware_apps:
            app=item(app)
        def caller(app):
            return app(request.wsgi.environ,request.wsgi.start_response)
        return lambda caller=caller, app=app: caller(app)
    return middleware

def environ_aux(environ,request):
    new_environ = copy.copy(environ)
    new_environ['wsgi.input'] = request.body
    new_environ['wsgi.version'] = 1
    return new_environ

def parse_get_post_vars(request, environ):

    # always parse variables in URL for GET, POST, PUT, DELETE, etc. in get_vars
    dget = cgi.parse_qsl(request.env.query_string, keep_blank_values=1)
    for (key, value) in dget:
        if key in request.get_vars:
            if isinstance(request.get_vars[key], list):
                request.get_vars[key] += [value]
            else:
                request.get_vars[key] = [request.get_vars[key]] + [value]
        else:
            request.get_vars[key] = value
        request.vars[key] = request.get_vars[key]

    # parse POST variables on POST, PUT, BOTH only in post_vars
    request.body = copystream_progress(request) ### stores request body
    if (request.body and request.env.request_method in ('POST', 'PUT', 'BOTH')):
        dpost = cgi.FieldStorage(fp=request.body,environ=environ,keep_blank_values=1)
        # The same detection used by FieldStorage to detect multipart POSTs
        is_multipart = dpost.type[:10] == 'multipart/'
        request.body.seek(0)
        isle25 = sys.version_info[1] <= 5

        def listify(a):
            return (not isinstance(a,list) and [a]) or a
        try:
            keys = sorted(dpost)
        except TypeError:
            keys = []
        for key in keys:
            dpk = dpost[key]
            # if en element is not a file replace it with its value else leave it alone
            if isinstance(dpk, list):
                if not dpk[0].filename:
                    value = [x.value for x in dpk]
                else:
                    value = [x for x in dpk]
            elif not dpk.filename:
                value = dpk.value
            else:
                value = dpk
            pvalue = listify(value)
            if key in request.vars:
                gvalue = listify(request.vars[key])
                if isle25:
                    value = pvalue + gvalue
                elif is_multipart:
                    pvalue = pvalue[len(gvalue):]
                else:
                    pvalue = pvalue[:-len(gvalue)]
            request.vars[key] = value
            if len(pvalue):
                request.post_vars[key] = (len(pvalue)>1 and pvalue) or pvalue[0]


def wsgibase(environ, responder):
    """
    this is the gluon wsgi application. the first function called when a page
    is requested (static or dynamic). it can be called by paste.httpserver
    or by apache mod_wsgi.

      - fills request with info
      - the environment variables, replacing '.' with '_'
      - adds web2py path and version info
      - compensates for fcgi missing path_info and query_string
      - validates the path in url

    The url path must be either:

    1. for static pages:

      - /<application>/static/<file>

    2. for dynamic pages:

      - /<application>[/<controller>[/<function>[/<sub>]]][.<extension>]
      - (sub may go several levels deep, currently 3 levels are supported:
         sub1/sub2/sub3)

    The naming conventions are:

      - application, controller, function and extension may only contain
        [a-zA-Z0-9_]
      - file and sub may also contain '-', '=', '.' and '/'
    """

    request = Request()
    response = Response()
    session = Session()
    request.env.web2py_path = global_settings.applications_parent
    request.env.web2py_version = web2py_version
    request.env.update(global_settings)
    static_file = False
    try:
        try:
            try:
                # ##################################################
                # handle fcgi missing path_info and query_string
                # select rewrite parameters
                # rewrite incoming URL
                # parse rewritten header variables
                # parse rewritten URL
                # serve file if static
                # ##################################################

                if not environ.get('PATH_INFO',None) and environ.get('REQUEST_URI',None):
                    # for fcgi, get path_info and query_string from request_uri
                    items = environ['REQUEST_URI'].split('?')
                    environ['PATH_INFO'] = items[0]
                    if len(items) > 1:
                        environ['QUERY_STRING'] = items[1]
                    else:
                        environ['QUERY_STRING'] = ''
                rewrite.select(env=environ, request=request)
                if rewrite.thread.routes.router.active:
                    (static_file, environ) = rewrite.map_url_in(request, environ)
                else:
                    (static_file, environ) = parse_url(request, environ)
                if static_file:
                    if request.env.get('query_string', '')[:10] == 'attachment':
                        response.headers['Content-Disposition'] = 'attachment'
                    response.stream(static_file, request=request)

                # ##################################################
                # fill in request items
                # ##################################################

                request.client = get_client(request.env)
                request.folder = os.path.join(request.env.applications_parent,
                        'applications', request.application) + '/'
                request.ajax = str(request.env.http_x_requested_with).lower() == 'xmlhttprequest'
                request.cid = request.env.http_web2py_component_element

                # ##################################################
                # access the requested application
                # ##################################################

                if not os.path.exists(request.folder):
                    if request.application == rewrite.thread.routes.default_application:
                        request.application = 'welcome'
                        redirect(Url(r=request))
                    elif rewrite.thread.routes.error_handler:
                        redirect(Url(rewrite.thread.routes.error_handler['application'],
                                     rewrite.thread.routes.error_handler['controller'],
                                     rewrite.thread.routes.error_handler['function'],
                                     args=request.application))
                    else:
                        raise HTTP(400,
                                   rewrite.thread.routes.error_message % 'invalid request',
                                   web2py_error='invalid application')
                request.url = Url(r=request, args=request.args,
                                       extension=request.raw_extension)

                # ##################################################
                # build missing folders
                # ##################################################

                create_missing_app_folders(request)

                # ##################################################
                # get the GET and POST data
                # ##################################################

                parse_get_post_vars(request, environ)

                # ##################################################
                # expose wsgi hooks for convenience
                # ##################################################

                request.wsgi.environ = environ_aux(environ,request)
                request.wsgi.start_response = lambda status='200', headers=[], \
                    exec_info=None, response=response: \
                    start_response_aux(status, headers, exec_info, response)
                request.wsgi.middleware = lambda *a: middleware_aux(request,response,*a)

                # ##################################################
                # load cookies
                # ##################################################

                if request.env.http_cookie:
                    try:
                        request.cookies.load(request.env.http_cookie)
                    except Cookie.CookieError, e:
                        pass # invalid cookies

                # ##################################################
                # try load session or create new session file
                # ##################################################

                session.connect(request, response)

                # ##################################################
                # set no-cache headers
                # ##################################################

                response.headers['Content-Type'] = contenttype('.'+request.extension)
                response.headers['Cache-Control'] = \
                    'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
                response.headers['Expires'] = \
                    time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
                response.headers['Pragma'] = 'no-cache'

                # ##################################################
                # run controller
                # ##################################################

                serve_controller(request, response, session)

            except HTTP, http_response:
                if static_file:
                    return http_response.to(responder)

                if request.body:
                    request.body.close()

                # ##################################################
                # on success, try store session in database
                # ##################################################
                session._try_store_in_db(request, response)

                # ##################################################
                # on success, commit database
                # ##################################################

                if response._custom_commit:
                    response._custom_commit()
                else:
                    BaseAdapter.close_all_instances(BaseAdapter.commit)

                # ##################################################
                # if session not in db try store session on filesystem
                # this must be done after trying to commit database!
                # ##################################################

                session._try_store_on_disk(request, response)

                # ##################################################
                # store cookies in headers
                # ##################################################

                if request.cid:
                    if response.flash and not 'web2py-component-flash' in http_response.headers:
                        http_response.headers['web2py-component-flash'] = \
                            str(response.flash).replace('\n','')
                    if response.js and not 'web2py-component-command' in http_response.headers:
                        http_response.headers['web2py-component-command'] = \
                            str(response.js).replace('\n','')
                if session._forget:
                    del response.cookies[response.session_id_name]
                elif session._secure:
                    response.cookies[response.session_id_name]['secure'] = True
                if len(response.cookies)>0:
                    http_response.headers['Set-Cookie'] = \
                        [str(cookie)[11:] for cookie in response.cookies.values()]
                ticket=None

            except RestrictedError, e:

                if request.body:
                    request.body.close()

                # ##################################################
                # on application error, rollback database
                # ##################################################

                ticket = e.log(request) or 'unknown'
                if response._custom_rollback:
                    response._custom_rollback()
                else:
                    BaseAdapter.close_all_instances(BaseAdapter.rollback)

                http_response = \
                    HTTP(500,
                         rewrite.thread.routes.error_message_ticket % dict(ticket=ticket),
                         web2py_error='ticket %s' % ticket)

        except:

            if request.body:
                request.body.close()

            # ##################################################
            # on application error, rollback database
            # ##################################################

            try:
                if response._custom_rollback:
                    response._custom_rollback()
                else:
                    BaseAdapter.close_all_instances(BaseAdapter.rollback)
            except:
                pass
            e = RestrictedError('Framework', '', '', locals())
            ticket = e.log(request) or 'unrecoverable'
            http_response = \
                HTTP(500,
                     rewrite.thread.routes.error_message_ticket % dict(ticket=ticket),
                     web2py_error='ticket %s' % ticket)

    finally:
        if response and hasattr(response, 'session_file') and response.session_file:
            response.session_file.close()

    session._unlock(response)
    http_response = rewrite.try_redirect_on_error(http_response,request,ticket)
    if global_settings.web2py_crontype == 'soft':
        newcron.softcron(global_settings.applications_parent).start()
    return http_response.to(responder)


def save_password(password, port):
    """
    used by main() to save the password in the parameters_port.py file.
    """

    password_file='parameters_%i.py' % port
    if password == '<random>':
        # make up a new password
        chars = string.letters + string.digits
        password = ''.join([random.choice(chars) for i in range(8)])
        cpassword = CRYPT()(password)[0]
        print '******************* IMPORTANT!!! ************************'
        print 'your admin password is "%s"' % password
        print '*********************************************************'
    elif password == '<recycle>':
        # reuse the current password if any
        if os.path.exists(password_file):
            return
        else:
            password = ''
    elif password.startswith('<pam_user:'):
        # use the pam password for specified user
        cpassword = password[1:-1]
    else:
        # use provided password
        cpassword = CRYPT()(password)[0]
    fp = open(password_file, 'w')
    if password:
        fp.write('password="%s"\n' % cpassword)
    else:
        fp.write('password=None\n')
    fp.close()


def appfactory(wsgiapp=wsgibase,
               logfilename='httpserver.log',
               profilerfilename='profiler.log'):
    """
    generates a wsgi application that does logging and profiling and calls
    wsgibase

    .. function:: gluon.main.appfactory(
            [wsgiapp=wsgibase
            [, logfilename='httpserver.log'
            [, profilerfilename='profiler.log']]])

    """
    if profilerfilename and os.path.exists(profilerfilename):
        os.unlink(profilerfilename)
    locker = thread.allocate_lock()

    def app_with_logging(environ, responder):
        """
        a wsgi app that does logging and profiling and calls wsgibase
        """
        status_headers = []

        def responder2(s, h):
            """
            wsgi responder app
            """
            status_headers.append(s)
            status_headers.append(h)
            return responder(s, h)

        time_in = time.time()
        ret = [0]
        if not profilerfilename:
            ret[0] = wsgiapp(environ, responder2)
        else:
            import cProfile
            import pstats
            logger.warn('profiler is on. this makes web2py slower and serial')

            locker.acquire()
            cProfile.runctx('ret[0] = wsgiapp(environ, responder2)',
                            globals(), locals(), profilerfilename+'.tmp')
            stat = pstats.Stats(profilerfilename+'.tmp')
            stat.stream = cStringIO.StringIO()
            stat.strip_dirs().sort_stats("time").print_stats(80)
            profile_out = stat.stream.getvalue()
            profile_file = open(profilerfilename, 'a')
            profile_file.write('%s\n%s\n%s\n%s\n\n' % \
               ('='*60, environ['PATH_INFO'], '='*60, profile_out))
            profile_file.close()
            locker.release()
        try:
            line = '%s, %s, %s, %s, %s, %s, %f\n' % (
                environ['REMOTE_ADDR'],
                datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                environ['REQUEST_METHOD'],
                environ['PATH_INFO'].replace(',', '%2C'),
                environ['SERVER_PROTOCOL'],
                (status_headers[0])[:3],
                time.time() - time_in,
                )
            if not logfilename:
                sys.stdout.write(line)
            elif isinstance(logfilename, str):
                open(logfilename, 'a').write(line)
            else:
                logfilename.write(line)
        except:
            pass
        return ret[0]

    return app_with_logging


class HttpServer(object):
    """
    the web2py web server (Rocket)
    """

    def __init__(
        self,
        ip='127.0.0.1',
        port=8000,
        password='',
        pid_filename='httpserver.pid',
        log_filename='httpserver.log',
        profiler_filename=None,
        ssl_certificate=None,
        ssl_private_key=None,
        min_threads=None,
        max_threads=None,
        server_name=None,
        request_queue_size=5,
        timeout=10,
        shutdown_timeout=None, # Rocket does not use a shutdown timeout
        path=None,
        interfaces=None # Rocket is able to use several interfaces - must be list of socket-tuples as string
        ):
        """
        starts the web server.
        """

        if interfaces:
            # if interfaces is specified, it must be tested for rocket parameter correctness
            # not necessarily completely tested (e.g. content of tuples or ip-format)
            import types
            if isinstance(interfaces,types.ListType):
                for i in interfaces:
                    if not isinstance(i,types.TupleType):
                        raise "Wrong format for rocket interfaces parameter - see http://packages.python.org/rocket/"
            else:
                raise "Wrong format for rocket interfaces parameter - see http://packages.python.org/rocket/"

        if path:
            # if a path is specified change the global variables so that web2py
            # runs from there instead of cwd or os.environ['web2py_path']
            global web2py_path
            path = os.path.normpath(path)
            web2py_path = path
            global_settings.applications_parent = path
            os.chdir(path)
            [add_path_first(p) for p in (path, abspath('site-packages'), "")]

        save_password(password, port)
        self.pid_filename = pid_filename
        if not server_name:
            server_name = socket.gethostname()
        logger.info('starting web server...')
        rocket.SERVER_NAME = server_name
        sock_list = [ip, port]
        if not ssl_certificate or not ssl_private_key:
              logger.info('SSL is off')
        elif not rocket.ssl:
             logger.warning('Python "ssl" module unavailable. SSL is OFF')
        if not ssl_certificate or not ssl_private_key:
            logger.info('SSL is off')
        elif not rocket.ssl:
            logger.warning('Python "ssl" module unavailable. SSL is OFF')
        elif not os.path.exists(ssl_certificate):
            logger.warning('unable to open SSL certificate. SSL is OFF')
        elif not os.path.exists(ssl_private_key):
            logger.warning('unable to open SSL private key. SSL is OFF')
        else:
            sock_list.extend([ssl_private_key, ssl_certificate])
            logger.info('SSL is ON')
        app_info = {'wsgi_app': appfactory(wsgibase,
                                           log_filename,
                                           profiler_filename) }

        self.server = rocket.Rocket(interfaces or tuple(sock_list),
                                    method='wsgi',
                                    app_info=app_info,
                                    min_threads=min_threads,
                                    max_threads=max_threads,
                                    queue_size=int(request_queue_size),
                                    timeout=int(timeout),
                                    handle_signals=False,
                                    )


    def start(self):
        """
        start the web server
        """
        try:
            signal.signal(signal.SIGTERM, lambda a, b, s=self: s.stop())
            signal.signal(signal.SIGINT, lambda a, b, s=self: s.stop())
        except:
            pass
        fp = open(self.pid_filename, 'w')
        fp.write(str(os.getpid()))
        fp.close()
        self.server.start()

    def stop(self, stoplogging=False):
        """
        stop cron and the web server
        """
        newcron.stopcron()
        self.server.stop(stoplogging)
        try:
            os.unlink(self.pid_filename)
        except:
            pass

# pattern to replace spaces with underscore in URL
#   also the html escaped variants '+' and '%20' are covered
regex_space = re.compile('(\+|\s|%20)+')

# pattern to find valid paths in url /application/controller/...
#   this could be:
#     for static pages:
#        /<b:application>/static/<x:file>
#     for dynamic pages:
#        /<a:application>[/<c:controller>[/<f:function>[.<e:ext>][/<s:args>]]]
#   application, controller, function and ext may only contain [a-zA-Z0-9_]
#   file and args may also contain '-', '=', '.' and '/'
#   apps in routes_apps_raw must parse raw_args into args

regex_static = re.compile(r'''
     (^                              # static pages
         /(?P<b> \w+)                # b=app
         /static                     # /b/static
         /(?P<x> (\w[\-\=\./]?)* )   # x=file
     $)
     ''', re.X)

regex_url = re.compile(r'''
     (^(                                  # (/a/c/f.e/s)
         /(?P<a> [\w\s+]+ )               # /a=app
         (                                # (/c.f.e/s)
             /(?P<c> [\w\s+]+ )           # /a/c=controller
             (                            # (/f.e/s)
                 /(?P<f> [\w\s+]+ )       # /a/c/f=function
                 (                        # (.e)
                     \.(?P<e> [\w\s+]+ )  # /a/c/f.e=extension
                 )?
                 (                        # (/s)
                     /(?P<r>              # /a/c/f.e/r=raw_args
                     .+
                     )
                 )?
             )?
         )?
     )?
     /?$)    # trailing slash
     ''', re.X)

regex_args = re.compile(r'''
     (^
         (?P<s>
             ( [\w@-][=./]? )+          # s=args
         )?
     /?$)    # trailing slash
     ''', re.X)

def parse_url(request, environ):
    "rewrite and parse incoming URL"

    # ##################################################
    # select application
    # rewrite URL if routes_in is defined
    # update request.env
    # ##################################################

    if rewrite.thread.routes.routes_in:
        environ = rewrite.filter_in(environ)

    for (key, value) in environ.items():
        request.env[key.lower().replace('.', '_')] = value

    path = request.env.path_info.replace('\\', '/')

    # ##################################################
    # serve if a static file
    # ##################################################

    match = regex_static.match(regex_space.sub('_', path))
    if match and match.group('x'):
        static_file = os.path.join(request.env.applications_parent,
                                   'applications', match.group('b'),
                                   'static', match.group('x'))
        return (static_file, environ)

    # ##################################################
    # parse application, controller and function
    # ##################################################

    path = re.sub('%20', ' ', path)
    match = regex_url.match(path)
    if not match or match.group('c') == 'static':
        raise HTTP(400,
                   rewrite.thread.routes.error_message % 'invalid request',
                   web2py_error='invalid path')

    request.application = \
        regex_space.sub('_', match.group('a') or rewrite.thread.routes.default_application)
    request.controller = \
        regex_space.sub('_', match.group('c') or rewrite.thread.routes.default_controller)
    request.function = \
        regex_space.sub('_', match.group('f') or rewrite.thread.routes.default_function)
    group_e = match.group('e')
    request.raw_extension = group_e and regex_space.sub('_', group_e) or None
    request.extension = request.raw_extension or 'html'
    request.raw_args = match.group('r')
    request.args = List([])
    if request.application in rewrite.thread.routes.routes_apps_raw:
        # application is responsible for parsing args
        request.args = None
    elif request.raw_args:
        match = regex_args.match(request.raw_args.replace(' ', '_'))
        if match:
            group_s = match.group('s')
            request.args = \
                List((group_s and group_s.split('/')) or [])
        else:
            raise HTTP(400,
                       rewrite.thread.routes.error_message % 'invalid request',
                       web2py_error='invalid path')
    return (None, environ)

