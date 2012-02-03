import os
import sys
import cStringIO
import gluon.contrib.shell
import gluon.dal
import gluon.html
import gluon.validators
import code, thread
from gluon.debug import communicate, web_debugger
import pydoc


if DEMO_MODE or MULTI_USER_MODE:
    session.flash = T('disabled in demo mode')
    redirect(URL('default','site'))

FE=10**9

def index():
    app = request.args(0) or 'admin'
    reset()
    # read buffer
    data = communicate()
    return dict(app=app,data=data)

def callback():
    app = request.args[0]
    command = request.vars.statement
    session['debug_commands:'+app].append(command)
    output = communicate(command)
    k = len(session['debug_commands:'+app]) - 1
    return '[%i] %s%s\n' % (k + 1, command, output)

def reset():
    app = request.args(0) or 'admin'
    session['debug_commands:'+app] = []
    return 'done'


# new implementation using qdb

def interact():
    app = request.args(0) or 'admin'
    reset()

    # process all pending messages in the frontend
    web_debugger.run()

    # if debugging, filename and lineno should have valid values
    filename = web_debugger.filename
    lineno = web_debugger.lineno
    if filename:
        lines = dict([(i+1, l) for (i, l) in enumerate(
                            [l.strip("\n").strip("\r") for l 
                                in open(filename).readlines()])])
        filename = os.path.basename(filename)
    else:
        lines = {}

    if filename:
        env = web_debugger.do_environment()
        f_locals = env['locals']
        f_globals = {}
        for name, value in env['globals'].items():
            if name not in gluon.html.__all__ and \
               name not in gluon.validators.__all__ and \
               name not in gluon.dal.__all__:
                f_globals[name] = pydoc.text.repr(value)
    else:
        f_locals = {}
        f_globals = {}

    return dict(app=app, data="", 
                filename=filename, lines=lines, lineno=lineno, 
                f_globals=f_globals, f_locals=f_locals)

def step():
    web_debugger.do_step()
    redirect(URL("interact"))

def next():
    web_debugger.do_next()
    redirect(URL("interact"))

def cont():
    web_debugger.do_continue()
    redirect(URL("interact"))

def ret():
    web_debugger.do_return()
    redirect(URL("interact"))

def stop():
    web_debugger.do_quit()
    redirect(URL("interact"))

def execute():
    app = request.args[0]
    command = request.vars.statement
    session['debug_commands:'+app].append(command)
    try:
        output = web_debugger.do_exec(command)
        if output is None:
            output = ""
    except Exception, e:
        output =  T("Exception %s") % str(e)
    k = len(session['debug_commands:'+app]) - 1
    return '[%i] %s%s\n' % (k + 1, command, output)

