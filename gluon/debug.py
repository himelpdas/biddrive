#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>,
limodou <limodou@gmail.com> and srackham <srackham@gmail.com>.
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

"""

import logging
import pdb
import Queue
import sys

logger = logging.getLogger("web2py")

class Pipe(Queue.Queue):
    def __init__(self, name, mode='r', *args, **kwargs):
        self.__name = name
        Queue.Queue.__init__(self, *args, **kwargs)

    def write(self, data):
        logger.debug("debug %s writting %s" % (self.__name, data))
        self.put(data)

    def flush(self):
        # mark checkpoint (complete message)
        logger.debug("debug %s flushing..." % self.__name)
        self.put(None)
        # wait until it is processed
        self.join()
        logger.debug("debug %s flush done" % self.__name)

    def read(self, count=None, timeout=None):
        logger.debug("debug %s reading..." % (self.__name, ))
        data = self.get(block=True, timeout=timeout)
        # signal that we are ready
        self.task_done()
        logger.debug("debug %s read %s" % (self.__name, data))
        return data

    def readline(self):
        logger.debug("debug %s readline..." % (self.__name, ))
        return self.read()


pipe_in = Pipe('in')
pipe_out = Pipe('out')

debugger = pdb.Pdb(completekey=None, stdin=pipe_in, stdout=pipe_out,)

def set_trace():
    "breakpoint shortcut (like pdb)"
    logger.info("DEBUG: set_trace!")
    debugger.set_trace(sys._getframe().f_back)


def stop_trace():
    "stop waiting for the debugger (called atexit)"
    # this should prevent communicate is wait forever a command result
    # and the main thread has finished
    logger.info("DEBUG: stop_trace!")
    pipe_out.write("debug finished!")
    pipe_out.write(None)
    #pipe_out.flush()

def communicate(command=None):
    "send command to debbuger, wait result"
    if command is not None:
        logger.info("DEBUG: sending command %s" % command)
        pipe_in.write(command)
        #pipe_in.flush()
    result = []
    while True:
        data = pipe_out.read()
        if data is None:
            break
        result.append(data)
    logger.info("DEBUG: result %s" % repr(result))
    return ''.join(result)


# New debugger implementation using qdb and a web UI

import gluon.contrib.qdb as qdb


def check_interaction(fn):
    "Decorator to clean and prevent interaction when not available"
    def check_fn(self, *args, **kwargs):
        if self.filename:
            self.clear_interaction()
            fn(self, *args, **kwargs)
    return check_fn

      
class WebDebugger(qdb.Frontend):
    "Qdb web2py interface"
    
    def __init__(self, pipe, completekey='tab', stdin=None, stdout=None, skip=None):
        qdb.Frontend.__init__(self, pipe)
        self.clear_interaction()

    def clear_interaction(self):
        self.filename = None
        self.lineno = None
        self.exception_info = None

    # redefine Frontend methods:
    
    def run(self):
        while self.pipe.poll():
            qdb.Frontend.run(self)

    def interaction(self, filename, lineno, line):
        # store current status
        self.filename = filename
        self.lineno = lineno

    def exception(self, title, extype, exvalue, trace, request):
        self.exception_info = {'title': title, 
                               'extype': extype, 'exvalue': exvalue,
                               'trace': trace, 'request': request}

    @check_interaction
    def do_continue(self):
        qdb.Frontend.do_continue(self)

    @check_interaction
    def do_step(self):
        qdb.Frontend.do_step(self)

    def do_return(self):
        qdb.Frontend.do_return(self)

    @check_interaction
    def do_next(self):
        qdb.Frontend.do_next(self)

    @check_interaction
    def do_quit(self):
        qdb.Frontend.do_quit(self)



# create the connection between threads:

parent_queue, child_queue = Queue.Queue(), Queue.Queue()
front_conn = qdb.QueuePipe("parent", parent_queue, child_queue)
child_conn = qdb.QueuePipe("child", child_queue, parent_queue)

web_debugger = WebDebugger(front_conn)                          # frontend
qdb_debugger = qdb.Qdb(pipe=child_conn, redirect_stdio=False)   # backend
dbg = qdb_debugger

