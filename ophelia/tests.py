# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

import unittest
from zope.testing.doctestunit import DocFileSuite


def test_suite():
    return unittest.TestSuite((
        DocFileSuite("util.txt", package="ophelia"),
        ))


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
