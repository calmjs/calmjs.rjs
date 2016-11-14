# -*- coding: utf-8 -*-
"""
Integration with various tools proided by the calmjs.dev package
"""

import logging
from os.path import join
from os.path import sep

from calmjs.exc import ToolchainAbort
from calmjs.registry import get
from calmjs.toolchain import ARTIFACT_PATHS
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import TEST_MODULE_PATHS_MAP
from calmjs.utils import json_dump
from calmjs.utils import json_dumps

try:
    from calmjs.dev.karma import BEFORE_KARMA
except ImportError:  # pragma: no cover
    # Package not available; None is the advice blackhole
    BEFORE_KARMA = None

from calmjs.rjs.registry import RJS_LOADER_PLUGIN_REGISTRY
from calmjs.rjs.registry import RJS_LOADER_PLUGIN_REGISTRY_NAME
from calmjs.rjs.requirejs import extract_defines_with_deps_from_paths
from calmjs.rjs.umdjs import UMD_REQUIREJS_JSON_EXPORT_HEADER
from calmjs.rjs.umdjs import UMD_REQUIREJS_JSON_EXPORT_FOOTER

logger = logging.getLogger(__name__)


TEST_SCRIPT_TEMPLATE = """
var deps = %s;
var tests = %s;

var start = function() {
    // The test function will then require all the tests be available as
    // karma starts.
    require(tests, window.__karma__.start);
};

requirejs.config({
    // Karma serves files from '/base'
    baseUrl: '/base',
    // ask RequireJS to load all dependencies
    deps: deps,
    // start test run, once Require.js is done
    callback: start
});

window.DEBUG = true;
"""


def rjs_advice(spec, extras=None):
    # As requirejs has specific integration requirements with karma,
    # a test runner the calmjs.dev package provides, advise that
    # runner that before its execution, special handling needs to be
    # done to correct the generated configuration file.
    spec.advise(BEFORE_KARMA, karma_requirejs, spec)


def process_artifacts(paths):
    """
    If they are provided, assuming the defined modules there will not be
    listed as a deps for loading.
    """

    # TODO figure out how to have a flag to disable this feature for use
    # cases where this is undesirable (e.g. performance reasons).
    return extract_defines_with_deps_from_paths(paths)


def karma_requirejs(spec):
    """
    An advice for the karma runtime before execution of karma that is
    needed for integrating the requirejs framework for testing into
    karma; needed when RJSToolchain was used for artifact generation.

    This advice should be registered to BEFORE_KARMA by RJSToolchain.

    This will modify the related items in spec for the generation of the
    karma.conf.js to ensure compatibility with requirejs idioms for the
    execution of the tests through karma.
    """

    # Importing this here as these modules may not be available, so to
    # avoid potential issues, import them within the scope of this
    # function; this function should never be called if the calmjs.dev
    # python package is not available for import (and the setup should
    # not add this to a valid advice).

    try:
        from calmjs.dev import karma
    except ImportError:
        logger.error(
            "package 'calmjs.dev' not available; cannot apply requirejs "
            "specific information without karma being available."
        )
        return

    required_keys = [karma.KARMA_CONFIG, BUILD_DIR]
    for key in required_keys:
        if key not in spec:
            logger.error(
                "'%s' not provided by spec; aborting configuration for karma "
                "test runner", key
            )
            raise ToolchainAbort("spec missing key '%s'" % key)

    config = spec.get(karma.KARMA_CONFIG)
    config_files = config.get('files', [])
    build_dir = spec.get(BUILD_DIR)
    plugin_registry = spec.get(RJS_LOADER_PLUGIN_REGISTRY)
    if not plugin_registry:
        logger.warning(
            'no rjs loader plugin registry provided in spec; '
            "falling back to default registry '%s'",
            RJS_LOADER_PLUGIN_REGISTRY_NAME
        )
        plugin_registry = get(RJS_LOADER_PLUGIN_REGISTRY_NAME)

    test_module_paths_map = spec.get(TEST_MODULE_PATHS_MAP, {})
    test_conf = plugin_registry.modname_target_mapping_to_config_paths(
        test_module_paths_map)

    # Ensure '/absolute' is prefixed like so to eliminate spurious error
    # messages in the test runner, simply because the requirejs plugin
    # will try to go through this mechanism to find a timestamp and fail
    # to find its expected path, triggering the unwanted messages.  This
    # naive prefixing is actually consistent for all platforms including
    # Windows...
    new_paths = {
        # however, the actual path fragments need to be split and joined
        # with the web standard '/' separator.
        k: '/absolute' + '/'.join(v.split(sep))
        for k, v in test_conf['paths'].items()
    }

    test_conf['paths'] = new_paths
    test_config_path = spec['karma_requirejs_test_config'] = join(
        build_dir, 'requirejs_test_config.js')
    with open(test_config_path, 'w') as fd:
        fd.write(UMD_REQUIREJS_JSON_EXPORT_HEADER)
        json_dump(test_conf, fd)
        fd.write(UMD_REQUIREJS_JSON_EXPORT_FOOTER)

    # Export all the module dependencies first so they get pre-loaded
    # and thus be able to be loaded synchronously by test modules.
    deps = sorted(spec.get('export_module_names', []))

    if spec.get(ARTIFACT_PATHS):
        # TODO have a flag of some sort for flagging this as optional.
        deps.extend(process_artifacts(spec.get(ARTIFACT_PATHS)))

    # Include tests separately
    tests = sorted(test_module_paths_map.keys())

    test_script_path = spec['karma_requirejs_test_script'] = join(
        build_dir, 'karma_test_init.js')
    with open(test_script_path, 'w') as fd:
        fd.write(TEST_SCRIPT_TEMPLATE % (json_dumps(deps), json_dumps(tests)))

    frameworks = ['requirejs']
    frameworks.extend(config['frameworks'])
    config['frameworks'] = frameworks
    # rebuild the files listing in specific ordering as the load order
    # matters from within a test browser spawned by karma.
    files = []
    # first include the configuration files
    files.extend(spec.get(CONFIG_JS_FILES, []))
    # then append the test configuration path
    files.append(test_config_path)
    # then the script
    files.append(test_script_path)
    # then extend the configured paths but do not auto-include them.
    files.extend({'pattern': f, 'included': False} for f in config_files)
    # update the file listing with modifications; this will be written
    # out as part of karma.conf.js by the KarmaRuntime.
    config['files'] = files
