#!/usr/bin/env python
#
# Copyright (c) 2006-2008 Thomas Lotze
# See also LICENSE.txt

"""Ophelia builds a web site from TAL templates with zero code repetition.
"""

import os.path
import glob
from setuptools import setup, find_packages


project_path = lambda *names: os.path.join(os.path.dirname(__file__), *names)

longdesc = open(project_path("README.txt")).read() + """
Changes
=======

For a continuously updated change log, see
<https://svn.thomas-lotze.de/repos/public/Ophelia/trunk/CHANGES.txt>.
"""

data_files = [("", glob.glob(project_path("*.txt")))]

entry_points = {
    "console_scripts": [
    "ophelia-dump = ophelia.dump:dump",
    "ophelia-wsgiref = ophelia.wsgi:wsgiref_server [wsgiref]",
    ],
    }

install_requires = [
    "zope.interface",
    "zope.tales",
    "zope.tal<3.5", # XXX remove this line in 0.4
    "zope.pagetemplate",
    "zope.exceptions",
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
      version="trunk",
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
      zip_safe=False,
      test_suite="ophelia.tests.test_suite",
      )
