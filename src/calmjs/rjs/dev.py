# -*- coding: utf-8 -*-
"""
Integration with various tools proided by the calmjs.dev package
"""

import json
import logging
from os.path import join

from calmjs.exc import ToolchainAbort
from calmjs.registry import get
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import CALMJS_MODULE_REGISTRY_NAMES
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import SOURCE_PACKAGE_NAMES
from calmjs.toolchain import TEST_MODULE_PATHS

from calmjs.rjs.registry import RJS_LOADER_PLUGIN_REGISTRY
from calmjs.rjs.registry import RJS_LOADER_PLUGIN_REGISTRY_NAME
from calmjs.rjs.umdjs import UMD_REQUIREJS_JSON_EXPORT_HEADER
from calmjs.rjs.umdjs import UMD_REQUIREJS_JSON_EXPORT_FOOTER

logger = logging.getLogger(__name__)


TEST_SCRIPT_TEMPLATE = """
var tests = %s;

requirejs.config({
    // Karma serves files from '/base'
    baseUrl: '/base',
    // ask Require.js to load these files (all our tests)
    deps: tests,
    // start test run, once Require.js is done
    callback: window.__karma__.start
});

window.DEBUG = true;
"""


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
        from calmjs.dev import dist
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

    # TODO figure this out later
    # though for testing, maybe the underlying files provided should be
    # part of deps for the client side test runner startup script?
    # export_module_names = spec[EXPORT_MODULE_NAMES]

    reg = spec.get(CALMJS_MODULE_REGISTRY_NAMES, [])
    pkg = spec.get(SOURCE_PACKAGE_NAMES, [])
    mapping = dist.get_module_default_test_registries_dependencies(pkg, reg)

    test_conf = plugin_registry.modname_target_mapping_to_config_paths(mapping)
    test_config_path = spec['karma_requirejs_test_config'] = join(
        build_dir, 'requirejs_test_config.js')
    with open(test_config_path, 'w') as fd:
        fd.write(UMD_REQUIREJS_JSON_EXPORT_HEADER)
        json.dump(test_conf, fd, indent=4)
        fd.write(UMD_REQUIREJS_JSON_EXPORT_FOOTER)

    # build test script
    test_module_paths = spec.get(TEST_MODULE_PATHS, [])
    # TODO consider using path joiner??
    deps = ['/absolute' + p for p in test_module_paths if p.endswith('.js')]

    test_script_path = spec['karma_requirejs_test_script'] = join(
        build_dir, 'karma_test_init.js')
    with open(test_script_path, 'w') as fd:
        fd.write(TEST_SCRIPT_TEMPLATE % json.dumps(deps, fd, indent=4))

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
    # then extend the configuration files without included by default
    files.extend({'pattern': f, 'included': False} for f in config_files)
    # update the file listing with modifications; this will be written
    # out as part of karma.conf.js by the KarmaRuntime.
    config['files'] = files
