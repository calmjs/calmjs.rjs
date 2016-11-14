# -*- coding: utf-8 -*-
"""
Workarounds for dumb design decisions and terrible implementation
details that the requirejs library made.
"""

# <insert expletives regarding the months of wasted time/effort here>

import logging
import re
from functools import partial

from slimit import ast

from calmjs.rjs.ecma import parse

logger = logging.getLogger(__name__)
strip_quotes = partial(re.compile('([\"\'])(.*)(\\1)').sub, '\\2')
strip_slashes = partial(re.compile(r'\\(.)').sub, '\\1')


def to_str(ast_string):
    return strip_slashes(strip_quotes(ast_string.value))


def extract_function_argument_visitor(
        node, f_name, f_argn, f_argt, visitor=None):

    if visitor is None:
        visitor = extract_function_argument_visitor

    for child in node:
        # only skimming the top function, not going in.
        if isinstance(child, ast.FunctionCall) and isinstance(
                child.identifier, ast.Identifier):
            if child.identifier.value == f_name and f_argn < len(
                    child.args) and isinstance(child.args[f_argn], f_argt):
                yield to_str(child.args[f_argn])
        else:
            # yield from visit(child)
            for value in visitor(child, f_name, f_argn, f_argt):
                yield value


def extract_function_argument(text, f_name, f_argn, f_argt=ast.String):
    """
    Extract a specific argument from a specific function name.

    Arguments:

    text
        The source text.
    f_name
        The name of the function
    f_argn
        The argument number
    f_argt
        The argument type from slimit.ast; default: slimit.ast.String
    """

    tree = parse(text)
    return list(extract_function_argument_visitor(
        tree, f_name, f_argn, f_argt))


def extract_defines(text):
    """
    For the execution of tests, there is no way to tell requirejs that
    all the modules are already available synchronously through the
    provided artifact files.  This function will extract all the define
    names which can be chucked into the requirejs.deps configuration
    section.
    """

    return extract_function_argument(text, 'define', 0)


def extract_requires(text):
    """
    The requirejs library has NO way to automatically ignore files that
    it cannot find, so we have to do it for them.  This function takes
    a source file, returns all the string literals that the source file
    use as the first argument for requires.
    """

    return extract_function_argument(text, 'require', 0)


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
        f_argt = ast.String

        for child in node:
            if isinstance(child, ast.FunctionCall) and isinstance(
                    child.identifier, ast.Identifier):
                if child.identifier.value == f_name and f_argn < len(
                        child.args) and isinstance(child.args[f_argn], f_argt):
                    modname = to_str(child.args[f_argn])
                    moddeps = list(extract_function_argument_visitor(
                        child, 'require', 0, ast.String))
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


def extract_all_amd_requires(text):
    """
    Extract all require and define calls from unbundled JavaScript
    source files in both AMD and CommonJS syntax.
    """

    f_names = ('require', 'define',)
    # reserved modules
    define_wrapped = dict(enumerate(('require', 'exports', 'module',)))
    reserved = ['module']

    def visit(node):
        for child in node:
            if isinstance(child, ast.FunctionCall) and isinstance(
                    child.identifier, ast.Identifier):
                if not child.args:
                    continue

                args = child.args
                # either require or define
                standard_amd = ((
                    len(child.args) >= 2 and
                    isinstance(args[0], ast.Array) and
                    isinstance(args[1], ast.FuncExpr) and
                    child.identifier.value in f_names
                ), 0)
                # only for define
                named_define = ((
                    len(child.args) >= 3 and
                    isinstance(args[0], ast.String) and
                    isinstance(args[1], ast.Array) and
                    isinstance(args[2], ast.FuncExpr) and
                    child.identifier.value == 'define'
                ), 1)

                if (isinstance(args[0], ast.String) and
                        child.identifier.value == 'require'):
                    # only yield names just from require
                    yield to_str(args[0])
                    continue

                for checks in (standard_amd, named_define):
                    cond, pos = checks
                    if not cond:
                        continue

                    for i, node in enumerate(child.args[pos]):
                        if isinstance(node, ast.String):
                            result = to_str(node)
                            if ((result not in reserved) and (
                                    result != define_wrapped.get(i))):
                                yield result

            # yield from visit(child)
            for value in visit(child):
                yield value

    tree = parse(text)
    return visit(tree)


def process_path(path, f):
    """
    Take the path and process it through one of the above functions
    """

    try:
        with open(path) as fd:
            text = fd.read()
        return f(text)
    except (OSError, IOError) as e:
        logger.error("failed to read '%s': %s: %s", path, type(e).__name__, e)
    except SyntaxError as e:
        logger.error("syntax error in '%s': %s", path, e)
