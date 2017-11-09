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

from calmjs import loaderplugin
from calmjs.rjs.loaderplugin import RJSLoaderPluginHandlerMixin
from calmjs.rjs.utils import dict_key_update_overwrite_check

logger = getLogger(__name__)
_default_handler = RJSLoaderPluginHandlerMixin('<calmjs.rjs.default>')

RJS_LOADER_PLUGIN_REGISTRY_NAME = 'calmjs.rjs.loader_plugin'
RJS_LOADER_PLUGIN_REGISTRY = 'rjs_loader_plugin_registry'


class LoaderPluginRegistry(loaderplugin.LoaderPluginRegistry):

    def _mapping_to_config_paths(self, mapping, method_prefix):
        """
        Private implementation, please use the public version.

        Additional Arguments:
        method_prefix
            The prefix will be combined with '_to_config_paths' to get
            the actual resolution method from the plugin handlers.
        """

        method_name = method_prefix + '_to_config_paths'
        default_to_config_paths = getattr(_default_handler, method_name)
        paths = {}
        result = {'paths': paths}

        def map_plugin_fragment(plugin, fragment):
            handler = self.get(plugin)
            if handler is None:
                logger.warning(
                    "no handler found for loader plugin '%s', the entry "
                    "{'%s': '%s'} will be dropped from generated mapping; "
                    "this action may be fatal later.", plugin, modname, path,
                )
                return
            dict_key_update_overwrite_check(
                result, 'paths', getattr(handler, method_name)(modname, path))

        def map_default(modname, path):
            # only generate and the mapping if the path assigned to
            # modname in paths is absent or incompatible
            if paths.get(modname) != path[:-3]:
                # this is compatible.
                dict_key_update_overwrite_check(
                    result, 'paths', default_to_config_paths(modname, path))

        # bring ALL the plugin entries to the top to not affect the
        # resolution of standard modules.
        for modname, path in sorted(
                mapping.items(), key=lambda x: ('!' not in x[0], x[0], x[1])):
            plugin_fragment = modname.split('!', 1)
            if len(plugin_fragment) == 1:
                map_default(modname, path)
            else:
                map_plugin_fragment(*plugin_fragment)

        return result

    def modname_sourcepath_mapping_to_config_paths(self, mapping):
        """
        For a mapping of exported module names and the specified source
        locations, produce a mapping that is compatible for usage with
        the ``requirejs.config`` function, using the plugin loaders
        available in this module.

        Returns a dictionary with a single key ``paths`` with the value
        being the new dictionary of the mapping produced.

        Arguments:

        mapping
            A sourcepath mapping, from modname to source.
        """

        return self._mapping_to_config_paths(mapping, 'modname_source')

    def modname_targetpath_mapping_to_config_paths(self, mapping):
        """
        For a mapping of exported module names and the specified target
        locations, produce a mapping that is compatible for usage with
        the ``requirejs.config`` function, using the plugin loaders
        available in this module.

        Returns a dictionary with a single key ``paths`` with the value
        being the new dictionary of the mapping produced.

        Arguments:

        mapping
            A targetpath mapping, from modname to target.
        """

        return self._mapping_to_config_paths(mapping, 'modname_target')
