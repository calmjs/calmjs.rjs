# -*- coding: utf-8 -*-
import unittest

from calmjs.utils import pretty_logging
from calmjs.rjs import utils

from calmjs.testing.mocks import StringIO


class DictGetTestCase(unittest.TestCase):
    """
    A special get that also creates keys.
    """

    def test_dict_get(self):
        items = {}
        utils.dict_get(items, 'a_key')
        self.assertEqual(items, {'a_key': {}})

        a_key = items['a_key']
        utils.dict_get(items, 'a_key')
        self.assertIs(items['a_key'], a_key)


class DictKeyGetUpdateTestCase(unittest.TestCase):
    """
    A function for updating specific dict/spec via a key, and ensure
    that any overwritten values are warned.
    """

    def test_dict_key_update_overwrite_check_standard(self):
        a = {}
        a['base_key'] = {'k1': 'v1'}
        mapping = {'k2': 'v2'}
        with pretty_logging(logger='calmjs.rjs', stream=StringIO()) as s:
            utils.dict_key_update_overwrite_check(a, 'base_key', mapping)
        self.assertEqual(s.getvalue(), '')
        self.assertEqual(a['base_key'], {'k1': 'v1', 'k2': 'v2'})

    def test_dict_key_update_overwrite_check_no_update(self):
        a = {}
        a['base_key'] = {'k1': 'v1'}
        mapping = {'k1': 'v1'}
        with pretty_logging(logger='calmjs.rjs', stream=StringIO()) as s:
            utils.dict_key_update_overwrite_check(a, 'base_key', mapping)
        self.assertEqual(s.getvalue(), '')
        self.assertEqual(a['base_key'], {'k1': 'v1'})

    def test_dict_key_update_overwrite_check_overwritten_single(self):
        a = {}
        a['base_key'] = {'k1': 'v1'}
        mapping = {'k1': 'v2'}
        with pretty_logging(logger='calmjs.rjs', stream=StringIO()) as s:
            utils.dict_key_update_overwrite_check(a, 'base_key', mapping)
        self.assertIn(
            "value of base_key['k1'] is being rewritten from 'v1' to 'v2';",
            s.getvalue())
        self.assertEqual(a['base_key'], {'k1': 'v2'})

    def test_dict_key_update_overwrite_check_overwritten_multi(self):
        a = {}
        a['base_key'] = {'k1': 'v1', 'k2': 'v2'}
        mapping = {'k1': 'v2', 'k2': 'v4'}
        with pretty_logging(logger='calmjs.rjs', stream=StringIO()) as s:
            utils.dict_key_update_overwrite_check(a, 'base_key', mapping)
        self.assertIn(
            "value of base_key['k1'] is being rewritten from 'v1' to 'v2';",
            s.getvalue())
        self.assertIn(
            "value of base_key['k2'] is being rewritten from 'v2' to 'v4';",
            s.getvalue())
        self.assertEqual(a['base_key'], {'k1': 'v2', 'k2': 'v4'})
