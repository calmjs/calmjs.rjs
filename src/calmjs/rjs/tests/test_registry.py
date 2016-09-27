# -*- coding: utf-8 -*-
import unittest

from calmjs.registry import get

from calmjs.rjs.registry import LoaderPlugin
from calmjs.rjs.plugin import text

from calmjs.utils import pretty_logging
from calmjs.testing.mocks import StringIO
from calmjs.testing.mocks import WorkingSet


class LoaderPluginTestCase(unittest.TestCase):

    def test_initialize_standard(self):
        # ensure that we have a proper working registry
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'text = calmjs.rjs.plugin:text',
        ]})
        registry = LoaderPlugin(
            'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIs(registry.get('text'), text)

    def test_initialize_failure(self):
        # ensure that we have a proper working registry
        working_set = WorkingSet({'calmjs.rjs.loader_plugin': [
            'not_plugin = calmjs.rjs.not_plugin:nothing',
        ]})
        # should not trigger import failure
        with pretty_logging(stream=StringIO()) as stream:
            registry = LoaderPlugin(
                'calmjs.rjs.loader_plugin', _working_set=working_set)
        self.assertIsNone(registry.get('not_plugin'))
        self.assertIn(
            "registry 'calmjs.rjs.loader_plugin' failed to load loader plugin "
            "handler for entry point 'not_plugin =", stream.getvalue(),
        )

    def test_initialize_integration(self):
        # Use the global set and see that the defaults are registered
        registry = get('calmjs.rjs.loader_plugin')
        self.assertIs(registry.get('text'), text)
