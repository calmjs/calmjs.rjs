# -*- coding: utf-8 -*-
import unittest
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
        utils.setup_class_integration_environment(cls)

    @classmethod
    def tearDownClass(cls):
        utils.teardown_class_integration_environment(cls)

    def test_generate_transpile_source_maps_none(self):
        mapping = dist.generate_transpile_source_maps(
            ['site'], registries=(self.registry_name,), method='none')
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_transpile_source_maps_site_default(self):
        mapping = dist.generate_transpile_source_maps(
            ['site'], registries=(self.registry_name,))
        self.assertEqual(sorted(mapping.keys()), [
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ])

    def test_generate_transpile_source_maps_site_explicit(self):
        mapping = dist.generate_transpile_source_maps(
            ['site'], registries=(self.registry_name,), method='explicit')
        # it doesn't remove this, but only mark it as empty as the
        # underlying tool will fail otherwise if any require statements
        # having that as its argument will result in r.js failing to do
        # anything.
        self.assertEqual(sorted(mapping.keys()), [
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ])

        self.assertEqual(sorted(
            [k for k, v in mapping.items() if v == 'empty:']
        ), [
            'forms/ui', 'framework/lib', 'widget/core', 'widget/datepicker',
            'widget/richedit',
        ])

    def test_generate_transpile_source_maps_service_default(self):
        mapping = dist.generate_transpile_source_maps(
            ['service'], registries=(self.registry_name,))
        self.assertEqual(sorted(mapping.keys()), [
            'framework/lib', 'service/endpoint', 'service/rpc/lib',
        ])

    def test_generate_transpile_source_maps_service_explicit(self):
        mapping = dist.generate_transpile_source_maps(
            ['service'], registries=(self.registry_name,), method='explicit')
        self.assertEqual(sorted(mapping.keys()), [
            'framework/lib', 'service/endpoint', 'service/rpc/lib',
        ])
        self.assertEqual(mapping['framework/lib'], 'empty:')
        self.assertNotEqual(mapping['service/endpoint'], 'empty:')
        self.assertNotEqual(mapping['service/rpc/lib'], 'empty:')

    def test_generate_bundled_source_maps_none(self):
        mapping = dist.generate_bundled_source_maps(
            ['site'], method='none')
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_bundled_source_maps_bad_dir(self):
        bad_dir = utils.mkdtemp(self)
        mapping = dist.generate_bundled_source_maps(
            ['service'], bad_dir)
        self.assertEqual(sorted(mapping.keys()), [])

    def test_generate_bundled_source_maps_site_default(self):
        mapping = dist.generate_bundled_source_maps(
            ['site'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), ['jquery', 'underscore'])
        self.assertTrue(mapping['jquery'].endswith(
            'fake_modules/jquery/dist/jquery.js'))
        self.assertTrue(mapping['underscore'].endswith(
            'fake_modules/underscore/underscore.js'))

    def test_generate_bundled_source_maps_default(self):
        mapping = dist.generate_bundled_source_maps(
            ['framework'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn('underscore/underscore-min.js', mapping['underscore'])
        mapping = dist.generate_bundled_source_maps(
            ['service'], self.dist_dir)
        self.assertEqual(sorted(mapping.keys()), [
            'jquery', 'underscore',
        ])
        self.assertIn('underscore/underscore.js', mapping['underscore'])
        self.assertIn('jquery', mapping['jquery'])

    def test_generate_bundled_source_maps_service_explicit(self):
        mapping = dist.generate_bundled_source_maps(
            ['service'], self.dist_dir, method='explicit')
        self.assertEqual(sorted(mapping.keys()), ['underscore'])
        self.assertIn('underscore/underscore.js', mapping['underscore'])

    def test_generate_bundled_source_maps_service_empty(self):
        mapping = dist.generate_bundled_source_maps(
            ['service'], self.dist_dir, method='empty')
        # Note that this ends up including all it sparents
        self.assertEqual(mapping, {
            'jquery': 'empty:',
            'underscore': 'empty:',
        })

    def test_generate_bundled_source_maps_site_empty(self):
        # This one declares exact, should still work.
        mapping = dist.generate_bundled_source_maps(
            ['site'], self.dist_dir, method='empty')
        self.assertEqual(sorted(mapping.keys()), ['jquery', 'underscore'])
        self.assertEqual(mapping['jquery'], 'empty:')
        self.assertEqual(mapping['underscore'], 'empty:')
