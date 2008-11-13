# Copyright (c) 2007-2008 Thomas Lotze
# See also LICENSE.txt

import os
import os.path
import unittest
from zope.testing import doctest


flags = (doctest.ELLIPSIS |
         doctest.INTERPRET_FOOTNOTES |
         doctest.NORMALIZE_WHITESPACE |
         doctest.REPORT_NDIFF)


def test_suite():
    return unittest.TestSuite([
        doctest.DocFileSuite(filename,
                             package="ophelia",
                             optionflags=flags,
                             )
        for filename in sorted(os.listdir(os.path.dirname(__file__)))
        if filename.endswith(".txt")
        ])
