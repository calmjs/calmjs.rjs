calmjs.rjs
==========

A `RequireJS`__ toolchain built on top of |calmjs|_ for a well managed
workflow for bundling JavaScript code sourced from Python modules or
through standard JavaScript or `Node.js`_ packages.

.. __: http://requirejs.org/
.. image:: https://travis-ci.org/calmjs/calmjs.rjs.svg?branch=master
    :target: https://travis-ci.org/calmjs/calmjs.rjs
.. image:: https://ci.appveyor.com/api/projects/status/jbta6dfdynk5ke59/branch/master?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-rjs/branch/master
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.rjs/badge.svg?branch=master
    :target: https://coveralls.io/github/calmjs/calmjs.rjs?branch=master

.. |AMD| replace:: AMD (Asynchronous Module Definition)
.. |bower| replace:: ``bower``
.. |calmjs| replace:: ``calmjs``
.. |calmjs.bower| replace:: ``calmjs.bower``
.. |calmjs.rjs| replace:: ``calmjs.rjs``
.. |calmjs.dev| replace:: ``calmjs.deg``
.. |npm| replace:: ``npm``
.. |r.js| replace:: ``r.js``
.. |requirejs| replace:: ``requirejs``
.. _AMD: https://github.com/amdjs/amdjs-api/blob/master/AMD.md
.. _bower: https://bower.io/
.. _calmjs: https://pypi.python.org/pypi/calmjs
.. _calmjs.bower: https://pypi.python.org/pypi/calmjs.bower
.. _calmjs.dev: https://pypi.python.org/pypi/calmjs.dev
.. _Node.js: https://nodejs.org/
.. _npm: https://www.npmjs.com/
.. _requirejs: https://www.npmjs.com/package/requirejs


Introduction
------------

User interfaces for web applications typically rely on some form of
JavaScript for its front-end user interfaces, regardless of what
language the backend is written in.  Many Python packages have adopted
the usage of `Node.js`_ for testing the JavaScript code that's required
by the front-end, with |npm|_ (or |bower|_) being the package manager
for the acquisition of JavaScript packages required for the associated
functionality.  This often resulted in the separation of what would have
been a single set of configuration into multiple sets, and often this
also resulted in the package being fractured into two parts to fit in
with the distribution channels being used (PyPI vs npm and others).

The consequences of this decision can end up being problematic due to
the increase in difficulty in propagating the package's version and
dependency information across both channels in a consistent and
reproducible manner for downstream packages and their users.  The
problem Python packages and their users face is that there is no native
or unified way to generate all the required artifacts needed to make
this version of the site to run; very often users have to reply on
package specific instructions on getting those artifacts downloaded or
generated.

The goal of the calmjs framework is to bring this separation back
together by providing the method to expose JavaScript sources included
with Python packages, with this package, |calmjs.rjs|, provide the
facilities to produce deployable artifacts from those exported source
files, plus the other declared external bundles to be sourced from |npm|
or other related Node.js package management systems.


Features
--------

How it works
~~~~~~~~~~~~

This is achieved by treating JavaScript files as both source and
compilation target, with the final deployable artifact(s) being produced
through |r.js| from the |requirejs|_ package.  Under the most default
configuration, the sources included within the Python packages are
headerless and footerless JavaScript files that have ``require`` and
``exports.obj = obj;`` statements; note how the ``exports`` is not
``module.exports`` as the ``calmjs rjs`` transpiler will add the
appropriate headers and footers for the target platform to be generated,
(currently |AMD|_ only, but support for CommonJS and later ES6 can be
provided).

The resulting sources will be placed in a build directory, along with
all the declared bundled sources acquired from the Node.js package
repositories.  A build file will then be generated that includes all the
relevant sources as selected to enable the generation of the final
artifact file through |r.js|.  These can then be deployed to the
appropriate environment, or the whole above process can be included as
part of the functionality of the Python backend at hand.

Ultimately, the goal of |calmjs.rjs| is to ease the integration and
interactions between of client-side JavaScript with server-side Python,
by simplifying the task of building, shipping and deployment of the two
set of sources in one shared package and environment.  |calmjs| provides
the linkage between these two environment and the tools provided by
there will assist with the setup of a common, reproducible local Node.js
environments.

Finally, for quality control, |calmjs.dev| will provide the tools needed
to set up the test environment and harnesses for running of JavaScript
tests that are part of the Python packages for the associated JavaScript
code.

