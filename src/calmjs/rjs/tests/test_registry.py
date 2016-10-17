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
