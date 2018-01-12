calmjs.rjs
==========

Package for the integration of `RequireJS`__ into a Python environment
via the `Calmjs framework`__, to provide a reproducible workflow for the
generation of deployable artifacts from JavaScript source code provided
by Python packages in conjunction with standard JavaScript or `Node.js`_
packages sourced from |npm|_ or other similar package repositories.

.. __: http://requirejs.org/
.. __: https://pypi.python.org/pypi/calmjs
.. image:: https://travis-ci.org/calmjs/calmjs.rjs.svg?branch=2.0.x
    :target: https://travis-ci.org/calmjs/calmjs.rjs
.. image:: https://ci.appveyor.com/api/projects/status/jbta6dfdynk5ke59/branch/2.0.x?svg=true
    :target: https://ci.appveyor.com/project/metatoaster/calmjs-rjs/branch/2.0.x
.. image:: https://coveralls.io/repos/github/calmjs/calmjs.rjs/badge.svg?branch=2.0.x
    :target: https://coveralls.io/github/calmjs/calmjs.rjs?branch=2.0.x

.. |AMD| replace:: AMD (Asynchronous Module Definition)
.. |bower| replace:: ``bower``
.. |calmjs| replace:: ``calmjs``
.. |calmjs.bower| replace:: ``calmjs.bower``
.. |calmjs.rjs| replace:: ``calmjs.rjs``
.. |calmjs.dev| replace:: ``calmjs.dev``
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

Web applications can be created using any language, however the
interactive front-end user interfaces they provide ultimately rely on
some form of JavaScript.  Python web application frameworks or systems
that provide frontend functionalities that bridge the backend have
adopted the usage of `Node.js`_ for testing the JavaScript code that
they may provide, with |npm|_ (or |bower|_) being the package manager
for the acquisition of JavaScript packages required for the associated
functionality.  This often resulted in the separation of what would have
been a single set of package dependency configuration into multiple
different sets; often this also resulted in the package being fractured
into two parts to fit in with the distribution channels being used (PyPI
vs npm and others).

This outcome ends up being problematic for Python package management due
to the increase in difficulty in the propagation of the package's
version and dependency information across all relevant package
management channels in a consistent, portable and reproducible manner
for downstream packages and their users.  The other issue is that the
configuration files used for asset management or artifact generation is
often coupled tightly to the system at hand, making it rather difficult
for their downstream package to reuse these configurations to generate
a combined artifacts that work also with their other upstream packages
in a consistent manner.

Some other package managers attempt to solve this by being utterly
generic, however they lack the awareness of locally available Python
packages (such as Python wheels already installed in the local
environment not being understood by Bower), thus build processes that
involve Bower often end up relying on public infrastructure, and options
to move it to a private infrastructure or even reuse locally available
artifacts/packages require extra configurations which negate the
benefits offered by these systems.  Also, these build scripts are
tightly coupled to a specific project which are not portable.

The goal of the Calmjs framework is to bring this separation back
together by providing the method to expose JavaScript sources included
with Python packages, with this package, |calmjs.rjs|, to provide the
facilities to produce deployable artifacts from those exported source
files, plus the other declared external bundles to be sourced from |npm|
or other related Node.js package management systems.


Features
--------

How |calmjs.rjs| works
~~~~~~~~~~~~~~~~~~~~~~

The Calmjs framework provides the framework to allow Python packages to
declare the dependencies they need against |npm| based packages for the
JavaScript code they provide, and also the system that allow Python
packages to declare which of their modules export JavaScript sources
that can be reused.

The utility included with |calmjs.rjs| provide the means to consume
those declarations, treating the JavaScript files as both source and
compilation target, with the final deployable artifact(s) being produced
through |r.js| from the |requirejs|_ package.

Currently, the source files could be written in both AMD and CommonJS
module formats, although the CommonJS format is recommended due to their
wide support under most systems, and that |calmjs.rjs| provides
transpilation and configuration generation utilities that processes the
JavaScript source code into a form that is compatible with the |r.js|
optimizer.  However, the ``exports`` statement in the source file should
be not part of ``module.exports`` for the mean time.  The AMD headers
and footers can be absent too, as the ``calmjs rjs`` transpiler will add
the appropriate headers and footers needed (for example, have
``require`` be imported from the correct source, or for mapping
``exports`` to ``module.exports``) so that the final script will be
usable for the target platform or format.

