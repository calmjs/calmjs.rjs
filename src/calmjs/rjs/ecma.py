# -*- coding: utf-8 -*-
"""
ECMA integration module.

Provides a parse function for parsing a JavaScript source text into a
source tree through the slimit module.
"""

from slimit.parser import Parser

_parser = None


# TODO name parse functions after the version of the expected input.

def parse(text):
    """
    Turn a valid JavaScript source string and turn it into a source tree
    through the Parser provided by the slimit.parser module.
    """

    global _parser
    if _parser is None:
        _parser = Parser()

    return _parser.parse(text)
