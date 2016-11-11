# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
from os.path import exists
from os.path import join

from io import StringIO

from calmjs.toolchain import Spec
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.vlqsm import SourceWriter
from calmjs.npm import get_npm_version
from calmjs.utils import pretty_logging

from calmjs.rjs.ecma import parse
from calmjs.rjs import toolchain

from calmjs.testing import utils
from calmjs.testing import mocks


class SpecUpdateSourceMapTestCase(unittest.TestCase):
    """
    A function for updating the spec with a source map for target keys,
    in such a way that makes it compatible with the base system.
    """

    def test_spec_update_source_map_standard_modules_base(self):
        source_map = {
            'standard/module': 'standard/module',
            'standard.module': 'standard.module',
        }
        spec = {}

        toolchain.spec_update_source_map(spec, source_map, 'source_key')
        self.assertEqual(spec, {
            'source_key': {
                'standard/module': 'standard/module',
                'standard.module': 'standard.module',
            }
        })

    def test_spec_update_source_map_standard_modules_id(self):
        source_map = {
            'standard/module': 'standard/module',
        }
        base_map = {}
        spec = {'source_key': base_map}

        toolchain.spec_update_source_map(spec, source_map, 'source_key')
        self.assertIs(spec['source_key'], base_map)
        self.assertEqual(base_map, {
            'standard/module': 'standard/module',
        })

    def test_spec_update_source_map_plugin_modules(self):
        source_map = {
            'plugin/module!argument': 'some/filesystem/path',
            'text!argument': 'some/text/file.txt',
        }
        spec = {}

        toolchain.spec_update_source_map(spec, source_map, 'source_key')
        self.maxDiff = 123123
        self.assertEqual(spec, {
            'requirejs_plugins': {
                'plugin/module': {
                    'plugin/module!argument': 'some/filesystem/path',
                },
                'text': {
                    'text!argument': 'some/text/file.txt',
                },
            },
            'source_key': {
            },
        })

        toolchain.spec_update_source_map(spec, {
            'text!argument2': 'some/text/file2.txt',
        }, 'source_key')
        self.assertEqual(spec['requirejs_plugins']['text'], {
            'text!argument': 'some/text/file.txt',
            'text!argument2': 'some/text/file2.txt',
        })


