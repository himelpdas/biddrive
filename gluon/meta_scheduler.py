import os
import time
import multiprocessing
import sys
import cStringIO
import threading
import traceback
import signal

class Task(object):
    def __init__(self,function,timeout,args=None,vars=None,row=None):
        print 'new task'
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
    output, sys.stdout = sys.stdout, cStringIO.StringIO()
    try:
        result = eval(task.function)(*task.args,**task.vars)
        queue.put(TaskReport('success',result,sys.stdout.getvalue()))
    except BaseException,e:
        queue.put(TaskReport('failed',tb=traceback.format_exc()))

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
            function = 'f',
            timeout = 7,
            args = [5],
            vars = {},
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
