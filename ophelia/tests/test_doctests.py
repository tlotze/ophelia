# Copyright (c) 2007-2012 Thomas Lotze
# See also LICENSE.txt

import doctest
import os
import os.path
import unittest


flags = (doctest.ELLIPSIS |
         doctest.NORMALIZE_WHITESPACE |
         doctest.REPORT_NDIFF)


def test_suite():
    return unittest.TestSuite([
        doctest.DocFileSuite(filename,
                             package="ophelia",
                             optionflags=flags,
                             )
        for filename in sorted(
                os.listdir(os.path.dirname(os.path.dirname(__file__))))
        if filename.endswith(".txt")
        ])
