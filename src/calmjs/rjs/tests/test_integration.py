# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
import re
import sys
from os import makedirs
from os.path import exists
from os.path import join
from shutil import copytree

from pkg_resources import get_distribution

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.npm import get_npm_version
from calmjs.cli import node
from calmjs import runtime
from calmjs.registry import get as get_registry
from calmjs.utils import pretty_logging

try:
    from calmjs.dev import karma
except ImportError:  # pragma: no cover
    karma = None

from calmjs.rjs import toolchain
from calmjs.rjs import cli
from calmjs.rjs.registry import LoaderPluginRegistry

from calmjs.testing import utils
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet


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


def cls_setup_rjs_example_package(cls):
    from calmjs import dist as calmjs_dist

    # cls.dist_dir created by setup_class_integration_environment
    cls._ep_root = join(cls.dist_dir, 'example', 'package')
    makedirs(cls._ep_root)

    test_root = join(cls._ep_root, 'tests')
    makedirs(test_root)

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

    test_math_js = join(cls._ep_root, 'tests', 'test_math.js')
    with open(test_math_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var math = require("example/package/math");\n'
            '\n'
            'describe("basic math functions", function() {\n'
            '    it("addition", function() {\n'
            '        expect(math.add(3, 4)).equal(7);\n'
            '        expect(math.add(5, 6)).equal(11);\n'
            '    });\n'
            '\n'
            '    it("multiplication", function() {\n'
            '        expect(math.mul(3, 4)).equal(12);\n'
            '        expect(math.mul(5, 6)).equal(30);\n'
            '    });\n'
            '});\n'
        )

    # map for our one and only test
    cls._example_package_test_map = {
        'example/package/tests/test_math': test_math_js,
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
        'example/package/loader!example/package/data': data_js,
    }

    # also add a proper mock distribution for this.
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('calmjs_module_registry.txt', cls.registry_name),
        ('entry_points.txt', (
            '[%s]\n'
            'example.package = example.package\n'
            '[%s.tests]\n'
            'example.package = example.package.tests\n' % (
                cls.registry_name,
                cls.registry_name,
            )
        )),
    ), 'example.package', '1.0', working_dir=cls.dist_dir)

    # also include the entry_point information for this package
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('entry_points.txt', (
            get_distribution('calmjs.rjs').get_metadata('entry_points.txt')
        )),
    ), 'calmjs.rjs', '0.0', working_dir=cls.dist_dir)

    # re-add it again
    calmjs_dist.default_working_set.add_entry(cls.dist_dir)
    # TODO produce package_module_map

    registry = get_registry(cls.registry_name)
    record = registry.records['example.package'] = {}
    # loader note included
    record.update(cls._example_package_map)
    registry.package_module_map['example.package'] = ['example.package']

    test_registry = get_registry(cls.registry_name + '.tests')
    test_record = test_registry.records['example.package.tests'] = {}
    test_record.update(cls._example_package_test_map)
    test_registry.package_module_map['example.package'] = [
        'example.package.tests']


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

        utils.setup_class_install_environment(
            cls, Driver, ['calmjs.rjs'], production=False)

        # For the duration of this test, operate in the tmpdir where the
        # node_modules are available.
        os.chdir(cls._env_root)

        # This is done after the above, as the setup of the following
        # integration harness will stub out the root distribution which
        # will break the installation of real tools.
        utils.setup_class_integration_environment(cls)
        # also our test data.
        cls_setup_rjs_example_package(cls)

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
        os.chdir(cls._cwd)
        utils.rmtree(cls._cls_tmpdir)

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
        export_target = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            export_target=export_target,
            build_dir=build_dir,
        )
        rjs(spec)

        self.assertTrue(exists(export_target))

        # verify that the bundle works with node
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var main = requirejs("example/package/main");\n'
            'main.main();\n',
            export_target,
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '2\n4\n')

    def test_build_bundle_no_indent(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_source_map = {}
        transpile_source_map.update(self._example_package_map)
        bundle_source_map = {}
        export_target = join(bundle_dir, 'example.package.js')

        rjs = toolchain.RJSToolchain()
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            export_target=export_target,
            build_dir=build_dir,
            transpile_no_indent=True,
        )
        rjs(spec)

        self.assertTrue(exists(export_target))

        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            '%s\n'
            'var main = requirejs("example/package/main");\n'
            'main.main(true);\n',
            spec['node_config_js'],
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
        export_target = join(bundle_dir, 'example.package')
        requirejs_plugins = {
            'example/package/loader': self._example_package_data
        }

        custom_registry = LoaderPluginRegistry(
            'custom', _working_set=WorkingSet({
                'custom': [
                    'example/package/loader = calmjs.rjs.plugin:TextPlugin']})
        )
        rjs = toolchain.RJSToolchain()
        rjs.loader_plugin_registry = custom_registry
        spec = Spec(
            transpile_source_map=transpile_source_map,
            bundle_source_map=bundle_source_map,
            requirejs_plugins=requirejs_plugins,
            export_target=export_target,
            build_dir=build_dir,
        )

        with pretty_logging(stream=StringIO()):
            # to avoid logging the issue of mismatch map to extension
            # to stderr.
            rjs(spec)

        self.assertTrue(exists(export_target))

        # verify that the bundle works with node
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var result = requirejs(\n'
            '    "example/package/loader!example/package/data");\n'
            'process.stdout.write("" + result.results.item_count);\n',
            export_target,
        )

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '0')

    def test_cli_create_spec(self):
        with pretty_logging(stream=StringIO()):
            spec = cli.create_spec(
                ['site'], source_registries=(self.registry_name,))
        self.assertEqual(spec['export_target'], 'site.js')

    def test_cli_compile_all_site(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Finally, install dependencies for site in the new directory
        # normally this might be done
        # npm = Driver()
        # npm.npm_install('site', production=True)
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
            spec['export_target'], join(working_dir, 'site.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var datepicker = requirejs("widget/datepicker");\n'
            'console.log(datepicker.DatePickerWidget);\n',
            spec['export_target'],
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
            spec['export_target'], join(working_dir, 'service.js'))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_node(
            'var requirejs = require("requirejs");\n'
            'var define = requirejs.define;\n'
            '%s\n'
            'var rpclib = requirejs("service/rpc/lib");\n'
            'console.log(rpclib.Library);\n',
            spec['export_target'],
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
        self.assertEqual(spec['export_target'], service_js)

        with open(service_js) as fd:
            self.assertIn('service/rpc/lib', fd.read())

        # build its parent js separately, too
        spec = cli.compile_all(
            ['framework'], source_registries=(self.registry_name,),
            bundle_map_method='none', source_map_method='explicit',
        )
        framework_js = join(working_dir, 'framework.js')
        self.assertEqual(spec['export_target'], framework_js)

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

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

    def test_runtime_cli_help_text(self):
        utils.stub_stdouts(self)
        with self.assertRaises(SystemExit) as e:
            runtime.main(['rjs', '-h'])
        self.assertEqual(e.exception.args[0], 0)
        out = ' '.join(i.strip() for i in sys.stdout.getvalue().splitlines())
        self.assertIn(
            '--export-target EXPORT_TARGET output filename; '
            'defaults to last ${package_name}.js ', out)
        self.assertIn(
            '--working-dir WORKING_DIR the working directory; '
            'for this tool it will be used as the base directory to '
            'find source files declared for bundling; ', out)
        self.assertIn('default is current working directory', out)

    def setup_runtime_main_env(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        current_dir = utils.mkdtemp(self)
        target_file = join(current_dir, 'bundle.js')

        # invoke installation of "fake_modules"
        copytree(
            join(self.dist_dir, 'fake_modules'),
            join(current_dir, 'fake_modules'),
        )

        return current_dir, target_file

    def test_runtime_cli_compile_all_service(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'service', 'site',
                '--export-target=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

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

    def test_runtime_cli_compile_all_service_cwd(self):
        current_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'site',
                '--export-target=' + target_file,
                '--working-dir=' + current_dir,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

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
            'jquery/dist/jquery.js\n'
            'underscore/underscore.js\n'
        ))

    def test_runtime_cli_compile_framework_simple_invocation(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'framework',
                '--export-target=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with requirejs library installed.
        os.chdir(self._env_root)

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
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'site',
                '--source-map-method=explicit',
                '--bundle-map-method=none',
                '--export-target=' + target_file,
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
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'site',
                '--source-registry-method=explicit',
                '--export-target=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with open(target_file) as fd:
            contents = fd.read()

        # As the registry is NOT declared for that package, it should
        # result in nothing.
        self.assertNotIn('framework/lib', contents)
        self.assertIn(
            'no module registry declarations found using packages',
            sys.stderr.getvalue(),
        )
        self.assertIn("'site'", sys.stderr.getvalue())
        self.assertIn(
            "using acquisition method 'explicit'", sys.stderr.getvalue())

    def test_runtime_cli_bundle_method_empty(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_slim_js = join(current_dir, 'widget_slim.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=empty',
                '--export-target=' + widget_slim_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are not copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertFalse(exists(join(build_dir, 'jquery.js')))

        with open(join(build_dir, 'build.js')) as fd:
            # strip off the header and footer
            build_js = json.loads(''.join(fd.readlines()[1:-1]))

        with open(join(build_dir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[4:-10]))

        self.assertEqual(build_js['paths'], {
            'jquery': 'empty:',
            'underscore': 'empty:',
        })
        self.assertEqual(sorted(build_js['include']), [
            'framework/lib',
            'widget/core',
            'widget/datepicker',
            'widget/richedit',
        ])

        self.assertEqual(config_js['paths'], {
            'framework/lib': 'framework/lib.js?',
            'widget/core': 'widget/core.js?',
            'widget/datepicker': 'widget/datepicker.js?',
            'widget/richedit': 'widget/richedit.js?',
        })
        self.assertEqual(config_js['include'], [])

    def test_runtime_cli_bundle_method_force_empty(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_slim_js = join(current_dir, 'widget_slim.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--empty',
                '--source-map-method=all',
                '--bundle-map-method=none',
                '--export-target=' + widget_slim_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are not copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertFalse(exists(join(build_dir, 'jquery.js')))

        with open(join(build_dir, 'build.js')) as fd:
            # strip off the header and footer
            build_js = json.loads(''.join(fd.readlines()[1:-1]))

        with open(join(build_dir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[4:-10]))

        self.assertEqual(build_js['paths'], {
            # this is missing because no sources actually poke into it,
            # whereas the previous test it showed up as extras_calmjs
            # 'jquery': 'empty:',
            'underscore': 'empty:',
        })
        self.assertEqual(sorted(build_js['include']), [
            'framework/lib',
            'widget/core',
            'widget/datepicker',
            'widget/richedit',
        ])

        self.assertEqual(config_js['paths'], {
            'framework/lib': 'framework/lib.js?',
            'widget/core': 'widget/core.js?',
            'widget/datepicker': 'widget/datepicker.js?',
            'widget/richedit': 'widget/richedit.js?',
            # this is picked up by the source analysis when empty option
            # is appied
            'underscore': 'empty:',
        })
        self.assertEqual(config_js['include'], [])

    def test_runtime_cli_bundle_method_standard(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_js = join(current_dir, 'widget_standard.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=all',
                '--export-target=' + widget_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are copied
        self.assertTrue(exists(join(build_dir, 'underscore.js')))
        # even jquery.min.js is used, it's copied like this due to how
        # modules are renamed.
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_bundle_method_explicit(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_js = join(current_dir, 'widget_explicit.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'widget',
                '--build-dir=' + build_dir,
                '--source-map-method=all',
                '--bundle-map-method=explicit',
                '--export-target=' + widget_js,
            ])
        # as the explicit option only pulled dependencies from just
        # this file, the process does not actually complete
        self.assertNotEqual(e.exception.args[0], 0)
        # ensure that the explicitly defined bundled files are copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_compile_explicit_service_framework_widget(self):
        def run_node_with_require(*requires):
            os.chdir(self._env_root)
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
            os.chdir(current_dir)
            with self.assertRaises(SystemExit) as e:
                runtime.main(args)
            self.assertEqual(e.exception.args[0], error_code)

        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # stubbing to check for a _lack_ of error message.
        utils.stub_stdouts(self)

        # Invoke the thing through the main runtime
        runtime_main([
            'rjs', 'framework', 'forms', 'service',
            '--source-map-method=explicit',
            '--export-target=' + target_file,
            '--source-registry=' + self.registry_name,
        ])
        self.assertTrue(exists(target_file))
        # no complaints about missing 'widget/*' modules
        self.assertEqual('', sys.stderr.getvalue())

        # Try running it anyway with widget missing...
        stdout, stderr = run_node_with_require(target_file)
        # This naturally will not work, so the missing module will be in
        # the error
        self.assertIn('widget', stderr)

        # try again, after building the missing widget bundle.
        widget_js = join(current_dir, 'widget.js')
        runtime_main([
            'rjs', 'widget',
            '--source-map-method=explicit',
            '--export-target=' + widget_js,
            '--source-registry=' + self.registry_name,
        ])
        # no complaints about missing 'framework/lib'
        self.assertEqual('', sys.stderr.getvalue())

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
        widget_slim_js = join(current_dir, 'widget_slim.js')
        runtime_main([
            'rjs', 'widget',
            '--source-map-method=all',  # using all
            '--bundle-map-method=empty',
            '--export-target=' + widget_slim_js,
            '--source-registry=' + self.registry_name,
        ])
        # no complaints about missing 'underscores' as bundle empty
        self.assertEqual('', sys.stderr.getvalue())

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

    def test_runtime_cli_method_none_with_empty_various(self):
        # this time, use the empty option
        utils.remember_cwd(self)
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'export_target.js')

        os.chdir(current_dir)
        with self.assertRaises(SystemExit) as e:
            # this should fail
            runtime.main([
                'rjs', 'service', 'site',
                '--bundle-map-method=none',
                '--export-target=' + export_target,
                '--source-registry=' + self.registry_name,
            ])

        self.assertEqual(e.exception.args[0], 1)

        os.chdir(current_dir)
        with self.assertRaises(SystemExit) as e:
            # this time, apply empty, which should automatically patch
            # the configuration
            runtime.main([
                'rjs', 'service', 'site',
                '--empty',
                '--bundle-map-method=none',
                '--export-target=' + export_target,
                '--source-registry=' + self.registry_name,
            ])

        self.assertEqual(e.exception.args[0], 0)

    def test_runtime_cli_compile_no_indent(self):
        utils.remember_cwd(self)
        target_dir = utils.mkdtemp(self)
        target_file = join(target_dir, 'bundle.js')

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'example.package',
                '--transpile-no-indent',
                '--export-target=' + target_file,
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

    def test_runtime_example_package_auto_registry(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'example.package',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))


@unittest.skipIf(karma is None, 'calmjs.dev or its karma module not available')
class KarmaToolchainIntegrationTestCase(unittest.TestCase):
    """
    Test out the karma toolchain, involving requirejs completely along
    with the karma testing framework as defined by calmjs.dev
    """

    @classmethod
    def setUpClass(cls):
        cls._cwd = os.getcwd()
        utils.setup_class_install_environment(
            cls, Driver, ['calmjs.rjs', 'calmjs.dev'], production=False)

        # For the duration of this test, operate in the tmpdir where the
        # node_modules are available.
        os.chdir(cls._env_root)

        # This is done after the above, as the setup of the following
        # integration harness will stub out the root distribution which
        # will break the installation of real tools.
        utils.setup_class_integration_environment(cls)
        # also our test data.
        cls_setup_rjs_example_package(cls)

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
        os.chdir(cls._cwd)
        utils.rmtree(cls._cls_tmpdir)

    def test_karma_test_runner_basic(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'rjs', 'example.package',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

    def test_karma_test_runner_standalone_artifact(self):
        """
        What's the purpose of tests if they can't be executed any time,
        anywhere, against anything?
        """

        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        # first, generate our bundle.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'rjs', 'example.package', '--export-target', export_target])
        self.assertTrue(exists(export_target))

        # leverage the karma run command to run the tests provided by
        # the example.package against the resulting artifact.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'run',
                '--test-package', 'example.package',
                # TODO make this argument optional
                '--test-registry', self.registry_name + '.tests',
                '--artifact', export_target,
                # this is critical
                '--toolchain-package', 'calmjs.rjs',
            ])
        # tests should pass against the resultant bundle
        self.assertEqual(e.exception.args[0], 0)
