Module layout
=============

This module, ``calmjs.rjs``, also follows the ``calmjs`` module layout
order, but for clarity sake the modules defined here are included in the
descriptions.

exc
    Generic exception classes specific for this project.

utils
    Utilities for use here, and also for packages depending on this one.

umdjs
    Universal Module Definition headers and footers, sourced from the
    UMD repository.

ecma
    Provides the ECMAScript language family parsing helper functions
    through the ``slimit`` package.

requirejs
    Various utility functions for making ``requirejs``/``r.js`` work
    better, so that it can actually be used with minimum pain.

plugin
    For integration with the requirejs loader plugin system.

registry
    Currently contain just one registry implementation, which is for
    tracking the loader plugins that are supported.

dev
    Integration with the ``calmjs.dev`` package, for specifying the
    interoperation rules between ``r.js`` with ``karma`` for the Calmjs
    framework.

dist
    Module that interfaces with ``distutils``/``setuptools`` helpers
    provided by ``calmjs``, for assisting with gathering sources for
    bundling, and also helpers for the generation of configuration files
    to be fed into ``r.js``.

toolchain
    Provide the transpilation/artifact generation toolchain that
    integrates with ``r.js``, plus ``Spec`` keys support by this
    package through the ``RJSToolchain`` class.

cli
    Slightly higher level API for making use of the ``RJSToolchain``.

runtime
    Higher level API that also provide the user facing utility that
    provide interface to generate artifacts from the command line.

As a general rule, a module should not inherit from modules listed below
their respective position on the above list.
