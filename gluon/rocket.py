# -*- coding: utf-8 -*-

# This file is part of the Rocket Web Server
# Copyright (c) 2010 Timothy Farrell

# Import System Modules
import sys
import errno
import socket
import platform

# Define Constants
VERSION = '0.2.1'
SERVER_NAME = socket.gethostname()
SERVER_SOFTWARE = 'Rocket %s' % VERSION
HTTP_SERVER_SOFTWARE = '%s Python/%s' % (SERVER_SOFTWARE, sys.version.split(' ')[0])
BUF_SIZE = 16384
IS_JYTHON = platform.system() == 'Java' # Handle special cases for Jython
IGNORE_ERRORS_ON_CLOSE = set([errno.ECONNABORTED, errno.ECONNRESET])
DEFAULT_LISTEN_QUEUE_SIZE = 5
DEFAULT_MIN_THREADS = 10
DEFAULT_MAX_THREADS = 128
DEFAULTS = dict(LISTEN_QUEUE_SIZE = DEFAULT_LISTEN_QUEUE_SIZE,
                MIN_THREADS = DEFAULT_MIN_THREADS,
                MAX_THREADS = DEFAULT_MAX_THREADS)

PY3K = sys.version_info[0] > 2

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
           'Rocket', 'CherryPyWSGIServer', 'SERVER_NAME']
# Monolithic build...end of module: rocket\__init__.py# Monolithic build...start of module: rocket\connection.py
# Import System Modules
import time
import socket
try:
    import ssl
except ImportError:
    ssl = None
# Import Package Modules
# package imports removed in monolithic build

class Connection:
    def __init__(self, sock_tuple, port):
        self.client_addr, self.client_port = sock_tuple[1]
        self.server_port = port
        self.socket = sock_tuple[0]
        self.start_time = time.time()
        self.ssl = ssl and isinstance(self.socket, ssl.SSLSocket)

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
# Monolithic build...end of module: rocket\connection.py# Monolithic build...start of module: rocket\main.py
# Import System Modules
import os
import sys
import time
import signal
import socket
import logging
import traceback
from select import select
try:
    import ssl
except ImportError:
    ssl = None
# Import Package Modules
# package imports removed in monolithic build



# Setup Logging
log = logging.getLogger('Rocket')
try:
    log.addHandler(logging.NullHandler())
except:
    pass

