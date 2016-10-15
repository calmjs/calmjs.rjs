# -*- coding: utf-8 -*-
import unittest
from os import mkdir
from os.path import exists
from os.path import join

from calmjs.rjs import plugin

from calmjs.testing.utils import mkdtemp


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
        self.assertEqual(f('file'), 'file')
        self.assertEqual(f('dir/text'), 'dir/text')
        self.assertEqual(f('dir/text.txt'), 'dir/text')
        self.assertEqual(f('dotted.dir/text'), 'dotted')
        self.assertEqual(f('dotted.dir/text.txt'), 'dotted.dir/text')

        # the following also implement the stripping of trailing dots,
        # which requirejs-text>2.0.14 doesn't support, however this will
        # break what could be working paths under requirejs<=2.0.13
        self.assertEqual(f('file.'), 'file')
        self.assertEqual(f('dir/text.'), 'dir/text')
        self.assertEqual(f('dotted.dir/text.'), 'dotted.dir/text')

    def test_modname_target_to_config_paths(self):
        f = plugin.text.modname_target_to_config_paths
        self.assertEqual(
            f('text!file.txt', 'text!file.txt'),
            ('file', 'file'),
        )
        self.assertEqual(
            f('text!dir/file.txt', 'text!dir/file.txt'),
            ('dir/file', 'dir/file'),
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

        result = plugin.text(toolchain, spec, modname, source, target, modpath)
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

        result = plugin.text(toolchain, spec, modname, source, target, modpath)
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

        result = plugin.text(toolchain, spec, modname, source, target, modpath)
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
