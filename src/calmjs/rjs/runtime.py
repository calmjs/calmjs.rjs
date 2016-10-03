# -*- coding: utf-8 -*-
"""
The calmjs runtime collection
"""

from calmjs.runtime import ToolchainRuntime

from calmjs.rjs.dist import extras_calmjs_methods
from calmjs.rjs.dist import source_map_methods_list
from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import default_toolchain


class RJSRuntime(ToolchainRuntime):
    """
    A calmjs runtime

    e.g

    $ calmjs npm --init example.package
    $ calmjs npm --install example.package
    """

    def __init__(self, toolchain, description='r.js bundler tool', *a, **kw):
        super(RJSRuntime, self).__init__(
            toolchain, description=description, *a, **kw)

    def init_argparser(self, argparser):
        """
        Other runtimes (or users of ArgumentParser) can pass their
        subparser into here to collect the arguments here for a
        subcommand.
        """

        super(RJSRuntime, self).init_argparser(argparser)

        argparser.add_argument(
            '--export-filename', default=None,
            dest='export_filename',
            help='output filename; defaults to last ${package_name}.js',
        )

        cwd = self.cli_driver.join_cwd()
        argparser.add_argument(
            '--working-dir', default=cwd,
            dest='working_dir',
            help='the working directory; for this tool it will be used as the '
                 'base directory to find source files declared for bundling; '
                 'default is current working directory (%s)' % cwd,
        )

        argparser.add_argument(
            '--source-registry', default=('calmjs.module',),
            dest='source_registries', nargs='+',
            help='the registries to use for gathering JavaScript sources from '
                 'Python packages; default: calmjs.module',
        )

        argparser.add_argument(
            '--source-map-method', default='all',
            dest='source_map_method',
            choices=sorted(source_map_methods_list.keys()),
            help='the acquisition method for getting the source mappings from '
                 'the source registry for the given packages',
        )

        argparser.add_argument(
            '--bundle-map-method', default='all',
            dest='bundle_map_method',
            choices=sorted(extras_calmjs_methods.keys()),
            help='the acquisition method for the bundle sources for the given '
                 'packages',
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
            self, package_names=(), export_filename=None, working_dir=None,
            build_dir=None, source_registries=('calmjs.module',),
            source_map_method='all', bundle_map_method='all',
            transpile_no_indent=False,
            toolchain=None, **kwargs):
        """
        Accept all arguments, but also the explicit set of arguments
        that get passed down onto the toolchain.
        """

        return create_spec(
            package_names=package_names,
            export_filename=export_filename, working_dir=working_dir,
            build_dir=build_dir, source_registries=source_registries,
            source_map_method=source_map_method,
            bundle_map_method=bundle_map_method,
            transpile_no_indent=transpile_no_indent,
        )


default = RJSRuntime(default_toolchain)