class ToolchainBootstrapTestCase(unittest.TestCase):
    """
    Test the bootstrap function
    """

    def test_runtime_name(self):
        # seems redundant, but...
        platform = 'posix'
        self.assertEqual(toolchain.get_rjs_runtime_name(platform), 'r.js')
        platform = 'win32'
        self.assertEqual(toolchain.get_rjs_runtime_name(platform), 'r.js.cmd')


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
        target = SourceWriter(StringIO())
        spec = Spec()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(
            spec, source, target)

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
        target = SourceWriter(StringIO())
        spec = Spec()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(
            spec, source, target)

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

        Naturally, spec will also need to have no indent specified.
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
        target = SourceWriter(StringIO())
        spec = Spec(transpile_no_indent=True)

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(
            spec, source, target)

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
        target = SourceWriter(StringIO())
        spec = Spec()

        toolchain._transpile_generic_to_umd_node_amd_compat_rjs(
            spec, source, target)

        self.assertEqual(target.getvalue().splitlines()[2:8], [
            '        var exports = {};',  # no break after this.
            '        var dummy = function () {};',
            '',
            '        exports.dummy = dummy;',
            '',
            '        return exports;',
        ])

        self.assertEqual(target.mappings[:7], [
            [], [], [], [(8, 0, 1, 0)], [(0, 0, 1, 0)], [(8, 0, 1, 0)], []])

        target_main = SourceWriter(StringIO())
        toolchain._rjs_transpiler(spec, source, target_main)
        self.assertEqual(target.getvalue(), target_main.getvalue())

    def test_transpile_skip_on_amd_newline(self):
        source = StringIO(
            "\n"
            "define(['jquery'], function($) {\n"
            "    'use strict';\n"
            "    return {'testing': {}}\n"
            "});\n"
        )
        target = StringIO()
        spec = Spec()
        toolchain._rjs_transpiler(spec, source, target)
        self.assertEqual(source.getvalue(), target.getvalue())

    def test_transpile_skip_on_amd_strict_top(self):
        source = StringIO(
            "'use strict';\n"
            "define(['jquery'], function($) {\n"
            "    return {'testing': {}}\n"
            "});\n"
        )
        target = StringIO()
        spec = Spec()
        toolchain._rjs_transpiler(spec, source, target)
        self.assertEqual(source.getvalue(), target.getvalue())

    def test_modname_source_target_to_modpath(self):
        rjs = toolchain.RJSToolchain()
        spec = Spec()
        self.assertEqual(rjs.modname_source_target_to_modpath(
            spec,
            'example/module',
            '/tmp/src/example/module', '/tmp/build/example/module'),
            'example/module'
        )
        self.assertEqual(rjs.modname_source_target_to_modpath(
            spec,
            'example/module',
            'empty:', '/tmp/build/example/module'),
            'empty:'
        )

    def test_transpile_modname_source_target_normal(self):
        modname = 'module'
        src_file = join(utils.mkdtemp(self), 'module.js')
        tgt_file = 'module.js'
        tgt_dir = utils.mkdtemp(self)
        spec = Spec(build_dir=tgt_dir)

        with open(src_file, 'w') as fd:
            fd.write('console.log("Hello");')

        rjs = toolchain.RJSToolchain()
        rjs.transpile_modname_source_target(spec, modname, src_file, tgt_file)

        with open(join(tgt_dir, tgt_file)) as fd:
            # The transpiler will mutate it.
            result = fd.read()

        self.assertNotEqual('console.log("Hello");', result)
        self.assertIn('console.log("Hello");', result)

    def test_transpile_modname_source_target_empty(self):
        modname = 'module'
        src_file = 'empty:'
        tgt_dir = utils.mkdtemp(self)
        tgt_file = join(tgt_dir, 'module.js')
        spec = Spec(build_dir=tgt_dir)
        rjs = toolchain.RJSToolchain()
        rjs.transpile_modname_source_target(spec, modname, src_file, tgt_file)
        self.assertFalse(exists(tgt_file))


class ToolchainCompilePluginTestCase(unittest.TestCase):
    """
    Test the compile_plugin method
    """

    def test_toolchain_instance_transpile_skip_on_amd(self):
        source = StringIO(
            "define(['jquery'], function($) {\n"
            "    'use strict';\n"
            "    return {'testing': {}}\n"
            "});\n"
        )
        target = StringIO()
        spec = Spec()
        rjs = toolchain.RJSToolchain()
        rjs.transpiler(spec, source, target)
        self.assertEqual(source.getvalue(), target.getvalue())

    def test_compile_plugin_base(self):
        build_dir = utils.mkdtemp(self)
        src_dir = utils.mkdtemp(self)
        src = join(src_dir, 'mod.js')

        with open(src, 'w') as fd:
            fd.write('hello world')

        # prepare targets
        target1 = 'mod1.txt'
        target2 = join('namespace', 'mod2.txt')
        target3 = join('nested', 'namespace', 'mod3.txt')
        target4 = 'namespace.mod4.txt'

        rjs = toolchain.RJSToolchain()
        spec = {
            'build_dir': build_dir,
            toolchain.RJS_LOADER_PLUGIN_REGISTRY: rjs.loader_plugin_registry,
        }
        rjs.compile_plugin(spec, [
            ('text!mod1.txt', src, target1, 'mod1'),
            ('text!namespace/mod2.txt', src, target2, 'mod2'),
            ('text!nested/namespace/mod3.txt', src, target3, 'mod3'),
            ('text!namespace.mod4.txt', src, target4, 'mod4'),
        ])

        self.assertTrue(exists(join(build_dir, target1)))
        self.assertTrue(exists(join(build_dir, target2)))
        self.assertTrue(exists(join(build_dir, target3)))
        self.assertTrue(exists(join(build_dir, target4)))

    def test_compile_plugin_error(self):
        build_dir = utils.mkdtemp(self)
        src_dir = utils.mkdtemp(self)
        src = join(src_dir, 'mod.js')

        with open(src, 'w') as fd:
            fd.write('hello world')

        # prepare targets
        target = 'target.txt'

        rjs = toolchain.RJSToolchain()
        spec = {
            'build_dir': build_dir,
            toolchain.RJS_LOADER_PLUGIN_REGISTRY: rjs.loader_plugin_registry,
        }
        with self.assertRaises(TypeError):
            # This normally shouldn't happen, and for now the method
            # will not trap exceptions.
            rjs.compile_plugin(spec, [
                ('unregistered/mod!target.txt', src, target, 'target.txt'),
            ])


