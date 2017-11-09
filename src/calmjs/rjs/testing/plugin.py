# -*- coding: utf-8 -*-
import shutil
from os.path import join

from calmjs.loaderplugin import LoaderPluginHandler
from calmjs.rjs.loaderplugin import RJSLoaderPluginHandlerMixin


class DemoPluginHandler(LoaderPluginHandler, RJSLoaderPluginHandlerMixin):
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

        copy_target = join(spec['build_dir'], target)
        shutil.copy(source, copy_target)

        bundled_modpaths = {modname: target}
        bundled_targets = {modname: target}
        export_module_names = [modname]
        return bundled_modpaths, bundled_targets, export_module_names
