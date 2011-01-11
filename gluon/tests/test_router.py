#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import sys
import os
import unittest
import tempfile

sys.path.append(os.path.realpath('../..'))

from gluon.rewrite import load, filter_url, filter_err, get_effective_router
from gluon.fileutils import abspath
from gluon.settings import global_settings
from gluon.http import HTTP


class TestRouter(unittest.TestCase):
    """ Tests the routers logic from gluon.rewrite """


    def test_router_null(self):
        """ Tests the null router """
        router_null = dict()
        load(rdict=router_null)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'init')
        self.assertEqual(filter_url('http://domain.com/favicon.ico'), '/applications/init/static/favicon.ico')
        self.assertEqual(filter_url('http://domain.com/abc'), '/init/default/abc')
        self.assertEqual(filter_url('http://domain.com/index/abc'), "/init/default/index ['abc']")
        self.assertEqual(filter_url('http://domain.com/abc/def'), "/init/default/abc ['def']")
        self.assertEqual(filter_url('http://domain.com/index/a%20bc'), "/init/default/index ['a bc']")

    def test_router_welcome(self):
        """ Tests the welcome router """
        router_welcome = dict(BASE=dict(default_application='welcome'))
        load(rdict=router_welcome)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'welcome')

    def test_router_app(self):
        """ Tests the doctest router app resolution"""
        router_app = dict(
            BASE = dict(
                domains = {
                    "domain1.com" : "app1",
                    "www.domain1.com" : "app1",
                    "domain2.com" : "app2",
                },
            ),
            app1 = dict(),
            app2 = dict(),
            goodapp = dict(),
        )
        router_app['bad!app'] = dict()
        load(rdict=router_app)
        self.assertEqual(filter_url('http://domain.com/welcome', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com/welcome/', router='app'), 'welcome')
        self.assertEqual(filter_url('http://domain.com', router='app'), 'init')
        self.assertEqual(filter_url('http://domain.com/', router='app'), 'init')
        self.assertEqual(filter_url('http://domain.com/abc', router='app'), 'init')
        self.assertEqual(filter_url('http://domain1.com/abc', router='app'), 'app1')
        self.assertEqual(filter_url('http://www.domain1.com/abc', router='app'), 'app1')
        self.assertEqual(filter_url('http://domain2.com/abc', router='app'), 'app2')
        self.assertEqual(filter_url('http://domain2.com/admin', router='app'), 'admin')

        self.assertEqual(filter_url('http://domain.com/goodapp', router='app'), 'goodapp')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/bad!app', router='app')
        try:
            # 2.7+ only
            self.assertRaisesRegexp(HTTP, '400.*invalid application', filter_url, 'http://domain.com/bad!app')
        except AttributeError:
            pass


    def test_router_domain(self):
        '''
        Test URLs that map domains
        '''
        router_domain = dict(
            BASE = dict(
                applications = ['app1', 'app2', 'app2A', 'app3'],
                domains = {
                    #  two domains to the same app
                    "domain1.com"     : "app1",
                    "www.domain1.com" : "app1",
                    #  same domain, two ports, to two apps
                    "domain2.com"      : "app2a",
                    "domain2.com:8080" : "app2b",
                    #  two domains, same app, two controllers
                    "domain3a.com" : "app3/c3a",
                    "domain3b.com" : "app3/c3b",
                },
            ),
            app1 =  dict( default_controller = 'c1',  default_function = 'f1',  controllers = ['c1'], ),
            app2a = dict( default_controller = 'c2a', default_function = 'f2a', controllers = ['c2a'], ),
            app2b = dict( default_controller = 'c2b', default_function = 'f2b', controllers = ['c2b'], ),
            app3 =  dict( controllers = ['c3a', 'c3b'], ),
        )

        load(rdict=router_domain)
        self.assertEqual(filter_url('http://domain1.com/abc'), '/app1/c1/abc')
        self.assertEqual(filter_url('http://domain1.com/c1/abc'), '/app1/c1/abc')
        self.assertEqual(filter_url('http://domain1.com/abc.html'), '/app1/c1/abc')
        self.assertEqual(filter_url('http://domain1.com/abc.css'), '/app1/c1/abc.css')
        self.assertEqual(filter_url('http://domain1.com/index/abc'), "/app1/c1/index ['abc']")
        
        self.assertEqual(filter_url('https://domain1.com/app1/ctr/fcn', domain=('app1',None), out=True), "/ctr/fcn")
        self.assertEqual(filter_url('https://www.domain1.com/app1/ctr/fcn', domain=('app1',None), out=True), "/ctr/fcn")

        self.assertEqual(filter_url('http://domain2.com/abc'), '/app2a/c2a/abc')
        self.assertEqual(filter_url('http://domain2.com:8080/abc'), '/app2b/c2b/abc')

        self.assertEqual(filter_url('http://domain2.com/app2a/ctr/fcn', domain=('app2a',None), out=True), "/ctr/fcn")
        self.assertEqual(filter_url('http://domain2.com/app2a/ctr/f2a', domain=('app2a',None), out=True), "/ctr")
        self.assertEqual(filter_url('http://domain2.com/app2a/c2a/f2a', domain=('app2a',None), out=True), "/")
        self.assertEqual(filter_url('http://domain2.com/app2a/c2a/fcn', domain=('app2a',None), out=True), "/fcn")
        self.assertEqual(filter_url('http://domain2.com/app2a/ctr/fcn', domain=('app2b',None), out=True), "/app2a/ctr/fcn")
        self.assertEqual(filter_url('http://domain2.com/app2a/ctr/f2a', domain=('app2b',None), out=True), "/app2a/ctr")
        self.assertEqual(filter_url('http://domain2.com/app2a/c2a/f2a', domain=('app2b',None), out=True), "/app2a")

        self.assertEqual(filter_url('http://domain3a.com/'), '/app3/c3a/index')
        self.assertEqual(filter_url('http://domain3a.com/abc'), '/app3/c3a/abc')
        self.assertEqual(filter_url('http://domain3a.com/c3b'), '/app3/c3b/index')
        self.assertEqual(filter_url('http://domain3b.com/abc'), '/app3/c3b/abc')

        self.assertEqual(filter_url('http://domain3a.com/app3/c3a/fcn', domain=('app3','c3a'), out=True), "/fcn")
        self.assertEqual(filter_url('http://domain3a.com/app3/c3a/fcn', domain=('app3','c3b'), out=True), "/c3a/fcn")
        self.assertEqual(filter_url('http://domain3a.com/app3/c3a/fcn', domain=('app1',None), out=True), "/app3/c3a/fcn")


    def test_router_raise(self):
        '''
        Test URLs that raise exceptions
        '''
        # test non-exception variants
        router_raise = dict(
            init = dict(
                controllers = [],
            ),
            welcome = dict(
                map_hyphen = False,
            ),
        )
        load(rdict=router_raise)
        self.assertEqual(filter_url('http://domain.com/ctl'),  "/init/ctl/index")
        self.assertEqual(filter_url('http://domain.com/default/fcn'),  "/init/default/fcn")
        self.assertEqual(filter_url('http://domain.com/default/fcn.ext'),  "/init/default/fcn.ext")
        self.assertEqual(filter_url('http://domain.com/default/fcn/arg'),  "/init/default/fcn ['arg']")
        # now raise-HTTP variants
        self.assertRaises(HTTP, filter_url, 'http://domain.com/bad!ctl')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/bad!fcn')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/fcn.bad!ext')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/fcn/bad!arg')
        try:
            # 2.7+ only
            self.assertRaisesRegexp(HTTP, '400.*invalid controller', filter_url, 'http://domain.com/init/bad!ctl')
            self.assertRaisesRegexp(HTTP, '400.*invalid function', filter_url, 'http://domain.com/init/ctlr/bad!fcn')
            self.assertRaisesRegexp(HTTP, '400.*invalid extension', filter_url, 'http://domain.com/init/ctlr/fcn.bad!ext')
            self.assertRaisesRegexp(HTTP, '400.*invalid arg', filter_url, 'http://domain.com/appc/init/fcn/bad!arg')
        except AttributeError:
            pass

        self.assertEqual(filter_url('http://domain.com/welcome/default/fcn_1'),  "/welcome/default/fcn_1")
        self.assertRaises(HTTP, filter_url, 'http://domain.com/welcome/default/fcn-1')
        try:
            # 2.7+ only
            self.assertRaisesRegexp(HTTP, '400.*invalid function', filter_url, 'http://domain.com/welcome/default/fcn-1')
        except AttributeError:
            pass


    def test_router_out(self):
        '''
        Test basic outgoing routing
        '''
        router_out = dict(
            BASE = dict(),
            init = dict( controllers = ['default', 'ctr'], ),
            app = dict(),
        )
        load(rdict=router_out)
        self.assertEqual(filter_url('https://domain.com/app/ctr/fcn', out=True), "/app/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/init/ctr/fcn', out=True), "/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/init/default/fcn', out=True), "/fcn")
        self.assertEqual(filter_url('https://domain.com/init/default/index', out=True), "/")
        self.assertEqual(filter_url('https://domain.com/init/ctr/index', out=True), "/ctr")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn?query', out=True), "/fcn?query")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn#anchor', out=True), "/fcn#anchor")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn?query#anchor', out=True), "/fcn?query#anchor")


    def test_router_hyphen(self):
        '''
        Test hyphen conversion
        '''
        router_hyphen = dict(
            BASE = dict(
                applications = ['init', 'app2'],
            ),
            init = dict(
                controllers = ['default'],
            ),
            app2 = dict(
                controllers = ['default'],
                map_hyphen = False,
            ),
        )
        load(rdict=router_hyphen)
        self.assertEqual(filter_url('http://domain.com/fcn-1'), "/init/default/fcn_1")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn_1', out=True), "/fcn-1")
        self.assertEqual(filter_url('http://domain.com/static/filename-with_underscore'), "/applications/init/static/filename-with_underscore")
        self.assertEqual(filter_url('http://domain.com/init/static/filename-with_underscore', out=True), "/static/filename-with_underscore")

        self.assertEqual(filter_url('http://domain.com/app2/fcn_1'), "/app2/default/fcn_1")
        self.assertEqual(filter_url('http://domain.com/app2/ctr/fcn_1', domain=('app2',None), out=True), "/ctr/fcn_1")
        self.assertEqual(filter_url('http://domain.com/app2/static/filename-with_underscore', domain=('app2',None), out=True), "/static/filename-with_underscore")
        self.assertEqual(filter_url('http://domain.com/app2/static/filename-with_underscore'), "/applications/app2/static/filename-with_underscore")


    def test_router_lang(self):
        '''
        Test language specifications
        '''
        router_lang = dict(
            welcome = dict(),
            init = dict(
                controllers = ['default', 'ctr'],
                languages = ['en', 'it', 'it-it'], default_language = 'en',
            ),
        )
        load(rdict=router_lang)
        self.assertEqual(filter_url('http://domain.com/index/abc'), "/init/default/index ['abc'] (en)")
        self.assertEqual(filter_url('http://domain.com/en/abc/def'), "/init/default/abc ['def'] (en)")
        self.assertEqual(filter_url('http://domain.com/it/abc/def'), "/init/default/abc ['def'] (it)")
        self.assertEqual(filter_url('http://domain.com/it-it/abc/def'), "/init/default/abc ['def'] (it-it)")
        self.assertEqual(filter_url('http://domain.com/index/a%20bc'), "/init/default/index ['a bc'] (en)")

        self.assertEqual(filter_url('https://domain.com/init/ctr/fcn', lang='en', out=True), "/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/init/ctr/fcn', lang='it', out=True), "/it/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/init/ctr/fcn', lang='it-it', out=True), "/it-it/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/welcome/ctr/fcn', lang='it', out=True), "/welcome/ctr/fcn")
        self.assertEqual(filter_url('https://domain.com/welcome/ctr/fcn', lang='es', out=True), "/welcome/ctr/fcn")        


    def test_router_get_effective(self):
        '''
        Test get_effective_router
        '''
        router_get_effective = dict(
            BASE = dict(
                default_application = 'a1',
                applications = ['a1', 'a2'],
            ),
            a1 = dict(
                controllers = ['c1a', 'c1b', 'default'],
            ),
            a2 = dict(
                default_controller = 'c2',
                controllers = [],
            ),
        )
        load(rdict=router_get_effective)
        self.assertEqual(get_effective_router('a1').default_application, "a1")
        self.assertEqual(get_effective_router('a1').default_controller, "default")
        self.assertEqual(get_effective_router('a2').default_application, "a1")
        self.assertEqual(get_effective_router('a2').default_controller, "c2")
        self.assertEqual(get_effective_router('a1').controllers, ['c1a', 'c1b', 'default', 'static'])
        self.assertEqual(get_effective_router('a2').controllers, [])


    def test_router_error(self):
        '''
        Test rewrite of HTTP errors
        '''
        router_err = dict()
        load(rdict=router_err)
        self.assertEqual(filter_err(200), 200)
        self.assertEqual(filter_err(399), 399)
        self.assertEqual(filter_err(400), 400)


