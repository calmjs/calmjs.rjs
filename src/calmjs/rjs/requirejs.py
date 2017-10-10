# -*- coding: utf-8 -*-
"""
Workarounds for dumb design decisions and terrible implementation
details that the requirejs library made.
"""

# <insert expletives regarding the months of wasted time/effort here>

import logging
import codecs
from functools import partial

from calmjs.parse import asttypes
from calmjs.parse.parsers.es5 import parse

from calmjs.interrogate import to_str
from calmjs.interrogate import filter_function_argument

logger = logging.getLogger(__name__)


def extract_defines_with_deps_visitor(node_map):
    """
    For the execution of tests against a pre-built artifact, there is no
    way to tell requirejs that all the modules are already available
    synchronously through the provided artifact files.  This function
    will build a dictionary with keys being the module name and value
    being a list of module names it requires synchronously.
    """

    defines = {}
    yielded = set()

    def extract_defines_visitor(node, node_name):
        f_name = 'define'
        f_argn = 0
        f_argt = asttypes.String

        for child in node:
            if isinstance(child, asttypes.FunctionCall) and isinstance(
                    child.identifier, asttypes.Identifier):
                if child.identifier.value == f_name and f_argn < len(
                        child.args.items) and isinstance(
                            child.args.items[f_argn], f_argt):
                    modname = to_str(child.args.items[f_argn])
                    moddeps = list(filter_function_argument(
                        child, 'require', 0, asttypes.String))
                    if modname in defines:
                        logger.warning(
                            "module '%s' defined again in '%s'",
                            modname, node_name,
                        )
                        # don't do anything more since requirejs doesn't
                        # permit redefinition in general.
                        continue
                    defines[modname] = moddeps
            else:
                extract_defines_visitor(child, node_name)

    # first flatten it into a dependency map
    for node_name, node in node_map:
        extract_defines_visitor(node, node_name)

    # then process that map to generate the values in correct order.
    def process_defines(modname):
        if modname not in yielded:
            for modname_ in defines.get(modname, ()):
                for mn in process_defines(modname_):
                    yield mn
            if modname in defines:
                yielded.add(modname)
                yield modname
            else:
                logger.warning(
                    "module '%s' required but seems to be missing", modname)

    for modname in defines.keys():
        for mn in process_defines(modname):
            yield mn


def extract_defines_with_deps(text):
    tree = parse(text)
    return list(extract_defines_with_deps_visitor([('<text>', tree)]))


def extract_defines_with_deps_from_paths(paths):
    items = []

    def append_tree(path, text):
        items.append((path, parse(text)))

    for path in paths:
        process_path(path, partial(append_tree, path))

    return list(extract_defines_with_deps_visitor(items))


def process_path(path, f, encoding='utf-8'):
    """
    Take the path and process it through one of the above functions
    """

    try:
        with codecs.open(path, encoding=encoding) as fd:
            text = fd.read()
        return f(text)
    except (OSError, IOError) as e:
        logger.error("failed to read '%s': %s: %s", path, type(e).__name__, e)
    except SyntaxError as e:
        logger.error("syntax error in '%s': %s", path, e)
