#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import wsgiref.handlers

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)

if path in sys.path:
    sys.path.remove(path)
sys.path.insert(0, path)

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)
