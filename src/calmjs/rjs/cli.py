# -*- coding: utf-8 -*-
"""
CalmJS RequireJS cli tools.
"""

from calmjs.toolchain import Spec
from calmjs.rjs.toolchain import RJSToolchain
from calmjs.rjs.toolchain import spec_update_source_map

from calmjs.rjs.dist import generate_transpile_source_maps
from calmjs.rjs.dist import generate_bundle_source_maps

default_toolchain = RJSToolchain()


def create_spec(
        package_names, export_filename=None, working_dir=None, build_dir=None,
        source_registries=('calmjs.module',),
        source_map_method='all', bundle_map_method='all',
        transpile_no_indent=False):
    """
    Produce a spec for the compilation through the RJSToolchain.

    Arguments:

    package_names
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
        between 'all', 'explicit' or 'none'.  Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the sources declared for each of those modules.
        'explicit'
            Only acquire the sources for the specified package.
        'none'
            Do not acquire sources.  Useful for creating bundles of just
            the bundle sources.

    bundle_map_method
        The acquisition method for the bundle sources for the given
        module.  Choices are between 'all', 'explicit' or 'none'.
        Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package and
            acquire the declarations.
        'explicit'
            Only acquire the bundle sources declared for the specified
            package.
        'empty'
            Include all entries in a way that ensure that requirejs does
            not include them.  Useful for cases where these may be
            provided by other bundles, or for cases where only the
            declared sources are desired.
        'none'
            Do not specify any bundle files.  This only works for
            packages that have declared these as optional

        Defaults to 'all'.

    transpile_no_indent
        Ensure that the transpile targets have no indents.

    """

    working_dir = working_dir if working_dir else default_toolchain.join_cwd()

    if export_filename is None:
        # Take the final package name for now...
        if package_names:
            export_filename = package_names[-1] + '.js'
        else:
            export_filename = 'calmjs.rjs.export.js'

    spec = Spec(
        bundle_export_path=export_filename,
        build_dir=build_dir,
        transpile_no_indent=transpile_no_indent,
    )

    spec_update_source_map(spec, generate_transpile_source_maps(
        package_names=package_names,
        registries=source_registries,
        method=source_map_method,
    ), 'transpile_source_map')

    spec_update_source_map(spec, generate_bundle_source_maps(
        package_names=package_names,
        working_dir=working_dir,
        method=bundle_map_method,
    ), 'bundle_source_map')

    return spec


def compile_all(
        package_names, export_filename=None, working_dir=None, build_dir=None,
        source_registries=('calmjs.module',),
        source_map_method='all', bundle_map_method='all',
        transpile_no_indent=False,
        toolchain=default_toolchain):
    """
    Invoke the r.js compiler to generate a JavaScript bundle file for a
    given Python package.  The bundle will include all the dependencies
    as specified by it and its parents.

    Arguments:

    toolchain
        The toolchain instance to use.  Default is the instance in this
        module.

    For other arguments, please refer to create_spec as they are passed
    to it.

    Naturally, this package will need all its extras calmjs declarations
    available, plus the availability of r.js, before anything can be
    done.
    """

    spec = create_spec(
        package_names=package_names,
        export_filename=export_filename,
        working_dir=working_dir,
        build_dir=build_dir,
        source_registries=source_registries,
        source_map_method=source_map_method,
        bundle_map_method=bundle_map_method,
        transpile_no_indent=transpile_no_indent,
    )
    toolchain(spec)
    return spec
