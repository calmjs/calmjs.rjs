# -*- coding: utf-8 -*-
"""
This provides a JavaScript "toolchain".

When I have a hammer every problem starts to look like JavaScript.

Honestly, it's a bit easier to deal with JavaScript when one treats that
as a compilation target.

How this works?

1) Write raw JS code without any UMD wrappers, but treat everything in
the file as UMD.  Remember to import everything needed using ``require``
and declare the exported things by assigning it to ``exports``.
2) Leave that file somewhere in the src directory, along with Python
code.
3) Run compile.  They will be compiled into the corresponding thing that
correlates to the Pythonic namespace identifiers.

At least this is the idea, have to see whether this idea actually end up
being sane (it won't be sane, when the entire thing was insane to begin
with).

One final thing: es6 does have modules, imports and exports done in a
different but dedicated syntax.  Though to really support them a proper
es6 compatible environment will be needed, however those are not a norm
at the moment yet, especially given the fact that browsers do not have
support for them quite just yet as of mid 2016.
"""

from __future__ import unicode_literals

import json
import logging
from os.path import dirname
from os.path import join
from os.path import exists
from os.path import isdir
from subprocess import call

from calmjs.toolchain import Toolchain
from calmjs.npm import npm_bin

from .umdjs import UMD_NODE_AMD_HEADER
from .umdjs import UMD_NODE_AMD_FOOTER
from .umdjs import UMD_REQUIREJS_JSON_EXPORT_HEADER
from .umdjs import UMD_REQUIREJS_JSON_EXPORT_FOOTER


logger = logging.getLogger(__name__)

def update_base_requirejs_config(d):
    d.update({
        'paths': {},
        'shim': {},

        'wrapShim': True,

        # other configuration options
        'optimize': "none",
        'generateSourceMaps': False,
        'normalizeDirDefines': "skip",
        'uglify': {
            'toplevel': True,
            'ascii_only': True,
            'beautify': True,
            'max_line_length': 1000,
            'defines': {
                'DEBUG': ['name', 'false']
            },
            'no_mangle': True
        },
        'uglify2': {
            'output': {
                'beautify': True
            },
            'compress': {
                'sequences': False,
                'global_defs': {
                    'DEBUG': False
                }
            },
            'warnings': True,
            'mangle': False
        },
        'useStrict': True,
        'wrap': True,
        'logLevel': 0,
    })


def _transpile_generic_to_umd_node_amd_compat_rjs(reader, writer, indent=8):
    indent = ' ' * indent
    _states = {
        'pad': 3,  # length of the header to trac
    }

    def write_line(line):
        contents = line.strip()
        if _states['pad']:
            if not contents:
                _states['pad'] -= 1
                return
            _states['pad'] = 0
        if contents:
            writer.write(indent)
        writer.write(line)

    line = reader.readline()
    if line.strip() in ("'use strict';", '"use strict";'):
        header_lines = iter(UMD_NODE_AMD_HEADER.splitlines(True))
        writer.write(next(header_lines))
        writer.write(next(header_lines))
        writer.write(indent)
        writer.write(line)
        writer.write(next(header_lines))
    else:
        writer.write(UMD_NODE_AMD_HEADER)
        write_line(line)

    while line:
        line = reader.readline()
        write_line(line)

    writer.write(UMD_NODE_AMD_FOOTER)


class RJSToolchain(Toolchain):
    """
    The toolchain that make use of r.js (from require.js).
    """

    rjs_bin_key = 'rjs_bin'
    rjs_bin = 'r.js'
    build_manifest_name = 'build.js'
    requirejs_config_name = 'config.js'

    def prepare(self, spec):
        """
        Attempts to locate the r.js binary if not already specified.  If
        the binary file was not found, RuntimeError will be raised.
        """

        if self.rjs_bin_key not in spec:
            logger.debug("invoking 'npm bin' to determine node binary path.")
            npm_bin_path = npm_bin()
            if npm_bin_path is None:
                raise RuntimeError(
                    "Attempt to derive node binary path with 'npm bin' "
                    "failed.  Unable to locate r.js automatically."
                )
            spec[self.rjs_bin_key] = join(npm_bin_path, self.rjs_bin)

        if not exists(spec[self.rjs_bin_key]):
            # should we check whether target can be executed?
            raise RuntimeError(
                'r.js binary not found at %s' % spec[self.rjs_bin_key])

        # with requirejs, it would be nice to also build a simple config
        # that can be used from within node with the stuff in just the
        # build directory - if this wasn't already defined for some
        # reason.
        spec['requirejs_config_js'] = join(
            spec['build_dir'], self.requirejs_config_name)
        spec['build_manifest_path'] = join(
            spec['build_dir'], self.build_manifest_name)

        if 'bundle_export_path' not in spec:
            raise RuntimeError(
                "'bundle_export_path' not found in spec")

        if not isdir(dirname(spec['bundle_export_path'])):
            raise RuntimeError(
                "'bundle_export_path' will not be writable")

        keys = ('requirejs_config_js', 'build_manifest_path')
        matched = [k for k in keys if spec['bundle_export_path'] == spec[k]]

        if matched:
            raise RuntimeError(
                "'bundle_export_path' must not be same as '%s'" % matched[0])

        self.transpiler = _transpile_generic_to_umd_node_amd_compat_rjs

    def assemble(self, spec):
        """
        Assemble the library by compiling everything and generate the
        required files for the final bundling.
        """

        compiled_paths = spec['compiled_paths']
        bundled_paths = spec['bundled_paths']
        module_names = spec['module_names']

        # the build config is the file that will be passed to r.js for
        # building the final bundle.
        build_config = {}
        # Set up the statically defined settings.
        update_base_requirejs_config(build_config)
        build_config['shim'].update(spec.get('shim', {}))
        build_config['out'] = spec['bundle_export_path']

        # Update paths with names pointing to built files in build_dir
        # and generate the list of included files into the final bundle.
        build_config['paths'].update(compiled_paths)
        build_config['paths'].update(bundled_paths)
        build_config['include'] = module_names

        with open(spec['build_manifest_path'], 'w') as fd:
            fd.write('(\n')
            json.dump(build_config, fd, indent=4)
            fd.write('\n)')

        # the requirejs config is for usage of the "built" (in this
        # case, transpiled) files, so that the import names are mapped
        # to the right location within the build_dir.
        requirejs_config = {}
        requirejs_config.update(build_config)
        requirejs_config['baseUrl'] = spec['build_dir']

        with open(spec['requirejs_config_js'], 'w') as fd:
            fd.write(UMD_REQUIREJS_JSON_EXPORT_HEADER)
            json.dump(requirejs_config, fd, indent=4)
            fd.write(UMD_REQUIREJS_JSON_EXPORT_FOOTER)

    def link(self, spec):
        """
        Basically link everything up as a bundle, as if statically
        linking everything into "binary" file.
        """

        call([spec[self.rjs_bin_key], '-o', spec['build_manifest_path']])
