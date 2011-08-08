"""
## Example

For any existing app

Create File: app/models/scheduler.py ======
from gluon.scheduler import Scheduler

def demo1(*args,**vars):
    print 'you passed args=%s and vars=%s' % (args, vars)
    return 'done!'

def demo2():
    1/0

scheduler = Scheduler(db,dict(demo1=demo1,demo2=demo2))
=====================================

Create File: app/modules/scheduler.py ======
scheduler.worker_loop()
=====================================

## run worker nodes with:
python web2py.py -S app -M -N -R applications/app/modules/scheduler.py

## schedule jobs using
http://127.0.0.1:8000/scheduler/appadmin/insert/db/task_scheduled

## monitor scheduled jobs
http://127.0.0.1:8000/scheduler/appadmin/select/db?query=db.task_scheduled.id%3E0

## view completed jobs
http://127.0.0.1:8000/scheduler/appadmin/select/db?query=db.task_run.id%3E0

Works very much like celery & django-celery in web2py with some differences:
- it has no dependendecies but web2py
- it is much simpler to use and runs everywhere web2py runs 
  as long as you can at last one backrgound task
- it uses a database (via DAL) instead of rabbitMQ for message passing
  (this is not really a limitation for ~10 worker nodes)
- it does not allow stopping of running tasks
- it does not allow managed starting and stopping of worker nodes
- it does not allow mapping and filtering of tasks to workers
- it does not allow tasksets (but it does allow a task to submit another task)
"""

import traceback
import logging
import time
import sys
import cStringIO
import threading
from datetime import datetime, timedelta
from gluon import *
from gluon.contrib.simplejson import loads,dumps

STATUSES = QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT, OVERDUE = \
    ('queued','running','completed','failed', 'timeout', 'overdue')

class TYPE(object):
    def __init__(self,myclass=list,parse=False):
        self.myclass = myclass
        self.parse=parse
    def __call__(self,value):
        try:
            obj = loads(value)
        except:
            return (value,current.T('invalid json'))
        else:
            if isinstance(obj,self.myclass):
                if self.parse:
                    return (obj,None)
                else:
                    return (value,None)
            else:
                return (value,current.T('Not of type: %s') % self.myclass)

class TimeoutException(Exception): pass

def timeout_run(func, args=(), kwargs={}, timeout_duration=1):
    """http://code.activestate.com/recipes/473878-timeout-function-using-threading/"""
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)            
            self.result = self.output = self.traceback = None
        def run(self):
            try:
                stdout, sys.stdout = sys.stdout, cStringIO.StringIO()
                self.result = func(*args, **kwargs)
                self.status = COMPLETED
            except:
                self.status = FAILED
                self.result = None
                self.traceback = traceback.format_exc()
            sys.stdout, self.output = stdout, sys.stdout.getvalue()
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return TIMEOUT, it.result, it.output, it.traceback
    else:
        return it.status, it.result, it.output, it.traceback

class Scheduler(object):
    def __init__(self,db,tasks,migrate=True):
        self.db = db
        self.tasks = tasks
        now = current.request.now
        db.define_table(
            'task_scheduled',
            Field('name',requires=IS_NOT_IN_DB(db,'task_scheduled.name')),
            Field('group_name',default='main',writable=False),
            Field('status',requires=IS_IN_SET(STATUSES),default=QUEUED,writable=False),
            Field('func',requires=IS_IN_SET(sorted(self.tasks.keys()))),
            Field('args','text',default='[]',requires=TYPE(list)),
            Field('vars','text',default='{}',requires=TYPE(dict)),
            Field('enabled','boolean',default=True),
            Field('start_time','datetime',default=now),
            Field('next_run_time','datetime',default=now),
            Field('stop_time','datetime',default=now+timedelta(days=1)),
            Field('repeats','integer',default=1),
            Field('period','integer',default=60,comment='seconds'),
            Field('timeout','integer',default=60,comment='seconds'),
            Field('times_run','integer',default=0,writable=False),
            Field('last_run_time','datetime',writable=False,readable=False),
            migrate=migrate,format='%(name)s')
        db.define_table(
            'task_run',
            Field('task_scheduled','reference task_scheduled'),
            Field('status',requires=IS_IN_SET((RUNNING,COMPLETED,FAILED))),
            Field('start_time','datetime'),
            Field('output','text'),
            Field('result','text'),
            Field('traceback','text'),
            Field('worker_name',default=current.request.env.http_host),
            migrate=migrate)
        db.define_table(
            'worker_heartbeat',
            Field('name'),
            Field('last_heartbeat','datetime'),
            migrate=migrate)
    def form(self,id,**args):
        return SQLFORM(self.db.task_schedule,id,**args)
    def next_task(self,group_names=['main']):
        """find next task that needs to be executed"""
        from datetime import datetime
        db = self.db
        query = (db.task_scheduled.enabled==True)
        query &= (db.task_scheduled.status==QUEUED)
        query &= (db.task_scheduled.group_name.belongs(group_names))
        query &= (db.task_scheduled.next_run_time<datetime.now())
        return db(query).select(orderby=db.task_scheduled.next_run_time).first()
    def run_next_task(self,group_names=['main']):
        """get and execute next task"""
        db = self.db
        now = datetime.now()
        task = self.next_task(group_names=group_names)
        if task:
            logging.info('running task %s' % task.name)
            task.update_record(status=RUNNING,last_run_time=now)
            task_id = db.task_run.insert(task_scheduled=task.id,status=RUNNING,
                                         start_time=now)
            db.commit()
            times_run = task.times_run
            next_run_time = task.last_run_time + timedelta(seconds=task.period)
            func = self.tasks[task.func]
            args = loads(task.args)
            vars = loads(task.vars)
            status, result, output, tb = \
                timeout_run(func,args,vars,timeout_duration=task.timeout)
            status_repeat = status
            if status==COMPLETED:
                times_run += 1
                if times_run<task.repeats and next_run_time<task.stop_time:
                    status_repeat = QUEUED
            logging.warn('task %s %s' % (task.name,status))            
            db(db.task_run.id==task_id).update(status=status, output=output,
                                               traceback=tb, result=dumps(result))
            task.update_record(status=status_repeat, next_run_time=next_run_time,
                               times_run=times_run)
            db.commit()
            return True
        else:
            return False

    def log_heartbeat(self):
        db = self.db
        now = datetime.now()
        host = current.request.env.http_host
        if not db(db.worker_heartbeat.name==host).update(last_heartbeat=now):
            db.worker_heartbeat.insert(name=host,last_heartbeat=now)
        db.commit()

    def fix_failures(self):
        """find all tasks that have been running than they should and set OVERDUE"""
        db = self.db
        tasks = db(db.task_scheduled.status==RUNNING).select()
        ids = [task.id for task in tasks if \
                   task.last_run_time+timedelta(seconds=task.timeout)<datetime.now()]
        db(db.task_scheduled.id.belongs(ids)).update(status=OVERDUE)        
        db.commit()

    def worker_loop(self,logger_level='INFO',pause=10,group_names=['main']):
        """loop and log everything"""
        level = getattr(logging,logger_level)
        logging.basicConfig(format="%(asctime)-15s %(levename)-8s: %(message)s")
        logging.getLogger().setLevel(level)
        while True:
            if 'main' in group_names: 
                self.fix_failures()
            logging.info('checking for tasks...')
            self.log_heartbeat()
            while self.run_next_task(group_names=group_names):
                pass            
            time.sleep(pause)

    
            

