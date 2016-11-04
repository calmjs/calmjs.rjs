# -*- coding: utf-8 -*-
import unittest
from os.path import join

from calmjs.rjs import requirejs
from calmjs.utils import pretty_logging

from calmjs.testing.mocks import StringIO
from calmjs.testing.utils import mkdtemp

# an example bundle including webpack blobs and requirejs AMD blobs
artifact = """
(function () {
(function umd(root, factory) {
        if(typeof exports === 'object' && typeof module === 'object')
                module.exports = factory();
        else if(typeof define === 'function' && define.amd)
                define('lib1',[], factory);
        else if(typeof exports === 'object')
                exports["lib1"] = factory();
        else
                root["lib1"] = factory();
})(this, function() {});
;
(function(define) {
    define('lib2',['require','exports','module'],function (
        require, exports, module) {
    });

}(
    typeof module === 'object' &&
    module.exports &&
    typeof define !== 'function' ?
        function (factory) {
            module.exports = factory(require, exports, module);
        }
    :
        define
));
}());
"""

commonjs_require = """
var mod1 = require('mod1');
var mod2 = require("name/mod/mod2");
var invalid = require();
"""

requirejs_require = """
require(['some/dummy/module1', 'some/dummy/module2'], function(mod1, mod2) {
    var mod1_alt = require('some/dummy/module1');
    var mod3_alt = require('some/dummy/module3');
});

define(['defined/alternate/module', 'some.weird.module'], function(a, b) {
});

// this is a weird one
define('some test', ['require', 'module'], function(require, module) {});

// invalid code shouldn't choke the walker.
require();
define();
"""


class RequireJSHelperTestCase(unittest.TestCase):
    """
    Helpers to make this thing not suck like the other.
    """

    def test_extract_function_argument_basic(self):
        results = requirejs.extract_function_argument("""
        trial(1, 2, 'hello');
        trial(1, 2, "goodbye");
        """, 'trial', 2)
        self.assertEqual(results, ['hello', 'goodbye'])

    def test_extract_function_argument_mismatches(self):
        results = requirejs.extract_function_argument("""
        trial(1, 2);
        trial(1, 2, 23, 4, 5);
        """, 'trial', 2)
        self.assertEqual(results, [])

    def test_extract_function_argument_not_nested(self):
        results = requirejs.extract_function_argument("""
        (function() {
            trial(1, 2, 'hello', trial(1, 2, 'goodbye'));
            trial(1, 2, (function() { trial(1, 2, 'goodbye')})());
        })();
        """, 'trial', 2)
        self.assertEqual(results, ['hello'])

    def test_extract_function_not_sub(self):
        results = requirejs.extract_function_argument("""
        (function() {
            log('hello');
            log('');
            console.log('goodbye');
        })();
        """, 'log', 0)
        self.assertEqual(results, ['hello', ''])

    def test_extract_on_syntax_error(self):
        with self.assertRaises(SyntaxError):
            requirejs.extract_function_argument("""
            (function() {
                console.log('hello!');
                report('');
                missing_rparen(1, 2, 'hello';
            })();
            """, 'report', 0)

    def test_extract_defines(self):
        self.assertEqual(['lib1', 'lib2'], requirejs.extract_defines(artifact))

    def test_extract_requires(self):
        self.assertEqual(
            ['mod1', 'name/mod/mod2'],
            requirejs.extract_requires(commonjs_require),
        )
        self.assertEqual(
            ['mod1', 'name/mod/mod2'],
            requirejs.extract_requires(commonjs_require + requirejs_require),
        )

    def test_extract_all_amd_requires(self):
        self.assertEqual([
            'defined/alternate/module',
            'module',
            'require',
            'some.weird.module',
            'some/dummy/module1',
            'some/dummy/module2',
            'some/dummy/module3',
        ], sorted(set(requirejs.extract_all_amd_requires(requirejs_require))))

    def test_extract_read_from_file(self):
        tmpdir = mkdtemp(self)
        src_file = join(tmpdir, 'source.js')

        with open(src_file, 'w') as fd:
            fd.write(requirejs_require)

        result = requirejs.process_path(
            src_file, requirejs.extract_all_amd_requires)

        self.assertEqual([
            'defined/alternate/module',
            'module',
            'require',
            'some.weird.module',
            'some/dummy/module1',
            'some/dummy/module2',
            'some/dummy/module3',
        ], sorted(set(result)))

    def test_extract_read_from_file_syntax_error(self):
        tmpdir = mkdtemp(self)
        src_file = join(tmpdir, 'source.js')

        with open(src_file, 'w') as fd:
            fd.write("define([], function () { return 'blah' }")

        with pretty_logging(stream=StringIO()) as stream:
            result = requirejs.process_path(
                src_file, requirejs.extract_requires)

        self.assertIsNone(result)
        self.assertIn('syntax error', stream.getvalue())

    def test_extract_read_from_file_error(self):
        tmpdir = mkdtemp(self)
        src_file = join(tmpdir, 'source.js')

        with pretty_logging(stream=StringIO()) as stream:
            result = requirejs.process_path(
                src_file, requirejs.extract_requires)

        self.assertIsNone(result)
        self.assertIn('No such file or directory:', stream.getvalue())
        self.assertIn(src_file, stream.getvalue())