# -*- coding: utf-8 -*-
import unittest

from calmjs.rjs import ecma


class SpecUpdateSourceMapTestCase(unittest.TestCase):

    def test_parse(self):
        text = "process.stdout.write('hello world');"
        tree = ecma.parse(text)
        parser = ecma._parser
        self.assertEqual(text, tree.to_ecma())
        ecma.parse(text)
        # the parser is not mutated.
        self.assertIs(parser, ecma._parser)
