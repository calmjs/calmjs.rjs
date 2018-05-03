# -*- coding: utf-8 -*-
import os
from os.path import join
import unittest

from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging
from calmjs.rjs.registry import RJS_LOADER_PLUGIN_REGISTRY_NAME

from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import compile_all

from calmjs.testing.mocks import StringIO
from calmjs.testing.utils import mkdtemp
from calmjs.testing.utils import remember_cwd


class CliTestCase(unittest.TestCase):
    """
    Test mostly basic implementation, most of the core test will be done
    in the toolchain and/or the integration tests.
    """

    def setUp(self):
        self.cwd = mkdtemp(self)
        remember_cwd(self)
        os.chdir(self.cwd)

    def test_create_spec_empty(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([])

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], join(
            self.cwd, 'calmjs.rjs.export.js'))
        self.assertEqual(spec['calmjs_module_registry_names'], [])
        self.assertEqual(
            RJS_LOADER_PLUGIN_REGISTRY_NAME,
            spec['calmjs_loaderplugin_registry'].registry_name,
        )

    def test_create_spec_with_calmjs_rjs(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.rjs'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], join(
            self.cwd, 'calmjs.rjs.js'))
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.rjs'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "sourcepaths", log,
        )

    def test_create_spec_with_calmjs_rjs_manual_source(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.rjs'], source_registries=['calmjs.module.tests'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], join(
            self.cwd, 'calmjs.rjs.js'))
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module.tests'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.rjs'])

        log = stream.getvalue()
        self.assertIn(
            "using manually specified registries ['calmjs.module.tests'] for "
            "sourcepaths", log,
        )

    def test_create_spec_with_calmjs_rjs_manual_target(self):
        with pretty_logging(stream=StringIO()):
            spec = create_spec(['calmjs.rjs'], export_target='foo.js')
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'foo.js')

    def test_toolchain_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], join(
            self.cwd, 'calmjs.rjs.export.js'))

    def test_toolchain_transpile_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict, transpile_no_indent=True)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertTrue(spec['transpile_no_indent'])
