#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.template
"""

import sys
import os
sys.path.append(os.path.realpath('../'))

import unittest
from template import render

class TestVirtualFields(unittest.TestCase):

    def testRun(self):
        assert render(content='{{for i in range(n):}}{{=i}}{{pass}}',
                      context=dict(n=3)) == '012'
        assert render(content='{{if n>2:}}ok{{pass}}',
                      context=dict(n=3)) == 'ok'
        assert render(content='{{try:}}{{n/0}}{{except:}}fail{{pass}}',
                      context=dict(n=3)) == 'fail'
        assert render(content='{{="<&>"}}') == '&lt;&amp;&gt;'
        assert render(content='"abc"') == '"abc"'
        assert render(content='"a\'bc"') == '"a\'bc"'
        assert render(content='"a\"bc"') == '"a\"bc"'
        assert render(content=r'''"a\"bc"''') == r'"a\"bc"'
        assert render(content=r'''"""abc\""""''') == r'"""abc\""""'

if __name__ == '__main__':
    unittest.main()
