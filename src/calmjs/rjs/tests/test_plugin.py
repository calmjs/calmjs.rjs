# -*- coding: utf-8 -*-
import unittest
from os import mkdir
from os import makedirs
from os.path import exists
from os.path import join

from calmjs.rjs import plugin
from calmjs.utils import pretty_logging

from calmjs.testing.utils import mkdtemp
from calmjs.testing.mocks import StringIO


class LoaderPluginHandlerTestCase(unittest.TestCase):

    def test_config_paths(self):
        handler = plugin.LoaderPluginHandler(None)
        self.assertEqual(handler.modname_target_to_config_paths(
            'example/path', 'example/path.js'),
            {'example/path': 'example/path.js?'},
        )
        self.assertEqual(handler.modname_source_to_config_paths(
            'example/path', 'example/path.js'),
            {'example/path': 'example/path.js?'},
        )

    def test_others(self):
        handler = plugin.LoaderPluginHandler(None)
        modname_modpath = ('example/path', 'example/path')
        self.assertEqual(
            handler.modname_modpath_to_config_paths(*modname_modpath),
            dict([modname_modpath]),
        )
        with self.assertRaises(NotImplementedError):
            handler(None, None, None, None, None, None)


class TextLoaderPluginTestCase(unittest.TestCase):

    def test_strip_plugin(self):
        f = plugin.TextPlugin(None).strip_plugin
        self.assertEqual(f('file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt!strip'), 'file.txt')

    def test_strip_plugin_unstripped_values(self):
        f = plugin.TextPlugin(None).strip_plugin
        self.assertEqual(f('/file.txt'), '/file.txt')
        self.assertEqual(f('/text!file.txt'), '/text!file.txt')
        self.assertEqual(f('/text!file.txt!strip'), '/text!file.txt!strip')

    def test_strip_plugin_empty(self):
        f = plugin.TextPlugin(None).strip_plugin
        # this should be invalid, but we are forgiving
        self.assertEqual(f(''), '')
        self.assertEqual(f('text!'), '')

    def test_requirejs_text_issue123_handling(self):
        f = plugin.TextPlugin(None).requirejs_text_issue123
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(f('file'), ['file', ''])
            self.assertEqual(f('dir/text'), ['dir/text', ''])
            self.assertEqual(f('dir/text.txt'), ['dir/text', 'txt'])
            self.assertEqual(f('dotted.dir/text'), ['dotted', 'dir/text'])
            self.assertEqual(
                f('dotted.dir/text.txt'), ['dotted.dir/text', 'txt'])

        self.assertEqual(stream.getvalue(), '')

        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            # the following also implement the stripping of trailing
            # dots which requirejs-text doesn't support correctly,
            # and with requirejs>=2.0.13 will fail consistently.
            self.assertEqual(f('file.'), ['file', ''])
            self.assertEqual(f('dir/text.'), ['dir/text', ''])
            self.assertEqual(f('dotted.dir/text.'), ['dotted.dir/text', ''])

        # ensure the complaining loudly is done.
        self.assertIn('WARNING', stream.getvalue())
        self.assertIn('trailing', stream.getvalue())

    def test_empty_modname_target_to_config_paths(self):
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!', 'text!'),
                {'': ''},  # we are following our own rules...
            )
        self.assertEqual(stream.getvalue(), '')

    def test_modname_target_to_config_paths(self):
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        self.modname_x_to_config_paths(f)

    def test_modname_source_to_config_paths(self):
        f = plugin.TextPlugin(None).modname_source_to_config_paths
        self.modname_x_to_config_paths(f)

    def modname_x_to_config_paths(self, f):
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!file', 'text!file'),
                {'file': 'file'},
            )
            self.assertEqual(
                f('text!file.txt', 'text!file.txt'),
                {
                    'file': 'file',
                    'file.txt': 'file.txt',
                },
            )
            self.assertEqual(
                f('text!dir/file.txt', 'text!dir/file.txt'),
                {
                    'dir/file': 'dir/file',
                    'dir/file.txt': 'dir/file.txt',
                },
            )
            self.assertEqual(
                f('text!dir/file.txt', '/some/path/dir/file.txt'),
                {
                    'dir/file': '/some/path/dir/file',
                    'dir/file.txt': '/some/path/dir/file.txt',
                },
            )
            self.assertEqual(
                f('text!dir/file', '/some/path/dir/file'),
                {'dir/file': '/some/path/dir/file'},
            )
            self.assertEqual(
                f('text!dir/file', '/some/path/dir/file!strip'),
                {'dir/file': '/some/path/dir/file!strip'},
            )

        self.assertEqual(stream.getvalue(), '')

    def test_modname_target_to_config_paths_mismatch_file_ext(self):
        # this will blow up, actually, since requesting for file.htm
        # will NOT resolve it to file.html - no configuration can be
        # currently done to produce a working mapping.
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!file.htm', 'text!some.dotted/dir/file.html'),
                {'file.htm': 'some.dotted/dir/file.html'},
            )
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn('no possible workaround', err)

    def test_modname_target_to_config_paths_mismatch_dir_ext_file_noext(self):
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                {
                    'file': 'some.dotted/dir/file',
                    'file.ns': 'some.dotted/dir/file.ns',
                    'file.ns/html': 'some.dotted/dir/file.ns/html',
                },
                f('text!file.ns/html', 'text!some.dotted/dir/file.ns/html'),
            )
        # this one provides both the dot stripped and the underlying
        # directory, to cover both case (unless this screws up some
        # other thing).
        err = stream.getvalue()
        # though since this should work, better to warn about this.
        self.assertIn('WARNING', err)
        self.assertIn(
            "warning triggered by mapping config.paths from "
            "modpath 'text!file.ns/html' to "
            "target 'text!some.dotted/dir/file.ns/html'", err
        )
        self.assertIn("unsupported values provided", err)
        self.assertIn("potentially working mitigations applied", err)
        self.assertIn('text!file.ns/html', err)
        self.assertIn('text!some.dotted/dir/file.ns/html', err)

    def test_modname_target_to_config_paths_warning(self):
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        # There are cases where if the python style namespace separator
        # is used for the generated path, and the final fragment has no
        # further '.' characters, WILL result in a complete mismatch of
        # the key to the expected target.  That said, this particular
        # type of mapping doesn't seem to be supported at all by the
        # requirejs-text plugin.
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!some.target/file', '/src/some/target/file'),
                {'some.target/file': '/src/some/target/file'},
                # Do nothing as this type of conversion/mapping doesn't
                # work no matter what, because requirejs and/or the text
                # loader plugin fails at tracking directories if it has
                # a '.' somewhere, so the loader gets confused and just
                # don't see the mapping entry.

                # To mitigate, ensure the provided files or paths
                # provided have a filename extension and does not end
                # with a ``.`` character.
            )

        # ensure that is logged
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn('no possible workaround', err)

    def test_modname_target_to_config_paths_info_no_false_positive(self):
        # like the htm -> html example
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!some/file.html', '/src/some/target/file.rst'),
                {'some/file.html': '/src/some/target/file.rst'},
            )
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn('no possible workaround', err)

    def test_modname_target_to_config_paths_further_insanity(self):
        # Again, the mapping just do not work.  Mapping from 'some' to
        # '/src/some' will not suddenly make 'contents/html' map to
        # 'contents/rst'.
        f = plugin.TextPlugin(None).modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                {'some.contents/html': '/src/some.contents/rst'},
                f('text!some.contents/html', '/src/some.contents/rst'),
            )
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn('no possible workaround', err)

    def test_basic(self):
        # the target is 'text_file.txt'
        build_dir = mkdtemp(self)
        srcdir = mkdtemp(self)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'text_file.txt')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        modname = 'text!text_file.txt'
        target = 'text!text_file.txt'
        modpath = 'text!text_file.txt'

        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            result = plugin.TextPlugin(None)(
                toolchain, spec, modname, source, target, modpath)
        self.assertEqual(stream.getvalue(), '')

        self.assertTrue(exists(join(build_dir, 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result

        self.assertEqual(bundled_modpaths, {
            'text!text_file.txt': 'text!text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'text_file': 'text_file',
            'text_file.txt': 'text_file.txt',
        })
        self.assertEqual(module_name, ['text!text_file.txt'])

    def test_nested(self):
        # the target is 'namespace/text_file.txt'
        build_dir = mkdtemp(self)
        srcdir = join(mkdtemp(self), 'namespace')
        mkdir(srcdir)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'text_file.txt')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        modname = 'text!namespace/text_file.txt'
        target = 'text!namespace/text_file.txt'
        modpath = 'text!namespace/text_file.txt'

        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            result = plugin.TextPlugin(None)(
                toolchain, spec, modname, source, target, modpath)
        self.assertEqual(stream.getvalue(), '')

        self.assertTrue(exists(join(build_dir, 'namespace', 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!namespace/text_file.txt': 'text!namespace/text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'namespace/text_file': 'namespace/text_file',
            'namespace/text_file.txt': 'namespace/text_file.txt',
        })
        self.assertEqual(module_name, ['text!namespace/text_file.txt'])

    def test_dotted_namespace(self):
        # the target is 'dotted.ns/data'
        build_dir = mkdtemp(self)
        srcdir = join(mkdtemp(self), 'dotted.ns')
        mkdir(srcdir)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'data')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        modname = 'text!dotted.ns/data'
        target = 'text!dotted.ns/data'
        modpath = 'text!dotted.ns/data'

        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            result = plugin.TextPlugin(None)(
                toolchain, spec, modname, source, target, modpath)
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn('potentially working mitigations applied', err)

        self.assertTrue(exists(join(build_dir, 'dotted.ns', 'data')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!dotted.ns/data': 'text!dotted.ns/data',
        })
        # Yes, this is how bad requirejs-text is at figuring out what a
        # dot means within a path, how it misunderstand directories and
        # filename extensions within a path value.  Please refer to the
        # source code to note the issue at hand which is encapsulate by
        # text.requirejs_text_issue123 method.
        self.assertEqual(bundled_targets, {
            'dotted': 'dotted',
            'dotted.ns': 'dotted.ns',
            'dotted.ns/data': 'dotted.ns/data',
        })
        # Oh yeah, to confirm again that this is the expected value so
        # that the underlying loader will be able to load the target
        # dotted.ns/data.  This is especially critical for generation of
        # configuration for in-place testing/test files; see an earlier
        # test to show what kind of data other calmjs registries will
        # be able to produce.
        self.assertEqual(module_name, ['text!dotted.ns/data'])

    def test_dotted_namespace_mismatched_warning(self):
        # from src/dotted/ns/data to dotted.ns/data and this will blow
        # up completely (also not supported because requirejs-text issue
        # #123.
        build_dir = mkdtemp(self)
        srcdir = join(mkdtemp(self), 'dotted', 'ns')
        makedirs(srcdir)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'data')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        modname = 'text!dotted.ns/data'
        # note, this mismatch target and modpath shouldn't normally be
        # produced, however as the build script will have an empty paths
        # mapping, this wouldn't have worked as part of the build anyway.
        # So for plugin authors, do ensure the targets in the build
        # directory map directly to the intended locations.
        target = join('dotted', 'ns', 'data')
        modpath = 'text!dotted.ns/data'

        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            result = plugin.TextPlugin(None)(
                toolchain, spec, modname, source, target, modpath)
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn("modpath 'text!dotted.ns/data'", err)
        # trimming off the ends because they are identical but the
        # actual values depend on os.sep.
        self.assertIn("target 'dotted", err)

        self.assertTrue(exists(join(build_dir, 'dotted', 'ns', 'data')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!dotted.ns/data': 'text!dotted.ns/data',
        })
        # nothing was done, no mitigation applied as the generation of
        # a working config.paths is impossible
        self.assertEqual(bundled_targets, {
            'dotted.ns/data': target,  # 'dotted/ns/data'
        })
        self.assertEqual(module_name, ['text!dotted.ns/data'])
