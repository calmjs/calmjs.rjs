# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import os
import tempfile
from os import makedirs
from os.path import exists
from os.path import join
from shutil import rmtree

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.npm import get_npm_version
from calmjs.cli import node

from calmjs.rjs import toolchain
from calmjs.rjs import cli

from calmjs.testing import utils


def skip_full_toolchain_test():  # pragma: no cover
    if get_npm_version() is None:
        return (True, 'npm not available')
    if os.environ.get('SKIP_FULL'):
        return (True, 'skipping due to SKIP_FULL environment variable')
    return (False, '')


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

        # For the duration of this test, we will operate in this tmpdir
        # for the node_modules that will be installed shortly.
        os.chdir(cls._cls_tmpdir)

        npm = Driver()
        # avoid pulling in any of the devDependencies as these are only
        # capabilities test.
        npm.npm_install('calmjs.rjs', env={'NODE_ENV': 'production'})

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

        # This is done last, because the integration harness will stub
        # out the root distribution which will break the real setup.
        utils.setup_class_integration_environment(cls)

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
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
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        # verify that the bundle works with node
        stdout, stderr = node(
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
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        stdout, stderr = node(
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

    def test_cli_make_spec(self):
        spec = cli.make_spec('site', source_registries=(self.registry_name,))
        self.assertEqual(spec['bundle_export_path'], 'site.js')

    def test_cli_compile_all_site(self):
        # Set up the transpiler using the testcase's working directory
        # which has the r.js binary installed.
        cli.default_toolchain.setup_transpiler()

        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Finally, install dependencies for site in the new directory
        npm = Driver()
        # of course, no devDependencies.
        npm.npm_install('site', env={'NODE_ENV': 'production'})

        # Trigger the compile using the module level compile function
        spec = cli.compile_all('site', source_registries=(self.registry_name,))
        self.assertEqual(
            spec['bundle_export_path'], join(working_dir, 'site.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._cls_tmpdir)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            'require("%s");\n'
            'var datepicker = requirejs("widget/datepicker");\n'
            'console.log(datepicker.DatePickerWidget);\n' % (
                spec['bundle_export_path'],
            )
        )

        self.assertEqual(stdout, 'widget.datepicker.DatePickerWidget\n')

    def test_cli_compile_all_service(self):
        # Set up the transpiler using the testcase's working directory
        # which has the r.js binary installed.
        cli.default_toolchain.setup_transpiler()

        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Trigger the compile using the module level compile function,
        # but without bundling
        spec = cli.compile_all(
            'service', source_registries=(self.registry_name,),
            bundled_map_method='none',
        )
        self.assertEqual(
            spec['bundle_export_path'], join(working_dir, 'service.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._cls_tmpdir)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            'require("%s");\n'
            'var rpclib = requirejs("service/rpc/lib");\n'
            'console.log(rpclib.Library);\n' % (
                spec['bundle_export_path'],
            )
        )

        self.assertEqual(stdout, 'service.rpc.lib.Library\n')
