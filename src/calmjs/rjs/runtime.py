# -*- coding: utf-8 -*-
"""
The calmjs runtime collection
"""

from argparse import SUPPRESS
from calmjs.argparse import StoreDelimitedList
from calmjs.runtime import ToolchainRuntime

from calmjs.rjs.dist import extras_calmjs_methods
from calmjs.rjs.dist import source_map_methods_list
from calmjs.rjs.dist import calmjs_module_registry_methods
from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import default_toolchain


class RJSRuntime(ToolchainRuntime):
    """
    Runtime for the RJSToolchain

    Example: generate a require.js artifact

    $ calmjs rjs example.package
    """

    def __init__(self, toolchain, description='r.js bundler tool', *a, **kw):
        super(RJSRuntime, self).__init__(
            cli_driver=toolchain, description=description, *a, **kw)

    def init_argparser_export_target(self, argparser):
        super(RJSRuntime, self).init_argparser_export_target(
            argparser,
            help='output filename; defaults to last ${package_name}.js',
        )

    def init_argparser_working_dir(self, argparser):
        super(RJSRuntime, self).init_argparser_working_dir(
            argparser,
            explanation=(
                'for this tool it will be used as the base directory to '
                'find source files declared for bundling; '
            ),
        )

    def init_argparser(self, argparser):
        """
        Other runtimes (or users of ArgumentParser) can pass their
        subparser into here to collect the arguments here for a
        subcommand.
        """

        super(RJSRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '--source-map-method', default='all',
            dest='source_map_method',
            choices=sorted(source_map_methods_list.keys()),
            help='the acquisition method for getting the source mappings from '
                 'the source registry for the given packages; default: all',
        )

        argparser.add_argument(
            '--source-registry', default=None,
            dest='source_registries', action=StoreDelimitedList,
            help='comma separated list of registries to use for gathering '
                 'JavaScript sources from the given Python packages; default '
                 'behavior is to auto-select, enable verbose output to check '
                 'to see which ones were selected',
        )

        argparser.add_argument(
            '--source-registry-method', default='all',
            dest='source_registry_method',
            choices=sorted(calmjs_module_registry_methods.keys()),
            help='the acquisition method for getting the list of source '
                 'registries to use for the given packages; default: all',
        )

        argparser.add_argument(
            '--bundle-map-method', default='all',
            dest='bundle_map_method',
            choices=sorted(extras_calmjs_methods.keys()),
            help='the acquisition method for the bundle sources for the given '
                 'packages; default: all',
        )

        argparser.add_argument(
            '--transpile-no-indent',
            dest='transpile_no_indent', action='store_true',
            help='disable indentation of transpile sources',
        )

        argparser.add_argument(
            'package_names', help='names of the python package to use',
            metavar='package_names', nargs='+',
        )

    def create_spec(
            self, package_names=(), export_target=None,
            working_dir=None,
            build_dir=None,
            source_registry_method='all', source_registries=None,
            source_map_method='all', bundle_map_method='all',
            transpile_no_indent=False,
            toolchain=None, **kwargs):
        """
        Accept all arguments, but also the explicit set of arguments
        that get passed down onto the toolchain.
        """

        return create_spec(
            package_names=package_names,
            export_target=export_target,
            working_dir=working_dir,
            build_dir=build_dir,
            source_registry_method=source_registry_method,
            source_registries=source_registries,
            source_map_method=source_map_method,
            bundle_map_method=bundle_map_method,
            transpile_no_indent=transpile_no_indent,
        )


default = RJSRuntime(default_toolchain)
