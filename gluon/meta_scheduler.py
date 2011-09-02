#### WORK IN PROGRESS... NOT SUPPOSED TO WORK YET

import os
import time
import multiprocessing
import sys
import cStringIO
import threading
import traceback
import signal
import socket
import datetime

try:
    from gluon.contrib.simplejson import loads, dumps
except:
    from simplejson import loads, dumps

if 'WEB2PY_PATH' in os.environ:
    sys.path.append(os.environ['WEB2PY_PATH'])

QUEUED = 'QUEUED'
RUNNING = 'RUNNING'
COMPLETED = 'COMPLETED'
FAILED = 'FAILED'
TIMEOUT = 'TIMEOUT'
STOPPED = 'STOPPED'
ACTIVE = 'ACTIVE'
INACTIVE = 'INACTIVE'
DISABLED = 'DISABLED'
SECONDS = 1
HEARTBEAT = 20*SECONDS

class Task(object):
    def __init__(self,app,function,timeout,args='[]',vars='{}',**kwargs)
        print 'new task'
        self.app = app
        self.function = function
        self.timeout = timeout
        self.args = args # json
        self.vars = vars # json
        self.__dict__.update(kwargs)
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

def demo_function(*argv,**kwargs):
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
            from gluon import current
            _env = env(task.app,import_models=True)
            scheduler = current._scheduler
            scheduler_tasks = current._scheduler.tasks            
            _function = scheduler_tasks[task.function]
            globals().update(_env)            
            result = dumps(_function(*loads(task.args),**loads(task.vars)))
        else:
            ### for testing purpose only
            result = eval(task.function)(*loads(task.args),**loads(task.vars))
        stdout, sys.stdout = sys.stdout, stdout
        queue.put(TaskReport(COMPLETED, result,stdout.getvalue()))
    except BaseException,e:
        sys.stdout = stdout
        tb = traceback.format_exc()
        queue.put(TaskReport(FAILED,tb=tb))

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
            return TaskReport(STOPPED)
        if p.is_alive():
            p.terminate()
            p.join()            
            return TaskReport(TIMEOUT)
        elif queue.empty():
            self.heartbeat = False
            return TaskReport(STOPPED)
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
            app = None,
            function = 'demo_function',
            timeout = 7,
            args = '[2]',
            vars = '{}')

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


TASK_STATUS = (QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT, STOPPED)
RUN_STATUS = (RUNNING, COMPLETED, FAILED, TIMEOUT, STOPPED)
WORKER_STATUS = (ACTIVE,INACTIVE,DISABLED)

class Scheduler(MetaScheduler):
    def __init__(self,db,tasks={}):
        MetaScheduler.__init__(self)
        self.db = db
        self.tasks = tasks
        now = datetime.now()

        db.define_table(
            'scheduler_task',
            Field('application_name',requires=IS_NOT_EMPTY()),
            Field('task_name',requires=IS_NOT_EMPTY()),
            Field('group_name',default='main',writable=False),
            Field('status',requires=IS_IN_SET(TASK_STATUS),
                  default=QUEUED,writable=False),
            Field('function_name',
                  requires=IS_IN_SET(sorted(self.tasks.keys()))),
            Field('args','text',default='[]',requires=TYPE(list)),
            Field('vars','text',default='{}',requires=TYPE(dict)),
            Field('enabled','boolean',default=True),
            Field('start_time','datetime',default=now),
            Field('next_run_time','datetime',default=now),
            Field('stop_time','datetime',default=now+timedelta(days=1)),
            Field('repeats','integer',default=1,comment="0=unlimted"),
            Field('period','integer',default=60,comment='seconds'),
            Field('timeout','integer',default=60,comment='seconds'),
            Field('times_run','integer',default=0,writable=False),
            Field('last_run_time','datetime',writable=False,readable=False),
            Field('assigned_worker_name',default=None,writable=False),
            migrate=migrate,format='%(name)s')

        db.define_table(
            'shceduler_run',
            Field('scheduler_task','reference scheduler_task'),
            Field('status',requires=IS_IN_SET(RUN_STATUS)),
            Field('start_time','datetime'),
            Field('stop_time','datetime'),
            Field('output','text'),
            Field('result','text'),
            Field('traceback','text'),
            Field('worker_name',default=worker_name),
            migrate=migrate)

        db.define_table(
            'scheduler_worker',
            Field('worker_name'),
            Field('first_heartbeat','datetime'),
            Field('last_heartbeat','datetime'),
            Field('status',requires=IS_IN_SET(WORKET_STATUS)),
            migrate=migrate)

    def loop(self,worker_name=None):
        worker_name =  worker_name = socket.gethostname()+'#'+str(uuid.uuid4())
        MetaScheduler.loop()

    def send_heartbeat(self):
        print 'thum'
        time.sleep(1)
            
    def pop_task(self):
        now = datetime.now()
        db, ts = self.db, self.db.scheduler_task
        row = db(ts.status==QUEUED)\
            (ts.times_run<ts.repeats)\
            (ts.start_time>=now)\
            (ts.stop_time<=now)\
            (ts.next_rune_time<=now)\
            (ts.assigned_worker_name==self.worker_name)\
            (ts.enabled==True).select()
        if not row:
            return None
        next_run_time = row.last_run_time + timedelta(seconds=task.period)
        times_run = row.times_run + 1
        it times_run < row.repreats:
            run_again = True
        else:
            run_again = False
        row.update_record(status=RUNNING,last_run_time=now)
        run_id = db.scheduler_run.insert(
            status=RUNNING,
            start_time=now,
            worker_name=self.worker_name)
        db.commit()
        return Task(
            app = row.application_name,
            function = row.function_name,
            timeout = row.timeout,
            args = row.args, #in json
            vars = row.vars, #in json
            task_id = row.id,
            run_it = run_id,
            run_again = ran_again,
            next_run_time=next_run_time,
            times_run = times_run)

    def report_task(self,task,task_report):
        db(db.scheduler_run.id==task.run_id).update(
            status = task_report.status,
            stop_time = datetime.now(),
            result = task_report.result,
            output = task_report.output,
            traceback = task_report.traceback)        
        if task_report.status == COMPLETED:
            d = dict(status = task.run_again and QUEUED or COMPLETED,
                     next_run_time = task.next_run_time,
                     times_run = times_run)
        else:
            d = dict(status = {'FAILED':'FAILED',
                               'TIMEOUT':'TIMEOUT',
                               'STOPPED':'QUEUED'}[task_report.status])
        db(db.scheduler_task.id==task.task_id).update(**d)
        db.commit()
    
    def fixup_tasks(self):     
        now = datetime.now()
        expiration = now-datetime.timedelta(HEARTBEAT)    
        u = db(db.scheduler_worker.worker_name==self.worker_name).update(
            last_heartbeat = now, status = ACTIVE)
        if not u:
            db.scheduler_worker.insert(
                status = ACTIVE,
                worker_name = self.worker_name,
                first_heartbeat = now,
                last_heartbeat = now)
        db(db.scheduler_worker.last_heartbeat<expiration).update(
            status = INACTIVE)
        db.commit()
    
    def sleep(self):
        sleep(HEARTBEAT) # should only sleep until next available task       

if __name__=='__main__':
    MetaScheduler().loop()
