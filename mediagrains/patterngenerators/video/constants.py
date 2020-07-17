#
# Copyright 2020 British Broadcasting Corporation
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
from ...cogenums import CogFrameFormat

__all__ = ["pixel_ranges"]

# information about formats
# in the order:
# (num_bytes_per_sample, (offset, range), (offset, range), (offset, range), active_bits_per_sample)
# in YUV order
pixel_ranges = {
    CogFrameFormat.U8_444: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.U8_422: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.U8_420: (1, (16, 235-16), (128, 224), (128, 224), 8),
    CogFrameFormat.S16_444_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_422_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_420_10BIT: (2, (64, 940-64), (512, 896), (512, 896), 10),
    CogFrameFormat.S16_444_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_422_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_420_12BIT: (2, (256, 3760-256), (2048, 3584), (2048, 3584), 12),
    CogFrameFormat.S16_444: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
    CogFrameFormat.S16_422: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
    CogFrameFormat.S16_420: (2, (4096, 60160-4096), (32768, 57344), (32768, 57344), 16),
}
