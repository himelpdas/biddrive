#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import sys
import os
import unittest

sys.path.append(os.path.realpath('../..'))

from gluon.rewrite import load, filter_url, filter_out, filter_err, get_effective_router

router_null = dict()
router_welcome = dict(BASE=dict(default_application='welcome'))

class TestRouter(unittest.TestCase):
    """ Tests the utils.py module """


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

if __name__ == '__main__':
    oldpwd = os.getcwd()
    os.chdir(os.path.realpath('../../'))
    import gluon.main   # for initialization
    unittest.main()
    os.chdir(oldpwd)