Do note, in the initial implementation, the source file loosely follows
certain definitions that only mimic what ES6 intends to provide.  Even
with this, as a consequence of treating JavaScript within the Python
package as a source file for the compilation target which is the
deployable artifact file, the input source files and exported paths
generated by |calmjs.rjs| are NOT meant for direct consumption of web
clients such as web browsers.  The produced artifact from this framework
will be usable through the AMD API.


Installation
------------

It is recommended that the local environment already have Node.js and
|npm| installed at the very minimum to enable the installation of
|requirejs|, if it hasn't already been installed and available.

To install |calmjs.rjs| into a given Python environment, it may be
installed directly from PyPI with the following command:

.. code:: sh

    $ pip install calmjs.rjs

If a local installation of RequireJS into the current directory is
desired, it can be done through |calmjs| with the following command:

.. code:: sh

    $ calmjs npm --install calmjs.rjs

Which does the equivalent of ``npm install requirejs``; while this does
not seem immediately advantageous, other Python packages that declared
their dependencies for specific sets of tool can be invoked like so, and
to follow through on that.  As an example, ``example.package`` may
declare dependencies on RequireJS through |npm| plus a number of other
packages available through |requirejs|, the process then simply become
this:

.. code:: sh

    $ calmjs npm --install example.package

All standard JavaScript and Node.js dependencies for ``example.package``
will now be installed into the current directory through the relevant
tools.  This process will also install all the other dependencies
through |npm| or |requirejs| that other Python packages depended on by
``example.package`` have declared.  For more usage please refer to
further down this document or the documentation for |calmjs|_.

Alternative installation methods (advanced users)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Development is still ongoing with |calmjs.requirejs|, for the latest
features and bug fixes, the development version can be installed through
git like so:

.. code:: sh

    $ pip install calmjs
    $ pip install git+https://github.com/calmjs/calmjs.rjs.git#egg=calmjs.rjs

Alternatively, the git repository can be cloned directly and execute
``python setup.py develop`` while inside the root of the source
directory.

Keep in mind that |calmjs| MUST be available before the ``setup.py``
within the |calmjs.rjs| source tree is executed, for it needs the
``package_json`` writing capabilities in |calmjs|.  Please refer to the
base package for further information.

As |calmjs| is declared as both a namespace and a package, mixing
installation methods as described above when installing with other
|calmjs| packages may result in the module importer being unable to look
up the target module.  While this normally will not affect end users,
provided they use the same, standard installation method (i.e. wheel),
for developers it can be troublesome.  To resolve this, either stick to
the same installation method for all packages (i.e. ``python setup.py
develop``), or import a module from the main |calmjs| package.  Here
is an example run:

.. code:: python

    >>> import calmjs.rjs
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ImportError: No module named 'calmjs.rjs'
    >>> import calmjs.base
    >>> import calmjs.rjs
    >>>

If this behavior (and workaround) is undesirable, please ensure the
installation of all |calmjs| related packages follow the same method
(i.e. either ``python setup.py develop`` for all packages, or using the
wheels acquired through ``pip``).


Usage
-----

Any exposed JavaScript code through the ``calmjs.module`` registry will
be picked up and compiled into a working RequireJS artifact.  For
details on how the calmjs registry system works please refer to the
README included with the |calmjs|_ project.

For example, given the following entry points for that registry defined
by a package named ``example``:

.. code:: ini

    [calmjs.module]
    example.lib = example.lib
    example.app = example.app

While the import locations declared looks exactly like a Python module
(as per the rules of a Python entry point), the ``calmjs.module``
registry will present them using the es6 style import paths (i.e.
``'example/lib'`` and ``'example/app'``), so users of that need those
JavaScript modules to be sure they ``require`` those strings.  Also,
the default extractor will extract all source files within those
directories.  Also, as a consequence of how the imports are done, it is
recommended that no relative imports be used.

To extract all JavaScript modules declared within Python packages
through this registry can be done like so through the ``calmjs rjs``
build tool, which would extract all the relevant sources, create a
temporary build directory, generate the build manifest and invoke
``r.js`` on that file.  An example run:

.. code:: sh

    $ calmjs rjs example

    Tracing dependencies for: /home/user/example.js

    /home/user/example.js
    ----------------
    /tmp/tmp_build/build/example/lib/form.js
    /tmp/tmp_build/build/example/lib/ui.js
    /tmp/tmp_build/build/example/lib/main.js
    /tmp/tmp_build/build/example/app/index.js

