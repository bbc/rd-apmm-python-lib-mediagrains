#!/usr/bin/python
#
# Copyright 2018 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import print_function

from setuptools import setup
from sys import version_info

packages = {
    'mediagrains': 'mediagrains',
    'mediagrains.hypothesis': 'mediagrains/hypothesis',
    'mediagrains.comparison': 'mediagrains/comparison',
    'mediagrains.utils': 'mediagrains/utils'
}

packages_required = [
    "mediatimestamp >= 1.2.0",
    'enum34 >= 1.1.6;python_version<"3.4"',
    "six >= 1.10.0",
    "frozendict >= 1.2",
    'numpy >= 1.17.2;python_version>="3.6"',
    'numpy;python_version<"3.6"'
]

deps_required = []


if version_info[0] > 3 or (version_info[0] == 3 and version_info[1] >= 6):
    packages['mediagrains_py36'] = 'mediagrains_py36'
    packages['mediagrains_py36.asyncio'] = 'mediagrains_py36/asyncio'


package_names = list(packages.keys())

setup(name="mediagrains",
      version="2.6.0.post0",
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
