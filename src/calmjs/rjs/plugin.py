# -*- coding: utf-8 -*-
"""
The plugin system compatibility layer for requirejs.

Given that the plugin definitions are done on top of the requirejs
module system, the plugins are actually the top level modules, with the
arguments after the ``!`` identifier being completely opaque.  This
means that if the underlying loader expects paths in a different way it
will not understand the calmjs mapping from modname to target/modpath as
laid out.

This module provides the foundation to address this issue.  Combined
with the ``loader_plugin`` registry (see ``calmjs.rjs.registry``), this
will allow explicitly defined methods to deal with path resolution, even
for custom JavaScript plugins that are shipped with Python.  As custom
registries for this can be specified, this can cater to even the most
esoteric module setup, such as custom nested plugin configurations; this
can be implemented by calling specific functions nested within each of
the handlers, or the handler could invoke the registry system to get the
required target as the call method provides both the toolchain and the
spec.

As mentioned, loader plugin handlers should be registered to the
calmjs.rjs loader_plugin registry in order for them to be used.  There
are defaults provided, which the RJSToolchain will make use of in its
standard workflow.
"""

import shutil
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join


class LoaderPluginHandler(object):
    """
    Encapsulates a loader plugin for requirejs, this provides a
    framework to deal with path mangling and/or resolution for setting
    up the paths for usage from within a requirejs environment.
    """

    def modname_modpath_to_config_paths(self, modname, modpath):
        """
        In the default tool, this is not used, but this is left here as
        a placeholder.
        """

        return modname, modpath

    def modname_target_to_config_paths(self, modname, target):
        """
        For a given modnames and its target, convert them to the aliased
        locations that will be compatible with how requirejs parses the
        paths argument in its configuration json for a web environment.

        The return value must be a modname and target, which could be
        modified so they fit for usage within the paths mapping for the
        requirejs configuration.

        The default implementation simply add a '?' to the target.
        """

        return modname, target + '?'

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        """
        These need to provide the actual implementation required for the
        production of the final artifact, so this will need to locate
        the resources needed for this set of arguments to function.

        Each of these should return the associated bundled_modpaths,
        bundled_targets, and the export_module_name, after the copying
        or transpilation step was done.
        """

        raise NotImplementedError


class TextPlugin(LoaderPluginHandler):
    """
    A basic text loader plugin handler; does not handle further chained
    loader plugins that have been specified in the modname, as it
    assumes everything between the first and second '!' is the target.
    """

    def strip_plugin(self, value):
        result = value.split('!', 1)
        return result[-1].split('!', 1)[0]

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        # need to keep existing modname intact, call the modname to be
        # served as the keys for the bundled_* values as ththis
        config_modname = self.strip_plugin(modname)
        target = self.strip_plugin(target)
        copy_target = join(spec['build_dir'], target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        shutil.copy(source, copy_target)
        bundled_modpaths = {modname: modpath}
        bundled_targets = {modname: target}
        export_module_names = [modname]
        return bundled_modpaths, bundled_targets, export_module_names

text = TextPlugin()
