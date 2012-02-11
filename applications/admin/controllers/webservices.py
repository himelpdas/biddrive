from gluon.admin import *
from gluon.fileutils import abspath, read_file, write_file
from gluon.tools import Service
from glob import glob
import shutil
import platform
import time
import base64
import os


service = Service(globals())


@service.jsonrpc
def login():
    "dummy function to test credentials"
    return True


@service.jsonrpc
def list_apps():
    "list installed applications"
    regex = re.compile('^\w+$')
    apps = [f for f in os.listdir(apath(r=request)) if regex.match(f)]
    return apps


@service.jsonrpc
def list_files(app, pattern='.*\.py$'):
    files = listdir(apath('%s/' % app, r=request), pattern)
    return [x.replace('\\','/') for x in files]


@service.jsonrpc
def read_file(filename, binary=False):
    """ Visualize object code """
    f = open(apath(filename, r=request), "rb")
    try:
        data = f.read()
        if not binary:
            data = data.replace('\r','')
    finally:
        f.close()
    return data


@service.jsonrpc
def write_file(filename, data, binary=False):
    f = open(apath(filename, r=request), "wb")
    try:
        if not binary:
            data = data.replace('\r\n', '\n').strip() + '\n'
        f.write(data)
    finally:
        f.close()



@service.jsonrpc
def attach_debugger(host='localhost', port=6000, authkey='secret password'):
    import gluon.contrib.qdb as qdb
    import gluon.debug
    from multiprocessing.connection import Listener

    if isinstance(authkey, unicode):
        authkey = authkey.encode('utf8')

    # TODO: proper locking and cleanup
    
    if gluon.debug.web_debugger:
        # remove the web debugger
        gluon.debug.web_debugger = None

    elif hasattr(gluon.debug, 'qdb_listener'):
        # stop current debugger
        gluon.debug.qdb_listener.close()
        gluon.debug.qdb_listener = None
        gluon.debug.qdb_debugger = None
        
    # create a remote debugger server and wait for connection
    address = (host, port)     # family is deduced to be 'AF_INET'
    gluon.debug.qdb_listener = Listener(address, authkey=authkey)
    conn = gluon.debug.qdb_listener.accept()

    # create the backend
    gluon.debug.qdb_debugger = qdb.Qdb(conn)
    gluon.debug.dbg = gluon.debug.qdb_debugger
    
    return True     # connection successful!
            

def call():
    "Entry point. Prevents access to action if not admin password is present"

    basic = request.env.http_authorization
    if not basic or not basic[:6].lower() == 'basic ':
        raise HTTP(401,"Wrong credentials")
    (username, password) = base64.b64decode(basic[6:]).split(':')
    if not verify_password(password) or not is_manager():
        time.sleep(10)
        raise HTTP(403,"Not authorized")

    session.forget()
    return service()