class Rocket:
    """The Rocket class is responsible for handling threads and accepting and
    dispatching connections."""

    def __init__(self,
                 interfaces = ('127.0.0.1', 8000),
                 method='test',
                 app_info = None,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 queue_size = None,
                 timeout = 600):

        if not isinstance(interfaces, list):
            self.interfaces = [interfaces]
        else:
            self.interfaces = interfaces

        if queue_size:
            self.queue_size = queue_size
        else:
            if hasattr(socket, 'SOMAXCONN'):
                self.queue_size = socket.SOMAXCONN
            else:
                self.queue_size = DEFAULTS['LISTEN_QUEUE_SIZE']

        if max_threads and self.queue_size > max_threads:
            self.queue_size = max_threads

        self._monitor = Monitor()
        self._threadpool = T = ThreadPool(method,
                                          app_info = app_info,
                                          min_threads=min_threads,
                                          max_threads=max_threads,
                                          server_software=SERVER_SOFTWARE,
                                          timeout_queue = self._monitor.queue)

        self._monitor.out_queue = T.queue
        self._monitor.timeout = timeout

    def start(self):
        log.info('Starting %s' % SERVER_SOFTWARE)

        # Set up our shutdown signals
        try:
            signal.signal(signal.SIGTERM, self._sigterm)
            signal.signal(signal.SIGUSR1, self._sighup)
        except:
            log.info('This platform does not support signals.')

        # Start our worker threads
        self._threadpool.start()

        # Start our monitor thread
        self._monitor.daemon = True
        self._monitor.start()

        # Build our listening sockets (with appropriate options)
        self.listeners = list()
        self.listener_dict = dict()
        for i in self.interfaces:
            addr = i[0]
            port = i[1]
            secure = len(i) > 3 and i[2] and i[3]

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if secure:
                if not ssl:
                    log.error("ssl module required to serve HTTPS.")
                    del listener
                    continue
                elif not os.path.exists(i[2]):
                    data = (i[2], i[0], i[1])
                    log.error("Cannot find key file "
                              "'%s'.  Cannot bind to %s:%s" % data)
                elif not os.path.exists(i[3]):
                    data = (i[3], i[0], i[1])
                    log.error("Cannot find certificate file "
                              "'%s'.  Cannot bind to %s:%s" % data)
                else:
                    listener = ssl.wrap_socket(listener,
                                               keyfile=i[2],
                                               certfile=i[3],
                                               server_side=True,
                                               ssl_version=ssl.PROTOCOL_SSLv23
                                               )

            if not listener:
                log.error("Failed to get socket.")
                raise socket.error

            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except:
                msg = "Cannot share socket.  Using %s:%i exclusively."
                log.warning(msg % (addr, port))
            try:
                if not IS_JYTHON:
                    listener.setsockopt(socket.IPPROTO_TCP,
                                        socket.TCP_NODELAY,
                                        1)
            except:
                msg = "Cannot set TCP_NODELAY, things might run a little slower"
                log.warning(msg)
            try:
                listener.bind((addr, port))
            except:
                msg = "Socket %s:%i in use by other process and it won't share."
                log.error(msg % (addr, port))
                continue

            if IS_JYTHON:
                # Jython requires a socket to be in Non-blocking mode in order
                # to select on it.
                listener.setblocking(False)

            # Listen for new connections allowing self.queue_size number of
            # connections to wait before rejecting a connection.
            listener.listen(self.queue_size)

            self.listeners.append(listener)
            self.listener_dict.update({listener: i})

        if not self.listeners:
            log.critical("No interfaces to listen on...closing.")
            sys.exit(1)

        msg = 'Listening on sockets: '
        msg += ', '.join(['%s:%i%s' % (l[0], l[1], '*' if len(l) > 2 else '') for l in self.listener_dict.values()])
        log.info(msg)

        while not self._threadpool.stop_server:
            try:
                for l in select(self.listeners, [], [], 1.0)[0]:
                    self._threadpool.queue.put((l.accept(),
                                                self.listener_dict[l][1]))
            except KeyboardInterrupt:
                # Capture a keyboard interrupt when running from a console
                return self.stop()
            except:
                if not self._threadpool.stop_server:
                    log.error(str(traceback.format_exc()))
                    continue

        if not self._threadpool.stop_server:
            self.stop()

    def _sigterm(self, signum, frame):
        log.info('Received SIGTERM')
        self.stop()

    def _sighup(self, signum, frame):
        log.info('Received SIGHUP')
        self.restart()

    def stop(self, stoplogging = True):
        log.info("Stopping Server")

        self._monitor.queue.put(None)
        self._threadpool.stop()

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
# Monolithic build...end of module: rocket\main.py# Monolithic build...start of module: rocket\monitor.py
# Import System Modules
import time
import logging
from select import select
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from threading import Thread
# Import Package Modules
# package imports removed in monolithic build

