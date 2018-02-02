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
from __future__ import print_function
from uuid import UUID
from nmoscommon.timestamp import Timestamp
from collections import Sequence
from fractions import Fraction

class Grain(Sequence):
    """\
    A class representing a generic media grain.

        Several possible ways to construct:

          Grain(src_id, flow_id, origin_timestamp=current_time, sync_timestamp=origin_timestamp)

        creates a new empty grain in the specified source id (uuid.UUID or string) and flow_id

          Grain(meta, [ data ])

        creates a new grain with the specified data and optional buffer object for payload

    Any grain can be freely cast to a tuple:

      (meta, data)

    where meta is a dictionary containing the grain metadata, and data is a python buffer object representing the payload (or None for an empty grain).
    """
    def __init__(self, *args, **kwargs):
        meta = None
        data  = None
        if 'meta' in kwargs:
            meta = kwargs['meta']
        elif len(args) > 0:
            meta = args[0]
            if len(args) > 1:
                data = args[1]

        if 'data' in kwargs:
            data = kwargs['data']

        if isinstance(meta, dict):
            self.meta = meta
            self.data = data
        else:

            src_id = None
            flow_id = None
            cts = Timestamp.get_time()
            ots = None
            sts = None

            if "src_id" in kwargs:
                src_id = kwargs["srcid"]
            elif len(args) > 0:
                src_id = args[0]
                if len(args) > 1:
                    flow_id = args[1]
                    if len(args) > 2:
                        ots = args[2]
                        if len(args) > 3:
                            sts = args[3]
            if "flow_id" in kwargs:
                flow_id = kwargs["flow_id"]
            if "origin_timestamp" in kwargs:
                ots = kwargs["origin_timestamp"]
            if "sync_timestamp" in kwargs:
                sts = kwargs["sync_timestamp"]

            if src_id is None or flow_id is None:
                raise AttributeError("Must specify at least meta or src_id and flow_id")

            if ots is None:
                ots = cts
            if sts is None:
                sts = ots

            if isinstance(src_id, UUID):
                src_id = str(src_id)
            if isinstance(flow_id, UUID):
                flow_id = str(flow_id)

            if not isinstance(src_id, basestring) or not isinstance(flow_id, basestring):
                raise AttributeError("Invalid types for src_id and flow_id")

            self.meta = {
                "@_ns": "urn:x-ipstudio:ns:0.1",
                "grain": {
                    "grain_type": "empty",
                    "source_id": src_id,
                    "flow_id": flow_id,
                    "origin_timestamp": str(ots),
                    "sync_timestamp": str(sts),
                    "creation_timestamp": str(cts),
                    "rate": {
                        "numerator": 0,
                        "denominator": 1,
                        },
                    "duration": {
                        "numerator": 0,
                        "denominator": 1,
                        },
                    }
                }
            self.data = None

    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index == 0:
            return self.meta
        elif index == 1:
            return self.data
        else:
            raise IndexError("tuple index out of range")

    def __repr__(self):
        if self.data is None:
            return "Grain({!r})".format(self.meta)
        else:
            return "Grain({!r},{!r})".format(self.meta, self.data)

    @property
    def grain_type(self):
        return self.meta['grain']['grain_type']

    @grain_type.setter
    def grain_type(self, value):
        self.meta['grain']['grain_type'] = value

    @property
    def source_id(self):
        return UUID(self.meta['grain']['source_id'])

    @source_id.setter
    def source_id(self, value):
        self.meta['grain']['source_id'] = str(value)

    @property
    def flow_id(self):
        return UUID(self.meta['grain']['flow_id'])

    @flow_id.setter
    def flow_id(self, value):
        self.meta['grain']['flow_id'] = str(value)

    @property
    def origin_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['origin_timestamp'])

    @origin_timestamp.setter
    def origin_timestamp(self, value):
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
        self.meta['grain']['origin_timestamp'] = value

    @property
    def sync_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['sync_timestamp'])

    @sync_timestamp.setter
    def sync_timestamp(self, value):
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
        self.meta['grain']['sync_timestamp'] = value

    @property
    def creation_timestamp(self):
        return Timestamp.from_tai_sec_nsec(self.meta['grain']['creation_timestamp'])

    @creation_timestamp.setter
    def creation_timestamp(self, value):
        if isinstance(value, Timestamp):
            value = value.to_tai_sec_nsec()
        self.meta['grain']['creation_timestamp'] = value

    @property
    def rate(self):
        return Fraction(self.meta['grain']['rate']['numerator'],
                        self.meta['grain']['rate']['denominator'])

    @rate.setter
    def rate(self, value):
        value = Fraction(value)
        self.meta['grain']['rate'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def duration(self):
        return Fraction(self.meta['grain']['duration']['numerator'],
                        self.meta['grain']['duration']['denominator'])

    @duration.setter
    def duration(self, value):
        value = Fraction(value)
        self.meta['grain']['duration'] = {
            'numerator': value.numerator,
            'denominator': value.denominator
            }

    @property
    def timelabels(self):
        if 'timelabels' in self.meta:
            return self.meta['timelabels']
        else:
            return []

if __name__ == "__main__":
    from uuid import uuid1, uuid5

    src_id = uuid1()
    flow_id = uuid5(src_id, "flow_id:test_flow")

    grain1 = Grain(src_id, flow_id)
    grain2 = Grain(grain1.meta)
    print(grain1)
    print(grain2)
