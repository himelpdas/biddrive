#!/usr/bin/env python
# -*- coding: utf-8 -*-
# portalocker.py - Cross-platform (posix/nt) API for flock-style file locking.
#                  Requires python 1.5.2 or better.

"""
Cross-platform (posix/nt) API for flock-style file locking.

Synopsis:

   import portalocker
   file = open('somefile', 'r+')
   portalocker.lock(file, portalocker.LOCK_EX)
   file.seek(12)
   file.write('foo')
   file.close()

If you know what you're doing, you may choose to

   portalocker.unlock(file)

before closing the file, but why?

Methods:

   lock( file, flags )
   unlock( file )

flags can be:

   LOCK_EX
   LOCK_SH
   LOCK_NB

Derived from code by Jonathan Feinberg <jdf@pobox.com>

Modified by Massimo Di Pierro to use msvcrt so that no longer requires
Mark Hammond win32 extensions.
"""

import os
import logging
import platform
logger = logging.getLogger("web2py")

os_locking = None
try:
    import fcntl
    os_locking = 'posix'
except:
    pass
try:
    import msvcrt
    os_locking = 'windows'
except:
    pass


if os_locking == 'windows':
    LOCK_EX = 2
    LOCK_SH = 1
    LOCK_NB = 0

    LK_UNLCK = 0 # unlock the file region
    LK_LOCK = 1 # lock the file region
    LK_NBLCK = 2 # non-blocking lock
    LK_RLCK = 3 # lock for writing
    LK_NBRLCK = 4 # non-blocking lock for writing

    def lock(file, flags):
        file.fseek(0)
        mode = {LOCK_NB:LK_NBLCK, LOCK_SH:LK_NBLCK, LOCK_EX:LK_LOCK}[flags]
        msvcrt.locking(file.fileno(), mode, os.path.getsize(file.filename))

    def unlock(file):
        file.fseek(0)
        mode = LK_UNLCK
        msvcrt.locking(file.fileno(), mode, os.path.getsize(file.filename))

elif os_locking == 'posix':
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB

    def lock(file, flags):
        fcntl.flock(file.fileno(), flags)

    def unlock(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


else:
    logger.debug('no file locking, this will cause problems')

    LOCK_EX = None
    LOCK_SH = None
    LOCK_NB = None

    def lock(file, flags):
        pass

    def unlock(file):
        pass


if __name__ == '__main__':
    from time import time, strftime, localtime
    import sys

    log = open('log.txt', 'a+')
    lock(log, LOCK_EX)

    timestamp = strftime('%m/%d/%Y %H:%M:%S\n', localtime(time()))
    log.write(timestamp)

    print 'Wrote lines. Hit enter to release lock.'
    dummy = sys.stdin.readline()

    log.close()
