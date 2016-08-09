import unittest
from os.path import dirname


def test_suite():
    import calmjs.rjs
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(
        'calmjs.rjs.tests', pattern='test_*.py',
        # namespace packages are actually going to interfere if not
        # very explicit here.
        top_level_dir=dirname(calmjs.rjs.__file__)
    )
    return test_suite
