#!/usr/bin/env python
#
# Copyright (c) 2006-2012 Thomas Lotze
# See also LICENSE.txt

"""Ophelia builds a web site from TAL templates with zero code repetition.
"""

from setuptools import setup, find_packages
import glob
import os.path
import sys


project_path = lambda *names: os.path.join(os.path.dirname(__file__), *names)

longdesc = "\n\n".join((open(project_path("README.txt")).read(),
                        open(project_path("ABOUT.txt")).read()))

root_files = glob.glob(project_path("*.txt"))
data_files = [("", [name for name in root_files
                    if os.path.split(name)[1] != "index.txt"])]

entry_points = {
    "console_scripts": [
    "ophelia-dump = ophelia.dump:dump",
    "ophelia-wsgiref = ophelia.wsgi:wsgiref_server",
    ],
    }

install_requires = [
    "xsendfile",
    "zope.interface",
    "zope.tales",
    "zope.pagetemplate",
    "zope.exceptions",
    ]

extras_require = {
    "test": [
        'setuptools',
        'webtest',
        ],
    }

# BBB Python 2.6 compatibility
if sys.version_info < (2, 7):
    extras_require['test'].append('unittest2')

classifiers = """\
Environment :: Web Environment
License :: OSI Approved :: Zope Public License
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.6
Programming Language :: Python :: 2.7
Programming Language :: Python :: 2 :: Only
Topic :: Internet :: WWW/HTTP
Topic :: Internet :: WWW/HTTP :: Dynamic Content
"""[:-1].split('\n')

setup(name="ophelia",
      version="0.4dev",
      description=__doc__.strip(),
      long_description=longdesc,
      keywords="web template xhtml tal",
      classifiers=classifiers,
      author="Thomas Lotze",
      author_email="thomas@thomas-lotze.de",
      url="http://thomas-lotze.de/en/software/ophelia/",
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