class Monitor(Thread):
    # Monitor worker base class.
    queue = Queue() # Holds connections to be monitored
    connections = set()
    timeout = 0

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.Monitor')
        try:
            self.log.addHandler(logging.NullHandler())
        except:
            pass

        self.log.debug('Entering monitor loop.')

        # Enter thread main loop
        while True:
            # Move the queued connections to the selection pool
            while not self.queue.empty() or not len(self.connections):
                self.log.debug('In "receive timed-out connections" loop.')
                c = self.queue.get()

                if not c:
                    # A non-client is a signal to die
                    self.log.debug('Received a death threat.')
                    self.stop()
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
            readable = select(list(self.connections), [], [], 1.0)[0]

            # If we have any readable connections, put them back
            for r in readable:
                self.log.debug('Restoring readable connection')

                if IS_JYTHON:
                    # Jython requires a socket to be in Non-blocking mode in
                    # order to select on it, but the rest of the code requires
                    # that it be in blocking mode.
                    r.setblocking(True)

                r.start_time = time.time()
                self.out_queue.put(r)
                self.connections.remove(r)

            # If we have any stale connections, kill them off.
            if self.timeout:
                now = time.time()
                stale = set()
                for c in self.connections:
                    if now - c.start_time >= self.timeout:
                        stale.add(c)

                for c in stale:
                    data = (c.client_addr, c.server_port, '*' if c.ssl else '')
                    self.log.debug('Flushing stale connection: %s:%i%s' % data)
                    self.connections.remove(c)
                    try:
                        c.close()
                    finally:
                        del c

    def stop(self):
        self.log.debug('Flushing waiting connections')
        for c in self.connections:
            try:
                c.close()
            finally:
                del c

        self.log.debug('Flushing queued connections')
        while not self.queue.empty():
            c = self.queue.get()
            try:
                c.close()
            finally:
                del c
# Monolithic build...end of module: rocket\monitor.py# Monolithic build...start of module: rocket\threadpool.py
# Import System Modules
import sys
import time
import socket
import logging
import traceback
from threading import Lock
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
# Import Package Modules
# package imports removed in monolithic build


# Setup Logging
log = logging.getLogger('Rocket.ThreadPool')
try:
    log.addHandler(logging.NullHandler())
except:
    pass

class ThreadPool():
    """The ThreadPool class is a container class for all the worker threads. It
    manages the number of actively running threads."""
    # Web worker base class.
    queue = None
    threads = set()

    def __init__(self,
                 method,
                 min_threads=DEFAULTS['MIN_THREADS'],
                 max_threads=DEFAULTS['MAX_THREADS'],
                 app_info=None,
                 server_software=SERVER_SOFTWARE,
                 timeout_queue=None):

        log.debug("Initializing.")
        self.check_for_dead_threads = 0
        self.resize_lock = Lock()
        self.queue = Queue()

        self.worker_class = W = get_method(method)
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.timeout_queue = timeout_queue
        self.stop_server = False
        self.grow_threshold = int(max_threads/10) + 2

        if not isinstance(app_info, dict):
            app_info = dict()

        app_info.update(max_threads=max_threads,
                        min_threads=min_threads)

        W.app_info = app_info
        W.pool = self
        W.server_software = server_software
        W.queue = self.queue
        W.wait_queue = self.timeout_queue
        W.timeout = max_threads * 0.2 if max_threads != 0 else 2

        self.threads = set([self.worker_class() for x in range(min_threads)])

    def start(self):
        self.stop_server = False
        log.debug("Starting threads.")
        for thread in self.threads:
            thread.daemon = True
            thread._pool = self
            thread.start()

    def stop(self):
        log.debug("Stopping threads.")
        self.stop_server = True

        # Prompt the threads to die
        for t in self.threads:
            self.queue.put(None)

        # Give them the gun
        for t in self.threads:
            t.kill()

        # Wait until they pull the trigger
        for t in self.threads:
            t.join()

        # Clean up the mess
        self.resize_lock.acquire()
        self.bring_out_your_dead()
        self.resize_lock.release()

    def bring_out_your_dead(self):
        # Remove dead threads from the pool
        # Assumes resize_lock is acquired from calling thread

        dead_threads = [t for t in self.threads if not t.is_alive()]
        for t in dead_threads:
            log.debug("Removing dead thread: %s." % t.getName())
            self.threads.remove(t)
        self.check_for_dead_threads -= len(dead_threads)

    def grow(self, amount=None):
        # Assumes resize_lock is acquired from calling thread
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
        # Assumes resize_lock is acquired from calling thread
        log.debug("Shrinking by %i." % amount)

        self.check_for_dead_threads += amount

        for x in range(amount):
            self.queue.put(None)

    def dynamic_resize(self):
        locked = self.resize_lock.acquire(False)
        if locked and \
           (self.max_threads > self.min_threads or self.max_threads == 0):
            if self.check_for_dead_threads > 0:
                self.bring_out_your_dead()

            queueSize = self.queue.qsize()
            threadCount = len(self.threads)

            log.debug("Examining ThreadPool. %i threads and %i Q'd conxions"
                      % (threadCount, queueSize))

            if queueSize == 0 and threadCount > self.min_threads:
                self.shrink()

            elif queueSize > self.grow_threshold \
                 and threadCount < self.max_threads:

                self.grow(queueSize)

        if locked:
            self.resize_lock.release()
