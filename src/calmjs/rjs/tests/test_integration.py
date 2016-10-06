# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import os
import re
import sys
import tempfile
from os import makedirs
from os.path import exists
from os.path import join
from os.path import realpath
from shutil import rmtree
from shutil import copytree

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.npm import get_npm_version
from calmjs.cli import node
from calmjs import runtime
from calmjs.registry import get as get_registry
from calmjs.utils import finalize_env
from calmjs.utils import pretty_logging

from calmjs.rjs import toolchain
from calmjs.rjs import cli
from calmjs.rjs.registry import LoaderPlugin

from calmjs.testing import utils
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet
from calmjs.rjs.testing import env


def skip_full_toolchain_test():  # pragma: no cover
    if get_npm_version() is None:
        return (True, 'npm not available')
    if os.environ.get('SKIP_FULL'):
        return (True, 'skipping due to SKIP_FULL environment variable')
    return (False, '')


def run_node(src, *requires):
    # cross platform node runner with require paths.
    # escape backslashes in require paths.
    return node(src % ('\n'.join(
        'require("%s");' % r.replace('\\', '\\\\') for r in requires
    )))


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
        from calmjs import dist as calmjs_dist
        # nosetest will still execute setUpClass, so the test condition
        # will need to be checked here also.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        cls._cwd = os.getcwd()
        cls._node_root = cls._cls_tmpdir = tempfile.mkdtemp()

        test_env = os.environ.get('CALMJS_RJS_TEST_ENV')
        if not test_env:
            npm = Driver(working_dir=cls._cls_tmpdir)
            npm.npm_install('calmjs.rjs', env=finalize_env(env))
            # Save this as the env_path for RJSToolchain instance.  The
            # reason this is done here rather than using setup_transpiler
            # method is purely because under environments that have the
            # standard node_modules/.bin part of the PATH, it never gets
            # set, and then if the test changes the working directory, it
            # will then not be able to find the runtime needed.
            cls._env_path = join(cls._cls_tmpdir, 'node_modules', '.bin')
        else:  # pragma: no cover
            # This is for static test environment for development, not
            # generally suitable for repeatable tests
            cls._node_root = realpath(test_env)
            cls._env_path = join(cls._node_root, 'node_modules', '.bin')

        # For the duration of this test, operate in the tmpdir where the
        # node_modules are available.
        os.chdir(cls._node_root)

        # This is done after the above, as the setup of the following
        # integration harness will stub out the root distribution which
        # will break the installation of real tools.
        utils.setup_class_integration_environment(cls)

        # cls.dist_dir created by setup_class_integration_environment
        cls._ep_root = join(cls.dist_dir, 'example', 'package')
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

        # custom loader
        loader_js = join(cls._ep_root, 'loader.js')
        with open(loader_js, 'w') as fd:
            fd.write(
                # pulled from requirejs.org's plugin documentation
                'exports.load = function (name, req, onload, config) {\n'
                '    req([name], function (value) {\n'
                '        onload(value);\n'
                '    });\n'
                '}\n'
            )

        cls._example_package_loader = {
            'example/package/loader': loader_js,
        }

        # other data
        data_js = join(cls._ep_root, 'data.js')
        with open(data_js, 'w') as fd:
            fd.write(
                '(function() { define({"results": {"item_count": 0}})}());')

        cls._example_package_data = {
            'example/package/loader!example/package/data.js': data_js,
        }

        # also add a proper mock distribution for this.
        utils.make_dummy_dist(None, (
            ('requires.txt', ''),
            ('entry_points.txt', (
                '[%s]\n'
                'example.package = example.package' % cls.registry_name
            )),
        ), 'example.package', '1.0', working_dir=cls.dist_dir)
        # readd it again
        calmjs_dist.default_working_set.add_entry(cls.dist_dir)
        # TODO produce package_module_map

        registry = get_registry(cls.registry_name)
        record = registry.records['example.package'] = {}
        record.update(cls._example_package_map)
        registry.package_module_map['example.package'] = ['example.package']

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
        os.chdir(cls._cwd)
        rmtree(cls._cls_tmpdir)

    def setUp(self):
        # Set up the transpiler using env_path assigned in setUpClass,
        # which installed r.js to ensure the tests will find this.
        cli.default_toolchain.env_path = self._env_path

    def tearDown(self):
        # As the manipulation is done, should set this back to its
        # default state.
        cli.default_toolchain.env_path = None

    def test_build_bundle_standard(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        bundle_source_map = {}
        bundle_export_path = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            bundle_export_path=bundle_export_path,
            build_dir=build_dir,
        )
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        # verify that the bundle works with node
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var main = requirejs("example/package/main");\n'
            'main.main();\n',
            bundle_export_path,
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '2\n4\n')

    def test_build_bundle_no_indent(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        bundle_source_map = {}
        bundle_export_path = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            bundle_export_path=bundle_export_path,
            build_dir=build_dir,
            transpile_no_indent=True,
        )
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            '%s\n'
            'var main = requirejs("example/package/main");\n'
            'main.main(true);\n',
            spec['requirejs_config_js'],
        )
        self.assertIn(
            join('example', 'package', 'bad.js') + ':%d:%d' % (
                self._bad_notdefinedsymbol
            ),
            stderr
        )
        self.assertEqual(stdout, '2\n4\n')

    def test_build_bundle_with_data(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        # include custom loader and data
        transpile_source_map.update(self._example_package_loader)
        bundle_source_map = {}
        bundle_export_path = join(bundle_dir, 'example.package.js')
        requirejs_plugins = {
            'example/package/loader': self._example_package_data
        }

        custom_registry = LoaderPlugin('custom', _working_set=WorkingSet({
            'custom': ['example/package/loader = calmjs.rjs.plugin:text']
        }))
        rjs = toolchain.RJSToolchain()
        rjs.loader_plugin_registry = custom_registry
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            requirejs_plugins=requirejs_plugins,
            bundle_export_path=bundle_export_path,
            build_dir=build_dir,
        )
        rjs(spec)

        self.assertTrue(exists(bundle_export_path))

        # verify that the bundle works with node
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var result = requirejs(\n'
            '    "example/package/loader!example/package/data.js");\n'
            'process.stdout.write("" + result.results.item_count);\n',
            bundle_export_path,
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '0')

    def test_cli_create_spec(self):
        with pretty_logging(stream=StringIO()):
            spec = cli.create_spec(
                ['site'], source_registries=(self.registry_name,))
        self.assertEqual(spec['bundle_export_path'], 'site.js')

    def test_cli_compile_all_site(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Finally, install dependencies for site in the new directory
        # normally this might be done
        # npm = Driver()
        # npm.npm_install('site', env={'NODE_ENV': 'production'})
        # However, since we have our set of fake_modules, just install
        # by copying the fake_modules dir from dist_dir into the current
        # directory.

        copytree(
            join(self.dist_dir, 'fake_modules'),
            join(working_dir, 'fake_modules'),
        )

        # Trigger the compile using the module level compile function
        spec = cli.compile_all(
            ['site'], source_registries=(self.registry_name,))
        self.assertEqual(
            spec['bundle_export_path'], join(working_dir, 'site.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._node_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var datepicker = requirejs("widget/datepicker");\n'
            'console.log(datepicker.DatePickerWidget);\n',
            spec['bundle_export_path'],
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'widget.datepicker.DatePickerWidget\n')

    def test_cli_compile_all_service(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Trigger the compile using the module level compile function,
        # but without bundling
        spec = cli.compile_all(
            ['service'], source_registries=(self.registry_name,),
            bundle_map_method='none',
        )
        self.assertEqual(
            spec['bundle_export_path'], join(working_dir, 'service.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._node_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var rpclib = requirejs("service/rpc/lib");\n'
            'console.log(rpclib.Library);\n',
            spec['bundle_export_path'],
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

    def test_cli_compile_explicit_service(self):
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Trigger the compile using the module level compile function,
        # but without bundling
        spec = cli.compile_all(
            ['service'], source_registries=(self.registry_name,),
            bundle_map_method='none', source_map_method='explicit',
        )
        service_js = join(working_dir, 'service.js')
        self.assertEqual(spec['bundle_export_path'], service_js)

        with open(service_js) as fd:
            self.assertIn('service/rpc/lib', fd.read())

        # build its parent js separately, too
        spec = cli.compile_all(
            ['framework'], source_registries=(self.registry_name,),
            bundle_map_method='none', source_map_method='explicit',
        )
        framework_js = join(working_dir, 'framework.js')
        self.assertEqual(spec['bundle_export_path'], framework_js)

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._node_root)

        # The execution should then work as expected if we loaded both
        # bundles.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var rpclib = requirejs("service/rpc/lib");\n'
            'console.log(rpclib.Library);\n',
            framework_js,
            service_js,
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

    def setup_runtime_main_env(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        target_dir = utils.mkdtemp(self)
        target_file = join(target_dir, 'bundle.js')

        # invoke installation of "fake_modules"
        os.chdir(target_dir)
        copytree(
            join(self.dist_dir, 'fake_modules'),
            join(target_dir, 'fake_modules'),
        )

        return target_dir, target_file

    def test_runtime_cli_compile_all_service(self):
        target_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'service', 'site',
                '--export-filename=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._node_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var lib = requirejs("framework/lib");\n'
            'console.log(lib.Core);\n'
            'var datepicker = requirejs("widget/datepicker");\n'
            'console.log(datepicker.DatePickerWidget);\n'
            'var rpclib = requirejs("service/rpc/lib");\n'
            'console.log(rpclib.Library);\n'
            'var jquery = requirejs("jquery");\n'
            'console.log(jquery);\n'
            'var underscore = requirejs("underscore");\n'
            'console.log(underscore);\n'
            '',
            target_file
        )

        self.assertEqual(stderr, '')
        # note the names of the bundled files
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'service.rpc.lib.Library\n'
            'jquery/dist/jquery.js\n'
            'underscore/underscore.js\n'
        ))

    def test_runtime_cli_compile_framework_simple_invocation(self):
        target_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'framework',
                '--export-filename=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._node_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var lib = requirejs("framework/lib");\n'
            'console.log(lib.Core);\n'
            '',
            target_file
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
        ))

    def test_runtime_cli_compile_explicit_site(self):
        target_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'site',
                '--source-map-method=explicit',
                '--bundle-map-method=none',
                '--export-filename=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with open(target_file) as fd:
            contents = fd.read()

        # Since the package has no sources, and we disabled bundling of
        # sources (none works here because no code to automatically get
        # r.js to look for them), it should generate an empty bundle.
        self.assertEqual(contents, '(function () {}());')

    def test_runtime_cli_compile_explicit_registry_site(self):
        utils.stub_stdouts(self)
        target_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'site',
                '--source-registry-method=explicit',
                '--export-filename=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with open(target_file) as fd:
            contents = fd.read()

        # As the registry is NOT declared for that package, it should
        # result in nothing.
        self.assertNotIn('framework/lib', contents)
        self.assertIn(
            'no calmjs module registry declarations found for packages',
            sys.stderr.getvalue(),
        )
        self.assertIn("'site'", sys.stderr.getvalue())
        self.assertIn(
            "using acquisition method 'explicit'", sys.stderr.getvalue())

    def test_runtime_cli_bundle_method_empty(self):
        utils.stub_stdouts(self)
        target_dir, target_file = self.setup_runtime_main_env()
        build_dir = utils.mkdtemp(self)
        widget_slim_js = join(target_dir, 'widget_slim.js')
        os.chdir(target_dir)
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=empty',
                '--export-filename=' + widget_slim_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are not copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertFalse(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_bundle_method_standard(self):
        target_dir, target_file = self.setup_runtime_main_env()
        build_dir = utils.mkdtemp(self)
        widget_js = join(target_dir, 'widget_standard.js')
        os.chdir(target_dir)
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=all',
                '--export-filename=' + widget_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are copied
        self.assertTrue(exists(join(build_dir, 'underscore.js')))
        # even jquery.min.js is used, it's copied like this due to how
        # modules are renamed.
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_bundle_method_explicit(self):
        utils.stub_stdouts(self)
        target_dir, target_file = self.setup_runtime_main_env()
        build_dir = utils.mkdtemp(self)
        widget_js = join(target_dir, 'widget_explicit.js')
        os.chdir(target_dir)
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=explicit',
                '--export-filename=' + widget_js,
            ])
        # as the explicit option only pulled dependencies from just
        # this file, the process does not actually complete
        self.assertNotEqual(e.exception.args[0], 0)
        # ensure that the explicitly defined bundled files are copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_compile_explicit_service_framework_widget(self):
        def run_node_with_require(*requires):
            os.chdir(self._node_root)
            return run_node(
                'var requirejs = require("requirejs");\n'
                'var define = requirejs.define;\n'
                '%s\n'
                'var lib = requirejs("framework/lib");\n'
                'console.log(lib.Core);\n'
                'var datepicker = requirejs("widget/datepicker");\n'
                'console.log(datepicker.DatePickerWidget);\n'
                'var jquery = requirejs("jquery");\n'
                'console.log(jquery);\n'
                'var underscore = requirejs("underscore");\n'
                'console.log(underscore);\n',
                *requires
            )

        def runtime_main(args, error_code=0):
            # Invoke the thing through the main runtime
            os.chdir(target_dir)
            with self.assertRaises(SystemExit) as e:
                runtime.main(args)
            self.assertEqual(e.exception.args[0], error_code)

        target_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        runtime_main([
            'rjs', 'framework', 'forms', 'service',
            '--source-map-method=explicit',
            '--export-filename=' + target_file,
            '--source-registry=' + self.registry_name,
        ])
        self.assertTrue(exists(target_file))

        # Try running it anyway with widget missing...
        stdout, stderr = run_node_with_require(target_file)
        # This naturally will not work, so the missing module will be in
        # the error
        self.assertIn('widget', stderr)

        # try again, after building the missing widget bundle.
        os.chdir(target_dir)
        widget_js = join(target_dir, 'widget.js')
        runtime_main([
            'rjs', 'widget',
            '--source-map-method=explicit',
            '--export-filename=' + widget_js,
            '--source-registry=' + self.registry_name,
        ])

        # The execution should now work if the widget bundle is loaded
        # first, and output should be as expected.
        stdout, stderr = run_node_with_require(widget_js, target_file)
        self.assertEqual(stderr, '')
        # note the names of the bundled files
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'jquery/dist/jquery.min.js\n'  # from widget
            # widget_js contains this because the package 'framework'
            # declared the follow location.
            'underscore/underscore-min.js\n'
        ))

        # try again, this time the widget will NOT have underscore built
        # in as the bundles will be emptied out - however we need the
        # information in framework as the 'widget' package did NOT
        # declare the extras_calmjs for underscore so compilation will
        # fail otherwise.
        widget_slim_js = join(target_dir, 'widget_slim.js')
        runtime_main([
            'rjs', 'widget',
            '--source-map-method=all',  # using all
            '--bundle-map-method=empty',
            '--export-filename=' + widget_slim_js,
            '--source-registry=' + self.registry_name,
        ])

        # The execution should now work if the widget bundle is loaded
        # first, and output should be as expected.  This time the
        # bundles are loaded in reversed order.
        stdout, stderr = run_node_with_require(target_file, widget_slim_js)
        # Output should be as expected
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'jquery/dist/jquery.min.js\n'  # from widget
            # this time, the second bundle will supply this, which has
            # the one originally sourced from the location declared by
            # the 'service' package.
            'underscore/underscore.js\n'
        ))

    def test_runtime_cli_compile_no_indent(self):
        utils.remember_cwd(self)
        target_dir = utils.mkdtemp(self)
        target_file = join(target_dir, 'bundle.js')

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'example.package',
                '--transpile-no-indent',
                '--export-filename=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var main = requirejs("example/package/main");\n'
            'main.main(true);\n',
            target_file,
        )
        # The test should really test the files in the build directory,
        # but if we are doing this as an integration test, the bundle
        # should also at least maintain the same column when ran...
        patt = re.compile('%s:[0-9]+:%d' % (
            target_file.replace('\\', '\\\\'), self._bad_notdefinedsymbol[-1]))
        self.assertTrue(patt.search(stderr))
        self.assertEqual(stdout, '2\n4\n')

        # ... or, just see that the bad line is there, too.
        with open(target_file) as fd:
            bundle_source = fd.read()
        self.assertIn('\nvar die = function() {\n', bundle_source)
