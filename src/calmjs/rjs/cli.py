# -*- coding: utf-8 -*-
"""
CalmJS RequireJS cli tools.
"""

from calmjs.toolchain import Spec
from calmjs.rjs.toolchain import RJSToolchain

from calmjs.rjs.dist import generate_transpile_source_maps
from calmjs.rjs.dist import generate_bundled_source_maps

default_toolchain = RJSToolchain()


def make_spec(
        package_name, export_filename=None, working_dir=None, build_dir=None,
        source_registries=('calmjs.module',),
        source_map_method='all', bundled_map_method='all'):
    """
    Produce a spec for the compilation through the RJSToolchain.
    """

    working_dir = working_dir if working_dir else default_toolchain.join_cwd()

    if export_filename is None:
        export_filename = package_name + '.js'

    return Spec(
        bundle_export_path=export_filename,
        build_dir=build_dir,
        transpile_source_map=generate_transpile_source_maps(
            package_name=package_name,
            registries=source_registries,
            method=source_map_method,
        ),
        bundled_source_map=generate_bundled_source_maps(
            package_name=package_name,
            working_dir=working_dir,
            method=bundled_map_method,
        ),
    )


def compile_all(
        package_name, export_filename=None, working_dir=None, build_dir=None,
        source_registries=('calmjs.module',),
        source_map_method='all', bundled_map_method='all',
        toolchain=default_toolchain):
    """
    Invoke the r.js compiler to generate a JavaScript bundle file for a
    given Python package.  The bundle will include all the dependencies
    as specified by it and its parents.

    Arguments:

    package_name
        The name of the Python package to source the dependencies from.

    export_filename
        The filename for the output, can be an absolute path to a file.
        Defaults to the package_name with a '.js' suffix added in the
        working_dir.

    working_dir
        The working directory.  If the package specified any extras
        calmjs requirements (e.g. node_modules), they will be searched
        for from here.  Defaults to current working directory.

    build_dir
        The build directory.  Defaults to a temporary directory that is
        automatically removed when done.

    source_registries
        The calmjs registries to use for gathering sources.  Defaults to
        tuple ('calmjs.module',), i.e. the default module registry.
        Naturally, multiple registries can be specified.

    source_map_method
        The acquisition method for the source mapping for the given
        package from the source_registries specified.  Choices are
        between 'all', 'top' or None.  Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the sources declared for each of those modules.
        'top'
            Only acquire the sources for the specified package.
        'none'
            Do not acquire sources.  Useful for creating bundles of just
            the bundled sources.

    bundled_map_method
        The acquisition method for the bundled sources for the given
        module.  Choices are between 'all', 'top' or None.  Defaults to
        'all'.

        'all'
            Traverse the dependency graph for the specified package and
            acquire the declarations.
        'top'
            Only acquire the bundled sources declared for the specified
            package.
        'none'
            Do not bundle the declared bundles.  Useful for cases where
            these may be provided by other bundles, or for cases where
            only the declared sources are desired.

        Defaults to 'all'.

    toolchain
        The toolchain instance to use.  Default is the instance in this
        module.

    Naturally, this package will need all its extras calmjs declarations
    available, plus the availability of r.js, before anything can be
    done.
    """

    spec = make_spec(
        package_name=package_name,
        export_filename=export_filename,
        working_dir=working_dir,
        build_dir=build_dir,
        source_registries=source_registries,
        source_map_method=source_map_method,
        bundled_map_method=bundled_map_method,
    )
    toolchain(spec)
    return spec
