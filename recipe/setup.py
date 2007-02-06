#!/usr/bin/env python
#
# Copyright (c) 2007 Thomas Lotze
# See also LICENSE.txt

from setuptools import setup


entry_points = {
    "zc.buildout": [
    "apacheroot = apacheroot:ApacheRoot"
    ],
    }

setup(name="recipe",
      entry_points=entry_points,
      )
