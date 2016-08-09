# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
import tempfile
from os.path import dirname
from os.path import exists
from os.path import join
from shutil import rmtree

from io import StringIO

from calmjs.toolchain import Spec
from calmjs import npm

from calmjs.rjs import toolchain

from calmjs.testing import utils


class TranspilerTestCase(unittest.TestCase):
    """
    Test various "transpilers"  in the toolchain module
    """

    def test_transpile_generic_to_umd_node_amd_compat_rjs_basic(self):
        source = StringIO(
            'var dummy = function () {};\n'
            'exports.dummy = dummy;\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(source, target)

        self.assertEqual(target.getvalue().splitlines()[2:7], [
            '        var exports = {};',
            '        var dummy = function () {};',
            '        exports.dummy = dummy;',
            '        ',
            '        return exports;',
        ])

    def test_transpile_generic_to_umd_node_amd_compat_rjs_strict(self):
        source = StringIO(
            '"use strict";\n'
            'var dummy = function () {};\n'
            'exports.dummy = dummy;\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(source, target)

        self.assertEqual(target.getvalue().splitlines()[2:8], [
            '        "use strict";',
            '        var exports = {};',
            '        var dummy = function () {};',
            '        exports.dummy = dummy;',
            '        ',
            '        return exports;',
        ])


@unittest.skipIf(npm.get_npm_version() is None, "npm is unavailable")
class ToolchainUnitTestCase(unittest.TestCase):
    """
    Just testing out the toolchain units.
    """

    def test_prepare_no_node(self):
        utils.stub_os_environ(self)
        os.environ['PATH'] = ''
        rjs = toolchain.RJSToolchain()
        spec = Spec()
        with self.assertRaises(RuntimeError):
            rjs.prepare(spec)

    def test_prepare_failure_not_found(self):
        tmpdir = utils.mkdtemp(self)
        utils.remember_cwd(self)
        # must go to a directory where r.js is guaranteed to not be
        # available through node.
        os.chdir(tmpdir)
        rjs = toolchain.RJSToolchain()
        spec = Spec(build_dir=tmpdir)
        with self.assertRaises(RuntimeError):
            rjs.prepare(spec)

    def test_prepare_failure_bundle_export_path(self):
        tmpdir = utils.mkdtemp(self)
        rjs = toolchain.RJSToolchain()

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

        spec = Spec(build_dir=tmpdir)
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')

        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)
        self.assertEqual(
            str(e.exception), "'bundle_export_path' not found in spec")

        # what can possibly go wrong?
        spec['bundle_export_path'] = join(spec[rjs.rjs_bin_key], 'build.js')

        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)
        self.assertEqual(
            str(e.exception), "'bundle_export_path' will not be writable")

        spec['bundle_export_path'] = join(tmpdir, 'build.js')

        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)
        self.assertEqual(
            str(e.exception), "'bundle_export_path' must not be same as "
            "'build_manifest_path'")

    def test_assemble_null(self):
        tmpdir = utils.mkdtemp(self)

        spec = Spec(
            # this is not written
            bundle_export_path=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            compiled_paths={},
            bundled_paths={},
            module_names=[],
        )

        rjs = toolchain.RJSToolchain()
        rjs.prepare(spec)
        rjs.assemble(spec)

        self.assertTrue(exists(join(tmpdir, 'build.js')))
        self.assertTrue(exists(join(tmpdir, 'config.js')))
