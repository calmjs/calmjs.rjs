# -*- coding: utf-8 -*-
import unittest
import json
import os
import tempfile
from os import makedirs
from os.path import exists
from os.path import join
from shutil import rmtree

from io import StringIO

from calmjs.rjs import dist

from calmjs.testing import utils


class BaseDistTestCase(unittest.TestCase):
    """
    Test out dist functions
    """

    def test_acquire_method(self):
        foo = object()
        bar = object()
        r = dist.acquire_method({'foo': foo, 'bar': bar}, 'foo', default='bar')
        self.assertIs(r, foo)
        r = dist.acquire_method({'foo': foo, 'bar': bar}, 'wat', default='bar')
        self.assertIs(r, bar)


class DistIntegrationTestCase(unittest.TestCase):
    """
    A number of integration tests, using mocked up data created with the
    calmjs.testing helpers.
    """

    @classmethod
    def setUpClass(cls):
        from calmjs import dist as calmjs_dist
        from calmjs.registry import _inst as root_registry
        cls.dist_dir = tempfile.mkdtemp()
        results = utils.generate_integration_environment(cls.dist_dir)
        working_set, registry = results
        cls.registry_name = registry.registry_name
        root_registry.records[cls.registry_name] = registry
        cls.root_working_set, calmjs_dist.default_working_set = (
            calmjs_dist.default_working_set, working_set)

    @classmethod
    def tearDownClass(cls):
        from calmjs import dist as calmjs_dist
        from calmjs.registry import _inst as root_registry
        rmtree(cls.dist_dir)
        root_registry.records.pop(cls.registry_name)
        calmjs_dist.default_working_set = cls.root_working_set

    def test_generate_transpile_source_maps_none(self):
        mapping = dist.generate_transpile_source_maps(
            'site', registries=(self.registry_name,), method='none')
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_transpile_source_maps_site_default(self):
        mapping = dist.generate_transpile_source_maps(
            'site', registries=(self.registry_name,))
        self.assertEqual(sorted(mapping.keys()), [
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ])

    def test_generate_transpile_source_maps_service_default(self):
        mapping = dist.generate_transpile_source_maps(
            'service', registries=(self.registry_name,))
        self.assertEqual(sorted(mapping.keys()), [
            'framework/lib', 'service/endpoint', 'service/rpc/lib',
        ])

    def test_generate_transpile_source_maps_service_top(self):
        mapping = dist.generate_transpile_source_maps(
            'service', registries=(self.registry_name,), method='top')
        self.assertEqual(sorted(mapping.keys()), [
            'service/endpoint', 'service/rpc/lib',
        ])

    def test_generate_bundled_source_maps_none(self):
        mapping = dist.generate_bundled_source_maps('site', method='none')
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_bundled_source_maps_bad_dir(self):
        bad_dir = utils.mkdtemp(self)
        mapping = dist.generate_bundled_source_maps('service', bad_dir)
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_bundled_source_maps_site_default(self):
        mapping = dist.generate_bundled_source_maps('site', self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), ['jquery', 'underscore'])
        self.assertTrue(mapping['jquery'].endswith(
            'node_modules/jquery/dist/jquery.js'))
        self.assertTrue(mapping['underscore'].endswith(
            'node_modules/underscore/underscore.js'))

    def test_generate_bundled_source_maps_default(self):
        mapping = dist.generate_bundled_source_maps('framework', self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn('underscore/underscore-min.js', mapping['underscore'])
        mapping = dist.generate_bundled_source_maps('service', self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn('underscore/underscore.js', mapping['underscore'])

    def test_generate_bundled_source_maps_top(self):
        mapping = dist.generate_bundled_source_maps(
            'service', self.dist_dir, method='top')
        self.assertEqual(sorted(mapping.keys()), ['underscore'])
        self.assertIn('underscore/underscore.js', mapping['underscore'])
