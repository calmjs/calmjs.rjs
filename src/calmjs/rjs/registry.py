# -*- coding: utf-8 -*-
from logging import getLogger

from calmjs.base import BaseRegistry

logger = getLogger(__name__)


class LoaderPluginRegistry(BaseRegistry):

    def _init(self):
        for entry_point in self.raw_entry_points:
            try:
                f = entry_point.load()
            except ImportError:
                logger.warning(
                    "registry '%s' failed to load loader plugin handler for "
                    "entry point '%s'", self.registry_name, entry_point,
                )
                continue
            # maybe verify that f has the valid function signature?
            self.records[entry_point.name] = f

    def get_record(self, name):
        return self.records.get(name)
