# -*- coding: utf-8 -*-
import unittest

from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging

from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import compile_all

from calmjs.testing.mocks import StringIO


class CliTestCase(unittest.TestCase):
    """
    Test mostly basic implementation, most of the core test will be done
    in the toolchain and/or the integration tests.
    """

    def test_create_spec_empty(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([])

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.export.js')
        self.assertEqual(spec['calmjs_module_registry_names'], [])

    def test_create_spec_with_calmjs_rjs(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.rjs'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.rjs'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "building source map", log,
        )

    def test_create_spec_with_calmjs_rjs_manual_source(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.rjs'], source_registries=['calmjs.module.tests'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module.tests'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.rjs'])

        log = stream.getvalue()
        self.assertIn(
            "using manually specified registries ['calmjs.module.tests'] for "
            "building source map", log,
        )

    def test_toolchain_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.export.js')

    def test_toolchain_transpile_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict, transpile_no_indent=True)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertTrue(spec['transpile_no_indent'])