# Monolithic build...end of module: rocket\threadpool.py# Monolithic build...start of module: rocket\worker.py
# Import System Modules
import re
import sys
import time
import socket
import logging
import traceback
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
from threading import Thread
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
RESPONSE = '''\
HTTP/1.1 %s
Content-Length: %i
Content-Type: text/plain

%s
'''

class Worker(Thread):
    """The Worker class is a base class responsible for receiving connections
    and (a subclass) will run an application to process the the connection """

    # All of these class attributes should be correctly populated by the
    # parent thread or threadpool.
    queue = None
    app_info = None
    timeout = 1
    server_software = SERVER_SOFTWARE

    def _handleError(self, typ, val, tb):
        if typ == SSLError:
            if 'timed out' in val.args[0]:
                typ = SocketTimeout
        if typ == SocketTimeout:
            self.log.debug('Socket timed out')
            self.wait_queue.put(self.conn)
            return True
        if typ == SocketClosed:
            self.closeConnection = True
            self.log.debug('Client closed socket')
            return False
        if typ == socket.error:
            if val.args[0] in IGNORE_ERRORS_ON_CLOSE:
                self.closeConnection = True
                self.log.debug('Ignorable socket Error received...'
                               'closing connection.')
                return False
            else:
                self.closeConnection = True
                if not self.pool.stop_server:
                    self.log.critical(str(traceback.format_exc()))
                return False

        self.closeConnection = True
        self.log.error(str(traceback.format_exc()))
        self.send_response('500 Server Error')
        return False

    def run(self):
        self.name = self.getName()
        self.log = logging.getLogger('Rocket.%s' % self.name)
        try:
            self.log.addHandler(logging.NullHandler())
        except:
            pass
        self.log.debug('Entering main loop.')

        # Enter thread main loop
        while True:
            conn = self.queue.get()

            if isinstance(conn, tuple):
                self.pool.dynamic_resize()
                conn = Connection(*conn)

            if not conn:
                # A non-client is a signal to die
                self.log.debug('Received a death threat.')
                return

            self.conn = conn

            if IS_JYTHON:
                # In Jython we must set TCP_NODELAY here.
                # See: http://bugs.jython.org/issue1309
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            self.log.debug('Received a connection.')

            if hasattr(conn,'settimeout') and self.timeout:
                conn.settimeout(self.timeout)

            self.closeConnection = False

            # Enter connection serve loop
            while True:
                self.log.debug('Serving a request')
                try:
                    self.run_app(conn)
                except:
                    handled = self._handleError(*sys.exc_info())
                    if handled:
                        break

                if self.closeConnection:
                    conn.close()
                    break
                else:
                    conn.start_time = time.time()

    def run_app(self, conn):
        # Must be overridden with a method reads the request from the socket
        # and sends a response.
        raise NotImplementedError('Overload this method!')

    def send_response(self, status, disconnect=False):
        msg = RESPONSE % (status, len(status), status.split(' ', 1)[1])
        try:
            self.conn.sendall(b(msg))
        except socket.error:
            self.closeConnection = True
            self.log.error('Tried to send "%s" to client but received socket'
                           ' error' % status)

    def kill(self):
        if self.isAlive() and hasattr(self, 'conn'):
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except socket.error:
                info = sys.exc_info()
                if info[1].args[0] != socket.EBADF:
                    self.log.debug('Error on shutdown: '+str(info))

    def read_request_line(self, sock_file):
        try:
            # Grab the request line
            d = sock_file.readline()
            d = d.decode('ISO-8859-1') if PY3K else d

            if d == '\r\n':
                # Allow an extra NEWLINE at the beginner per HTTP 1.1 spec
                self.log.debug('Client sent newline')
                d = sock_file.readline()
                d = d.decode('ISO-8859-1') if PY3K else d
        except socket.timeout:
            raise SocketTimeout("Socket timed out before request.")

        if d.strip() == '':
            self.log.debug('Client did not send a recognizable request.')
            raise SocketClosed('Client closed socket.')

        try:
            method, uri, proto = d.strip().split(' ')
        except ValueError:
            # FIXME - Raise 400 Bad Request
            raise

        req = dict(method=method, protocol = proto)
        scheme = ''
        host = ''
        if uri == '*' or uri.startswith('/'):
            path = uri
        elif '://' in uri:
            scheme, rest = uri.split('://')
            host, path = rest.split('/', 1)
        else:
            path = ''

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
        headers = dict()
        l = sock_file.readline()

        lname = None
        lval = None
        while True:
            try:
                l = str(l, 'ISO-8859-1') if PY3K else l
            except UnicodeDecodeError:
                self.log.warning('Client sent invalid header: ' + l.__repr__())

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
                lname = 'HTTP_'+lname.upper()
                lval = l[-1].strip()
            headers.update({str(lname): str(lval)})

            l = sock_file.readline()
        return headers

