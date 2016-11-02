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
from slimit.parser import Parser

logger = logging.getLogger(__name__)
# TODO figure out what's the deal with the warnings this spew.
parser = Parser()
to_str = partial(re.compile('([\"\'])(.*)(\\1)').sub, '\\2')


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

    def visit(node):
        for child in node:
            # only skimming the top function, not going in.
            if isinstance(child, ast.FunctionCall) and isinstance(
                    child.identifier, ast.Identifier):
                if child.identifier.value == f_name and f_argn < len(
                        child.args) and isinstance(child.args[f_argn], f_argt):
                    yield to_str(child.args[f_argn].value)
            else:
                # yield from visit(child)
                for value in visit(child):
                    yield value

    tree = parser.parse(text)
    return list(visit(tree))


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
