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
        handler = plugin.LoaderPluginHandler()
        modname, target = handler.modname_target_to_config_paths(
            'example/path', 'example/path.js')

        self.assertEqual(modname, 'example/path')
        self.assertEqual(target, 'example/path.js?')

    def test_others(self):
        handler = plugin.LoaderPluginHandler()
        modname_modpath = ('example/path', 'example/path')
        self.assertEqual(
            handler.modname_modpath_to_config_paths(*modname_modpath),
            modname_modpath,
        )
        with self.assertRaises(NotImplementedError):
            handler(None, None, None, None, None, None)


class TextLoaderPluginTestCase(unittest.TestCase):

    def test_strip_plugin(self):
        f = plugin.text.strip_plugin
        self.assertEqual(f('file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt!strip'), 'file.txt')

    def test_requirejs_text_issue123_handling(self):
        f = plugin.text.requirejs_text_issue123
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

    def test_modname_target_to_config_paths(self):
        f = plugin.text.modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!file.txt', 'text!file.txt'),
                ('file', 'file'),
            )
            self.assertEqual(
                f('text!dir/file.txt', 'text!dir/file.txt'),
                ('dir/file', 'dir/file'),
            )
            self.assertEqual(
                f('text!dir/file.txt', '/some/path/dir/file.txt'),
                ('dir/file', '/some/path/dir/file'),
            )

        self.assertEqual(stream.getvalue(), '')

    def test_modname_target_to_config_paths_warning(self):
        f = plugin.text.modname_target_to_config_paths
        # There are cases where if the python style namespace separator
        # is used for the generated path, and the final fragment has no
        # further '.' characters, WILL result in a complete mismatch of
        # the key to the expected target.  That said, this particular
        # type of mapping doesn't seem to be supported at all by the
        # requirejs-text plugin.
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!some.target/file', '/src/some/target/file'),
                # TODO fix this when the following is rectified.
                # this is an undefined behavior/bugged behavior in
                # requirejs-text regardless of the output produced here
                ('some', '/src/some/target/file'),
                # even if we manage to track the directories and produce
                # valid examples like the following:
                # ('some.target', '/src/some/target')
                # ('some.target/file', '/src/some/target/file')

                # it will not work because requirejs-text fails at
                # tracking directories if it has a '.' somewhere.
                # Trying to traverse to open ``text!some.target/file``,
                # it will fail no matter what kind of configuration was
                # used.  Ensure the provided files or paths provided
                # have a filename extension and does not end with a
                # ``.`` character.
            )

        # ensure that is logged
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        self.assertIn(
            'provided values: {"some.target/file": "/src/some/target/file"}, '
            'generated values: {"some": "/src/some/target/file"}', err
        )

    def test_modname_target_to_config_paths_warning_no_false_positive(self):
        f = plugin.text.modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!some/file.html', '/src/some/target/file.rst'),
                ('some/file', '/src/some/target/file'),
            )
        # above shouldn't trigger a false positive, but just a general
        # warning will suffice
        # ensure that is logged
        err = stream.getvalue()
        self.assertIn('INFO', err)
        self.assertIn(
            'provided modname and target '
            '{"some/file.html": "/src/some/target/file.rst"} '
            'do not share the same suffix', err
        )

        f = plugin.text.modname_target_to_config_paths
        with pretty_logging('calmjs.rjs.plugin', stream=StringIO()) as stream:
            self.assertEqual(
                f('text!some.ns/file', '/src/some/ns/file.txt'),
                ('some', '/src/some/ns/file'),
            )
        # above shouldn't trigger a false positive, but just a general
        # warning will suffice
        # ensure that is logged
        err = stream.getvalue()
        self.assertIn('INFO', err)
        self.assertIn(
            'provided modname and target '
            '{"some.ns/file": "/src/some/ns/file.txt"} '
            'do not share the same suffix', err
        )

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
            result = plugin.text(
                toolchain, spec, modname, source, target, modpath)
        self.assertEqual(stream.getvalue(), '')

        self.assertTrue(exists(join(build_dir, 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result

        self.assertEqual(bundled_modpaths, {
            'text!text_file.txt': 'text!text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'text_file': 'text_file',
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
            result = plugin.text(
                toolchain, spec, modname, source, target, modpath)
        self.assertEqual(stream.getvalue(), '')

        self.assertTrue(exists(join(build_dir, 'namespace', 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!namespace/text_file.txt': 'text!namespace/text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'namespace/text_file': 'namespace/text_file',
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
            result = plugin.text(
                toolchain, spec, modname, source, target, modpath)
        self.assertEqual(stream.getvalue(), '')

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
            result = plugin.text(
                toolchain, spec, modname, source, target, modpath)
        err = stream.getvalue()
        self.assertIn('WARNING', err)
        # trimming off the ends because they are identical but the
        # actual values depend on os.sep.
        self.assertIn('provided values: {"dotted.ns/data": "dotted', err)
        self.assertIn('generated values: {"dotted": "dotted', err)

        self.assertTrue(exists(join(build_dir, 'dotted', 'ns', 'data')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!dotted.ns/data': 'text!dotted.ns/data',
        })
        # yep, a terrible mismatch results.
        self.assertEqual(bundled_targets, {
            'dotted': target,  # 'dotted/ns/data'
        })
        self.assertEqual(module_name, ['text!dotted.ns/data'])
