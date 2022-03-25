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

"""\
The submodule of mediagrains which contains the actual classes used to
represent grains. In general these classes do not need to be used
directly by client code, but their documentation may be instructive.
"""

from .grains import (
    GRAIN,
    VIDEOGRAIN,
    AUDIOGRAIN,
    CODEDVIDEOGRAIN,
    CODEDAUDIOGRAIN,
    EVENTGRAIN,
    attributes_for_grain_type,
    size_for_audio_format
)

__all__ = ["GRAIN", "VIDEOGRAIN", "AUDIOGRAIN", "CODEDVIDEOGRAIN", "CODEDAUDIOGRAIN", "EVENTGRAIN",
           "attributes_for_grain_type", "size_for_audio_format"]

if __name__ == "__main__":  # pragma: no cover
    from uuid import uuid1, uuid5
    from .grains import GrainFactory

    src_id = uuid1()
    flow_id = uuid5(src_id, "flow_id:test_flow")

    grain1 = GrainFactory(src_id=src_id, flow_id=flow_id)
    print(grain1)
