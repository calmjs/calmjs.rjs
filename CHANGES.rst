Changelog
=========

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
