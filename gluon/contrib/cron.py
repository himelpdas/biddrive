#!/usr/bin/env python
# -*- coding: utf-8 -*-

__name__ = 'cron'
__version__ = (0, 1, 1)
__author__ = 'Attila Csipa <web2py@csipa.in.rs>'

_generator_name = __name__ + '-' + '.'.join(map(str, __version__))

import sys
import os
import threading
import logging
import time
import sched
import re
import datetime
import traceback
import platform
from subprocess import Popen, PIPE, call

# crontype can be 'soft', 'hard', 'external', None
crontype = 'soft'

class extcron(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.path = apppath(dict(web2py_path=os.getcwd()))

    def run(self):
        logging.debug('External cron invocation')
        crondance(self.path, 'ext')

class hardcron(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.path = apppath(dict(web2py_path=os.getcwd()))
        self.startup = True
        self.launch()
        self.startup = False

    def launch(self):
        crondance(self.path, 'hard', startup = self.startup)

    def run(self):
        s = sched.scheduler(time.time, time.sleep)
        logging.info('Hard cron daemon started')
        while True:
            now = time.time()
            s.enter(60 - now % 60, 1, self.launch, ())
            s.run()

class softcron(threading.Thread):

    def __init__(self, env):
        threading.Thread.__init__(self)
        self.env = env
        self.cronmaster = 0
        self.softwindow = 120
        self.path = apppath(self.env)
        self.cronmaster = crondance(self.path, 'soft', startup = True)

    def run(self):
        if crontype != 'soft':
            return
        now = time.time()
        # our own thread did a cron check less than a minute ago, don't even
        # bother checking the file
        if self.cronmaster and 60 > now - self.cronmaster:
            logging.debug("Don't bother with cron.master, it's only %s s old"
                           % (now - self.cronmaster))
            return

        logging.debug('Cronmaster stamp: %s, Now: %s'
                      % (self.cronmaster, now))
        if 60 <= now - self.cronmaster:  # new minute, do the cron dance
            self.cronmaster = crondance(self.path, 'soft')


def tokenmaster(path, action = 'claim', startup = False):
    token = os.path.join(path, 'cron.master')
    tokeninuse = os.path.join(path, 'cron.running')
    global crontype

    if action == 'release':
        logging.debug('WEB2PY CRON: Releasing cron lock')
        try:
            os.unlink(tokeninuse)
            return time.time()
        except: # may raise IOError or WindowsError
            return 0

    if not startup and os.path.exists(token):
        tokentime = os.stat(token).st_mtime
        # already ran in this minute?
        if tokentime - (tokentime % 60) + 60 > time.time():
            return 0

    # running now?
    if os.path.exists(tokeninuse):
        logging.warning('alreadyrunning')
        # check if stale, just in case
        if os.stat(tokeninuse).st_mtime + 60 < time.time():
            logging.warning('WEB2PY CRON: Stale cron.master detected')
            try:
                os.unlink(tokeninuse)
            except: # may raise IOError or WindowsError
                logging.warning('WEB2PY CRON: unable to unlink %s' % tokeninuse)

    # no tokens, new install ? Need to regenerate anyho
    if not (os.path.exists(token) or os.path.exists(tokeninuse)):
        logging.warning(
            "WEB2PY CRON: cron.master not found at %s. Trying to re-create."
            % token)
        try:
            mfile = open(token, 'wb')
            mfile.close()
        except: # may raise IOError or WindowsError
            logging.error(
                'WEB2PY CRON: Unable to re-create cron.master, ' + \
                    'cron functionality likely not available')
            crontype = None
            return 0

    # has unclaimed token and not running ?
    if os.path.exists(token) and not os.path.exists(tokeninuse):
        logging.debug('WEB2PY CRON: Trying to acquire lock')
        try:
            os.rename(token, tokeninuse)
            # can't rename, must recreate as we need a correct claim time
            mfile = open(token, 'wb')
            mfile.close()
            logging.debug('WEB2PY CRON: Locked')
            return os.stat(token).st_mtime
        except: # may raise IOError or WindowsError
            logging.info('WEB2PY CRON: Failed to claim %s' % token)
            return 0

    logging.debug('WEB2PY CRON: already started from another process')
    return 0


def apppath(env=None):
    try:
        apppath = os.path.join(env.get('web2py_path'), 'applications')
    except:
        apppath = os.path.join(os.path.split(env.get('SCRIPT_FILENAME'))[0],
            'applications')
    return apppath


def rangetolist(s, period='min'):
    retval = []
    if s.startswith('*'):
        if period == 'min':
            s = s.replace('*', '0-59', 1)
        elif period == 'hr':
            s = s.replace('*', '0-23', 1)
        elif period == 'dom':
            s = s.replace('*', '1-31', 1)
        elif period == 'mon':
            s = s.replace('*', '1-12', 1)
        elif period == 'dow':
            s = s.replace('*', '0-6', 1)
    m = re.compile(r'(\d+)-(\d+)/(\d+)')
    match = m.match(s)
    if match:
        for i in range(int(match.group(1)), int(match.group(2)) + 1):
            if i % int(match.group(3)) == 0:
                retval.append(i)
    return retval


def parsecronline(line):
    task = {}
    if line.startswith('@reboot'):
        line=line.replace('@reboot', '-1 * * * *')
    elif line.startswith('@yearly'):
        line=line.replace('@yearly', '0 0 1 1 *')
    elif line.startswith('@annually'):
        line=line.replace('@annually', '0 0 1 1 *')
    elif line.startswith('@monthly'):
        line=line.replace('@monthly', '0 0 1 * *')
    elif line.startswith('@weekly'):
        line=line.replace('@weekly', '0 0 * * 0')
    elif line.startswith('@daily'):
        line=line.replace('@daily', '0 0 * * *')
    elif line.startswith('@midnight'):
        line=line.replace('@midnight', '0 0 * * *')
    elif line.startswith('@hourly'):
        line=line.replace('@hourly', '0 * * * *')
    params = line.strip().split(None, 6)
    if len(params) < 7:
        return None
    for (s, id) in zip(params[:5], ['min', 'hr', 'dom', 'mon', 'dow']):
        if not s in [None, '*']:
            task[id] = []
            vals = s.split(',')
            for val in vals:
                if val.find('/') > -1:
                    task[id] += rangetolist(val, id)
                elif val.isdigit() or val=='-1':
                    task[id].append(int(val))
    task['user'] = params[5]
    task['cmd'] = params[6]
    return task


class cronlauncher(threading.Thread):

    def __init__(self, cmd, shell=True):
        threading.Thread.__init__(self)
        if platform.system() == 'Windows':
            shell = False
        elif isinstance(cmd,list):
            cmd = ' '.join(cmd)
        self.cmd = cmd
        self.shell = shell

    def run(self):
        proc = Popen(self.cmd,
                     stdin=PIPE,
                     stdout=PIPE,
                     stderr=PIPE,
                     shell=self.shell)
        (stdoutdata,stderrdata) = proc.communicate()
        if proc.returncode != 0:
            logging.warning(
                'WEB2PY CRON Call returned code %s:\n%s' % \
                    (proc.returncode, stdoutdata+stderrdata))
        else:
            logging.debug('WEB2PY CRON Call retruned success:\n%s' \
                              % stdoutdata)

def crondance(apppath, ctype='soft',startup=False):
    cron_path = os.path.join(apppath,'admin','cron')
    cronmaster = tokenmaster(cron_path, action='claim', startup=startup)
    if not cronmaster:
        return cronmaster

    now_s = time.localtime()
    checks=(('min',now_s.tm_min),
            ('hr',now_s.tm_hour),
            ('mon',now_s.tm_mon),
            ('dom',now_s.tm_mday),
            ('dow',now_s.tm_wday))

    apps = [x for x in os.listdir(apppath)
            if os.path.isdir(os.path.join(apppath, x))]

    for app in apps:
        apath = os.path.join(apppath,app)
        cronpath = os.path.join(apath, 'cron')
        crontab = os.path.join(cronpath, 'crontab')
        if not os.path.exists(crontab):
            continue
        f = open(crontab, 'rt')
        cronlines = f.readlines()
        lines = [x for x in cronlines if x.strip() and x[0]!='#']
        tasks = [parsecronline(cline) for cline in lines]

        for task in tasks:
            commands = [sys.executable]
            if os.path.exists('web2py.py'):
                commands.append('web2py.py')

            if not task:
                continue
            elif not startup and task.get('min',[])==[-1]:
                continue
            if not task.get('min',[])==[-1]:
                for key, value in checks:
                    if key in task and not value in task[key]:
                        continue
            logging.info(
                'WEB2PY CRON (%s): Application: %s executing %s in %s at %s' \
                    % (ctype, app, task.get('cmd'),
                       os.getcwd(), datetime.datetime.now()))
            action, command, models = False, task['cmd'], ''
            if command.startswith('**'):
                (action,models,command) = (True,'',command[2:])
            elif command.startswith('*'):
                (action,models,command) = (True,'-M',command[1:])
            else:
                action=False
            if action and command.endswith('.py'):
                commands.extend(('-P',
                                 '-N',models,
                                 '-S',app,
                                 '-a','"<recycle>"',
                                 '-R',command))
                shell = True
            elif action:
                commands.extend(('-P',
                                 '-N',models,
                                 '-S',app+'/'+command,
                                 '-a','"<recycle>"'))
                shell = True
            else:
                commands = command
                shell = False
            try:
                cronlauncher(commands, shell=shell).start()
            except Exception, e:
                logging.warning(
                    'WEB2PY CRON: Execution error for %s: %s' \
                        % (task.get('cmd'), e))
    return tokenmaster(cron_path, action='release', startup=startup)
