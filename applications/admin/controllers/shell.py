import sys
import cStringIO
import gluon.contrib.shell
import code, thread
from gluon.shell import env

if DEMO_MODE:
    session.flash = T('disabled in demo mode')
    redirect(URL('default','site'))

FE=10**9

def index():
    app = request.args(0) or 'admin'
    reset()
    return dict(app=app)

def callback():    
    app = request.args[0]
    command = request.vars.statement
    escape = command[:1]!='!'
    session['history:'+app] = session.get('history:'+app,gluon.contrib.shell.History())
    if not escape:
        command = command[1:]
    if command == '%reset':
        reset()
        return '*** reset ***'
    elif command[0] == '%':
        try:
            command=session['commands:'+app][int(command[1:])]
        except ValueError:
            return ''
    session['commands:'+app].append(command)
    output = gluon.contrib.shell.run(session.history,command,env(app,True))
    k = len(session['commands:'+app]) - 1
    output = PRE(output)
    return TABLE(TR('In[%i]:'%k,PRE(command)),TR('Out[%i]:'%k,output))

def reset():
    app = request.args(0) or 'admin'
    session['commands:'+app] = []
    session['history:'+app] = gluon.contrib.shell.History()
    return 'done'
