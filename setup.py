#!/usr/bin/env python
#
# Copyright (c) 2006-2012 Thomas Lotze
# See also LICENSE.txt

# This should be only one line. If it must be multi-line, indent the second
# line onwards to keep the PKG-INFO file format intact.
"""Ophelia builds a web site from TAL templates with zero code repetition.
"""

from setuptools import setup, find_packages
import glob
import os.path
import sys


def project_path(*names):
    return os.path.join(os.path.dirname(__file__), *names)


longdesc = "\n\n".join((open(project_path("README.txt")).read(),
                        open(project_path("ABOUT.txt")).read()))

entry_points = """\
    [console_scripts]
    ophelia-wsgiref = ophelia.wsgi:wsgiref_server

    [paste.app_factory]
    main = ophelia.wsgi:Application.paste_app_factory
"""

install_requires = [
    "xsendfile",
    "zope.interface",
    "zope.tales",
    "zope.pagetemplate",
    "zope.exceptions",
    ]

extras_require = {
    "test": [
        'distribute',
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
      version='0.4',
      description=__doc__.strip(),
      long_description=longdesc,
      keywords="web template xhtml tal wsgi python",
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
      data_files=[('', glob.glob(project_path('*.txt')))],
      zip_safe=False,
      )
