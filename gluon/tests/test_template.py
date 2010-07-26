#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.template
"""

import sys
import os
sys.path.append(os.path.realpath('../'))

import unittest
from template_new import parse_template, TemplateParser, render

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
        
    def testExtends(self):
        path = 'templates/'
        
        def testit(target, expected):
            rendered = render(filename=path+target, path=path)            
            assert rendered.replace('\n\n', '') == expected
            
        testit('view/test_include.html', '''<html>
<title>TITLE0</title>
<body>Hello this is a test
</body>
</html>
''')
        testit('view/test_extends.html', '''<html>
<title>TITLE0</title>
<body>
I go in the middle of the content.</body>
</html>
''')
        testit('view/test_block.html', '''<html>
<title>
HI FROM BLOCK
</title>
<body>
I go in the middle of the content.</body>
</html>
''')

if __name__ == '__main__':
    unittest.main()
    
    
 #   def parse_template(filename,
  #      path    = 'views/',
 #       context = dict(),
 #       lexers  = {}):
 ##       
 #     return str(TemplateParser(text, context=context, path=path, lexers=lexers))