if __name__ == '__main__':

    def make_apptree():
        "build a temporary applications tree"
        #  applications/
        os.mkdir(abspath('applications'))
        #  applications/app/
        for app in ('admin', 'examples', 'welcome'):
            os.mkdir(abspath('applications', app))
            #  applications/app/(controllers, static)
            for subdir in ('controllers', 'static'):
                os.mkdir(abspath('applications', app, subdir))
        #  applications/admin/controllers/*.py
        for ctr in ('appadmin', 'default', 'gae', 'mercurial', 'shell', 'wizard'):
            open(abspath('applications', 'admin', 'controllers', '%s.py' % ctr), 'w').close()
        #  applications/examples/controllers/*.py
        for ctr in ('ajax_examples', 'appadmin', 'default', 'global', 'spreadsheet'):
            open(abspath('applications', 'examples', 'controllers', '%s.py' % ctr), 'w').close()
        #  applications/welcome/controllers/*.py
        for ctr in ('appadmin', 'default'):
            open(abspath('applications', 'welcome', 'controllers', '%s.py' % ctr), 'w').close()

    oldpwd = os.getcwd()
    os.chdir(os.path.realpath('../../'))
    import gluon.main   # for initialization after chdir
    global_settings.applications_parent = tempfile.mkdtemp()
    make_apptree()
    unittest.main()
    os.chdir(oldpwd)
