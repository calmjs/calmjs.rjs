# -*- coding: utf-8 -*-
"""
Exceptions specific for this module.
"""


class RJSRuntimeError(RuntimeError):
    """r.js runtime error"""


class RJSExitError(RuntimeError):
    """r.js exit error, for trapping exit code"""

    def __init__(self, exit_code, binary='r.js', *a):
        self.exit_code = exit_code
        if not a:
            a = ('%s terminated with exit code %d' % (binary, exit_code),)
        super(RJSExitError, self).__init__(*a)
