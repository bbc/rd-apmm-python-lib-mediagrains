#!/usr/bin/env python3
#
# Copyright 2021 British Broadcasting Corporation
#
# This is an internal BBC tool and is not licensed externally
# If you have received a copy of this erroneously then you do
# not have permission to reproduce it.

import argparse
import importlib.util
import sys
from unittest import mock
from pkg_resources import Requirement

parser = argparse.ArgumentParser(description='Extract a requirements.txt file from a setup.py')
parser.add_argument('file', type=str, nargs='?', default="./setup.py",
                    help='the file to process')
parser.add_argument('--output', '-o', type=str, default=None,
                    help='the file to output')
parser.add_argument('--constraints', '-c', action='store_true',
                    help='generate a constraints file instead of a requirements file')
args = parser.parse_args()

if args.output is None:
    outfile = sys.stdout
else:
    outfile = open(args.output, 'w')

module_name = 'setup'
spec = importlib.util.spec_from_file_location(module_name, args.file)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module

with mock.patch("setuptools.setup") as setup:
    spec.loader.exec_module(module)

name = setup.mock_calls[-1][2]['name']
requirements = [Requirement.parse(r) for r in setup.mock_calls[-1][2]['install_requires']]

if args.constraints:
    # constraints files must not contain extras, and should not contain anything with no version specified
    requirements = [r for r in requirements if r.specs]
    for r in requirements:
        r.extras = tuple()

outfile.write("""\
# {}.txt for {} automatically extracted from setup.py
#

""".format('constraints' if args.constraints else 'requirements', name))
outfile.write('\n'.join(str(r) for r in requirements))
outfile.write('\n')
