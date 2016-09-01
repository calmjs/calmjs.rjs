# -*- coding: utf-8 -*-
"""
Module that links to the calmjs.dist, for use with RJSToolchain.
"""

import logging

from os import getcwd
from os.path import join
from os.path import isdir

from calmjs.registry import get
from calmjs.dist import get_extras_calmjs
from calmjs.dist import get_module_registry_dependencies
from calmjs.dist import flatten_extras_calmjs
from calmjs.dist import flatten_module_registry_dependencies

logger = logging.getLogger(__name__)
_default = 'all'

module_registry_dependencies_methods = {
    'all': flatten_module_registry_dependencies,
    'explicit': get_module_registry_dependencies,
    'none': None,
}

extras_calmjs_methods = {
    'all': flatten_extras_calmjs,
    'explicit': get_extras_calmjs,
    'none': None,
}


def acquire_method(methods, key, default=_default):
    return methods.get(key, methods.get(default))


def generate_transpile_source_maps(
        package_names, registries=('calmjs.module',), method=_default):
    """
    Invoke the module_registry_dependencies family of dist functions,
    with the specified registries, to produce the required source maps.

    Arguments:

    package_names
        The names of the Python package to generate the source maps for.
    registries
        The names of the registries to source the packages from.
    method
        The method to acquire the dependencies for the given module
        across all the registries specified.  Choices are between 'all',
        'explicit' or None.  Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the mappings declared for each of those modules.
        'explicit'
            Only acquire the declared sources for the specified package.
        'none'
            Produce an empty source map.

        Defaults to 'all'.
    """

    acquire_module_registry_dependencies = acquire_method(
        module_registry_dependencies_methods, method)

    if acquire_module_registry_dependencies is None:
        return {}

    transpile_source_map = {}
    for registry_key in registries:
        transpile_source_map.update(acquire_module_registry_dependencies(
            package_names, registry_key=registry_key))

    return transpile_source_map


def generate_bundled_source_maps(
        package_names, working_dir=None, method=_default):
    """
    Acquire the bundled source maps through the calmjs registry system.

    Arguments:

    package_names
        The names of the package to acquire the sources for.
    working_dir
        The working directory.  Defaults to current working directory.
    method
        The method to acquire the bundled sources for the given module.
        Choices are between 'all', 'explicit' or None.

        'all'
            Traverse the dependency graph for the specified package and
            acquire the declarations. [default]
        'explicit'
            Only acquire the bundled sources declared for the specified
            package.
        'none'
            Produce an empty source map.  For requirejs, this means the
            default fallback behavior of loading through CommonJS will
            be used, if needed.  If truly none are required, try using
            'empty' instead.

        Defaults to 'all'.
    """

    working_dir = working_dir if working_dir else getcwd()
    acquire_extras_calmjs = acquire_method(extras_calmjs_methods, method)

    if acquire_extras_calmjs is None:
        return {}

    # the extras keys will be treated as valid Node.js package manager
    # subdirectories.
    valid_pkgmgr_dirs = set(get('calmjs.extras_keys').iter_records())
    extras_calmjs = acquire_extras_calmjs(package_names)
    bundled_source_map = {}

    for mgr in extras_calmjs:
        if mgr not in valid_pkgmgr_dirs:
            continue
        basedir = join(working_dir, mgr)
        if not isdir(basedir):
            if extras_calmjs[mgr]:
                logger.warning(
                    "acquired extras_calmjs needs from '%s', but working "
                    "directory '%s' does not contain it; bundling may fail.",
                    mgr, working_dir
                )
            continue  # pragma: no cover

        for k, v in extras_calmjs[mgr].items():
            bundled_source_map[k] = join(basedir, v)

    return bundled_source_map
