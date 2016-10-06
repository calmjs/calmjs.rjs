# -*- coding: utf-8 -*-
import unittest

from calmjs.toolchain import Spec

from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import compile_all


class CliTestCase(unittest.TestCase):
    """
    Test mostly basic implementation, most of the core test will be done
    in the toolchain and/or the integration tests.
    """

    def test_create_spec_empty(self):
        spec = create_spec([])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.export.js')
        self.assertEqual(spec['calmjs_module_registry_names'], [])

    def test_create_spec_with_calmjs_rjs(self):
        spec = create_spec(['calmjs.rjs'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])

    def test_toolchain_empty(self):
        # dict works well enough as a null toolchain
        spec = compile_all([], toolchain=dict)
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.rjs.export.js')

    def test_toolchain_transpile_empty(self):
        # dict works well enough as a null toolchain
        spec = compile_all([], toolchain=dict, transpile_no_indent=True)
        self.assertTrue(isinstance(spec, Spec))
        self.assertTrue(spec['transpile_no_indent'])
