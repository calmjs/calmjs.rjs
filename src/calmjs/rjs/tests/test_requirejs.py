# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
from os.path import join
from functools import partial

from calmjs.interrogate import extract_module_imports
from calmjs.interrogate import extract_function_argument
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

artifact_multiple1 = """
(function () {(function(define) {
    define('lib1',['require','exports','module','lib2'],function (
        require, exports, module
    ) {
        var lib2 = require('lib2');
    });
})();

define('text',['module'], function (module) {
});

define('lib2',['require','exports','module'],function () {
});

}());
"""

artifact_multiple2 = """
define('lib1',[],function () {
    require('lib2');
    require('lib3');
});

define('lib2',[],function () {
    require('lib3');
});

define('lib4',[],function () {
    require('lib1');
});

define('lib3',[],function () {
});
"""

# missing case
artifact_multiple3 = """
define('lib1',[],function () {
    require('lib4');
    require('lib2');
    require('missing');
});

define('lib2',[],function () {
    require('lib4');
    require('missing');
});

define('lib4',[],function () {
    require('missing');
});
"""

# redefinition case
artifact_multiple4 = """
define('lib1',[],function () {
    require('lib3');
});

define('lib1',[],function () {
    require('missing');
});

define('lib3',[],function () {
});
"""


commonjs_require = """
var mod1 = require('mod1');
var mod2 = require("name/mod/mod2");
var invalid = require();

// test out dynamic require calls.
var target = mod1.target;
var dynamic = require(target);
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

// test out dynamic define calls.
var target = window.target;
var dynamic = define([target], function(target_mod) {});
"""


class RequireJSHelperTestCase(unittest.TestCase):
    """
    Helpers to make this thing not suck like the other.
    """

    def test_extract_defines_amd_artifact1(self):
        result = requirejs.extract_defines_with_deps(artifact_multiple1)
        # since text has no dependencies, it can be anywhere.
        result.remove('text')
        self.assertEqual(['lib2', 'lib1'], result)

    def test_extract_defines_amd_artifact2(self):
        self.assertEqual([
            'lib3', 'lib2', 'lib1', 'lib4'
        ], requirejs.extract_defines_with_deps(artifact_multiple2))

    def test_extract_defines_amd_artifact3_missing(self):
        with pretty_logging(stream=StringIO()) as stream:
            result = requirejs.extract_defines_with_deps(artifact_multiple3)
        self.assertEqual(['lib4', 'lib2', 'lib1'], result)
        s = stream.getvalue()
        self.assertIn("module 'missing' required but seems to be missing", s)
        self.assertIn("WARNING", s)

    def test_extract_defines_amd_artifact4_dupe(self):
        with pretty_logging(stream=StringIO()) as stream:
            result = requirejs.extract_defines_with_deps(artifact_multiple4)
        self.assertEqual(['lib3', 'lib1'], result)
        s = stream.getvalue()
        self.assertNotIn("'missing' required but seems to be missing", s)
        self.assertIn("module 'lib1' defined again in '<text>'", s)
        self.assertIn("WARNING", s)

    def test_extract_read_from_file(self):
        tmpdir = mkdtemp(self)
        src_file = join(tmpdir, 'source.js')

        with open(src_file, 'w') as fd:
            fd.write(requirejs_require)

        result = requirejs.process_path(src_file, extract_module_imports)

        self.assertEqual([
            'defined/alternate/module',
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
            result = requirejs.process_path(src_file, partial(
                extract_function_argument, f_name='require', f_argn=0))

        self.assertIsNone(result)
        self.assertIn('syntax error', stream.getvalue())

    def test_extract_read_from_file_error(self):
        tmpdir = mkdtemp(self)
        src_file = join(tmpdir, 'source.js')

        with pretty_logging(stream=StringIO()) as stream:
            result = requirejs.process_path(src_file, partial(
                extract_function_argument, f_name='require', f_argn=0))

        self.assertIsNone(result)
        self.assertIn('No such file or directory:', stream.getvalue())
        self.assertIn(src_file, stream.getvalue())
