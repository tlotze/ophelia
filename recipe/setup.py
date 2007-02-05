from setuptools import setup

entry_points = {
    "zc.buildout": [
    "apacheroot = apacheroot:ApacheRoot"
    ],
    }

setup(name="recipe",
      entry_points=entry_points,
      )
