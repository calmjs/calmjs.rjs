# -*- coding: utf-8 -*-
"""
CalmJS RequireJS artifact generation helpers
"""

from calmjs.toolchain import Spec
from calmjs.toolchain import SETUP
from calmjs.rjs.cli import create_spec
from calmjs.rjs.cli import default_toolchain

from calmjs.rjs.dev import rjs_advice


def complete_rjs(package_names, export_target):
    """
    Return the toolchain and a spec that when executed together, will
    result in a complete artifact using the provided package names onto
    the export_target.
    """

    return default_toolchain, create_spec(package_names, export_target)


def test_complete_rjs(package_names, export_target):
    """
    Accompanied testing entry point for the complete_rjs artifact.
    """

    # importing in here as calmjs.dev is an optional dependency.
    from calmjs.dev.toolchain import KarmaToolchain

    spec = Spec(
        export_target=export_target,
        test_package_names=package_names,
    )
    spec.advise(SETUP, rjs_advice, spec)
    return KarmaToolchain(), spec