The resulting sources will be placed in a build directory, along with
all the declared bundled sources acquired from the Node.js package
managers or repositories.  A build file will then be generated that will
include all the relevant sources as selected to enable the generation of
the final artifact file through |r.js|.  These can then be deployed to
the appropriate environment, or the whole above process can be included
as part of the functionality of the Python backend at hand.

Ultimately, the goal of |calmjs.rjs| is to ease the integration and
interactions between of client-side JavaScript with server-side Python,
by simplifying the task of building, shipping and deployment of the two
set of sources in one shared package and environment.  The Calmjs
framework provides the linkage between these two environment and the
tools provided by there will assist with the setup of a common,
reproducible local Node.js environments.

Finally, for quality control, this package has integration with
|calmjs.dev|, which provides the tools needed to set up the test
environment and harnesses for running of JavaScript tests that are part
of the Python packages for the associated JavaScript code.  However,
that package is not declared as a direct dependency, as not all use
cases will require the availability of that package.  Please refer to
installation section for details.

Do note, in the initial implementation, the JavaScript source file
supported by this framework loosely follows certain definitions that
only mimic what ES6 intends to provide (as outlined earlier).  Even with
this, as a consequence of treating JavaScript within the Python package
as a source file for the compilation target which is the deployable
artifact file, the input source files and exported paths generated by
|calmjs.rjs| are NOT meant for direct consumption of web clients such as
web browsers.  The produced artifact from this framework will be usable
through the AMD API.


Installation
------------

It is recommended that the local environment already have Node.js and
|npm| installed at the very minimum to enable the installation of
|requirejs|, if it hasn't already been installed and available.  Also,
the version of Python must be either 2.7 or 3.3+; PyPy is supported,
with PyPy3 version 5.2.0-alpha1 must be used due to a upstream package
failing to function in the currently stable PyPy3 version 2.4.

To install |calmjs.rjs| into a given Python environment, it may be
installed directly from PyPI with the following command:

.. code:: sh

    $ pip install calmjs.rjs

Installing/using RequireJS with calmjs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To establish a development/build environment for a Python package with
the support for |r.js| through |calmjs.rjs| in the current working
directory (e.g. for a project), the following command may be executed:

.. code:: sh

    $ calmjs npm --install calmjs.rjs

While running ``npm install requirejs`` (along with other related
packages declared by |calmjs.rjs| that it needs from |npm|) will achieve
the same effect, do note the Calmjs framework makes it possible for
|npm| dependencies to be propagated down to dependent packages; such
that if a Python package that have declared |calmjs.rjs| as a dependency
(either through ``install_requires`` or an ``extras_require`` in its
``setup.py``) may have its complete set of dependencies on |npm| be
installed using the following command (assuming the package is named
``example.package``:

.. code:: sh

    $ calmjs npm --install example.package

All standard JavaScript and Node.js dependencies for ``example.package``
will now be installed into the current directory through the relevant
tools.  This process will also install all the other dependencies
through |npm| or |requirejs| that other Python packages depended on by
``example.package`` have declared.

For further details about how this all works can be found in the
documentation for |calmjs|_.  Otherwise, please continue on to the
`usage`_ section.

Alternative installation methods (advanced users)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Development is still ongoing with |calmjs.rjs|, for the latest features
and bug fixes, the development version can be installed through git like
so:

.. code:: sh

    $ pip install calmjs
    $ pip install git+https://github.com/calmjs/calmjs.rjs.git#egg=calmjs.rjs

Alternatively, the git repository can be cloned directly and execute
``python setup.py develop`` while inside the root of the source
directory.

Keep in mind that |calmjs| MUST be available before the ``setup.py``
within the |calmjs.rjs| source tree is executed, for it needs the
``package_json`` writing capabilities in |calmjs|.  Alternatively,
please execute ``python setup.py egg_info`` if any message about
``Unknown distribution option:`` is noted during the invocation of
``setup.py``.

As |calmjs| is declared as both namespace and package, there are certain
low-level setup that is required on the working Python environment to
ensure that all modules within can be located correctly.  However,
versions of ``setuptools`` earlier than `v31.0.0`__ does not create the
required package namespace declarations when a package is installed
using this development installation method when mixed with ``pip
install`` within the same namespace.  As a result, inconsistent import
failures can happen for any modules under the |calmjs| namespace.  As an
example:

.. __: https://setuptools.readthedocs.io/en/latest/history.html#v31-0-0

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
wheels acquired through ``pip``), or upgrade ``setuptools`` to version
31 or greater and reinstall all affected packages.

