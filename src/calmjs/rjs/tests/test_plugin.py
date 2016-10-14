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


class TextTestCase(unittest.TestCase):

    def test_basic(self):
        build_dir = mkdtemp(self)
        srcdir = mkdtemp(self)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'text_file.txt')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        # following are normally generated by default toolchain
        modname = 'text!text_file.txt'
        target = 'text!text_file.txt.js'
        modpath = 'text!text_file.txt'

        result = plugin.text(toolchain, spec, modname, source, target, modpath)
        self.assertTrue(exists(join(build_dir, 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result

        self.assertEqual(bundled_modpaths, {
            'text!text_file.txt': 'text!text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'text!text_file.txt': 'text_file.txt',
        })
        self.assertEqual(module_name, ['text!text_file.txt'])

    def test_nested(self):
        build_dir = mkdtemp(self)
        srcdir = join(mkdtemp(self), 'namespace')
        mkdir(srcdir)
        spec = {'build_dir': build_dir}
        source = join(srcdir, 'text_file.txt')

        with open(source, 'w') as fd:
            fd.write('a text file\n')

        toolchain = None  # this one is not necessary for text.
        # following are normally generated by default toolchain
        modname = 'text!namespace/text_file.txt'
        target = 'text!namespace/text_file.txt.js'
        modpath = 'text!namespace/text_file.txt'

        result = plugin.text(toolchain, spec, modname, source, target, modpath)
        self.assertTrue(exists(join(build_dir, 'namespace', 'text_file.txt')))
        bundled_modpaths, bundled_targets, module_name = result
        self.assertEqual(bundled_modpaths, {
            'text!namespace/text_file.txt': 'text!namespace/text_file.txt',
        })
        self.assertEqual(bundled_targets, {
            'text!namespace/text_file.txt': 'namespace/text_file.txt',
        })
        self.assertEqual(module_name, ['text!namespace/text_file.txt'])
