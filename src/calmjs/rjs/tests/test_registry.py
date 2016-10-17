# -*- coding: utf-8 -*-
import unittest

from calmjs.registry import get

from calmjs.rjs.registry import LoaderPluginRegistry
from calmjs.rjs.plugin import LoaderPluginHandler
from calmjs.rjs.plugin import TextPlugin

from calmjs.utils import pretty_logging
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet


class NotPlugin(LoaderPluginRegistry):
    """yeanah"""


class BadPlugin(LoaderPluginHandler):

    def __init__(self):
        """this will not be called; missing argument"""


class DupePlugin(LoaderPluginHandler):
    """
    Dummy duplicate plugin
    """


class LoaderPluginRegistryTestCase(unittest.TestCase):

    def test_initialize_standard(self):
        # ensure that we have a proper working registry
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'text = calmjs.rjs.plugin:TextPlugin',
        ]})
        registry = LoaderPluginRegistry(
            'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertTrue(isinstance(registry.get('text'), TextPlugin))

    def test_initialize_failure_missing(self):
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'not_plugin = calmjs.rjs.not_plugin:nothing',
        ]})
        # should not trigger import failure
        with pretty_logging(stream=StringIO()) as stream:
            registry = LoaderPluginRegistry(
                'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIsNone(registry.get('not_plugin'))
        self.assertIn(
            "registry 'calmjs.rjs.loader_plugin' failed to load loader plugin "
            "handler for entry point 'not_plugin =", stream.getvalue(),
        )

    def test_initialize_failure_not_plugin(self):
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'not_plugin = calmjs.rjs.tests.test_registry:NotPlugin',
        ]})
        # should not trigger import failure
        with pretty_logging(stream=StringIO()) as stream:
            registry = LoaderPluginRegistry(
                'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIsNone(registry.get('not_plugin'))
        self.assertIn(
            "'not_plugin = calmjs.rjs.tests.test_registry:NotPlugin' does not "
            "lead to a valid loader plugin handler class",
            stream.getvalue()
        )

    def test_initialize_failure_bad_plugin(self):
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'bad_plugin = calmjs.rjs.tests.test_registry:BadPlugin',
        ]})
        # should not trigger import failure
        with pretty_logging(stream=StringIO()) as stream:
            registry = LoaderPluginRegistry(
                'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIsNone(registry.get('bad_plugin'))
        self.assertIn(
            "the loader plugin class registered at 'bad_plugin = "
            "calmjs.rjs.tests.test_registry:BadPlugin' failed "
            "to be instantiated with the following exception",
            stream.getvalue()
        )

    def test_initialize_warning_dupe_plugin(self):
        # ensure that we have a proper working registry
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'text = calmjs.rjs.tests.test_registry:DupePlugin',
            'text = calmjs.rjs.plugin:TextPlugin',
        ]})
        # should not trigger import failure
        with pretty_logging(stream=StringIO()) as stream:
            registry = LoaderPluginRegistry(
                'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIn(
            "loader plugin handler for 'text' was already registered to an "
            "instance of 'calmjs.rjs.tests.test_registry:DupePlugin'",
            stream.getvalue()
        )
        # the second one will be registered
        self.assertTrue(isinstance(registry.get('text'), TextPlugin))

    def test_initialize_integration(self):
        # Use the global set and see that the defaults are registered
        registry = get('calmjs.rjs.loader_plugin')
        text = registry.get('text')
        self.assertTrue(isinstance(text, TextPlugin))
        # should return the identity as they should all be the same.
        self.assertIs(text.registry, registry)
        self.assertIs(text.registry.get('text'), text)


