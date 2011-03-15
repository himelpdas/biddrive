#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.template
"""

import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
from template import render

class TestVirtualFields(unittest.TestCase):

    def testRun(self):
        self.assertEqual(render(content='{{for i in range(n):}}{{=i}}{{pass}}',
                      context=dict(n=3)), '012')
        self.assertEqual(render(content='{{if n>2:}}ok{{pass}}',
                      context=dict(n=3)), 'ok')
        self.assertEqual(render(content='{{try:}}{{n/0}}{{except:}}fail{{pass}}',
                      context=dict(n=3)), 'fail')
        self.assertEqual(render(content='{{="<&>"}}'), '&lt;&amp;&gt;')
        self.assertEqual(render(content='"abc"'), '"abc"')
        self.assertEqual(render(content='"a\'bc"'), '"a\'bc"')
        self.assertEqual(render(content='"a\"bc"'), '"a\"bc"')
        self.assertEqual(render(content=r'''"a\"bc"'''), r'"a\"bc"')
        self.assertEqual(render(content=r'''"""abc\""""'''), r'"""abc\""""')

    def testEqualWrite(self):
        "test generation of response.write from ="
        self.assertEqual(render(content='{{="abc"}}'), 'abc')
        self.assertEqual(render(content='{{ ="abc"}}'), 'abc')
        self.assertEqual(render(content='{{ ="abc" }}'), 'abc')
        self.assertEqual(render(content='{{pass\n="abc" }}'), 'abc')
        self.assertEqual(render(content='{{xyz="xyz"\n="abc"\n="def"\n=xyz }}'), 'abcdefxyz')
        #self.assertEqual(render(content='{{="abc"\n="def" }}'), 'abcdef')
        self.assertEqual(render(content='{{if True:\n="abc"\npass }}'), 'abc')
        self.assertEqual(render(content='{{if True:\n="abc"\npass\n="def" }}'), 'abcdef')
        self.assertEqual(render(content='{{if False:\n="abc"\npass\n="def" }}'), 'def')
        self.assertEqual(render(content='{{if True:\n="abc"\nelse:\n="def"\npass }}'), 'abc')
        self.assertEqual(render(content='{{if False:\n="abc"\nelse:\n="def"\npass }}'), 'def')



if __name__ == '__main__':
    unittest.main()
