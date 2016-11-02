# -*- coding: utf-8 -*-
import unittest

from calmjs.rjs import requirejs

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

require(['some/dummy/module'], function(){});

describe('some test', function() {});
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

    def test_extract_defines(self):
        self.assertEqual(['lib1', 'lib2'], requirejs.extract_defines(artifact))

    def test_extract_requires(self):
        self.assertEqual(
            ['mod1', 'name/mod/mod2'],
            requirejs.extract_requires(commonjs_require),
        )
