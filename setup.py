#!/usr/bin/env python3
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

from setuptools import setup

packages = {
    'mediagrains': 'mediagrains',
    'mediagrains.hypothesis': 'mediagrains/hypothesis',
    'mediagrains.comparison': 'mediagrains/comparison',
    'mediagrains.utils': 'mediagrains/utils',
    'mediagrains.asyncio': 'mediagrains/asyncio',
    'mediagrains.numpy': 'mediagrains/numpy',
    'mediagrains.tools': 'mediagrains/tools',
    'mediagrains.patterngenerators': 'mediagrains/patterngenerators',
    'mediagrains.patterngenerators.video': 'mediagrains/patterngenerators/video',
    'mediagrains.patterngenerators.audio': 'mediagrains/patterngenerators/audio'
}

packages_required = [
    "mediajson >=2.0.0",
    "mediatimestamp >=2.1.0",
    "frozendict >= 1.2",
    'numpy >= 1.17.2',
    'mypy',
    'deprecated >= 1.2.6',
    "bitstring"
]

deps_required = []

package_names = list(packages.keys())

console_scripts = [
    'wrap_video_in_gsf=mediagrains.tools:wrap_video_in_gsf',
    'wrap_audio_in_gsf=mediagrains.tools:wrap_audio_in_gsf',
    'extract_gsf_essence=mediagrains.tools:extract_gsf_essence',
    'gsf_probe=mediagrains.tools:gsf_probe'
]

setup(name="mediagrains",
      version="2.15.1.post1",
      python_requires='>=3.6.0',
      description="Simple utility for grain-based media",
      url='https://github.com/bbc/rd-apmm-python-lib-mediagrains',
      author='James Weaver',
      author_email='james.barrett@bbc.co.uk',
      license='Apache 2',
      packages=package_names,
      package_dir=packages,
      package_data={name: ['py.typed'] for name in package_names},
      install_requires=packages_required,
      entry_points={
          'console_scripts': console_scripts
      },
      data_files=[],
      long_description="""
Simple python library for dealing with grain data in a python-native format.
""")