class ToolchainBaseUnitTestCase(unittest.TestCase):
    """
    Test the base functions in the toolchain.
    """

    def test_modname_source_target_to_modpath(self):
        modname = 'module'
        source = 'somemodule'
        rjs = toolchain.RJSToolchain()
        spec = Spec()
        self.assertEqual(
            rjs.modname_source_target_to_modpath(spec, modname, source, ''),
            'module',
        )

    def test_modname_source_target_to_modpath_empty(self):
        modname = 'module'
        source = 'empty:'
        rjs = toolchain.RJSToolchain()
        spec = Spec()
        self.assertEqual(
            rjs.modname_source_target_to_modpath(spec, modname, source, ''),
            'empty:',
        )


@unittest.skipIf(get_npm_version() is None, "npm is unavailable")
class ToolchainUnitTestCase(unittest.TestCase):
    """
    Just testing out the toolchain units.
    """

    def test_prepare_failure_manual(self):
        rjs = toolchain.RJSToolchain()
        spec = Spec(rjs_bin='/no/such/path')
        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)

        self.assertEqual(
            str(e.exception),
            "'/no/such/path' does not exist; cannot be used as '%s' binary" % (
                rjs.rjs_bin
            ),
        )

    def test_prepare_failure_which_fail(self):
        utils.stub_os_environ(self)
        utils.remember_cwd(self)

        # must go to a directory where r.js is guaranteed to not be
        # available through node_modules or the environmental PATH
        os.environ['NODE_PATH'] = ''
        os.environ['PATH'] = ''
        tmpdir = utils.mkdtemp(self)
        os.chdir(tmpdir)

        rjs = toolchain.RJSToolchain()
        spec = Spec()
        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)

        self.assertEqual(str(e.exception), "unable to locate '%s'" % (
            rjs.rjs_bin
        ))

    def test_prepare_failure_export_target(self):
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
            str(e.exception), "'export_target' not found in spec")

        # what can possibly go wrong?
        spec['export_target'] = join(spec[rjs.rjs_bin_key], 'build.js')

        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)
        self.assertEqual(
            str(e.exception), "'export_target' will not be writable")

        spec['export_target'] = join(tmpdir, 'build.js')

        with self.assertRaises(RuntimeError) as e:
            rjs.prepare(spec)
        self.assertEqual(
            str(e.exception), "'export_target' must not be same as "
            "'build_manifest_path'")

    def test_assemble_null(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

        spec = Spec(
            # this is not written
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={},
            bundled_modpaths={},
            plugins_modpaths={},
            transpiled_targets={},
            bundled_targets={},
            plugins_targets={},
            export_module_names=[],
        )

        rjs = toolchain.RJSToolchain()
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
        rjs.prepare(spec)
        rjs.assemble(spec)

        self.assertTrue(exists(join(tmpdir, 'build.js')))
        self.assertTrue(exists(join(tmpdir, 'config.js')))
        self.assertEqual(spec[CONFIG_JS_FILES], [join(tmpdir, 'config.js')])

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

    def test_prepare_assemble(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

        spec = Spec(
            # this is not written
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': '/path/to/src/example/module'
            },
            bundled_modpaths={
                'bundled_pkg': '/path/to/bundled/index',
                'bundled_empty': 'empty:',
            },
            plugins_modpaths={
                'loader/plugin!resource/name': '/resource/name'
            },
            transpiled_targets={
                'example/module': '/path/to/src/example/module.js',
            },
            bundled_targets={
                'bundled_pkg': '/path/to/bundled/index.js',
                'bundled_txt': '/path/to/bundled/txt',
                'bundled_dir': '/path/to/bundled/dir.js',
                'bundled_empty': 'empty:',
            },
            plugins_targets={
                'resource/name': '/resource/name',
            },
            export_module_names=[
                'example/module',
                'bundled_dir',
                'bundled_pkg',
                'bundled_txt',
                'bundled_empty',
                'loader/plugin!resource/name',
            ],
        )

        # we are going to fake the is_file checks
        utils.stub_item_attr_value(
            self, toolchain, 'isfile', lambda x: not x.endswith('dir.js'))

        rjs = toolchain.RJSToolchain()
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
        rjs.prepare(spec)

        # skip the compile step as those entries are manually applied.
        with pretty_logging(logger='calmjs.rjs', stream=mocks.StringIO()) as s:
            # the parser will try to load the file
            rjs.assemble(spec)

        self.assertIn('No such file or directory', s.getvalue())
        self.assertIn(
            join(*('path/to/src/example/module.js'.split('/'))),
            s.getvalue(),
        )

        self.assertTrue(exists(join(tmpdir, 'build.js')))
        self.assertTrue(exists(join(tmpdir, 'config.js')))

        with open(join(tmpdir, 'build.js')) as fd:
            # strip off the header and footer as this is for r.js
            build_js = json.loads(''.join(fd.readlines()[1:-1]))

        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer as this is for r.js
            config_js = json.loads(''.join(fd.readlines()[4:-10]))

        self.assertEqual(build_js['paths'], {
            'bundled_empty': 'empty:',
        })
        self.assertEqual(build_js['include'], [
            'example/module',
            'bundled_dir',
            'bundled_pkg',
            'bundled_txt',
            'bundled_empty',
            'loader/plugin!resource/name',
        ])

        self.assertEqual(config_js['paths'], {
            'example/module': '/path/to/src/example/module.js?',
            'bundled_pkg': '/path/to/bundled/index.js?',
            'bundled_txt': '/path/to/bundled/txt',
            'bundled_dir': '/path/to/bundled/dir.js',
            'resource/name': '/resource/name',
        })
        self.assertEqual(config_js['include'], [])

    def test_prepare_rjs_plugin_key(self):
        tmpdir = utils.mkdtemp(self)
        rjs = toolchain.RJSToolchain()

        with open(join(tmpdir, 'r.js'), 'w'):
            # mock a r.js file.
            pass

        spec = Spec(
            # this is not written
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={},
            bundled_modpaths={},
            export_module_names=[],
        )
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
        spec[toolchain.REQUIREJS_PLUGINS] = {
            'text': {
                'text!namespace/module/path.txt': '/namespace/module/path.txt',
            },
            'unsupported/unknown_plugin': {
                'also this is an invalid value': '/some/path',
            },
        }

        with pretty_logging(logger='calmjs.rjs', stream=mocks.StringIO()) as s:
            rjs.prepare(spec)

        self.assertEqual(spec['plugin_source_map'], {
            'text!namespace/module/path.txt': '/namespace/module/path.txt',
        })

        logs = s.getvalue()
        self.assertIn("DEBUG", logs)
        self.assertIn("found handler for 'text' loader plugin", logs)
        self.assertIn("WARNING", logs)
        self.assertIn(
            "handler for 'unsupported/unknown_plugin' loader plugin not found",
            logs)
        self.assertIn("also this is an invalid value", logs)

    def assemble_spec_config(self, **kw):
        # for the assemble related tests.
        tmpdir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        rjs = toolchain.RJSToolchain()

        export_target = join(build_dir, 'export.js')
        build_manifest_path = join(build_dir, 'build.js')
        node_config_js = join(build_dir, 'node_config.js')
        requirejs_config_js = join(build_dir, 'requirejs_config.js')

        with open(join(tmpdir, 'r.js'), 'w'):
            pass

        with open(join(build_dir, 'module1.js'), 'w') as fd:
            fd.write(
                "define(['jquery', 'underscore', 'some.pylike.module'], "
                "function(jquery, underscore, module) {"
                "});"
            )

        with open(join(build_dir, 'module2.js'), 'w') as fd:
            fd.write(
                "define(['module1', 'underscore'], "
                "function(module1, underscore) {"
                "});"
            )

        with open(join(build_dir, 'module3.js'), 'w') as fd:
            fd.write(
                "'use strict';\n"
                "var $ = require('jquery');\n"
                "var _ = require('underscore');\n"
                "var module2 = require('module2');\n"
            )

        spec = Spec(
            build_dir=build_dir,
            export_target=export_target,
            build_manifest_path=build_manifest_path,
            node_config_js=node_config_js,
            requirejs_config_js=requirejs_config_js,
            transpiled_modpaths={
                'module1': 'module1',
                'module2': 'module2',
                'module3': 'module3',
            },
            # these are not actually transpiled sources, but will fit
            # with the purposes of this test.
            transpiled_targets={
                'module1': 'module1.js',
                'module2': 'module2.js',
                'module3': 'module3.js',
            },
            # the "bundled" names were specified to be omitted.
            bundled_modpaths={},
            bundled_targets={},
            plugins_modpaths={},
            plugins_targets={},
            export_module_names=['module1', 'module2', 'module3'],
            **kw
        )
        spec[rjs.rjs_bin_key] = join(tmpdir, 'r.js')
        rjs.assemble(spec)

        # the main config file
        # check that they all exists
        self.assertTrue(exists(build_manifest_path))
        self.assertTrue(exists(node_config_js))
        self.assertTrue(exists(requirejs_config_js))

        # only checking the build_manifest version, as the node config
        # version is not that much different.
        with open(build_manifest_path) as fd:
            build_tree = parse(fd.read())

        # this is the node for the json in the build file
        build_js = json.loads(build_tree.children()[0].children()[0].to_ecma())

        with open(requirejs_config_js) as fd:
            config_tree = parse(fd.read())

        # this is the node for json in the config file
        config_js = json.loads(
            config_tree.children()[0].children()[0].children()[0].children(
                )[2].children()[0].children()[1].to_ecma())

        return build_js, config_js

    def test_assemble_standard(self):
        with pretty_logging(logger='calmjs.rjs', stream=mocks.StringIO()) as s:
            build_js, config_js = self.assemble_spec_config()

        self.assertIn('ERROR', s.getvalue())
        self.assertIn(
            "source file(s) referenced modules that are missing in the "
            "build directory: 'jquery', 'some.pylike.module', 'underscore'",
            s.getvalue()
        )

        self.assertEqual(build_js['paths'], {})
        self.assertEqual(config_js['paths'], {
            'module1': 'module1.js?',
            'module2': 'module2.js?',
            'module3': 'module3.js?',
        })

    def test_assemble_standard_emptied(self):
        with pretty_logging(logger='calmjs.rjs', stream=mocks.StringIO()) as s:
            build_js, config_js = self.assemble_spec_config(
                stub_missing_with_empty=1
            )

        self.assertNotIn('ERROR', s.getvalue())
        self.assertIn(
            "source file(s) referenced modules that are missing in the "
            "build directory: 'jquery', 'some.pylike.module', 'underscore'",
            s.getvalue()
        )

        self.assertEqual(build_js['paths'], {
            'jquery': 'empty:',
            'some.pylike.module': 'empty:',
            'underscore': 'empty:',
        })
        self.assertEqual(config_js['paths'], {
            'module1': 'module1.js?',
            'module2': 'module2.js?',
            'module3': 'module3.js?',
            'jquery': 'empty:',
            'some.pylike.module': 'empty:',
            'underscore': 'empty:',
        })