As the build process used by |calmjs.rjs| is done in a separate build
directory, all imports through the Node.js module system must be
declared as ``extras_calmjs``.  For instance, if ``example/app/index``
need to use the ``jquery`` and ``underscore`` modules like so:

.. code:: JavaScript

    var $ = require('jquery'),
        _ = require('underscore');

It will need to declare the target location sourced from |npm| plus the
package_json for the dependencies, it will need to declare this in its
``setup.py``:

.. code:: Python

    setup(
        # ...
        package_json={
            "dependencies": {
                "jquery": "~3.1.0",
                "underscore": "~1.8.0",
            },
        },
        extras_calmjs = {
            'node_modules': {
                'jquery': 'jquery/dist/jquery.js',
                'underscore': 'underscore/underscore.js',
            },
        },
    )

Once that is done, rerun ``python setup.py egg_info`` to write the
freshly declared metadata into the package's egg-info directory, so that
it can be used from within the environment.  ``calmjs npm --install``
can now be invoked to install the |npm| dependencies into the current
directory; to permit |calmjs.rjs| to find the required files sourced
from |npm| to put into the build directory for ``r.js`` to locate them.

The resulting calmjs run may then end up looking something like this:

.. code:: sh

    $ calmjs rjs example

    Tracing dependencies for: /home/user/example.js

    /home/user/example.js
    ----------------
    /tmp/tmp_build/build/jquery.js
    /tmp/tmp_build/build/underscore.js
    /tmp/tmp_build/build/example/lib/form.js
    /tmp/tmp_build/build/example/lib/ui.js
    /tmp/tmp_build/build/example/lib/main.js
    /tmp/tmp_build/build/example/app/index.js


The transpiler will add the appropriate boilerplates and thus the
``require`` statements through |requirejs| will import from
``node_modules`` if the extras_calmjs have been declared.  However,
there are cases where the desired artifact should only contain the
sources from the Python package without the extras or vice versa (due to
the library being available via another deployed artifact), this is
supported by the ``empty:`` scheme by ``r.js``, and to enable it for
``calmjs rjs`` it can be done like so:

.. code:: sh

    $ calmjs rjs example --bundled-map-method empty --export-filename main.js

    Tracing dependencies for: /home/user/main.js

    /home/user/main.js
    ----------------
    /tmp/tmp_build/build/example/lib/form.js
    /tmp/tmp_build/build/example/lib/ui.js
    /tmp/tmp_build/build/example/lib/main.js
    /tmp/tmp_build/build/example/app/index.js

    $ calmjs rjs example --source-map-method empty --export-filename deps.js

    Tracing dependencies for: /home/user/deps.js

    /home/user/deps.js
    ----------------
    /tmp/tmp_build/build/jquery.js
    /tmp/tmp_build/build/underscore.js

The above example shows the generation of two separate artifacts, one
containing just the sources from the Python package ``example`` that had
been declared in the ``calmjs.module`` registry, and the other contains
only the external extra sources.

The explicit ``extras_calmjs`` declaration also supports the usage
through ``bower`` (supported via |calmjs.bower|_); instead of using
``node_modules`` as the key, ``bower_components`` should be used
instead.

Alternative registeries aside from ``calmjs.module`` can be specified
with the ``--source-registry`` flag.  Assuming there are registries in
the current environment registered as ``myreg1`` and ``myreg2`` and the
``example`` package has registered sources to both of them, the command
to build a bundle from both those registries into one artifact can be
triggered like so:

.. code:: sh

    $ calmjs rjs --source-registry myreg1 myreg2 -- example

Note the ``--`` after the registry lists and before the package to
denote the end of the ``--source-registry`` section.


Troubleshooting
---------------

When calling ``calmjs rjs`` on a package, got ``ENOENT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typically this is caused by the package being used not declaring the
needed ``extras_calmjs`` for the appropriate packages within the correct
section.


Contribute
----------

- Issue Tracker: https://github.com/calmjs/calmjs.rjs/issues
- Source Code: https://github.com/calmjs/calmjs.rjs


Legal
-----

The |calmjs.rjs| package is part of the calmjs project.

The calmjs project is copyright (c) 2016 Auckland Bioengineering
Institute, University of Auckland.  |calmjs.rjs| is licensed under the
terms of the GPLv2 or later.
