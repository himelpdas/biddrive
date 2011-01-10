#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import sys
import os
import unittest
import tempfile

sys.path.append(os.path.realpath('../..'))

from gluon.rewrite import load, filter_url, filter_out, filter_err, get_effective_router
from gluon.fileutils import abspath
from gluon.settings import global_settings
from gluon.http import HTTP

router_null = dict()
router_welcome = dict(BASE=dict(default_application='welcome'))
router_doctest = dict(
    BASE = dict(
        applications = ['welcome', 'admin', 'myapp', 'app', 'appc', 'bad!app'],
        default_application = 'myapp',
        domains = {
            "domain1.com" : "app1",
            "domain2.com" : "app2"
        },
    ),
    app = dict(),
    myapp = dict(
        controllers = ['myctlr', 'ctr'], default_controller = 'myctlr', default_function = 'myfunc',
        languages = ['en', 'it', 'it-it'], default_language = 'en',
    ),
    app1 = dict( default_controller = 'ctr1', default_function = 'fcn1', ),
    app2 = dict( default_controller = 'ctr2', default_function = 'fcn2', map_hyphen = False, ),
    appc = dict( controllers=[] ),
)

class TestRouter(unittest.TestCase):
    """ Tests the routers logic from gluon.rewrite """


    def test_router_null(self):
        """ Tests the null router """

        load(rdict=router_null)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'init')

    def test_router_welcome(self):
        """ Tests the welcome router """

        load(rdict=router_welcome)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'welcome')

    def test_router_doctest_app(self):
        """ Tests the doctest router app resolution"""

        load(rdict=router_doctest)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/welcome/', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com', router='app'), 'myapp')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'myapp')
        self.assertEqual(filter_url('http://domain.com/abc', router='app'), 'myapp')
        self.assertEqual(filter_url('http://domain1.com/abc', router='app'), 'app1')
        self.assertEqual(filter_url('http://domain2.com/abc', router='app'), 'app2')
        self.assertEqual(filter_url('http://domain2.com/admin', router='app'), 'admin')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/bad!app', router='app')
        try:
            # 2.7+ only
            self.assertEqual(filter_url('http://domain.com/appc'),  "/appc/default/index")
            self.assertRaisesRegexp(HTTP, '400.*invalid application', filter_url, 'http://domain.com/bad!app')
        except AttributeError:
            pass

    def test_router_doctest(self):
        """ Tests the doctest router"""

        load(rdict=router_doctest)
        self.assertEqual(filter_url('http://domain.com/favicon.ico'), '/applications/myapp/static/favicon.ico')
        self.assertEqual(filter_url('http://domain.com/abc'), '/myapp/myctlr/abc (en)')
        self.assertEqual(filter_url('http://domain1.com/abc'), '/app1/abc/fcn1')
        self.assertEqual(filter_url('http://domain.com/index/abc'), "/myapp/myctlr/index ['abc'] (en)")
        self.assertEqual(filter_url('http://domain1.com/default/abc.html'), '/app1/default/abc')
        self.assertEqual(filter_url('http://domain1.com/default/abc.css'), '/app1/default/abc.css')
        self.assertEqual(filter_url('http://domain1.com/default/index/abc'), "/app1/default/index ['abc']")
        self.assertEqual(filter_url('http://domain.com/en/abc/def'), "/myapp/myctlr/abc ['def'] (en)")
        self.assertEqual(filter_url('http://domain1.com/default/index/a bc'), "/app1/default/index ['a bc']")
        self.assertEqual(filter_url('http://domain.com/it/abc/def'), "/myapp/myctlr/abc ['def'] (it)")
        self.assertEqual(filter_url('http://domain.com/it-it/abc/def'),  "/myapp/myctlr/abc ['def'] (it-it)")
        
        self.assertRaises(HTTP, filter_url, 'http://domain.com/bad!ctl')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/bad!fcn')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/fcn.bad!ext')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/fcn/bad!arg')
        try:
            # 2.7+ only
            self.assertEqual(filter_url('http://domain.com/appc/ctlr'),  "/appc/ctlr/index")
            self.assertRaisesRegexp(HTTP, '400.*invalid controller', filter_url, 'http://domain.com/appc/bad!ctl')
            
            self.assertEqual(filter_url('http://domain.com/appc/ctlr/fcn'),  "/appc/ctlr/fcn")
            self.assertRaisesRegexp(HTTP, '400.*invalid function', filter_url, 'http://domain.com/appc/ctlr/bad!fcn')
            
            self.assertEqual(filter_url('http://domain.com/appc/ctlr/fcn.ext'),  "/appc/ctlr/fcn.ext")
            self.assertRaisesRegexp(HTTP, '400.*invalid extension', filter_url, 'http://domain.com/appc/ctlr/fcn.bad!ext')
            
            self.assertEqual(filter_url('http://domain.com/appc/ctlr/fcn/arg'),  "/appc/ctlr/fcn ['arg']")
            self.assertRaisesRegexp(HTTP, '400.*invalid arg', filter_url, 'http://domain.com/appc/ctlr/fcn/bad!arg')
        except AttributeError:
            pass

if __name__ == '__main__':

    def make_apptree():
        "build a temporary applications tree"
        base = global_settings.applications_parent
        os.mkdir(abspath('applications'))
        for app in ('admin', 'examples', 'welcome'):
            os.mkdir(abspath('applications', app))
            for subdir in ('controllers', 'static'):
                os.mkdir(abspath('applications', app, subdir))
        for ctr in ('appadmin', 'default', 'gae', 'mercurial', 'shell', 'wizard'):
            os.mkdir(abspath('applications', 'admin', 'controllers', '%s.py' % ctr))
        for ctr in ('ajax_examples', 'appadmin', 'default', 'global', 'spreadsheet'):
            os.mkdir(abspath('applications', 'examples', 'controllers', '%s.py' % ctr))
        for ctr in ('appadmin', 'default'):
            os.mkdir(abspath('applications', 'welcome', 'controllers', '%s.py' % ctr))

    oldpwd = os.getcwd()
    os.chdir(os.path.realpath('../../'))
    import gluon.main   # for initialization
    global_settings.applications_parent = tempfile.mkdtemp()
    make_apptree()
    unittest.main()
    os.chdir(oldpwd)
