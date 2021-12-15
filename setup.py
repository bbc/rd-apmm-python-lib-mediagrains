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

# Basic metadata
name = 'mediagrains'
description = "Simple utility for grain-based media"
url = 'https://github.com/bbc/rd-apmm-python-lib-mediagrains'
author = u'James Sandford'
author_email = u'james.sandford@bbc.co.uk'
license = 'Apache 2'
long_description = description


# Execute version file to set version variable
try:
    with open(("{}/_version.py".format(name)), "r") as fp:
        exec(fp.read())
except IOError:
    # Version file doesn't exist, fake it for now
    __version__ = "0.0.0"

package_names = [
    'mediagrains',
    'mediagrains.hypothesis',
    'mediagrains.comparison',
    'mediagrains.utils',
    'mediagrains.asyncio',
    'mediagrains.numpy',
    'mediagrains.tools',
    'mediagrains.patterngenerators',
    'mediagrains.patterngenerators.video',
    'mediagrains.patterngenerators.audio'
]
packages = {
    pkg: pkg.replace('.', '/') for pkg in package_names
}

packages_required = [
    "mediajson >=2.0.0",
    "mediatimestamp >=2.1.0",
    "frozendict >= 1.2",
    'numpy >= 1.17.2',
    'deprecated >= 1.2.6',
    "bitstring"
]

console_scripts = [
    'wrap_video_in_gsf=mediagrains.tools:wrap_video_in_gsf',
    'wrap_audio_in_gsf=mediagrains.tools:wrap_audio_in_gsf',
    'extract_gsf_essence=mediagrains.tools:extract_gsf_essence',
    'gsf_probe=mediagrains.tools:gsf_probe'
]

setup(name=name,
      version=__version__,
      python_requires='>=3.10.0',
      description=description,
      url=url,
      author=author,
      author_email=author_email,
      license=license,
      packages=package_names,
      package_dir=packages,
      package_data={package_name: ['py.typed'] for package_name in package_names},
      install_requires=packages_required,
      entry_points={
          'console_scripts': console_scripts
      },
      data_files=[],
      long_description=long_description)
