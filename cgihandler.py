#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import wsgiref.handlers

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path = [path]+[p for p in sys.path if not p==path]

import gluon.main

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)
