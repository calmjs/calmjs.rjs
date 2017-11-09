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
the handlers, or the handler could invoke the registry system (which
under the default case is accessible through its ``self.registry``
attribute) to get the required target as the call method provides both
the toolchain and the spec.

As mentioned, loader plugin handlers should be registered to the
calmjs.rjs loader_plugin registry in order for them to be used.  There
are defaults provided, which the RJSToolchain will make use of in its
standard workflow (regsistered as ``calmjs.rjs.loader_plugin``).

One final note on module layout for ``calmjs.rjs``: this module should
not import anything from the calmjs namespace.
"""

import logging
import shutil
from os import makedirs
from os.path import dirname
from os.path import exists
from os.path import join

from calmjs.loaderplugin import NPMLoaderPluginHandler
from calmjs.loaderplugin import BaseLoaderPluginHandler

logger = logging.getLogger(__name__)


class RJSLoaderPluginHandlerMixin(BaseLoaderPluginHandler):
    """
    A mixin for the loader plugin handler that also address the specific
    needs of the requirejs system; provides a framework to deal with path
    mangling and/or resolution for setting up the paths for usage from
    within a requirejs environment.
    """

    def modname_source_to_target(self, toolchain, spec, modname, source):
        """
        This overrides the default to also call the toolchain version to
        get the target
        """

        target = super(
            RJSLoaderPluginHandlerMixin, self).modname_source_to_target(
                toolchain, spec, modname, source)
        # Assuming that the toolchain instance IS RJSToolchain.  The
        # reason for the reliance on the parent is that the behavior of
        # adding file name suffix is _required_ for certain lookup
        # operations that requirejs does.  However, given that the
        # default Toolchain instance WILL make use of the registry again
        # to find a handler for further lookups, this can wrap back into
        # this handler somehow (or even prematurely) which can trigger
        # infinite recursion... So only trigger the lookup on the
        # final cleanup, i.e. when the implementation returns a target
        # without any loaderplugin syntax.
        if '!' not in target:
            return toolchain.modname_source_to_target(spec, target, source)
        return target

    # remainder are proprietary to the requirejs interfaces.

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

    def modname_source_to_config_paths(self, modname, source):
        """
        In general, there shouldn't be a difference, however in practice
        subclasses may choose to make handling of source files somewhat
        different.  This is used by the registry system for generation
        of mapping directly from the source file provided through the
        module registry system for calmjs.
        """

        return self.modname_target_to_config_paths(modname, source)


class TextPlugin(NPMLoaderPluginHandler, RJSLoaderPluginHandlerMixin):
    """
    A basic text loader plugin handler; does not handle further chained
    loader plugins that have been specified in the modname, as it
    assumes everything between the first and second '!' is the target.
    """

    node_module_pkg_name = 'requirejs-text'

    def __init__(self, registry, name='text'):
        # just give this a default value for ease of use.
        super(TextPlugin, self).__init__(registry, name)

    def strip_plugin(self, value):
        """
        The text plugin only support the first argument, does not have
        chaining, thus only the argument after the first '!' will be
        returned with all remaining tokens stripped.

        Returns the target resource identifier.
        """

        if value.startswith(self.name + '!'):
            result = value.split('!', 1)
            return result[-1].split('!', 1)[0]
        else:
            return value

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
        modname_s = self.strip_plugin(modname)
        target_s = self.strip_plugin(target)

        # the default, ideal result to be returned, however...
        result = {modname_s: target_s}

        # the requirejs-text plugin works incorrectly, stripping the
        # loader plugin related strings should allow the underlying
        # loader for requirejs be able to lookup the actual path from
        # the ``paths`` configured.  However, this is not the case, due
        # to its special treatment of dots.  See the method for reason
        # and the actual issue.
        modname_i123, modname_x = self.requirejs_text_issue123(modname_s)
        target_i123, target_x = self.requirejs_text_issue123(target_s)

        if not (modname_x or target_x):
            # no filename extension, we are done.
            return result

        # ugh, I hate it when I have to pretend the brokeness exported
        # out of your everyday JavaScript library is normal.

        def unsupported_warning():
            logger.warning(
                "warning triggered by mapping config.paths from "
                "modpath '%s' to target '%s'",
                modname, target
            )
            logger.warning(
                'unsupported values provided for configuration for requirejs '
                'paths in the context of the text loader plugin; provided '
                'values will result in paths mapping that will malfunction in '
                'in the context of the AMD loader provided by requirejs when '
                'these settings are applied to a configuration on the web, '
                'including usage through an http-based test runner; however, '
                'this should not affect the production of artifact through '
                'the RJSToolchain, but test failures may result'
            )
            logger.warning(
                'to silence this warning and to fully mitigate against this '
                'issue, please ensure all final filename fragments or '
                'files made available through the registry provide a file '
                'name extension for both the modpath and the associated '
                'mapped target url or file on filesystem; please refer to '
                '<https://github.com/requirejs/text/issues/123> for complete '
                'details about this issue at hand'
            )
            logger.warning(
                "If possible, potential remedy to this issue may be resolved "
                "by renaming '%s' to '%s.ext'", target_s, target_s,
            )

        if modname_x == target_x:
            if not ('/' in modname_x and '/' in target_x):
                # Standard filename extension, glad to get this one
                # quickly over with.  Include the normal one in case the
                # issue gets fixed.
                return {
                    modname_i123: target_i123,
                    modname_s: target_s,
                }
            else:
                # Well, a separator is a lot more annoying to deal with;
                # this one definitely need the warning because if the
                # directory support is fixed this will no longer work.
                # not to mention requirejs-text>=2.0.13 it may not work.
                unsupported_warning()
                logger.warning('potentially working mitigations applied')
                modname_dir, modname_junk = modname_x.split('/', 1)
                target_dir, target_junk = target_x.split('/', 1)
                modname_i123_dir = '.'.join([modname_i123, modname_dir])
                target_i123_dir = '.'.join([target_i123, target_dir])
                return {
                    modname_s: target_s,
                    modname_i123: target_i123,
                    modname_i123_dir: target_i123_dir,
                }

        # For everything else, there are too much potential variance.
        #
        # Given this mapping::
        #
        #     requirejs.config({"paths": {
        #         "org.example.ns1/file": "/src/org.example/ns1/file",
        #         "org.example.ns2/file": "/alt/org.example/ns2/file",
        #     }});
        #
        # One would expect that the following would work
        #
        #     require(['text!org.example.ns1/file'], function() {});
        #
        # Except it does not, because of how requirejs deals with file
        # name extensions as something special and doing it wrong at
        # that, which lead to this problem.  Spoiler: a given filename
        # extension does not go beyond a path separator.  For a full
        # illustration of the problem, first limit it to the first
        # example (ns1).
        #
        # Under the above workaround rules, the generated filename
        # mapping for ns1 will be {"org.example": "/src/org"}, which is
        # wrong.  However, an observer that has full understanding of
        # the rules for dealing with this kind of path mangling will see
        # that the following configuration will work:
        #
        #     requirejs.config({"paths": {
        #         'org.example': '/src/org.example',  // for ns1/file
        #     }});
        #
        # With the following require() call successfully load from the
        # url /src/org.example.ns1/file.
        #
        #     require(['text!org.example.ns1/file'], function() {});
        #
        # But now the logic have to further infer and mixing and
        # matching of all of these fragments and things get get
        # complicated real fast.  If only the libraries can directly
        # lookup the config.paths and short circuit the evaluation...
        #
        # Anyway, if both the ns1 and ns2 definitions have to be added
        # now the rules become wildly ambiguous:
        #
        #     requirejs.config({"paths": {
        #         'org.example': '/src/org.example',  // for ns1/file
        #         'org.example': '/alt/org.example',  // for ns2/file
        #     }});
        #
        # Now, what do the following two statements actually load?
        #
        #     require(['text!org.example.ns1/file'], function() {});
        #     require(['text!org.example.ns2/file'], function() {});
        #
        # On my testing (with requirejs 2.3.2 and text 2.0.15), both
        # looked up via the second mapping, as expected.  We can further
        # reduce this problem to the following mapping:
        #
        #     requirejs.config({"paths": {
        #         'text.rst': '/srv/text.html',
        #     }});
        #
        # As we had demonstrated, loading the module like so::
        #
        #     require(['text!text.rst'], function() {});
        #
        # Will simply fail, only targets suffixed with another ".ext"
        # will work.  Removing the .rst and .html from the respective
        # key and value will not convey the desired mapping.  Due to
        # this utter ambiguity we are not going to even bother doing the
        # first step.  A sane developer will quickly decide that they
        # are done playing the stupid unnecessary filename extension
        # game that requirejs invented, unlike the one who wrote this
        # huge wall of text in comment form.

        unsupported_warning()
        logger.warning(
            'provided modname and target has no possible workaround; '
            'changes to generated config paths not applied'
        )
        return result

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
