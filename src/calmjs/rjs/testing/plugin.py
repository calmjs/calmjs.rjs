# -*- coding: utf-8 -*-
import shutil
from os.path import join

from calmjs.loaderplugin import BaseLoaderPluginHandler
from calmjs.rjs.plugin import RJSLoaderPluginHandlerMixin


class DemoPluginHandler(BaseLoaderPluginHandler, RJSLoaderPluginHandlerMixin):
    """
    A demo plugin handler; currently only copies the stripped path to
    where requirejs expects the data to be.
    """

    def __call__(self, toolchain, spec, modname, source, target, modpath):
        """
        Simply return the expected identity without modifications, after
        copying the extracted target to the target location in the build
        directory.
        """

        stripped_target = self.strip_plugin(target)
        copy_target = join(spec['build_dir'], stripped_target)
        shutil.copy(source, copy_target)

        bundled_modpaths = {modname: modpath}
        bundled_targets = {modname: target}
        export_module_names = [modname]
        return bundled_modpaths, bundled_targets, export_module_names