Testing the installation
~~~~~~~~~~~~~~~~~~~~~~~~

Finally, to verify for the successful installation of |calmjs.rjs|, the
included tests may be executed through this command:

.. code:: sh

    $ python -m unittest calmjs.rjs.tests.make_suite

However, if the steps to install external Node.js dependencies to the
current directory was followed, the current directory may be specified
as the ``CALMJS_TEST_ENV`` environment variable.  Under POSIX compatible
shells this may be executed instead from within that directory:

.. code:: sh

    $ CALMJS_TEST_ENV=. python -m unittest calmjs.rjs.tests.make_suite

Do note that if the |calmjs.dev| package is unavailable, a number of
tests will be skipped.  To avoid this, either install that package
separately, or install |calmjs.rjs| using its extras dependencies
declaration like so:

.. code:: sh

    $ pip install calmjs.rjs[dev]


Usage
-----

To generate a RequireJS artifact from packages that have JavaScript code
exposed through the Calmjs module registry system that are already
installed into the current environment, simply execute the following
command:

.. code:: sh

    $ calmjs rjs example.package

The following sections in this document will provide an overview on how
to enable the JavaScript module export feature for a given Python
package through the Calmjs module registry system, however a more
thorough description on this topic may be found in the README provided
by the |calmjs|_ package, under the section `Export JavaScript code from
Python packages`__.

.. __: https://pypi.python.org/pypi/calmjs/#export-javascript-code-from-python-packages

Declaring JavaScript exports for Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Any exposed JavaScript code through the ``calmjs.module`` registry will
be picked up and compiled into a working RequireJS artifact.  For
example, given the following entry points for that registry defined by a
package named ``example``:

.. code:: ini

    [calmjs.module]
    example = example

This is the most basic declaration that works for packages that share
the same name as the import location provided.

The following is am example for packages that have nested submodules
(called ``example.lib`` and ``example.app``):

.. code:: ini

    [calmjs.module]
    example.lib = example.lib
    example.app = example.app

While the import locations declared looks exactly like a Python module
(as per the rules of a Python entry point), the ``calmjs.module``
registry will present them using the CommonJS/ES6 style import paths
(i.e.  ``'example/lib'`` and ``'example/app'``), so users of that need
those JavaScript modules to be sure they ``require`` those strings.

Please also note that the default source extractor will extract all
JavaScript files within those directories.  Finally, as a consequence of
how the imports are done, it is recommended that no relative imports are
to be used.

If the package at hand does not directly declare its dependency on
|calmjs|, an explicit ``calmjs_module_registry=['calmjs.module']`` may
need to be declared in the ``setup`` function for the package to ensure
that this default module registry will be used to acquire the JavaScript
sources from.

Putting this together, the ``setup.py`` file should contain the
following:

.. code:: Python

    setup(
        name='example',
        # ... plus other declarations
        # This is one of the recommended options, even though the
        # project will not be importing from Calmjs.
        license='gpl',
        install_requires=[
            'calmjs>=3.0.0,<4',
            'calmjs.rjs>=2.0.0,<3',
            # plus other installation requirements
        ],
        # If the usage of the GPL is impossible for the project, or
        # declaring a direct dependency on calmjs packages is impossible
        # for the project for whatever other reasons (even though the
        # project itself will NOT be required to include/import ANY code
        # from the calmjs namespace), setup_requires may be used instead
        # of install_requires, and the following should also be included
        # as well:
        package_json={
            "devDependencies": {
                "requirejs": "~2.1.17",
            }
        },
        calmjs_module_registry=['calmjs.module'],
        # the entry points are required to allow calmjs to pick this up
        entry_points="""
        [calmjs.module]
        example = example
        example.lib = example.lib
        example.app = example.app
        """,
    )

