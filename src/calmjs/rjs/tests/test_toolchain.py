# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
import tempfile
from os import makedirs
from os.path import exists
from os.path import join
from shutil import rmtree

from io import StringIO

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.npm import get_npm_version
from calmjs.npm import npm_bin
from calmjs import cli

from calmjs.rjs import toolchain

from calmjs.testing import utils


def skip_full_toolchain_test():  # pragma: no cover
    if get_npm_version() is None:
        return (True, 'npm not available')
    if os.environ.get('SKIP_FULL'):
        return (True, 'skipping due to SKIP_FULL environment variable')
    return (False, '')


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


@unittest.skipIf(get_npm_version() is None, "npm is unavailable")
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

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

        spec = Spec(
            # this is not written
            bundle_export_path=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            compiled_paths={},
            bundled_paths={},
            module_names=[],
        )

        rjs = toolchain.RJSToolchain()
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
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

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

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
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
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
            'example/module': '/path/to/src/example/module',
            'bundled_pkg': '/path/to/bundled/index',
        })
        self.assertEqual(config_js['include'], [
            'example/module',
            'bundled_pkg',
        ])


@unittest.skipIf(*skip_full_toolchain_test())
class ToolchainIntegrationTestCase(unittest.TestCase):
    """
    Test out the full toolchain, involving requirejs completely.
    """

    # Ensure that requirejs is properly installed through the calmjs
    # framework and specification for this package.  This environment
    # will be reused for the duration for this test.

    @classmethod
    def setUpClass(cls):
        # nosetest will still execute setUpClass, so the test condition
        # will need to be checked here also.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        cls._cwd = os.getcwd()
        cls._cls_tmpdir = tempfile.mkdtemp()
        os.chdir(cls._cls_tmpdir)
        # avoid pulling in any of the devDependencies as these are only
        # capabilities test.
        npm = Driver()
        npm.npm_install('calmjs.rjs', env={'NODE_ENV': 'production'})
        # TODO figure out a better way to derive this.
        cls.rjs_bin = join(npm_bin(npm), toolchain.RJSToolchain.rjs_bin)
        cls._srcdir = tempfile.mkdtemp()
        cls._ep_root = join(cls._srcdir, 'example', 'package')
        makedirs(cls._ep_root)

        math_js = join(cls._ep_root, 'math.js')
        with open(math_js, 'w') as fd:
            fd.write(
                '"use strict";\n'
                '\n'
                'exports.add = function(x, y) {\n'
                '    return x + y;\n'
                '};\n'
                '\n'
                'exports.mul = function(x, y) {\n'
                '    return x * y;\n'
                '};\n'
            )

        bad_js = join(cls._ep_root, 'bad.js')
        with open(bad_js, 'w') as fd:
            fd.write(
                '"use strict";\n'
                '\n'
                '\n'
                '\n'
                'var die = function() {\n'
                '    return notdefinedsymbol;\n'
                '};\n'
                '\n'
                'exports.die = die;\n'
            )

        # TODO derive this (line, col) from the above
        cls._bad_notdefinedsymbol = (6, 12)

        main_js = join(cls._ep_root, 'main.js')
        with open(main_js, 'w') as fd:
            fd.write(
                '"use strict";\n'
                '\n'
                'var math = require("example/package/math");\n'
                'var bad = require("example/package/bad");\n'
                '\n'
                'var main = function(trigger) {\n'
                '    console.log(math.add(1, 1));\n'
                '    console.log(math.mul(2, 2));\n'
                '    if (trigger === true) {\n'
                '        bad.die();\n'
                '    }\n'
                '};\n'
                '\n'
                'exports.main = main;\n'
            )

        # JavaScript import/module names to filesystem path.
        # Normally, these are supplied through the calmjs setuptools
        # integration framework.
        cls._example_package_map = {
            'example/package/math': math_js,
            'example/package/bad': bad_js,
            'example/package/main': main_js,
        }

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        os.chdir(cls._cwd)
        rmtree(cls._cls_tmpdir)
        rmtree(cls._srcdir)

    def test_build_bundle_standard(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        bundled_source_map = {}
        bundle_export_path = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundled_source_map=bundled_source_map,
            bundle_export_path=bundle_export_path,
            build_dir=build_dir,
        )
        spec[rjs.rjs_bin_key] = self.rjs_bin
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        # verify that the bundle works with node
        stdout, stderr = cli.node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            'require("%s");\n'
            'var main = requirejs("example/package/main");\n'
            'main.main();\n' % (
                bundle_export_path,
            )
        )

        self.assertEqual(stdout, '2\n4\n')

    def test_build_bundle_no_indent(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        bundled_source_map = {}
        bundle_export_path = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundled_source_map=bundled_source_map,
            bundle_export_path=bundle_export_path,
            build_dir=build_dir,
            transpile_no_indent=True,
        )
        spec[rjs.rjs_bin_key] = self.rjs_bin
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        stdout, stderr = cli.node(
            'var requirejs = require("requirejs");\n'
            'var config = require("%s");\n'
            'var main = requirejs("example/package/main");\n'
            'main.main(true);\n' % (
                spec['requirejs_config_js'],
            )
        )
        self.assertEqual(stdout, '2\n4\n')
        self.assertIn(
            'example/package/bad.js:%d:%d' % self._bad_notdefinedsymbol,
            stderr
        )
