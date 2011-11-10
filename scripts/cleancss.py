#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re

filename = sys.argv[1]

datafile = open(filename, 'r')
try:
    data = datafile.read()
finally:
    datafile.close()

data = re.compile('[ ]+').sub(' ', data)
data = re.compile('\s*{\s*').sub(' {\n    ', data)
data = re.compile('\s*;\s*').sub(';\n    ', data)
data = re.compile('\s*\*/\s*').sub('*/\n    ', data)
data = re.compile('\s*}\s*').sub('\n}\n', data)
data = re.compile('\n\s*\n').sub('\n', data)
data = re.compile('[ ]+\n').sub('\n', data)

print data