For the construction of the RequireJS artifact, the command ``calmjs
rjs`` will automatically extract all relevant source files from the
dependencies of the selected Python package(s) into a temporary build
directory, where the build manifest will also be generated for the
invocation of ``r.js`` to construct the artifact.  An example run:

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

    $ calmjs rjs example --bundlepath-method empty --export-filename main.js

    Tracing dependencies for: /home/user/main.js

    /home/user/main.js
    ----------------
    /tmp/tmp_build/build/example/lib/form.js
    /tmp/tmp_build/build/example/lib/ui.js
    /tmp/tmp_build/build/example/lib/main.js
    /tmp/tmp_build/build/example/app/index.js

    $ calmjs rjs example --sourcepath-method empty --export-filename deps.js

    Tracing dependencies for: /home/user/deps.js

    /home/user/deps.js
    ----------------
    /tmp/tmp_build/build/jquery.js
    /tmp/tmp_build/build/underscore.js

The above example shows the generation of two separate artifacts, one
containing just the sources from the Python package ``example`` that had
been declared in the ``calmjs.module`` registry, and the other contains
only the external extra sources.

If the above triggers a dependency trace error for |r.js|, there is a
last resort ``--empty`` flag that can be applied; do note that this
completely disables the trace functionality for |r.js| as this initiates
a similar trace process to locate all the imported module names for
stubbing them out with the ``empty:`` scheme within the generated
configuration file.  Ensure that the modules required by the resulting
artifact has all its required modules provided elsewhere.

The explicit ``extras_calmjs`` declaration also supports the usage
through ``bower`` (supported via |calmjs.bower|_); instead of using
``node_modules`` as the key, ``bower_components`` should be used
instead.

Alternative registries aside from ``calmjs.module`` can be specified
with the ``--source-registry`` flag.  Assuming there are registries in
the current environment registered as ``myreg1`` and ``myreg2`` and the
``example`` package has registered sources to both of them, the command
to build a bundle from both those registries into one artifact can be
triggered like so:

.. code:: sh

    $ calmjs rjs --source-registry=myreg1,myreg2 example

Handling of RequireJS loader plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The AMD system as defined by RequireJS has the concept of loader
plugins, where the module name provided may be suffixed with a ``!`` as
arguments for handling by the plugin.  As the string provided after is
opaque to the |requirejs| system as a whole and thus handled directly by
the preceding plugin, the resources that it need will be specific to the
plugin itself.  As it may load resources through the |requirejs| system,
any paths that require configuration will need to be done.

To account for this issue, |calmjs.rjs| introduces the concept of loader
plugin handlers and a registry system for dealing with this.  A given
``RJSToolchain`` will have a default loader plugin registry assigned,
but this can be overridden by specifying a custom identifier (overriding
the default ``'calmjs.rjs.loader_plugin'``) for the registry to be used,
which will allow the handling of very customized loaders for a given
project.  Please refer to the ``calmjs.rjs.registry`` module for more
details on how this is constructed and set up for usage.

By default, the ``text`` handler is registered to the default loader
plugin registry, which should cover the most common use case encountered
by the |calmjs| framework.  Do note that packages are still required to
declare their (dev)dependencies in their ``package_json`` to the plugin,
ideally with a well constrained version, so to ensure a consistent build
experience for all end users.

Testing standalone, finalized RequireJS artifacts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AMD artifacts generated using the standard ``calmjs rjs`` toolchain
runtime may be tested using the ``calmjs karma`` runtime provided by the
``calmjs.dev`` package.  Given a finalized ``example.js`` that
implements the features provided by the ``example`` package, the
artifact may be tested with the tests provided by the ``example``
package using the following command:

.. code:: sh

    $ calmjs karma run \
        -t calmjs.rjs \
        --artifact=example.js \
        example

The above command invokes the standalone Karma runner using the
``calmjs.rjs`` settings to test against the ``example.js`` artifact
file, using the tests provided by the ``example`` package.  The test
execution is similar to the one during the development process.

