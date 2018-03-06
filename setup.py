#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

from __future__ import print_function
from setuptools import setup
import os


def check_packages(packages):
    failure = False
    for python_package, package_details in packages:
        try:
            __import__(python_package)
        except ImportError:
            failure = True
            print("Cannot find", python_package,)
            print("you need to install :", package_details)

    return not failure


def check_dependencies(packages):
    failure = False
    for python_package, dependency_filename, dependency_url in packages:
        try:
            __import__(python_package)
        except ImportError:
            failure = True
            print()
            print("Cannot find", python_package,)
            print("you need to install :", dependency_filename)
            print("... originally retrieved from", dependency_url)

    return not failure


def is_package(path):
    return (
        os.path.isdir(path) and
        os.path.isfile(os.path.join(path, '__init__.py'))
        )


def find_packages(path, base=""):
    """ Find all packages in path """
    packages = {}
    for item in os.listdir(path):
        dir = os.path.join(path, item)
        if is_package(dir):
            if base:
                module_name = "%(base)s.%(item)s" % vars()
            else:
                module_name = item
            packages[module_name] = dir
            packages.update(find_packages(dir, module_name))
    return packages


packages = find_packages(".")
package_names = packages.keys()

packages_required = [
    "nmoscommon",
    "enum34",
    "six",
    "frozendict",
]

deps_required = []

setup(name="mediagrains",
      version="0.1.0",
      description="Simple utility for grain-based media",
      url='https://github.com/bbc/rd-apmm-python-lib-mediagrains',
      author='James Weaver',
      author_email='james.barrett@bbc.co.uk',
      license='Apache 2',
      packages=package_names,
      package_dir=packages,
      install_requires=packages_required,
      scripts=[],
      data_files=[],
      long_description="""
Simple python library for dealing with grain data in a python-native format.
""")
