# -*- coding: utf-8 -*-
"""
As all of the following headers and footers are directly lifted from the
UMD (Universal Module Definition) repository [1], the MIT License should
govern this file.

[1] https://github.com/umdjs/umd/

The MIT License (MIT)

Copyright (c) 2014 the UMD contributors.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import unicode_literals


def _find_indent(s):
    t = s.splitlines()[-1]
    return len(t) - len(t.lstrip())


# Template for configurating requireJS.

UMD_REQUIREJS_JSON_EXPORT_HEADER = """\
(function() {
    'use strict';

    var requirejsOptions = (
"""

UMD_REQUIREJS_JSON_EXPORT_FOOTER = """
    );

    if (typeof exports !== 'undefined' && typeof module !== 'undefined') {
        module.exports = requirejsOptions;
    }
    if (typeof requirejs !== 'undefined' && requirejs.config) {
        requirejs.config(requirejsOptions);
    }

}());
"""

# CommonJS is basically incompatible with AMD as defined by requirejs
# and so this template had some failings if mixed in with modules that
# are defined purely in requirejs AMD syntax due to the ``var define``
# on the global scope.

UMD_COMMONJS_AMD_HEADER = """\
if (typeof exports === 'object' && typeof exports.nodeName !== 'string'
        && typeof define !== 'function') {
    var define = function (factory) {
        factory(require, exports, module);
    };
}

define(function (require, exports, module) {
"""

UMD_COMMONJS_AMD_FOOTER = """\
});
"""

# This mostly works, but certain plugins seems to be broken in some
# unspecified ways that I've failed to document earlier.

UMD_NODE_AMD_HEADER = """\
(function(define) {
    define(function (require, exports, module) {
        var exports = {};
"""

UMD_NODE_AMD_FOOTER = """
        return exports;
    });

}(
    typeof module === 'object' &&
    /* istanbul ignore next */
    module.exports &&
    /* istanbul ignore next */
    typeof define !== 'function' ?
        /* istanbul ignore next */
        function (factory) {
            module.exports = factory(require, exports, module);
        }
    :
        /* istanbul ignore next */
        define
));
"""

UMD_NODE_AMD_INDENT = _find_indent(UMD_NODE_AMD_HEADER)
