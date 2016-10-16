# -*- coding: utf-8 -*-
"""
The plugin system compatibility layer for requirejs.

Given that the plugin definitions are done on top of the requirejs
module system, the plugins are actually the top level modules, with the
arguments after the ``!`` identifier being completely opaque.  This
means that if the underlying loader expects paths in a different way it
will not understand the calmjs mapping from modname to target/modpath as
laid out.

This module provides the foundation to address this issue.  Combined
with the ``loader_plugin`` registry (see ``calmjs.rjs.registry``), this
will allow explicitly defined methods to deal with path resolution, even
for custom JavaScript plugins that are shipped with Python.  As custom
registries for this can be specified, this can cater to even the most
esoteric module setup, such as custom nested plugin configurations; this
can be implemented by calling specific functions nested within each of
the handlers, or the handler could invoke the registry system to get the
required target as the call method provides both the toolchain and the
spec.

As mentioned, loader plugin handlers should be registered to the
calmjs.rjs loader_plugin registry in order for them to be used.  There
are defaults provided, which the RJSToolchain will make use of in its
standard workflow.
"""

import logging
import shutil
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join

logger = logging.getLogger(__name__)


class LoaderPluginHandler(object):
    """
    Encapsulates a loader plugin for requirejs, this provides a
    framework to deal with path mangling and/or resolution for setting
    up the paths for usage from within a requirejs environment.
    """

    def modname_modpath_to_config_paths(self, modname, modpath):
        """
        In the default tool, this is not used, but this is left here as
        a placeholder.
        """

        return {modname: modpath}

    def modname_target_to_config_paths(self, modname, target):
        """
        For a given modnames and its target, convert them to the aliased
        locations that will be compatible with how requirejs parses the
        paths argument in its configuration json for a web environment.

        The return value must be a modname and target, which could be
        modified so they fit for usage within the paths mapping for the
        requirejs configuration.

        The default implementation simply add a '?' to the target.
        """

        return {modname: target + '?'}

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        """
        These need to provide the actual implementation required for the
        production of the final artifact, so this will need to locate
        the resources needed for this set of arguments to function.

        Each of these should return the associated bundled_modpaths,
        bundled_targets, and the export_module_name, after the copying
        or transpilation step was done.
        """

        raise NotImplementedError


class TextPlugin(LoaderPluginHandler):
    """
    A basic text loader plugin handler; does not handle further chained
    loader plugins that have been specified in the modname, as it
    assumes everything between the first and second '!' is the target.
    """

    def requirejs_text_issue123(self, value):
        """
        Basically, it appears a dot (``.``) character occuring anywhere
        inside that string is treated as a filename extension, and if
        the same identical path (with the ``.``) is later requested, the
        lookup from the requirejs config will NOT be triggered.  If the
        dot character is omitted, it will work.

        For further information and the test data that support the above
        observation, please refer to the issue reported at:

        https://github.com/requirejs/text/issues/123

        Specifically note the interactions of::

            var requirejsOptions = ({"paths": {
                'nodot/target': '/srv/tmp/nodot/target',
            }});

        and

            require([
                // /srv/tmp/nodot/target.d/file
                'text!nodot/target.d/file',
            ], function() {});

        even though the filename "extension" is applied to the directory
        one level down.
        """

        if value.endswith('.'):
            logger.warning(
                "trailing '.' character for config.paths is unsupported by "
                "requirejs-text; please refer to "
                "<https://github.com/requirejs/text/issues/123>"
            )

        result = value.rsplit('.', 1)
        if len(result) < 2:
            result.append('')
        return result

    def strip_plugin(self, value):
        """
        Strip the first plugin fragment and return just the value.
        """

        result = value.split('!', 1)
        return result[-1].split('!', 1)[0]

    def modname_target_to_config_paths(self, modname, target):
        """
        A text loader plugin will need to have its modname stripped of
        all loader plugin specific bits, and the target be either
        stripped of its filename extension OR take the dirname as it
        just does NOT understand explicit complete filenames.
        """

        # the values provided _will_ include the `text!` portion as the
        # default toolchain generation provides this.  Here strip them
        # off from both modname and target.
        modname = self.strip_plugin(modname)
        target = self.strip_plugin(target)
        # if the requirejs-text plugin works correctly, stripping the
        # loader plugin related strings should allow the underlying
        # loader for requirejs be able to lookup the actual path from
        # the ``paths`` configured.  However, this is not the case, due
        # to its special treatment of dots.  See the method for reason
        # and the actual issue.
        modname_result, modname_x = self.requirejs_text_issue123(modname)
        target_result, target_x = self.requirejs_text_issue123(target)

        if modname_x.endswith(target_x) != target_x.endswith(modname_x):
            # BUG this is NOT a supported outcome due to how requirejs
            # does not correctly handle directories anyway.
            logger.warning(
                'unsupported values provided for configuration for requirejs '
                'paths in the context of the text plugin; provided values '
                'result in paths mapping that will malfunction in requirejs '
                'and its text loader plugin'
            )
            logger.warning(
                'provided values: {"%s": "%s"}, '
                'generated values: {"%s": "%s"}',
                modname, target, modname_result, target_result
            )
            logger.warning(
                'to mitigate, please ensure all final filename fragments have '
                'a filename extension for both the modpath and the associated '
                'mapped target url or file on filesystem; please refer to '
                '<https://github.com/requirejs/text/issues/123> for complete '
                'details about this issue at hand'
            )
        elif modname_x != target_x:
            logger.info(
                'provided modname and target {"%s": "%s"} do not share the '
                'same suffix', modname, target,
            )
        return {modname_result: target_result}

    def __call__(self, toolchain, spec, modname, source, target, modpath):

        # the write target, however, is very different from the config
        # target given the issue #123 workaround applied.
        stripped_target = self.strip_plugin(target)
        copy_target = join(spec['build_dir'], stripped_target)
        if not exists(dirname(copy_target)):
            makedirs(dirname(copy_target))
        shutil.copy(source, copy_target)

        bundled_modpaths = {modname: modpath}
        bundled_targets = self.modname_target_to_config_paths(modname, target)
        export_module_names = [modname]
        return bundled_modpaths, bundled_targets, export_module_names

text = TextPlugin()
