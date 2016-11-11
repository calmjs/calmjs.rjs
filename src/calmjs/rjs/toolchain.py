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
import sys
from os.path import dirname
from os.path import join
from os.path import exists
from os.path import isdir
from os.path import isfile
from subprocess import call

from calmjs.registry import get
from calmjs.toolchain import Toolchain
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import EXPORT_TARGET
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import EXPORT_MODULE_NAMES

from .utils import dict_get
from .utils import dict_key_update_overwrite_check
from .dev import rjs_advice
from .exc import RJSRuntimeError
from .exc import RJSExitError
from .registry import RJS_LOADER_PLUGIN_REGISTRY
from .registry import RJS_LOADER_PLUGIN_REGISTRY_KEY
from .registry import RJS_LOADER_PLUGIN_REGISTRY_NAME
from .requirejs import extract_all_amd_requires
from .requirejs import process_path
from .umdjs import UMD_NODE_AMD_HEADER
from .umdjs import UMD_NODE_AMD_FOOTER
from .umdjs import UMD_NODE_AMD_INDENT
from .umdjs import UMD_REQUIREJS_JSON_EXPORT_HEADER
from .umdjs import UMD_REQUIREJS_JSON_EXPORT_FOOTER

from .dist import EMPTY

logger = logging.getLogger(__name__)

_PLATFORM_SPECIFIC_RUNTIME = {
    'win32': 'r.js.cmd',
}
_DEFAULT_RUNTIME = 'r.js'

# reserved spec keys for this package
REQUIREJS_PLUGINS = 'requirejs_plugins'
STUB_MISSING_WITH_EMPTY = 'stub_missing_with_empty'


def spec_update_source_map(spec, source_map, default_source_key):
    default = dict_get(spec, default_source_key)
    for modname, source in source_map.items():
        parts = modname.split('!', 1)
        if len(parts) == 1:
            # default
            default[modname] = source
            continue

        plugin_name, arguments = parts
        plugins = dict_get(spec, REQUIREJS_PLUGINS)
        plugin = dict_get(plugins, plugin_name)
        plugin[modname] = source


def get_rjs_runtime_name(platform):
    return _PLATFORM_SPECIFIC_RUNTIME.get(platform, 'r.js')


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


def _null_transpiler(spec, reader, writer):
    line = reader.readline()
    while line:
        writer.write(line)
        line = reader.readline()


def _transpile_generic_to_umd_node_amd_compat_rjs(spec, reader, writer):
    level = UMD_NODE_AMD_INDENT
    indent = '' if spec.get('transpile_no_indent') else ' ' * level
    _states = {
        'pad': 3,  # length of the header to track
    }

    def write_line(line):
        contents = line.strip()
        if _states['pad']:
            if not contents:
                writer.discard(line)
                _states['pad'] -= 1
                return
            _states['pad'] = 0
        if contents:
            writer.write_padding(indent)
        writer.write(line)

    line = reader.readline()
    if line.strip() in ("'use strict';", '"use strict";'):
        header_lines = iter(UMD_NODE_AMD_HEADER.splitlines(True))
        writer.write_padding(next(header_lines))
        writer.write_padding(next(header_lines))
        writer.write_padding(indent)
        writer.write(line)
        writer.write_padding(next(header_lines))
    else:
        writer.write_padding(UMD_NODE_AMD_HEADER)
        write_line(line)

    while line:
        line = reader.readline()
        write_line(line)

    writer.write_padding(UMD_NODE_AMD_FOOTER)


def _rjs_transpiler(spec, reader, writer):
    # ensure the reader is done from beginning
    reader.seek(0)
    line = reader.readline()
    while line and line.strip() in ('', "'use strict';", '"use strict";'):
        line = reader.readline()
    # back to the beginning
    reader.seek(0)
    if line.strip().startswith('define('):
        return _null_transpiler(spec, reader, writer)
    else:
        return _transpile_generic_to_umd_node_amd_compat_rjs(
            spec, reader, writer)


