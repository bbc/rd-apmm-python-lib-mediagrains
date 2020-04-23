#!/usr/bin/env python3
#
# Copyright 2019 British Broadcasting Corporation
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
"""Given GSF file, dump out the raw essence"""

import argparse
import sys
import mediajson

from ..gsf import GSFDecoder
from ._file_or_pipe import file_or_pipe


def extract_gsf_essence():
    """Provide a utility to extract raw essence from a GSF file"""
    parser = argparse.ArgumentParser(
        description="A utility to dump the essence data out of a GSF file"
    )

    parser.add_argument("input_file", help="Input file. Specify - for stdin", type=str)
    parser.add_argument("output_file", help="Output GSF file path. Specify - for stdout", type=str)

    parser.add_argument("--only-id", help="Only include Grains with this GSF local ID. May be specified more than once",
                        type=int, action="append", default=None)

    args = parser.parse_args()

    with file_or_pipe(args.input_file, "rb") as input_data, file_or_pipe(args.output_file, "wb") as output_data:
        decoder = GSFDecoder(file_data=input_data)
        decoder.decode_file_headers()

        for grain, local_id in decoder.grains(local_ids=args.only_id):
            print("Got grain with local_id {} at {}".format(local_id, grain.origin_timestamp.to_sec_nsec()),
                  file=sys.stderr)
            output_data.write(grain.data)


def gsf_probe():
    """Provide a utility to dump information about a GSF file"""
    parser = argparse.ArgumentParser(
        description="A utility to dump the metadata out of a GSF file"
    )

    parser.add_argument("input_file", help="Input file. Specify - for stdin", type=str)

    args = parser.parse_args()

    with file_or_pipe(args.input_file, "rb") as input_data:
        decoder = GSFDecoder(file_data=input_data)
        file_data = decoder.decode_file_headers()

        file_data["segments"] = {segment["local_id"]: segment for segment in file_data["segments"]}
        file_data["created"] = str(file_data["created"])  # Work around mediajson's inability to serialize datetimes

        for grain, local_id in decoder.grains(load_lazily=True):
            this_segment = file_data["segments"][local_id]

            try:
                this_segment["timerange"] = \
                    this_segment["timerange"].extend_to_encompass_timerange(grain.origin_timerange())
            except KeyError:
                this_segment["timerange"] = grain.origin_timerange()
                this_segment["grain_data"] = grain.meta["grain"]

        print(mediajson.dumps(file_data, indent=True))