class MappingConversionTestCase(unittest.TestCase):

    def setUp(self):
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'text = calmjs.rjs.plugin:TextPlugin',
        ]})
        self.registry = LoaderPluginRegistry(
            'calmjs.rjs.loader_plugin', _working_set=working_set)

    def test_standard_modpath_source(self):
        result = self.registry.modname_source_mapping_to_config_paths({
            'foo/bar': '/src/foo/bar.js',
            'foo/baz': '/src/foo/baz.js',
        })
        self.assertEqual({
            'foo/bar': '/src/foo/bar.js?',
            'foo/baz': '/src/foo/baz.js?',
        }, result['paths'])
        self.assertEqual(sorted(result.keys()), ['paths'])

    def test_standard_modpath_target(self):
        result = self.registry.modname_target_mapping_to_config_paths({
            'bar/bar': '/src/bar/baz.js',
            'foo/baz': '/src/foo/baz.js',
        })
        self.assertEqual({
            'bar/bar': '/src/bar/baz.js?',
            'foo/baz': '/src/foo/baz.js?',
        }, result['paths'])

    def test_standard_modpath_plugins(self):
        result = self.registry.modname_source_mapping_to_config_paths({
            'text!foo/bar': 'text!/src/foo/bar',
            'text!example.ns/baz.txt': 'text!/src/example/ns/baz.txt',
        })
        self.assertEqual({
            'foo/bar': '/src/foo/bar',
            'example.ns/baz': '/src/example/ns/baz',
            'example.ns/baz.txt': '/src/example/ns/baz.txt',
        }, result['paths'])

    def test_standard_modpath_plugin_not_found(self):
        with pretty_logging(stream=StringIO()) as stream:
            result = self.registry.modname_source_mapping_to_config_paths({
                'nosuchplugin!foo/bar': 'nosuchplugin!/src/foo/bar',
                'text!example.ns/baz.txt': 'text!/src/example/ns/baz.txt',
            })
        err = stream.getvalue()
        self.assertEqual({
            'example.ns/baz': '/src/example/ns/baz',
            'example.ns/baz.txt': '/src/example/ns/baz.txt',
        }, result['paths'])
        self.assertIn('WARNING', err)
        self.assertIn("no handler found for loader plugin 'nosuchplugin'", err)
        self.assertIn(
            "{'nosuchplugin!foo/bar': 'nosuchplugin!/src/foo/bar'} will be "
            "dropped", err,
        )
        self.assertIn("this action may be fatal later", err)

    def test_fun_edge_case(self):
        """
        A very (un)fun edge case.

        Since the base module isn't so strict, there are situations
        where the workaround is still valid.
        """

        with pretty_logging(stream=StringIO()) as stream:
            result = self.registry.modname_source_mapping_to_config_paths({
                'foo/bar': '/src/foo/bar.js',
                'text!foo/bar.txt': '/src/foo/bar.txt',
            })
        err = stream.getvalue()
        # The mapping created by the plugin is compatible so no warnings
        # are issued.
        self.assertNotIn('WARNING', err)
        self.assertEqual({
            'foo/bar': '/src/foo/bar',
            # the exact text mapping is also present.
            'foo/bar.txt': '/src/foo/bar.txt',
        }, result['paths'])

    def test_non_working_workaround(self):
        """
        A test to show non-working workaround

        The annoyances just keeps on giving.
        """

        with pretty_logging(stream=StringIO()) as stream:
            result = self.registry.modname_source_mapping_to_config_paths({
                'foo/bar': '/src/foo/bar.js',
                'text!foo/bar.txt': '/alt/src/foo/bar.txt',
            })
        err = stream.getvalue()
        self.assertEqual({
            'foo/bar': '/src/foo/bar.js?',
            'foo/bar.txt': '/alt/src/foo/bar.txt',
        }, result['paths'])
        self.assertIn('WARNING', err)
        self.assertIn(
            "the value of paths['foo/bar'] is being rewritten from "
            "'/alt/src/foo/bar' to '/src/foo/bar.js?'; "
            "configuration may be in an invalid state.", err)

    def test_unsupported_mapping(self):
        """
        The unsupported mapping we have seen before with mismatched
        filename extensions.
        """

        with pretty_logging(stream=StringIO()) as stream:
            result = self.registry.modname_target_mapping_to_config_paths({
                'text!foo/bar.html': 'text!/alt/src/foo/bar.txt',
            })
        err = stream.getvalue()
        # mapping untouched completely, saved for removal of plugin name
        self.assertEqual({
            'foo/bar.html': '/alt/src/foo/bar.txt',
        }, result['paths'])
        self.assertIn('WARNING', err)
        self.assertIn(
            "warning triggered by mapping config.paths from modpath "
            "'text!foo/bar.html' to target 'text!/alt/src/foo/bar.txt'", err)
        self.assertIn(
            "provided modname and target has no possible workaround", err)

    def test_requirejs_is_pretty_much_completely_broken(self):
        """
        Showing how requirejs and/or requirejs-text is basically broken

        I mean, I covered how it basically can't deal with filename
        extensions correctly, so no amount of workaround can really fix
        the underlying brokenness.
        """

        with pretty_logging(stream=StringIO()) as stream:
            result = self.registry.modname_target_mapping_to_config_paths({
                'text!foo/bar.txt': 'text!/src/foo/bar.txt',
                'text!foo/bar.html': 'text!/alt/src/foo/bar.html',
            })
        err = stream.getvalue()
        # html comes before txt, since the mapping is pre-sorted in
        # alphabetical order, so txt will end up overwriting html's base
        # directory.
        self.assertEqual({
            'foo/bar': '/src/foo/bar',
            'foo/bar.txt': '/src/foo/bar.txt',
            'foo/bar.html': '/alt/src/foo/bar.html',
        }, result['paths'])
        self.assertIn('WARNING', err)
        self.assertIn("value of paths['foo/bar'] is being rewritten", err)
        self.assertIn("configuration may be in an invalid state", err)
        self.assertIn(
            "the value of paths['foo/bar'] is being rewritten from "
            "'/alt/src/foo/bar' to '/src/foo/bar'; "
            "configuration may be in an invalid state.", err)