class RJSToolchain(Toolchain):
    """
    The toolchain that make use of r.js (from require.js).
    """

    rjs_bin_key = 'rjs_bin'
    rjs_bin = get_rjs_runtime_name(sys.platform)
    build_manifest_name = 'build.js'
    requirejs_config_name = 'config.js'
    node_config_name = 'node.js'

    def __init__(
            self,
            loader_plugin_registry=RJS_LOADER_PLUGIN_REGISTRY_NAME,
            *a, **kw):
        super(RJSToolchain, self).__init__(*a, **kw)
        self.loader_plugin_registry = get(loader_plugin_registry)
        self.binary = self.rjs_bin
        self._set_env_path_with_node_modules()

    def setup_transpiler(self):
        self.transpiler = _rjs_transpiler

    def build_compile_entries(self):
        return super(RJSToolchain, self).build_compile_entries() + (
            ('plugin', 'plugin', 'plugins'),
        )

    def compile_plugin(self, spec, entries):
        """
        The associated spec entry that ultimately call this should be
        prepared through this class's prepare method.
        """

        plugins_modpaths = {}
        plugins_targets = {}
        export_module_names = []

        for modname, source, target, modpath in entries:
            plugin_name, arguments = modname.split('!', 1)
            handler = spec[RJS_LOADER_PLUGIN_REGISTRY].get_record(plugin_name)
            p_pm, p_pt, m_ns = handler(
                self, spec, modname, source, target, modpath)
            _spec = locals()
            dict_key_update_overwrite_check(_spec, 'plugins_modpaths', p_pm)
            dict_key_update_overwrite_check(_spec, 'plugins_targets', p_pt)
            export_module_names.extend(m_ns)
        return plugins_modpaths, plugins_targets, export_module_names

    def modname_source_target_to_modpath(self, spec, modname, source, target):
        """
        Return 'empty:' if the source is also that, as this is the only
        way to ensure r.js won't try to bundle that location if any
        modules try to require whatever that was.  Also not raising an
        exception simply because these entries are needed to be added to
        the resulting paths.
        """

        return EMPTY if source == EMPTY else modname

    def transpile_modname_source_target(self, spec, modname, source, target):
        if source == EMPTY:
            # This is inserted by the source mapper if this item was
            # marked to be ignored for r.js, and so don't bother letting
            # parent "compile" this (which is just a simple copying)
            return
        super(RJSToolchain, self).transpile_modname_source_target(
            spec, modname, source, target)

    def prepare(self, spec):
        """
        Attempts to locate the r.js binary if not already specified.  If
        the binary file was not found, RJSRuntimeError will be raised.
        """

        loader_plugin_registry = get(spec.get(RJS_LOADER_PLUGIN_REGISTRY_KEY))
        loader_plugin_registry = spec[RJS_LOADER_PLUGIN_REGISTRY] = (
            loader_plugin_registry or self.loader_plugin_registry)

        if self.rjs_bin_key not in spec:
            which_bin = spec[self.rjs_bin_key] = (
                self.which() or self.which_with_node_modules())
            if which_bin is None:
                raise RJSRuntimeError(
                    "unable to locate '%s'" % self.binary)
            logger.debug("using '%s' as '%s'", which_bin, self.binary)
        elif not exists(spec[self.rjs_bin_key]):
            # should we check whether target can be executed?
            raise RJSRuntimeError(
                "'%s' does not exist; cannot be used as '%s' binary" % (
                    spec[self.rjs_bin_key],
                    self.rjs_bin
                )
            )

        # with requirejs, it would be nice to also build a simple config
        # that can be used from within node with the stuff in just the
        # build directory - if this wasn't already defined for some
        # reason.
        spec['requirejs_config_js'] = join(
            spec['build_dir'], self.requirejs_config_name)
        spec['node_config_js'] = join(
            spec['build_dir'], self.node_config_name)
        spec['build_manifest_path'] = join(
            spec[BUILD_DIR], self.build_manifest_name)

        if EXPORT_TARGET not in spec:
            raise RJSRuntimeError(
                "'%s' not found in spec" % EXPORT_TARGET)

        # no effect if EXPORT_TARGET already absolute.
        spec[EXPORT_TARGET] = spec[EXPORT_TARGET] = self.join_cwd(
            spec[EXPORT_TARGET])
        # Only providing the standard web one, as the node version is
        # for internal testing
        spec[CONFIG_JS_FILES] = [spec['requirejs_config_js']]

        if not isdir(dirname(spec[EXPORT_TARGET])):
            raise RJSRuntimeError(
                "'%s' will not be writable" % EXPORT_TARGET)
        logger.debug(
            "'%s' declared to be '%s'",
            EXPORT_TARGET, spec[EXPORT_TARGET]
        )

        keys = ('requirejs_config_js', 'build_manifest_path')
        matched = [k for k in keys if spec[EXPORT_TARGET] == spec[k]]

        if matched:
            raise RJSRuntimeError(
                "'%s' must not be same as '%s'" % (EXPORT_TARGET, matched[0]))

        plugin_source_map = spec['plugin_source_map'] = {}
        raw_plugins = spec.get(REQUIREJS_PLUGINS, {})
        for key, value in raw_plugins.items():
            handler = loader_plugin_registry.get_record(key)
            if handler:
                # assume handler will do the job.
                plugin_source_map.update(value)
                logger.debug("found handler for '%s' loader plugin", key)
            else:
                logger.warning(
                    "handler for '%s' loader plugin not found in registry; "
                    "as arguments associated with requirejs loader plugins "
                    "are specific, processing is disabled and the following "
                    "names will not be compiled into the target: %s",
                    key, sorted(value.keys()),
                )

        # setup own advice.
        rjs_advice(spec)

    def assemble(self, spec):
        """
        Assemble the library by compiling everything and generate the
        required files for the final bundling.
        """

        export_module_names = spec[EXPORT_MODULE_NAMES]

        # the build config is the file that will be passed to r.js for
        # building the final bundle.
        build_config = {}
        # Set up the statically defined settings.
        update_base_requirejs_config(build_config)
        build_config['shim'].update(spec.get('shim', {}))
        build_config['out'] = spec[EXPORT_TARGET]
        build_config['include'] = export_module_names

        # the requirejs config is for usage of the "built" (in this
        # case, transpiled) files, so that the import names are mapped
        # to the right location within the build_dir.  Doing this here
        # because the path handling becomes different here.
        requirejs_config = {}
        requirejs_config.update(build_config)

        # Update paths with names pointing to built files in build_dir
        # for the configuration for serving.
        requirejs_config['baseUrl'] = spec['build_dir']
        # leave as empty as this is only applicable to build
        requirejs_config['include'] = []

        # These are the configured paths
        configured_paths = {}
        # as a last resort, all targets loaded will have their soruce
        # tree inspected for module names they need; this is done so
        # that the r.js bundler will not choke when it finds missing
        # paths.
        parsed_required_paths = {}
        # the final result will be merged here.
        requirejs_config['paths'] = {}

        emptied = set()

        # correct the targets by appending a ? for the affected targets
        source_prefixes = ('transpiled', 'bundled')
        for prefix in source_prefixes:
            key = prefix + '_targets'
            modpaths_group = prefix + '_modpaths'
            for modname, target in spec[key].items():
                if spec[modpaths_group].get(modname) == EMPTY:
                    # simply omit empty exported modpaths_group.
                    emptied.add(modname)
                    continue
                if target.endswith('.js'):
                    full_target = join(spec[BUILD_DIR], *target.split('/'))
                    # requirejs loader will automatically append another
                    # .js filename extension as it doesn't know anything
                    # about the path, so to avoid this append a '?', the
                    # canonical way to tell it not to do this.
                    if isfile(full_target):
                        configured_paths[modname] = target + '?'
                        # also, do the parsing for the parsed paths
                        # this should also preemptively report potential
                        # syntax error.
                        parsed_required_paths.update({
                            modname: EMPTY for modname in (process_path(
                                full_target, extract_all_amd_requires) or [])
                        })
                        continue

                configured_paths[modname] = target

        # finally, update the config with the plugin targets, which
        # should have been correctly processed by the plugin handlers.
        configured_paths.update(spec['plugins_targets'])

        missing_modname = (
            set(parsed_required_paths) - set(configured_paths) - emptied)

        # now merge the results together and figure out the logger.
        if spec.get(STUB_MISSING_WITH_EMPTY):
            missing_logger = logger.info
            requirejs_config['paths'].update(parsed_required_paths)
            build_config['paths'].update({
                modname: parsed_required_paths[modname]
                for modname in missing_modname
            })
        else:
            # TODO adjust the message somewhat for the error case
            missing_logger = logger.error

        requirejs_config['paths'].update(configured_paths)

        # Back to the build config.  Grab only paths that have been
        # made empty and apply it to the build configuration, plus log
        # the modules.
        if missing_modname:
            missing_logger(
                'source file(s) referenced modules that are missing in the '
                'build directory: %s', ', '.join(
                    sorted(repr(m) for m in missing_modname))
            )

        prefixes = ('transpiled', 'bundled', 'plugins')
        for prefix in prefixes:
            key = prefix + '_modpaths'
            build_config['paths'].update(
                {k: v for k, v in spec[key].items() if v == EMPTY})

        # build a configuration for usage directly from nodejs (which
        # may or may not work, but a test can find out).
        nodejs_config = {}
        nodejs_config.update(build_config)
        nodejs_config['baseUrl'] = spec['build_dir']

        # write out the configuration files
        with open(spec['build_manifest_path'], 'w') as fd:
            fd.write('(\n')
            json.dump(build_config, fd, indent=4)
            fd.write('\n)')

        with open(spec['requirejs_config_js'], 'w') as fd:
            fd.write(UMD_REQUIREJS_JSON_EXPORT_HEADER)
            json.dump(requirejs_config, fd, indent=4)
            fd.write(UMD_REQUIREJS_JSON_EXPORT_FOOTER)

        with open(spec['node_config_js'], 'w') as fd:
            fd.write(UMD_REQUIREJS_JSON_EXPORT_HEADER)
            json.dump(nodejs_config, fd, indent=4)
            fd.write(UMD_REQUIREJS_JSON_EXPORT_FOOTER)

    def link(self, spec):
        """
        Basically link everything up as a bundle, as if statically
        linking everything into "binary" file.
        """

        args = (spec[self.rjs_bin_key], '-o', spec['build_manifest_path'])
        logger.info('invoking %s %s %s', *args)
        rc = call(args)
        if rc != 0:
            logger.error(
                "the spec may have contained insufficient information "
                "required for r.js to locate all dependencies it needs for "
                "the final build process."
            )
            raise RJSExitError(rc, spec[self.rjs_bin_key])
