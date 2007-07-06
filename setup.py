#!/usr/bin/env python
# -*- coding: latin-1 -*-
#
# Copyright (c) 2006-2007 Thomas Lotze
# See also LICENSE.txt

"""Ophelia builds a web site from TAL templates with zero code repetition.
"""

import os, os.path
import glob
from setuptools import setup, find_packages


project_path = lambda *names: os.path.join(os.path.dirname(__file__), *names)


def include_tree(dest, source):
    source_len = len(source)
    for dirpath, dirnames, filenames in os.walk(source):
        yield (dest + dirpath[source_len:],
               [os.path.join(dirpath, fn) for fn in filenames])
        if ".svn" in dirnames:
            dirnames.remove(".svn")


longdesc = open(project_path("doc", "OVERVIEW.txt")).read()

data_files = [("", glob.glob(project_path("*.txt")))] + \
             list(include_tree("doc", "doc"))

entry_points = {
    "console_scripts": [
    "ophelia-dump = ophelia.dump:dump",
    "ophelia-wsgiref = ophelia.wsgi:wsgiref_server [wsgiref]",
    ],
    }

provides = [
    "ophelia",
    ]

install_requires = [
    "zope.interface",
    "zope.tales",
    "zope.pagetemplate",
    "zope.exceptions",
    "feedparser",
    ]

extras_require = {
    "test": ["zope.testing"],
    "wsgiref": ["wsgiref"],
    }

classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Web Environment",
    "License :: OSI Approved :: Zope Public License",
    "Programming Language :: Python",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ]

setup(name="ophelia",
      version="0.3",
      description=__doc__.strip(),
      long_description=longdesc,
      keywords="web template xhtml tal",
      classifiers=classifiers,
      author="Thomas Lotze",
      author_email="thomas@thomas-lotze.de",
      url="http://www.thomas-lotze.de/en/software/ophelia/",
      license="ZPL 2.1",
      packages=find_packages(),
      entry_points=entry_points,
      install_requires=install_requires,
      extras_require=extras_require,
      include_package_data=True,
      data_files=data_files,
      provides=provides,
      test_suite="ophelia.tests.test_suite",
      )
