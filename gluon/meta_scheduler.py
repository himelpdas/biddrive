import os
import time
import multiprocessing
import sys
import cStringIO
import threading
import traceback
import signal
try:
    from gluon.contrib.simplejson import loads, dumps
except:
    from simplejson import loads, dumps

if 'WEB2PY_PATH' in os.environ:
    sys.path.append(os.environ['WEB2PY_PATH'])

class Task(object):
    def __init__(self,app,function,timeout,args=None,vars=None,row=None):
        print 'new task'
        self.app = app
        self.function = function
        self.timeout = timeout
        self.args = args or []
        self.vars = vars or {}
        self.row = row
    def __str__(self):
        return '<Task: %s>' % self.function

class TaskReport(object):
    def __init__(self,status,result=None,output=None,tb=None):
        print 'new task report'
        if tb:
            print tb
        else:
            print '    output =',output
            print '    result =',result
        self.status = status
        self.result = result
        self.output = output
        self.tb = tb
    def __str__(self):
        return '<TaskReport: %s>' % self.status

def f(*argv,**kwargs):
    """ test function """
    for i in range(argv[0]):
        print 'click',i
        time.sleep(1)    
    return 'done'

def executor(queue,task):
    """ the background process """
    print 'task started'
    stdout, sys.stdout = sys.stdout, cStringIO.StringIO()
    try:
        if task.app:
            os.chdir(os.environ['WEB2PY_PATH'])
            from gluon.shell import env
            from gluon.dal import BaseAdapter
            _env = env(task.app,import_models=True)
            scheduler_tasks = _env.get('scheduler_tasks',{})
            function = scheduler_tasks[task.function]
            result = dumps(function(*loads(task.args),**loads(task.vars)))
        else:
            ### for testing purpose only
            result = eval(task.function)(*loads(task.args),**loads(task.vars))
        stdout, sys.stdout = sys.stdout, stdout
        queue.put(TaskReport('success', result,stdout.getvalue()))
    except BaseException,e:
        sys.stdout = stdout
        tb = traceback.format_exc()
        queue.put(TaskReport('failed',tb=tb))

class MetaScheduler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.process = None     # the backround process
        self.heartbeat = True   # set to False to kill
    def async(self,task):
        """
        starts the background process and returns:
        ('ok',result,output)
        ('error',exception,None)
        ('timeout',None,None)
        ('terminated',None,None)
        """
        queue = multiprocessing.Queue(maxsize=1)
        p = multiprocessing.Process(target=executor,args=(queue,task))
        self.process = p
        print 'starting task'
        p.start()
        try:
            p.join(task.timeout)
        except:
            p.terminate()
            p.join()
            self.heartbeat = False
            return TaskReport('terminated')
        if p.is_alive():
            p.terminate()
            p.join()            
            return TaskReport('timeout')
        elif queue.empty():
            self.heartbeat = False
            return TaskReport('terminated')
        else:
            return queue.get()

    def die(self):
        print 'die now'
        self.heartbeat = False
        self.terminate_process()
        
    def terminate_process(self):
        try:
            self.process.terminate()
        except:
            pass # no process to terminate

    def run(self):
        """ the thread that sends heartbeat """
        while self.heartbeat:
            self.fixup_tasks()
            self.send_heartbeat()

    def start_heartbeats(self):
        self.start()
        
    def send_heartbeat(self):
        print 'thum'
        time.sleep(1)
            
    def pop_task(self):
        return Task(
            app = 'scheduler',
            function = 'demo1',
            timeout = 7,
            args = '[2]',
            vars = '{}',
            row = None)

    def report_task(self,task,task_report):
        print 'reporting task'
        pass
    
    def fixup_tasks(self):
        pass
    
    def sleep(self):
        pass

    def loop(self):
        try:
            self.start_heartbeats()
            while True and self.heartbeat:
                task = self.pop_task()
                if task:
                    self.report_task(task,self.async(task))
                else:
                    self.sleep()
        except KeyboardInterrupt:
            self.die()

if __name__=='__main__':
    MetaScheduler().loop()