class SocketTimeout(Exception):
    "Exception for when a socket times out between requests."
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

class TestWorker(Worker):
    HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s\r\n'''

    def run_app(self, conn):
        self.closeConnection = True
        sock_file = conn.makefile('rb', BUF_SIZE)
        n = sock_file.readline().strip()
        while n:
            self.log.debug(n)
            n = sock_file.readline().strip()

        response = self.HEADER_RESPONSE % ('200 OK', 'Content-type: text/html')
        response += '\r\n<h1>It Works!</h1>'

        try:
            self.log.debug(response)
            conn.sendall(b(response))
        finally:
            sock_file.close()

def get_method(method):

    methods = dict(test=TestWorker,
                   wsgi=WSGIWorker)

    return methods.get(method.lower(), TestWorker)
# Monolithic build...end of module: rocket\worker.py# Monolithic build...start of module: rocket\methods\__init__.py# Monolithic build...end of module: rocket\methods\__init__.py# Monolithic build...start of module: rocket\methods\wsgi.py
# Import System Modules
import os
import sys
import socket
from email.utils import formatdate
from wsgiref.simple_server import demo_app
from wsgiref.util import FileWrapper
# Import Package Modules
# package imports removed in monolithic build


# Define Constants
HEADER_LINE = '%s: %s\r\n'
NEWLINE = b('\r\n')
HEADER_RESPONSE = '''HTTP/1.1 %s\r\n%s\r\n'''
BASE_ENV = {'SERVER_NAME': SERVER_NAME,
            'wsgi.errors': sys.stderr,
            'wsgi.version': (1, 0),
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            'wsgi.file_wrapper': FileWrapper
            }

class WSGIWorker(Worker):
    def __init__(self):
        """Builds some instance variables that will last the life of the
        thread."""
        if isinstance(self.app_info, dict):
            multithreaded = self.app_info.get('max_threads') != 1
        else:
            multithreaded = False
        self.base_environ = dict({'SERVER_SOFTWARE': self.server_software,
                                  'wsgi.multithread': multithreaded,
                                  })
        self.base_environ.update(BASE_ENV)
        # Grab our application
        if isinstance(self.app_info, dict):
            self.app = self.app_info.get('wsgi_app', demo_app)
        else:
            self.app = demo_app

        Worker.__init__(self)

    def build_environ(self, sock_file, conn):
        """ Build the execution environment. """
        # Grab the request line
        request = self.read_request_line(sock_file)

        # Grab the headers
        self.headers = self.read_headers(sock_file)

        # Copy the Base Environment
        environ = dict(self.base_environ)

        # Add CGI Variables
        environ['REQUEST_METHOD'] = request['method']
        # I haven't decided if we really need to be like Apache.
        #environ['REQUEST_URI'] = '?'.join((request['path'], request['query_string']))
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
        # Before the first output, send the stored headers
        header_dict = dict([(x.lower(), y) for (x,y) in self.header_set])

        # Does the app want us to send output chunked?
        self.chunked = header_dict.get('transfer-encoding', '').lower() == 'chunked'

        # Add a Date header if it's not there already
        if not 'date' in header_dict:
            self.header_set.append(('Date', formatdate(usegmt=True)))

        # Add a Server header if it's not there already
        if not 'server' in header_dict:
            self.header_set.append(('Server', HTTP_SERVER_SOFTWARE))

        if 'content-length' not in header_dict:
            s = int(self.status.split(' ')[0])
            if s < 200 or s not in (204, 205, 304):
                if not self.chunked:
                    if sections == 1:
                        # Add a Content-Length header if it's not there already
                        self.header_set.append(('Content-Length', len(data)))
                    else:
                        # If they sent us more than one section, we blow chunks
                        self.header_set.append(('Transfer-Encoding', 'Chunked'))
                        self.chunked = True
                        self.log.debug('Adding header...Transfer-Encoding: '
                                       'Chunked')

        # If the client or application asks to keep the connection alive, do so.
        conn = header_dict.get('connection', '').lower()
        client_conn = self.headers.get('HTTP_CONNECTION', '').lower()
        if conn != 'close' and client_conn == 'keep-alive':
            self.header_set.append(('Connection', 'keep-alive'))
            self.closeConnection = False
        else:
            self.header_set.append(('Connection', 'close'))
            self.closeConnection = True

        # Build our output headers
        serialized_headers = ''.join([HEADER_LINE % (k,v)
                                      for (k,v) in self.header_set])
        header_data = HEADER_RESPONSE % (self.status, serialized_headers)

        # Send the headers
        self.log.debug('Sending Headers: %s' % header_data.__repr__())
        self.conn.sendall(b(header_data))
        self.headers_sent = True

    def write_warning(self, data, sections=None):
        self.log.warning('WSGI app called write method directly.  This is '
                         'obsolete behavior.  Please update your app.')
        return self.write(data, sections)

    def write(self, data, sections=None):
        """ Write the data to the output socket. """

        if self.error[0]:
            self.status = self.error[0]
            data = b(self.error[1])

        if not self.headers_sent:
            self.send_headers(data, sections)

        if self.request_method != 'HEAD':
            if self.chunked:
                self.conn.sendall(b('%x\r\n' % len(data)))

            try:
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
            self.header_set = [(h[0].strip(),
                                h[1].strip()) for h in response_headers]
        except UnicodeDecodeError:
            self.error = ('500 Internal Server Error',
                          'HTTP Headers should be bytes')
            self.log.error('Received HTTP Headers from client that contain'
                           ' invalid characters for Latin-1 encoding.')

        return self.write_warning

    def run_app(self, conn):
        self.header_set = []
        self.headers_sent = False
        self.error = (None, None)
        sections = None
        output = None

        self.log.debug('Getting sock_file')
        # Build our file-like object
        sock_file = conn.makefile('rb',BUF_SIZE)

        try:
            # Read the headers and build our WSGI environment
            environ = self.build_environ(sock_file, conn)

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

            # Send headers if the body was empty
            if not self.headers_sent:
                self.write(b(''))

            # If chunked, send our final chunk length
            if self.chunked:
                self.conn.sendall(b('0\r\n\r\n'))

        finally:
            self.log.debug('Finally closing output and sock_file')
            if hasattr(output,'close'):
                output.close()

            sock_file.close()
# Monolithic build...end of module: rocket\methods\wsgi.py
