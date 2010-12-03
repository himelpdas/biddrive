# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import sys
import errno
import socket
import logging
import platform

# Define Constants
VERSION = '1.2.0'
SERVER_NAME = socket.gethostname()
SERVER_SOFTWARE = 'Rocket %s' % VERSION
HTTP_SERVER_SOFTWARE = '%s Python/%s' % (SERVER_SOFTWARE, sys.version.split(' ')[0])
BUF_SIZE = 16384
SOCKET_TIMEOUT = 1 # in secs
THREAD_STOP_CHECK_INTERVAL = 1 # in secs, How often should threads check for a server stop message?
IS_JYTHON = platform.system() == 'Java' # Handle special cases for Jython
IGNORE_ERRORS_ON_CLOSE = set([errno.ECONNABORTED, errno.ECONNRESET])
DEFAULT_LISTEN_QUEUE_SIZE = 5
DEFAULT_MIN_THREADS = 10
DEFAULT_MAX_THREADS = 0
DEFAULTS = dict(LISTEN_QUEUE_SIZE = DEFAULT_LISTEN_QUEUE_SIZE,
                MIN_THREADS = DEFAULT_MIN_THREADS,
                MAX_THREADS = DEFAULT_MAX_THREADS)

PY3K = sys.version_info[0] > 2

class NullHandler(logging.Handler):
    "A Logging handler to prevent library errors."
    def emit(self, record):
        pass

