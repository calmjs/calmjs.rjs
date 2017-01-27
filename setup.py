from setuptools import setup
from setuptools import find_packages

version = '1.0.1'

classifiers = """
Development Status :: 5 - Production/Stable
Environment :: Console
Intended Audience :: Developers
License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)
Operating System :: OS Independent
Programming Language :: JavaScript
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3.3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
""".strip().splitlines()

package_json = {
    "dependencies": {
        "requirejs": "~2.1.17",
        # This should be provided by some templating library that
        # require text templates through the same import mechanism.
        # "requirejs-text": "~2.0.12",
    },
    "devDependencies": {
        "karma-requirejs": "~0.2.2",
    },
}


long_description = (
    open('README.rst').read()
    + '\n' +
    open('CHANGES.rst').read()
    + '\n')

setup(
    name='calmjs.rjs',
    version=version,
    description=(
        "Package for the integration of RequireJS into a Python "
        "environment via the Calmjs framework, to provide a reproducible "
        "workflow for the generation of deployable artifacts from "
        "JavaScript source code provided by Python packages in "
        "conjunction with standard JavaScript or Node.js packages sourced "
        "from npm or other similar package repositories."
    ),
    long_description=long_description,
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=classifiers,
    keywords='',
    author='Tommy Yu',
    author_email='tommy.yu@auckland.ac.nz',
    url='https://github.com/calmjs/calmjs.rjs',
    license='gpl',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['calmjs'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'calmjs>=2.0.0,<3',
        'slimit>=0.8.0',
    ],
    extras_require={
        'dev': [
            'calmjs.dev>=1.0.2,<2',
        ],
    },
    entry_points={
        # If to be unleashed as a standalone tool.
        # 'console_scripts': [
        #     'rjs = calmjs.rjs.runtime:default',
        # ],
        'calmjs.registry': [
            'calmjs.rjs.loader_plugin'
            ' = calmjs.rjs.registry:LoaderPluginRegistry',
        ],
        'calmjs.rjs.loader_plugin': [
            'text = calmjs.rjs.plugin:TextPlugin',
        ],
        'calmjs.runtime': [
            'rjs = calmjs.rjs.runtime:default',
        ],
        'calmjs.toolchain.advice': [
            'calmjs.dev.toolchain:KarmaToolchain = calmjs.rjs.dev:rjs_advice',
        ],
    },
    package_json=package_json,
    calmjs_module_registry=['calmjs.module'],
    test_suite="calmjs.rjs.tests.make_suite",
)
