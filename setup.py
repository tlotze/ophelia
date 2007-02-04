#!/usr/bin/env python
# -*- coding: latin-1 -*-
#
# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

"""Create XHTML pages from templates written in Zope TAL.

Ophelia creates XHTML pages from templates written in TAL, the Zope Tag
Attribute Language. It is designed to reduce code repetition to zero.

At present, Ophelia contains a request handler for the Apache2 web server.
"""

import os, os.path
import glob
from setuptools import setup, find_packages


def include_tree(dest, source):
    source_len = len(source)
    for dirpath, dirnames, filenames in os.walk(source):
        yield (dest + dirpath[source_len:],
               [os.path.join(dirpath, fn) for fn in filenames])
        if ".svn" in dirnames:
            dirnames.remove(".svn")

desc, longdesc = __doc__.split("\n\n", 1)

data_files = [("", glob.glob("*.txt"))] + list(include_tree("doc", "doc"))

provides = [
    "ophelia",
    ]

setup(name="Ophelia",
      version="trunk",
      description=desc,
      long_description=longdesc,
      author="Thomas Lotze",
      author_email="thomas@thomas-lotze.de",
      url="http://www.thomas-lotze.de/en/software/ophelia/",
      license="ZPL 2.1",
      packages=find_packages(),
      include_package_data=True,
      data_files=data_files,
      provides=provides,
      )
