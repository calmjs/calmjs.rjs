# -*- coding: utf-8 -*-
"""
Registry system for ``calmjs.rjs``.

This module provides the registries needed for the full functionality of
``calmjs.rjs``.  Only the ``LoaderPluginRegistry`` is currently provided
for the management of ``requirejs`` loader plugins for assisting with
conversion of paths to module names and target locations that are better
understood by the underlying path loader system.

Each plugin constructed will simply be a class that inherits from the
parent class ``calmjs.rjs.plugin.LoaderPluginHandler`` to faciliate type
checking, and it must accept the registry the loaded it as an argument;
this registry reference can then be used by a plugin to resolve other
sibling plugins registered to the same registry system to faciliate the
lookup of further names to build the targets needed.  For specific
implementation details, please refer to the ``calmjs.rjs.plugin``
module.

"""

from logging import getLogger

from calmjs.base import BaseRegistry
from calmjs.rjs.plugin import LoaderPluginHandler

logger = getLogger(__name__)


class LoaderPluginRegistry(BaseRegistry):

    # TODO make upstream consider implement this pattern of construction
    # through a new generic base registry class of some sort.

    def _init(self):
        for entry_point in self.raw_entry_points:
            try:
                cls = entry_point.load()
            except ImportError:
                logger.warning(
                    "registry '%s' failed to load loader plugin handler for "
                    "entry point '%s'", self.registry_name, entry_point,
                )
                continue

            if not issubclass(cls, LoaderPluginHandler):
                logger.warning(
                    "entry point '%s' does not lead to a valid loader plugin "
                    "handler class", entry_point
                )
                continue

            try:
                inst = cls(self)
            except Exception:
                logger.exception(
                    "the loader plugin class registered at '%s' failed "
                    "to be instantiated with the following exception",
                    entry_point,
                )
                continue

            if entry_point.name in self.records:
                old = type(self.records[entry_point.name])
                logger.warning(
                    "loader plugin handler for '%s' was already registered to "
                    "an instance of '%s:%s'; '%s' will now override this "
                    "registration",
                    entry_point.name, old.__module__, old.__name__, entry_point
                )
            self.records[entry_point.name] = inst

    def get_record(self, name):
        return self.records.get(name)
