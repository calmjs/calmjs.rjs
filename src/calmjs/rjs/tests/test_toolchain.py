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
            '\n'
            'exports.dummy = dummy;\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(source, target)

        self.assertEqual(target.getvalue().splitlines()[2:8], [
            '        var exports = {};',
            '        var dummy = function () {};',
            '',
            '        exports.dummy = dummy;',
            '',
            '        return exports;',
        ])

    def test_transpile_generic_to_umd_node_amd_compat_rjs_strict(self):
        source = StringIO(
            '"use strict";\n'
            'var dummy = function () {};\n'
            '\n'
            'exports.dummy = dummy;\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(source, target)

        self.assertEqual(target.getvalue().splitlines()[2:9], [
            '        "use strict";',
            '        var exports = {};',
            '        var dummy = function () {};',
            '',
            '        exports.dummy = dummy;',
            '',
            '        return exports;',
        ])

    def test_transpile_generic_to_umd_node_amd_compat_rjs_strict_padded(self):
        """
        Show that padding empty lines will simply be used as padding,
        and that the 'use strict' declaration will just be moved down.
        This is to provide an option for developers so that line numbers
        of the "transpiled" code can be mapped directly back to its
        original.
        """

        original = (
            'var dummy = function () {};\n'
            'exports.dummy = dummy;'
        )

        source = StringIO(
            '"use strict";\n'
            '\n'
            '\n'
            '\n' +
            original + '\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(
            source, target, indent=0)

        self.assertEqual(
            '\n'.join(target.getvalue().splitlines()[4:6]), original)

    def test_transpile_generic_to_umd_node_amd_compat_rjs_basic_padded(self):
        """
        Similar as above, but insufficient lines will just result in
        not much happening...
        """

        source = StringIO(
            '\n'
            'var dummy = function () {};\n'
            '\n'
            'exports.dummy = dummy;\n'
        )
        target = StringIO()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(source, target)

        self.assertEqual(target.getvalue().splitlines()[2:8], [
            '        var exports = {};',  # no break after this.
            '        var dummy = function () {};',
            '',
            '        exports.dummy = dummy;',
            '',
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

        with open(join(tmpdir, 'build.js')) as fd:
            # strip off the header and footer
            build_js = json.loads(''.join(fd.readlines()[1:-1]))

        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[4:-10]))

        self.assertEqual(build_js['paths'], {})
        self.assertEqual(build_js['include'], [])

        self.assertEqual(config_js['paths'], {})
        self.assertEqual(config_js['include'], [])

    def test_assemble_compiled(self):
        tmpdir = utils.mkdtemp(self)

        spec = Spec(
            # this is not written
            bundle_export_path=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            compiled_paths={
                'example/module': '/path/to/src/example/module'
            },
            bundled_paths={
                'bundled_pkg': '/path/to/bundled/index'
            },
            module_names=[
                'example/module',
                'bundled_pkg',
            ],
        )

        rjs = toolchain.RJSToolchain()
        rjs.prepare(spec)
        rjs.assemble(spec)

        self.assertTrue(exists(join(tmpdir, 'build.js')))
        self.assertTrue(exists(join(tmpdir, 'config.js')))

        with open(join(tmpdir, 'build.js')) as fd:
            # strip off the header and footer as this is for r.js
            build_js = json.loads(''.join(fd.readlines()[1:-1]))

        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer as this is for r.js
            config_js = json.loads(''.join(fd.readlines()[4:-10]))

        self.assertEqual(build_js['paths'], {
            'example/module': '/path/to/src/example/module',
            'bundled_pkg': '/path/to/bundled/index',
        })
        self.assertEqual(build_js['include'], [
            'example/module',
            'bundled_pkg',
        ])

        self.assertEqual(config_js['paths'], {
            'example/module': 'example/module',
            'bundled_pkg': 'bundled/index',
        })
        self.assertEqual(config_js['include'], [
            'example/module',
            'bundled_pkg',
        ])