if PY3K:
    def b(val):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(val, str):
            return val.encode()
        else:
            return val

    def u(val, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(val, bytes):
            return val.decode(encoding)
        else:
            return val

else:
    def b(val):
        """ Convert string/unicode/bytes literals into bytes.  This allows for
        the same code to run on Python 2.x and 3.x. """
        if isinstance(val, unicode):
            return val.encode()
        else:
            return val

    def u(val, encoding="us-ascii"):
        """ Convert bytes into string/unicode.  This allows for the
        same code to run on Python 2.x and 3.x. """
        if isinstance(val, str):
            return val.decode(encoding)
        else:
            return val

# Import Package Modules
# package imports removed in monolithic build

__all__ = ['VERSION', 'SERVER_SOFTWARE', 'HTTP_SERVER_SOFTWARE', 'BUF_SIZE',
           'IS_JYTHON', 'IGNORE_ERRORS_ON_CLOSE', 'DEFAULTS', 'PY3K', 'b', 'u',
           'Rocket', 'CherryPyWSGIServer', 'SERVER_NAME', 'NullHandler']

# Monolithic build...end of module: rocket\__init__.py
# Monolithic build...start of module: rocket\connection.py

# Import System Modules
import sys
import time
import socket
try:
    import ssl
    has_ssl = True
except ImportError:
    has_ssl = False
# package imports removed in monolithic build

class Connection:
    def __init__(self, sock_tuple, port, secure=False):
        self.client_addr, self.client_port = sock_tuple[1]
        self.server_port = port
        self.socket = sock_tuple[0]
        self.start_time = time.time()
        self.ssl = has_ssl and isinstance(self.socket, ssl.SSLSocket)
        self.secure = secure

        if IS_JYTHON:
            # In Jython we must set TCP_NODELAY here.
            # See: http://bugs.jython.org/issue1309
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if hasattr(self.socket, 'settimeout'):
            self.socket.settimeout(SOCKET_TIMEOUT)

        for x in dir(self.socket):
            if not hasattr(self, x):
                try:
                    self.__dict__[x] = self.socket.__getattribute__(x)
                except:
                    pass

    def close(self):
        if hasattr(self.socket, '_sock'):
            try:
                self.socket._sock.close()
            except socket.error:
                info = sys.exc_info()
                if info[1].errno != socket.EBADF:
                    raise info[1]
                else:
                    pass
        self.socket.close()

# Monolithic build...end of module: rocket\connection.py
# Monolithic build...start of module: rocket\listener.py

# Import System Modules
import os
import sys
import socket
import logging
import traceback
from threading import Thread

try:
    import ssl
    from ssl import SSLError
    has_ssl = True
except ImportError:
    has_ssl = False
    class SSLError(socket.error):
        pass
# Import Package Modules
# package imports removed in monolithic build

class Listener(Thread):
    """The Listener class is a class responsible for accepting connections
    and queuing them to be processed by a worker thread."""

    def __init__(self, interface, queue_size, active_queue, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)

        # Instance variables
        self.active_queue = active_queue
        self.interface = interface
        self.addr = interface[0]
        self.port = interface[1]
        self.secure = len(interface) == 4 and \
                      os.path.exists(interface[2]) and \
                      os.path.exists(interface[3])
        self.ready = False

        # Error Log
        self.err_log = logging.getLogger('Rocket.Errors.Port%i' % self.port)
        self.err_log.addHandler(NullHandler())

        # Build the socket
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if not listener:
            self.err_log.error("Failed to get socket.")
            return

        if self.secure:
            if not has_ssl:
                self.err_log.error("ssl module required to serve HTTPS.")
                del listener
                return
            elif not os.path.exists(interface[2]):
                data = (interface[2], interface[0], interface[1])
                self.err_log.error("Cannot find key file "
                          "'%s'.  Cannot bind to %s:%s" % data)
                del listener
                return
            elif not os.path.exists(interface[3]):
                data = (interface[3], interface[0], interface[1])
                self.err_log.error("Cannot find certificate file "
                          "'%s'.  Cannot bind to %s:%s" % data)
                del listener
                return

        # Set socket options
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:
            msg = "Cannot share socket.  Using %s:%i exclusively."
            self.err_log.warning(msg % (self.addr, self.port))

        try:
            if not IS_JYTHON:
                listener.setsockopt(socket.IPPROTO_TCP,
                                    socket.TCP_NODELAY,
                                    1)
        except:
            msg = "Cannot set TCP_NODELAY, things might run a little slower"
            self.err_log.warning(msg)

        try:
            listener.bind((self.addr, self.port))
        except:
            msg = "Socket %s:%i in use by other process and it won't share."
            self.err_log.error(msg % (self.addr, self.port))
        else:
            # We want socket operations to timeout periodically so we can
            # check if the server is shutting down
            listener.settimeout(THREAD_STOP_CHECK_INTERVAL)
            # Listen for new connections allowing queue_size number of
            # connections to wait before rejecting a connection.
            listener.listen(queue_size)

            self.listener = listener

            self.ready = True

    def wrap_socket(self, sock_pair):
        sock, client = sock_pair
        try:
            sock = ssl.wrap_socket(sock,
                                   keyfile=self.interface[2],
                                   certfile=self.interface[3],
                                   server_side=True,
                                   ssl_version=ssl.PROTOCOL_SSLv23)
        except SSLError:
            # Generally this happens when an HTTP request is received on a
            # secure socket. We don't do anything because it will be detected
            # by Worker and dealt with appropriately.
            pass

        return (sock, client)

    def run(self):
        if not self.ready:
            self.err_log.warning('Listener started when not ready.')
            return

        self.err_log.debug('Entering main loop.')
        while True:
            try:
                sock = self.listener.accept()
                if self.secure:
                    sock = self.wrap_socket(sock)

                self.active_queue.put((sock, self.interface[1], self.secure))

            except socket.timeout:
                # socket.timeout will be raised every THREAD_STOP_CHECK_INTERVAL
                # seconds.  When that happens, we check if it's time to die.

                if not self.ready:
                    self.err_log.info('Listener exiting.')
                    return
                else:
                    continue
            except:
                self.err_log.error(str(traceback.format_exc()))

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        self.closeConnection = True
        raise NotImplementedError('Overload this method!')

    def kill(self):
        if self.isAlive() and hasattr(self, 'conn'):
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    self.err_log.debug('Error on shutdown: '+str(info))

# Monolithic build...end of module: rocket\listener.py
# Monolithic build...start of module: rocket\main.py

# Import System Modules
import sys
import time
import socket
import logging
import traceback

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

# Import Package Modules
# package imports removed in monolithic build





# Setup Logging
log = logging.getLogger('Rocket')
log.addHandler(NullHandler())

class Rocket:
    """The Rocket class is responsible for handling threads and accepting and
    dispatching connections."""

    def __init__(self,
                 interfaces = ('127.0.0.1', 8000),
                 method = 'wsgi',
                 app_info = None,
                 min_threads = None,
                 max_threads = None,
                 queue_size = None,
                 timeout = 600,
                 handle_signals = True):

        self.handle_signals = handle_signals

        if not isinstance(interfaces, list):
            self.interfaces = [interfaces]
        else:
            self.interfaces = interfaces

        if None == min_threads:
            min_threads = DEFAULTS['MIN_THREADS']

        if None == max_threads:
            max_threads = DEFAULTS['MAX_THREADS']

        if not queue_size:
            if hasattr(socket, 'SOMAXCONN'):
                queue_size = socket.SOMAXCONN
            else:
                queue_size = DEFAULTS['LISTEN_QUEUE_SIZE']

        if max_threads and queue_size > max_threads:
            queue_size = max_threads

        if isinstance(app_info, dict):
            app_info['server_software'] = SERVER_SOFTWARE

        monitor_queue = Queue()
        active_queue = Queue()

        self._monitor = Monitor(monitor_queue, active_queue, timeout)

        self._threadpool = ThreadPool(get_method(method),
                                      app_info = app_info,
                                      active_queue=active_queue,
                                      monitor_queue = monitor_queue,
                                      min_threads=min_threads,
                                      max_threads=max_threads)

        # Build our socket listeners
        self.listeners = [Listener(i, queue_size, active_queue) for i in self.interfaces]
        for ndx in range(len(self.listeners)-1, 0, -1):
            if not self.listeners[ndx].ready:
                del self.listeners[ndx]

        if not self.listeners:
            log.critical("No interfaces to listen on...closing.")
            sys.exit(1)

    def _sigterm(self, signum, frame):
        log.info('Received SIGTERM')
        self.stop()

    def _sighup(self, signum, frame):
        log.info('Received SIGHUP')
        self.restart()

    def start(self):
        log.info('Starting %s' % SERVER_SOFTWARE)

        # Set up our shutdown signals
        if self.handle_signals:
            try:
                import signal
                signal.signal(signal.SIGTERM, self._sigterm)
                signal.signal(signal.SIGUSR1, self._sighup)
            except:
                log.debug('This platform does not support signals.')

        # Start our worker threads
        self._threadpool.start()

        # Start our monitor thread
        self._monitor.daemon = True
        self._monitor.start()

        # I know that EXPR and A or B is bad but I'm keeping it for Py2.4
        # compatibility.
        str_extract = lambda l: (l.addr, l.port, l.secure and '*' or '')

        msg = 'Listening on sockets: '
        msg += ', '.join(['%s:%i%s' % str_extract(l) for l in self.listeners])
        log.info(msg)

        for l in self.listeners:
            l.start()

        tp = self._threadpool
        dynamic_resize = tp.dynamic_resize

        while not tp.stop_server:
            try:
                dynamic_resize()
                time.sleep(THREAD_STOP_CHECK_INTERVAL)
            except KeyboardInterrupt:
                # Capture a keyboard interrupt when running from a console
                break;
            except:
                if not tp.stop_server:
                    log.error(str(traceback.format_exc()))
                    continue

        return self.stop()

    def stop(self, stoplogging = True):
        log.info("Stopping Server")

        # Stop listeners
        for l in self.listeners:
            l.ready = False
            if l.isAlive():
                l.join()

        # Stop Worker threads
        self._threadpool.stop()

        # Stop Monitor
        self._monitor.stop()
        if self._monitor.isAlive():
            self._monitor.join()

        if stoplogging:
            logging.shutdown()

    def restart(self):
        self.stop(False)
        self.start()

def CherryPyWSGIServer(bind_addr,
                       wsgi_app,
                       numthreads=10,
                       server_name=None,
                       max=-1,
                       request_queue_size=5,
                       timeout=10,
                       shutdown_timeout=5):
    """ A Cherrypy wsgiserver-compatible wrapper. """
    max_threads = max
    if max_threads < 0:
        max_threads = 0
    return Rocket(bind_addr, 'wsgi', {'wsgi_app': wsgi_app},
                  min_threads = numthreads,
                  max_threads = max_threads,
                  queue_size = request_queue_size,
                  timeout = timeout)

# Monolithic build...end of module: rocket\main.py
# Monolithic build...start of module: rocket\monitor.py

# Import System Modules
import time
import logging
import select
from threading import Thread

# Import Package Modules
# package imports removed in monolithic build


class Monitor(Thread):
    # Monitor worker class.

    def __init__(self,
                 monitor_queue,
                 active_queue,
                 timeout,
                 *args,
                 **kwargs):

        Thread.__init__(self, *args, **kwargs)

        # Instance Variables
        self.monitor_queue = monitor_queue
        self.active_queue = active_queue
        self.timeout = timeout

        self.connections = set()
        self.active = False

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.Monitor')
        self.log.addHandler(NullHandler())

        self.active = True

        self.log.debug('Entering monitor loop.')

        # Enter thread main loop
        while self.active:
            # Move the queued connections to the selection pool
            while not self.monitor_queue.empty() or not len(self.connections):
                self.log.debug('In "receive timed-out connections" loop.')

                c = self.monitor_queue.get()

                if None == c:
                    # A non-client is a signal to die
                    self.log.debug('Received a death threat.')
                    return

                self.log.debug('Received a timed out connection.')

                assert(c not in self.connections)

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it.
                    c.setblocking(False)

                self.log.debug('Adding connection to monitor list.')
                self.connections.add(c)

            # Wait on those connections
            self.log.debug('Blocking on connections')
            readable = select.select(list(self.connections),
                                     [], [], THREAD_STOP_CHECK_INTERVAL)[0]

            # If we have any readable connections, put them back
            for r in readable:
                self.log.debug('Restoring readable connection')

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it, but the rest of the code requires
                    # that it be in blocking mode.
                    r.setblocking(True)

                r.start_time = time.time()
                self.active_queue.put(r)
                self.connections.remove(r)

            # If we have any stale connections, kill them off.
            if self.timeout:
                now = time.time()
                stale = set()
                for c in self.connections:
                    if (now - c.start_time) >= self.timeout:
                        stale.add(c)

                for c in stale:
                    # "EXPR and A or B" kept for Py2.4 compatibility
                    data = (c.client_addr, c.server_port, c.ssl and '*' or '')
                    self.log.debug('Flushing stale connection: %s:%i%s' % data)
                    self.connections.remove(c)
                    try:
                        c.close()
                    finally:
                        del c

    def stop(self):
        self.active = False

        self.log.debug('Flushing waiting connections')
        for c in self.connections:
            try:
                c.close()
            finally:
                del c

        self.log.debug('Flushing queued connections')
        while not self.monitor_queue.empty():
            c = self.monitor_queue.get()

            if None == c:
                continue

            try:
                c.close()
            finally:
                del c

        # Place a None sentry value to cause the monitor to die.
        self.monitor_queue.put(None)

# Monolithic build...end of module: rocket\monitor.py
# Monolithic build...start of module: rocket\threadpool.py

# Import System Modules
import logging
# Import Package Modules
# package imports removed in monolithic build

# Setup Logging
log = logging.getLogger('Rocket.Errors.ThreadPool')
log.addHandler(NullHandler())

class ThreadPool:
    """The ThreadPool class is a container class for all the worker threads. It
    manages the number of actively running threads."""

    def __init__(self,
                 method,
                 app_info,
                 active_queue,
                 monitor_queue,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 ):

        log.debug("Initializing ThreadPool.")
        self.check_for_dead_threads = 0
        self.active_queue = active_queue

        self.worker_class = method
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.monitor_queue = monitor_queue
        self.stop_server = False
        self.grow_threshold = int(max_threads/10) + 2

        if not isinstance(app_info, dict):
            app_info = dict()

        app_info.update(max_threads=max_threads,
                        min_threads=min_threads)

        self.threads = set()
        for x in range(min_threads):
            worker = self.worker_class(app_info,
                                       self.active_queue,
                                       self.monitor_queue)
            self.threads.add(worker)

    def start(self):
        self.stop_server = False
        log.debug("Starting threads.")
        for thread in self.threads:
            thread.setDaemon(True)
            thread._pool = self
            thread.start()

    def stop(self):
        log.debug("Stopping threads.")
        self.stop_server = True

        # Prompt the threads to die
        for t in self.threads:
            self.active_queue.put(None)

        # Give them the gun
        for t in self.threads:
            t.kill()

        # Wait until they pull the trigger
        for t in self.threads:
            t.join()

        # Clean up the mess
        self.bring_out_your_dead()

    def bring_out_your_dead(self):
        # Remove dead threads from the pool

        dead_threads = [t for t in self.threads if not t.isAlive()]
        for t in dead_threads:
            log.debug("Removing dead thread: %s." % t.getName())
            try:
                # Py2.4 complains here so we put it in a try block
                self.threads.remove(t)
            except:
                pass
        self.check_for_dead_threads -= len(dead_threads)

    def grow(self, amount=None):
        if self.stop_server:
            return

        if not amount:
            amount = self.max_threads

        amount = min([amount, self.max_threads - len(self.threads)])

        log.debug("Growing by %i." % amount)

        for x in range(amount):
            new_worker = self.worker_class()
            self.threads.add(new_worker)
            new_worker.start()

    def shrink(self, amount=1):
        log.debug("Shrinking by %i." % amount)

        self.check_for_dead_threads += amount

        for x in range(amount):
            self.active_queue.put(None)

    def dynamic_resize(self):
        if (self.max_threads > self.min_threads or self.max_threads == 0):
            if self.check_for_dead_threads > 0:
                self.bring_out_your_dead()

            queueSize = self.active_queue.qsize()
            threadCount = len(self.threads)

            log.debug("Examining ThreadPool. %i threads and %i Q'd conxions"
                      % (threadCount, queueSize))

            if queueSize == 0 and threadCount > self.min_threads:
                self.shrink()

            elif queueSize > self.grow_threshold \
                 and threadCount < self.max_threads:

                self.grow(queueSize)

# Monolithic build...end of module: rocket\threadpool.py
# Monolithic build...start of module: rocket\worker.py

# Import System Modules
import re
import sys
import socket
import logging
import traceback
#from wsgiref.headers import Headers
from threading import Thread
from datetime import datetime

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO

try:
    from ssl import SSLError
except ImportError:
    class SSLError(socket.error):
        pass
# Import Package Modules
# package imports removed in monolithic build


# Define Constants
re_SLASH = re.compile('%2F', re.IGNORECASE)
LOG_LINE = '%(client_ip)s - "%(request_line)s" - %(status)s %(size)s'
RESPONSE = '''\
HTTP/1.1 %s
Content-Length: %i
Content-Type: %s

%s
'''

###
# The Headers and FileWrapper classes are ripped straight from the Python
# Standard Library. I've removed some docstrings and integrated my BUF_SIZE.
# See the Python License here: http://docs.python.org/license.html
###

# Regular expression that matches `special' characters in parameters, the
# existance of which force quoting of the parameter value.
import re
_tspecials = re.compile(r'[ \(\)<>@,;:\\"/\[\]\?=]')

def _formatparam(param, value=None, quote=1):
    """Convenience function to format and return a key=value pair.

    This will quote the value if needed or if quote is true.
    """
    if value is not None and len(value) > 0:
        if quote or _tspecials.search(value):
            value = value.replace('\\', '\\\\').replace('"', r'\"')
            return '%s="%s"' % (param, value)
        else:
            return '%s=%s' % (param, value)
    else:
        return param

class Headers:
    def __init__(self,headers):
        if type(headers) is not type([]):
            raise TypeError("Headers must be a list of name/value tuples")
        self._headers = headers

    def __len__(self):
        return len(self._headers)

    def __setitem__(self, name, val):
        del self[name]
        self._headers.append((name, val))

    def __delitem__(self,name):
        name = name.lower()
        self._headers[:] = [kv for kv in self._headers if kv[0].lower() != name]

    def __getitem__(self,name):
        return self.get(name)

    def has_key(self, name):
        return self.get(name) is not None

    __contains__ = has_key

    def get_all(self, name):
        name = name.lower()
        return [kv[1] for kv in self._headers if kv[0].lower()==name]

    def get(self,name,default=None):
        name = name.lower()
        for k,v in self._headers:
            if k.lower()==name:
                return v
        return default

    def keys(self):
        return [k for k, v in self._headers]

    def values(self):
        return [v for k, v in self._headers]

    def items(self):
        return self._headers[:]

    def __repr__(self):
        return "Headers(%r)" % self._headers

    def __str__(self):
        return '\r\n'.join(["%s: %s" % kv for kv in self._headers]+['',''])

    def setdefault(self,name,value):
        result = self.get(name)
        if result is None:
            self._headers.append((name,value))
            return value
        else:
            return result


    def add_header(self, _name, _value, **_params):
        parts = []
        if _value is not None:
            parts.append(_value)
        for k, v in _params.items():
            if v is None:
                parts.append(k.replace('_', '-'))
            else:
                parts.append(_formatparam(k.replace('_', '-'), v))
        self._headers.append((_name, "; ".join(parts)))

class FileWrapper:
    """Wrapper to convert file-like objects to iterables"""

    def __init__(self, filelike, blksize=BUF_SIZE):
        self.filelike = filelike
        self.blksize = blksize
        if hasattr(filelike,'close'):
            self.close = filelike.close

    def __getitem__(self,key):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError

    def __iter__(self):
        return self

    def next(self):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise StopIteration

class Worker(Thread):
    """The Worker class is a base class responsible for receiving connections
    and (a subclass) will run an application to process the the connection """

    def __init__(self,
                 app_info,
                 active_queue,
                 monitor_queue,
                 *args,
                 **kwargs):

        Thread.__init__(self, *args, **kwargs)

        # Instance Variables
        self.app_info = app_info
        self.active_queue = active_queue
        self.monitor_queue = monitor_queue

        # Request Log
        self.req_log = logging.getLogger('Rocket.Requests')
        self.req_log.addHandler(NullHandler())

        # Error Log
        self.err_log = logging.getLogger('Rocket.Errors.'+self.getName())
        self.err_log.addHandler(NullHandler())

    def _handleError(self, typ, val, tb):
        if typ == SSLError:
            if 'timed out' in val.args[0]:
                typ = SocketTimeout
        if typ == SocketTimeout:
            self.err_log.debug('Socket timed out')
            self.monitor_queue.put(self.conn)
            return True
        if typ == SocketClosed:
            self.closeConnection = True
            self.err_log.debug('Client closed socket')
            return False
        if typ == BadRequest:
            self.closeConnection = True
            self.err_log.debug('Client sent a bad request')
            return True
        if typ == socket.error:
            self.closeConnection = True
            if val.args[0] in IGNORE_ERRORS_ON_CLOSE:
                self.closeConnection = True
                self.err_log.debug('Ignorable socket Error received...'
                                   'closing connection.')
                return False
            else:
                self.status = "999 Utter Server Failure"
                tb = traceback.format_exception((typ, val, tb))
                self.err_log.error('Unhandled Error when serving '
                                   'connection:\n' + tb)
                return False

        self.closeConnection = True
        self.err_log.error(str(traceback.format_exc()))
        self.send_response('500 Server Error')
        return False

    def run(self):
        self.err_log.debug('Entering main loop.')

        # Enter thread main loop
        while True:
            conn = self.active_queue.get()

            if not conn:
                # A non-client is a signal to die
                self.err_log.debug('Received a death threat.')
                return

            if isinstance(conn, tuple):
                conn = Connection(*conn)

            self.conn = conn

            if conn.ssl != conn.secure:
                self.err_log.info('Received HTTP connection on HTTPS port.')
                self.send_response('400 Bad Request')
                self.closeConnection = True
                conn.close()
                continue
            else:
                self.err_log.debug('Received a connection.')
                self.closeConnection = False

            # Enter connection serve loop
            while True:
                self.err_log.debug('Serving a request')
                try:
                    self.run_app(conn)
                    log_info = dict(client_ip = conn.client_addr,
                                    time = datetime.now().strftime('%c'),
                                    status = self.status.split(' ')[0],
                                    size = self.size,
                                    request_line = self.request_line)
                    self.req_log.info(LOG_LINE % log_info)
                except:
                    exc = sys.exc_info()
                    handled = self._handleError(*exc)
                    if handled:
                        break
                    else:
                        if self.request_line:
                            log_info = dict(client_ip = conn.client_addr,
                                            time = datetime.now().strftime('%c'),
                                            status = self.status.split(' ')[0],
                                            size = self.size,
                                            request_line = self.request_line + ' - not stopping')
                            self.req_log.info(LOG_LINE % log_info)

                if self.closeConnection:
                    try:
                        conn.close()
                    except:
                        self.err_log.error(str(traceback.format_exc()))

                    break

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        self.closeConnection = True
        raise NotImplementedError('Overload this method!')

    def send_response(self, status):
        msg = RESPONSE % (status,
                          len(status),
                          'text/plain',
                          status.split(' ', 1)[1])
        try:
            self.conn.sendall(b(msg))
        except socket.error:
            self.closeConnection = True
            self.err_log.error('Tried to send "%s" to client but received socket'
                           ' error' % status)

    def kill(self):
        if self.isAlive() and hasattr(self, 'conn'):
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    self.err_log.debug('Error on shutdown: '+str(info))

    def read_request_line(self, sock_file):
        self.request_line = ''
        try:
            # Grab the request line
            d = sock_file.readline()
            if PY3K:
                d = d.decode('ISO-8859-1')

            if d == '\r\n':
                # Allow an extra NEWLINE at the beginner per HTTP 1.1 spec
                self.err_log.debug('Client sent newline')
                d = sock_file.readline()
                if PY3K:
                    d = d.decode('ISO-8859-1')
        except socket.timeout:
            raise SocketTimeout("Socket timed out before request.")

        if d.strip() == '':
            self.err_log.debug('Client did not send a recognizable request.')
            raise SocketClosed('Client closed socket.')

        try:
            self.request_line = d.strip()
            method, uri, proto = self.request_line.split(' ')
            assert proto.startswith('HTTP')
        except ValueError:
            self.send_response('400 Bad Request')
            raise BadRequest
        except AssertionError:
            self.send_response('400 Bad Request')
            raise BadRequest

        req = dict(method=method, protocol = proto)
        scheme = ''
        host = ''
        if uri == '*' or uri.startswith('/'):
            path = uri
        elif '://' in uri:
            scheme, rest = uri.split('://')
            host, path = rest.split('/', 1)
        else:
            self.send_response('400 Bad Request')
            raise BadRequest

        query_string = ''
        if '?' in path:
            path, query_string = path.split('?', 1)

        path = r'%2F'.join([unquote(x) for x in re_SLASH.split(path)])

        req.update(path=path,
                   query_string=query_string,
                   scheme=scheme.lower(),
                   host=host)
        return req

    def read_headers(self, sock_file):
        headers = Headers([])
        l = sock_file.readline()

        lname = None
        lval = None
        while True:
            try:
                if PY3K:
                    l = str(l, 'ISO-8859-1')
            except UnicodeDecodeError:
                self.err_log.warning('Client sent invalid header: ' + repr(l))

            if l == '\r\n':
                break

            if l[0] in ' \t' and lname:
                # Some headers take more than one line
                lval += ', ' + l.strip()
            else:
                # HTTP header values are latin-1 encoded
                l = l.split(':', 1)
                # HTTP header names are us-ascii encoded
                lname = l[0].strip().replace('-', '_')
                lval = l[-1].strip()
            headers[str(lname)] = str(lval)

            l = sock_file.readline()
        return headers

class SocketTimeout(Exception):
    "Exception for when a socket times out between requests."
    pass

class BadRequest(Exception):
    "Exception for when a client sends an incomprehensible request."
    pass

class SocketClosed(Exception):
    "Exception for when a socket is closed by the client."
    pass

class ChunkedReader:
    def __init__(self, sock_file):
        self.stream = sock_file
        self.buffer = None
        self.buffer_size = 0

    def _read_chunk(self):
        if not self.buffer or self.buffer.tell() == self.buffer_size:
            try:
                self.buffer_size = int(self.stream.readline().strip(), 16)
            except ValueError:
                self.buffer_size = 0

            if self.buffer_size:
                self.buffer = StringIO(self.stream.read(self.buffer_size))

    def read(self, size):
        data = b('')
        while size:
            self._read_chunk()
            if not self.buffer_size:
                break
            read_size = min(size, self.buffer_size)
            data += self.buffer.read(read_size)
            size -= read_size
        return data

    def readline(self):
        data = b('')
        c = self.read(1)
        while c != b('\n') or c == b(''):
            data += c
            c = self.read(1)
        data += c
        return data

    def readlines(self):
        yield self.readline()

def get_method(method):

    methods = dict(wsgi=WSGIWorker)
    return methods[method.lower()]

# Monolithic build...end of module: rocket\worker.py
# Monolithic build...start of module: rocket\methods\__init__.py

# Monolithic build...end of module: rocket\methods\__init__.py
# Monolithic build...start of module: rocket\methods\wsgi.py

# Import System Modules
import sys
import socket
#from wsgiref.headers import Headers
#from wsgiref.util import FileWrapper
# Import Package Modules
# package imports removed in monolithic build

if PY3K:
    from email.utils import formatdate
else:
    # Caps Utils for Py2.4 compatibility
    from email.Utils import formatdate

# Define Constants
NEWLINE = b('\r\n')
HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s'''
BASE_ENV = {'SERVER_NAME': SERVER_NAME,
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.file_wrapper': FileWrapper
            }

class WSGIWorker(Worker):
    def __init__(self, *args, **kwargs):
        """Builds some instance variables that will last the life of the
        thread."""
        Worker.__init__(self, *args, **kwargs)

        if isinstance(self.app_info, dict):
            multithreaded = self.app_info.get('max_threads') != 1
        else:
            multithreaded = False
        self.base_environ = dict({'SERVER_SOFTWARE': self.app_info['server_software'],
                                  'wsgi.multithread': multithreaded,
                                  })
        self.base_environ.update(BASE_ENV)
        # Grab our application
        self.app = self.app_info.get('wsgi_app')

        if not hasattr(self.app, "__call__"):
            raise TypeError("The wsgi_app specified (%s) is not a valid WSGI application." % repr(self.app))


    def build_environ(self, sock_file, conn):
        """ Build the execution environment. """
        # Grab the request line
        request = self.read_request_line(sock_file)

        # Grab the headers
        self.headers = dict([(str('HTTP_'+k.upper()), v) for k, v in self.read_headers(sock_file).items()])

        # Copy the Base Environment
        environ = dict(self.base_environ)

        # Add CGI Variables
        environ['REQUEST_METHOD'] = request['method']
        environ['PATH_INFO'] = request['path']
        environ['SERVER_PROTOCOL'] = request['protocol']
        environ['SCRIPT_NAME'] = '' # Direct call WSGI does not need a name
        environ['SERVER_PORT'] = str(conn.server_port)
        environ['REMOTE_PORT'] = str(conn.client_port)
        environ['REMOTE_ADDR'] = str(conn.client_addr)
        environ['QUERY_STRING'] = request['query_string']
        if 'HTTP_CONTENT_LENGTH' in self.headers:
            environ['CONTENT_LENGTH'] = self.headers['HTTP_CONTENT_LENGTH']
        if 'HTTP_CONTENT_TYPE' in self.headers:
            environ['CONTENT_TYPE'] = self.headers['HTTP_CONTENT_TYPE']

        # Save the request method for later
        self.request_method = environ['REQUEST_METHOD'].upper()

        # Add Dynamic WSGI Variables
        if conn.ssl:
            environ['wsgi.url_scheme'] = 'https'
            environ['HTTPS'] = 'on'
        else:
            environ['wsgi.url_scheme'] = 'http'
        if self.headers.get('HTTP_TRANSFER_ENCODING', '').lower() == 'chunked':
            environ['wsgi.input'] = ChunkedReader(sock_file)
        else:
            environ['wsgi.input'] = sock_file

        # Add HTTP Headers
        environ.update(self.headers)

        return environ

    def send_headers(self, data, sections):
        h_set = self.header_set
        # Does the app want us to send output chunked?
        self.chunked = h_set.get('transfer-encoding', '').lower() == 'chunked'

        # Add a Date header if it's not there already
        if not 'date' in h_set:
            h_set['Date'] = formatdate(usegmt=True)

        # Add a Server header if it's not there already
        if not 'server' in h_set:
            h_set['Server'] = HTTP_SERVER_SOFTWARE

        if 'content-length' in h_set:
            self.size = int(h_set['content-length'])
        else:
            s = int(self.status.split(' ')[0])
            if s < 200 or s not in (204, 205, 304):
                if not self.chunked:
                    if sections == 1:
                        # Add a Content-Length header if it's not there already
                        h_set['Content-Length'] = str(len(data))
                        self.size = len(data)
                    else:
                        # If they sent us more than one section, we blow chunks
                        h_set['Transfer-Encoding'] = 'Chunked'
                        self.chunked = True
                        self.err_log.debug('Adding header...Transfer-Encoding: '
                                           'Chunked')

        if 'connection' not in h_set:
            # If the application did not provide a connection header, fill it in
            client_conn = self.headers.get('HTTP_CONNECTION', '').lower()
            if self.environ['SERVER_PROTOCOL'] == 'HTTP/1.1':
                # HTTP = 1.1 defaults to keep-alive connections
                if client_conn:
                    h_set['Connection'] = client_conn
                else:
                    h_set['Connection'] = 'keep-alive'
            else:
                # HTTP < 1.1 supports keep-alive but it's quirky so we don't support it
                h_set['Connection'] = 'close'

        # Close our connection if we need to.
        self.closeConnection = h_set.get('connection', '').lower() == 'close'

        # Build our output headers
        header_data = HEADER_RESPONSE % (self.status, str(h_set))

        # Send the headers
        self.err_log.debug('Sending Headers: %s' % repr(header_data))
        self.conn.sendall(b(header_data))
        self.headers_sent = True

    def write_warning(self, data, sections=None):
        self.err_log.warning('WSGI app called write method directly.  This is '
                             'deprecated behavior.  Please update your app.')
        return self.write(data, sections)

    def write(self, data, sections=None):
        """ Write the data to the output socket. """

        if self.error[0]:
            self.status = self.error[0]
            data = b(self.error[1])

        if not self.headers_sent:
            self.send_headers(data, sections)

        if self.request_method != 'HEAD':
            try:
                if self.chunked:
                    self.conn.sendall(b('%x\r\n' % len(data)))
                # Send another NEWLINE for good measure
                self.conn.sendall(data)
                if self.chunked:
                    self.conn.sendall(b('\r\n'))
            except socket.error:
                # But some clients will close the connection before that
                # resulting in a socket error.
                self.closeConnection = True

    def start_response(self, status, response_headers, exc_info=None):
        """ Store the HTTP status and headers to be sent when self.write is
        called. """
        if exc_info:
            try:
                if self.headers_sent:
                    # Re-raise original exception if headers sent
                    # because this violates WSGI specification.
                    raise
            finally:
                exc_info = None
        elif self.header_set:
            raise AssertionError("Headers already set!")

        if PY3K and not isinstance(status, str):
            self.status = str(status, 'ISO-8859-1')
        else:
            self.status = status
        # Make sure headers are bytes objects
        try:
            self.header_set = Headers(response_headers)
        except UnicodeDecodeError:
            self.error = ('500 Internal Server Error',
                          'HTTP Headers should be bytes')
            self.err_log.error('Received HTTP Headers from client that contain'
                               ' invalid characters for Latin-1 encoding.')

        return self.write_warning

    def run_app(self, conn):
        self.size = 0
        self.header_set = Headers([])
        self.headers_sent = False
        self.error = (None, None)
        self.chunked = False
        sections = None
        output = None

        self.err_log.debug('Getting sock_file')
        # Build our file-like object
        sock_file = conn.makefile('rb',BUF_SIZE)

        try:
            # Read the headers and build our WSGI environment
            self.environ = environ = self.build_environ(sock_file, conn)

            # Handle 100 Continue
            if environ.get('HTTP_EXPECT', '').lower() == '100-continue':
                res = environ['SERVER_PROTOCOL'] + ' 100 Continue\r\n\r\n'
                conn.sendall(b(res))

            # Send it to our WSGI application
            output = self.app(environ, self.start_response)
            if not hasattr(output, '__len__') and not hasattr(output, '__iter__'):
                self.error = ('500 Internal Server Error',
                              'WSGI applications must return a list or '
                              'generator type.')

            if hasattr(output, '__len__'):
                sections = len(output)

            for data in output:
                # Don't send headers until body appears
                if data:
                    self.write(data, sections)

            if self.chunked:
                # If chunked, send our final chunk length
                self.conn.sendall(b('0\r\n\r\n'))
            elif not self.headers_sent:
                # Send headers if the body was empty
                self.send_headers('', sections)

        # Don't capture exceptions here.  The Worker class handles
        # them appropriately.
        finally:
            self.err_log.debug('Finally closing output and sock_file')
            if hasattr(output,'close'):
                output.close()

            sock_file.close()

# Monolithic build...end of module: rocket\methods\wsgi.py
