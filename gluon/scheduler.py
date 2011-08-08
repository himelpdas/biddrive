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
from datetime import datetime, timedelta
from gluon import *
from gluon.contrib.simplejson import loads,dumps

STATUSES = QUEUED, RUNNING, DONE, FAILED = ('queued','running','done','failed')

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

class Scheduler(object):
    def __init__(self,db,tasks):
        self.db = db
        self.tasks = tasks
        now = current.request.now
        db.define_table(
            'task_scheduled',
            Field('name',requires=IS_NOT_IN_DB(db,'task_scheduled.name')),
            Field('status',requires=IS_IN_SET(STATUSES),default=QUEUED,writable=False),
            Field('func',requires=IS_IN_SET(sorted(self.tasks.keys()))),
            Field('args','text',default='[]',requires=TYPE(list)),
            Field('vars','text',default='{}',requires=TYPE(dict)),
            Field('enabled','boolean',default=True),
            Field('start_time','datetime',default=now),
            Field('stop_time','datetime',default=now+timedelta(days=1)),
            Field('repeats','integer',default=1),
            Field('period','integer',default=60), # seconds
            Field('times_run','integer',default=0,writable=False),
            Field('last_run_time','datetime',writable=False,readable=False),
            Field('next_run_time','datetime',writable=False,readable=False,default=now))
        db.define_table(
            'task_run',
            Field('task_scheduled','reference task_scheduled'),
            Field('status',requires=IS_IN_SET((RUNNING,DONE,FAILED))),
            Field('start_time','datetime'),
            Field('output','text'),
            Field('result','text'),
            Field('traceback','text'),
            Field('worker',default=current.request.env.http_host))
    def form(self,id,**args):
        db.task_scheduled.next_run_time.compute = lambda row: row.start_time
        return SQLFORM(self.db.task_schedule,id,**args)
    def next_task(self):
        from datetime import datetime
        db = self.db
        query = (db.task_scheduled.enabled==True)
        query &= (db.task_scheduled.status==QUEUED)
        query &= (db.task_scheduled.next_run_time<datetime.now())
        return db(query).select(orderby=db.task_scheduled.next_run_time).first()
    def run_next_task(self):
        db = self.db
        now = datetime.now()
        task = self.next_task()
        if task:
            logging.info('running task %s' % task.name)
            task.update_record(status=RUNNING,last_run_time=now)
            task_id = db.task_run.insert(task_scheduled=task.id,status=RUNNING,
                                         start_time=now)
            db.commit()
            times_run = task.times_run + 1
            try:
                func = self.tasks[task.func]
                args = loads(task.args)
                vars = loads(task.vars)
                stdout, sys.stdout = sys.stdout, cStringIO.StringIO()
                result = func(*args,**vars)                
            except:
                sys.stdout, output = stdout, sys.stdout.getvalue()
                logging.warn('task %s failed' % task.name)
                db(db.task_run.id==task_id).update(status=FAILED,output=output,
                                                   traceback=traceback.format_exc())
                task.update_record(status=FAILED, next_run_time=now,
                                   times_run=times_run)
            else:
                sys.stdout, output = stdout, sys.stdout.getvalue()
                logging.info('task %s done' % task.name)
                next_run_time = now + timedelta(seconds=task.period)
                db(db.task_run.id==task_id).update(status=DONE, output=output,
                                                   result=dumps(result))
                if times_run<task.repeats and next_run_time<task.stop_time:
                    status = QUEUED
                else:
                    status = DONE
                task.update_record(status=status, next_run_time=next_run_time,
                                   times_run=times_run)
            db.commit()
            return True
        else:
            return False

    def worker_loop(self,logger_level='DEBUG',pause=10):
        level = getattr(logging,logger_level)
        logging.basicConfig(format="%(asctime)-15s %(levename)-8s: %(message)s")
        logging.getLogger().setLevel(level)
        while True:
            logging.info('checking for tasks...')
            while self.run_next_task(): pass
            time.sleep(pause)

    
            