Declare prebuilt JavaScript artifacts for Python packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, to complete the Python package deployment story, the process
should include the automatic generation and inclusion of the JavaScript
artifacts in the resulting Python wheel.  This can be achieved by
specifying an entry in the ``calmjs.artifacts`` registry, with the key
being the filename of the artifact and the value being the import
location to a builder.  A default builder function provided at
``calmjs.rjs.artifact:complete_rjs`` will enable the generation of a
complete RequireJS artifact for the Python package.  For example:

.. code:: ini

    [calmjs.artifacts]
    example.package.rjs.js = calmjs.rjs.artifact:complete_rjs

Once those entry points are installed, running ``calmjs artifact build
example.package`` will make use of the RequireJS toolchain and build the
artifact at ``example.package.rjs.js`` inside the ``calmjs_artifacts``
directory within the metadata directory for ``example.package``.
Alternatively, for solution more integrated with ``setuptools``, the
``setup`` function in ``setup.py`` should also enable the
``build_calmjs_artifacts`` flag such that ``setup.py build`` will also
trigger the building process.  This is useful for automatically
generating and including the artifact as part of the wheel building
process.  Consider this ``setup.py``:

.. code:: Python

    setup(
        name='example.package',
        # ... other required fields truncated
        build_calmjs_artifacts=True,
        entry_points="""
        # ... other entry points truncated
        [calmjs.module]
        example.package = example.package

        [calmjs.artifacts]
        example.package.rjs.js = calmjs.rjs.artifact:complete_rjs
        """,
    )

Building the wheel using ``setup.py`` may result in something like this.
Note that the execution of ``r.js`` was part of the process and that the
metadata (egg-info) directory was then built into the wheel.

.. code::

    $ python setup.py bdist_wheel
    running bdist_wheel
    running build
    ...
    running build_calmjs_artifacts
    automatically picked registries ['calmjs.module'] for sourcepaths
    using loaderplugin registry 'calmjs.rjs.loader_plugin'
    ...
    /src/example.package.egg-info/calmjs_artifacts/example.package.rjs.js
    ----------------
    /tmp/tmpm_2jf151/build/example/package/index.js
    ...
    running install_egg_info
    Copying src/example.package.egg-info to build/.../wheel/example.package...
    running install_scripts
    creating build/.../wheel/example.package-1.0.dist-info/WHEEL

For testing the package artifact, the following entry point should also
be specified under the ``calmjs.artifacts.tests`` registry, such that
running ``calmjs artifact karma example.package`` will execute the
JavaScript tests declared by ``example.package`` against the artifacts
that were declared in ``calmjs.artifacts``.

.. code:: ini

    [calmjs.artifacts.tests]
    example.package.rjs.js = calmjs.rjs.artifact:test_complete_rjs

Troubleshooting
---------------

The following are some known issues with regards to this package and its
integration with other Python/Node.js packages.

When calling ``calmjs rjs`` on a package, got ``ENOENT``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typically this is caused by source files from the source package or
registry invoking ``require`` a JavaScript module that is not available
in the build directory.  One possible cause through the ``calmjs``
framework is that the Python package failed to declare ``extras_calmjs``
that it might require, or that explicit map method and/or source
registry that was selected did not result in all required sources be
loaded into the build directory.

If the missing source files are intended, applying the ``--empty`` or
the ``-e`` flag to the ``rjs`` tool will stub out all the missing
modules from the bundle; do note that this will result in the generated
artifact bundle not having all the required modules for its execution.
The resulting artifact bundle should be used in conjunction with the
other artifact bundles that provide the result of the required
dependencies.

RJSRuntimeError: unable to locate 'r.js'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This means the current Node.js environment is missing the requirejs
package from |npm|; either install it manually with it or through
|calmjs| on this package.  If a given Python package is required to use
requirejs to generate the package, its ``package_json`` should declare
that, or declare dependency on ``calmjs.rjs``.

UserWarning: Unknown distribution option:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During setup and installation using the development method, if this
warning message is shown, please ensure the egg metadata is correctly
generated by running ``python setup.py egg_info`` in the source
directory, as the package |calmjs| was not available when the setup
script was initially executed.


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
