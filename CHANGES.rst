Changelog
=========

2.0.1 (2018-05-03)
------------------

- Update the export_target production and usage of working_dir to be
  inline with what is expected by ``calmjs-3.1.0``. [
  `#3 <https://github.com/calmjs/calmjs.rjs/issues/3>`_
  ]

2.0.0 (2018-01-12)
------------------

- Support for ``calmjs-3.0.0`` features and breaking changes.
- Loader plugin framework migrated upstream; downstream packages that
  make use of them should no longer declare explicit entries in
  ``extras_calmjs`` to permit wider portability.
- Removed usage of ``slimit`` in favor of the capabilities now provided
  by ``calmjs`` and ``calmjs.parse``.
- The flags for the ``calmjs rjs`` runtime have been changed to remove
  some naming confusion, mainly due to sourcemap and also to maintain
  consistency with other ``calmjs`` tools.

  - ``--bundle-map-method`` is deprecated in favor for
    ``--bundlepath-method``; will be fully removed by 3.0.0
  - ``--source-map-method`` is deprecated in favor for
    ``--sourcepath-method``; will be fully removed by 3.0.0

- Provide a generic package-level artifact builder for the
  ``calmjs.artifacts`` registry along with the respective tester for the
  ``calmjs.artifacts.tests`` registry.

1.0.2 (2017-05-22)
------------------

- Corrected the issue where plugins that have been unmapped using the
  ``empty:`` scheme triggering ``FileNotFoundError``.

1.0.1 (2017-01-27)
------------------

- Load the non-test files in deps also, instead as part of the tests to
  avoid automatic inclusion.
- Test files should start with the name test as per convention.

1.0.0 (2016-11-18)
------------------

- Initial implementation that brings in the support of the production of
  AMD artifacts (bundles) from JavaScript sources included with Python
  packages (along with their declared dependencies through ``npm`` or
  other supported tools) through the calmjs framework.
- Enabled the ``calmjs rjs`` tool entry point.
- Also provide integration with ``calmjs.dev`` by correcting the correct
  hooks so that this package can be used as an advice package for the
  execution of tests against artifacts generated through this package.
