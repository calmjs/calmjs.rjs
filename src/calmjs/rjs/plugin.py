# -*- coding: utf-8 -*-
"""
The plugin system compatibility layer for requirejs.

Given that the plugin definitions are done on top of the module system,
its declarations are on the same level however each plugin has the
potential to implement their own syntax system, thus the resource name
referenced can be anything.  Thus this module is needed to normalize the
provided "modname" entries into the ones that are understood here.  The
functions must have the following signature

    def plugin(toolchain, spec, modname, source, target, modpath):
        # do processing
        # typical return value
        return {modname: modpath}, {modname: target}, [modname]

The RJSToolchain compile_plugins method will make use of functions of
the above type registered to the registry system.
"""

import shutil
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join


def text(toolchain, spec, modname, source, target, modpath):
    """
    Each of these should return this bundled_modpaths, bundled_targets,
    and the exported module_name.
    """

    plugin_name, resource_name = modname.split('!', 1)
    target = resource_name
    copy_target = join(spec['build_dir'], target)
    if not exists(dirname(copy_target)):
        makedirs(dirname(copy_target))
    shutil.copy(source, copy_target)
    bundled_modpaths = {modname: target}
    bundled_targets = {modname: target}
    module_names = [modname]
    return bundled_modpaths, bundled_targets, module_names
