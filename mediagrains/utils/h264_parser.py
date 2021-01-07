# Copyright 2021 British Broadcasting Corporation
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

"""H.264 raw bitstream parser"""

from typing import Optional, Dict, Iterator, Iterable, List, Tuple
from enum import IntEnum
from itertools import chain
from bitstring import BitStream, ReadError
from fractions import Fraction


class UnavailableParamSets(ValueError):
    """SPS or PPS referenced by a Slice are not available in the parsed bitstream"""
    pass


class NALUnitTypes(IntEnum):
    CODED_SLICE_NON_IDR_PICT = 1
    CODED_SLICE_DATA_PART_A = 2
    CODED_SLICE_DATA_PART_B = 3
    CODED_SLICE_DATA_PART_C = 4
    CODED_SLICE_IDR_PICT = 5
    SEI = 6
    SEQUENCE_PARAMETER_SET = 7
    PICTURE_PARAMETER_SET = 8
    ACCESS_UNIT_DELIMITER = 9
    END_OF_SEQUENCE = 10
    END_OF_STREAM = 11
    FILLER = 12
    SEQUENCE_PARAMETER_SET_EXT = 13
    PREFIX_NAL_UNIT = 14
    SUBSET_SEQUENCE_PARAMETER_SET = 15
    CODED_SLICE_AUX_NO_PART = 19
    CODED_SLICE_EXT = 20


class SPS(object):
    """Holds some but not all properties from a Sequence Parameter Set"""
    def __init__(self):
        self.profile_idc = None
        self.flags = None
        self.level_idc = None
        self.seq_parameter_set_id = None
        self.chroma_format_idc = 1
        self.chroma_array_type = 1
        self.video_format = 5
        self.colour_primaries = 2
        self.transfer_characteristics = 2
        self.matrix_coefficients = 2
        self.vui_parameters_present_flag = 0
        self.video_signal_type_present_flag = 0
        self.colour_description_present_flag = 0
        self.pic_height_in_map_units_minus1 = 0
        self.pic_width_in_mbs_minus1 = 0
        self.frame_mbs_only_flag = 0
        self.frame_crop_left_offset = 0
        self.frame_crop_top_offset = 0
        self.frame_crop_right_offset = 0
        self.frame_crop_bottom_offset = 0
        self.aspect_ratio_idc = 0
        self.sar_width = 0
        self.sar_height = 0
        self.timing_info_present_flag = 0
        self.num_units_in_tick = 0
        self.time_scale = 0
        self.fixed_frame_rate_flag = 0
        self.pic_order_cnt_type = 0
        self.log2_max_pic_order_cnt_lsb_minus4 = 0
        self.bit_depth_luma_minus8 = 0
        self.bit_depth_chroma_minus8 = 0
        self.separate_colour_plane_flag = 0
        self.log2_max_frame_num_minus4 = 0
        self.delta_pic_order_always_zero_flag = 0


class PPS(object):
    """Holds some but not all properties from a Picture Parameter Set"""
    def __init__(self):
        self.seq_parameter_set_id = 0
        self.pic_parameter_set_id = 0
        self.bottom_field_pic_order_in_frame_present_flag = 0
        self.redundant_pic_cnt_present_flag = 0


class SliceHeader(object):
    """Holds some but not all properties from a Slice header"""
    def __init__(self):
        self.slice_type = 0
        self.nal_ref_idc = 0
        self.nal_unit_type = 0
        self.pic_parameter_set_id = 0
        self.field_pic_flag = 0
        self.idr_pic_flag = 0
        self.idr_pic_id = 0
        self.pic_order_cnt_lsb = 0
        self.delta_pic_order_cnt_bottom = 0
        self.delta_pic_order_cnt_0 = 0
        self.delta_pic_order_cnt_1 = 0
        self.redundant_pic_cnt = 0
        self.frame_num = 0
        self.bottom_field_flag = 0


class FrameInfo(object):
    """Frame information parsed from the parameter sets and slice header"""
    def __init__(self):
        self.profile = None
        self.level = None
        self.flags = None
        self.bit_depth = None
        self.coded_width = None
        self.coded_height = None
        self.width = None
        self.height = None
        self.frame_rate = None
        self.fixed_frame_rate = None
        self.sample_aspect_ratio = None
        self.key_frame = None


class H264Parser(object):
    def __init__(self):
        self.sps_sets: Dict[int, SPS] = {}
        self.pps_sets: Dict[int, PPS] = {}

    @classmethod
    def get_nalu_byte_offsets(cls, frame_data: bytes) -> Iterator[int]:
        """Returns a generator of NALU offsets in the frame

        The nalu_byte_offsets offsets are at the start code prefix 0x000001.
        Add 3 to get to the start of the NAL data.

        :param frame_data: frame data bytes
        :returns: a iterable of byte offsets
        """
        frame_bits = BitStream(bytes=frame_data)
        return (offset//8 for offset in frame_bits.findall('0x000001', bytealigned=True))

    def parse_frame(self, frame_data: bytes) -> Tuple[Optional[int], Optional[Iterable[int]], Optional[FrameInfo]]:
        """Returns the frame size, unit offsets and frame info if emough data is available.

        Returns None if not enough data is available to detect the end of a frame.

        :param frame_data: frame data bytes
        :returns: tuple of frame size, NALU byte offsets and frame info, or None for all if there is insufficient data
        :raises ValueError: if the is an issue with the bitstream
        :raises MissingParameterSets: a ValueError that is raised if referenced SPS and PPS are unavailable
        """
        insufficient_data_return = (None, None, None)

        try:
            frame_bits = BitStream(bytes=frame_data)

            nalu_offsets = self._get_nalu_offsets(frame_bits)
            nalu_byte_offsets = []

            offset = next(nalu_offsets, None)
            if offset is None:
                # No NALU found
                return insufficient_data_return

            primary_slice_headers: List[SliceHeader] = []
            have_start_next_frame = False
            for next_offset in chain(nalu_offsets, [frame_bits.len]):
                nal_unit_type = self._parse_nal_unit_type(frame_bits[offset:next_offset])

                if (nal_unit_type == NALUnitTypes.CODED_SLICE_NON_IDR_PICT or
                        nal_unit_type == NALUnitTypes.CODED_SLICE_DATA_PART_A or
                        nal_unit_type == NALUnitTypes.CODED_SLICE_IDR_PICT):
                    rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                    slice_header = self._parse_slice_header(rbsp_bits)

                    pps = self.pps_sets[slice_header.pic_parameter_set_id]
                    sps = self.sps_sets[pps.seq_parameter_set_id]

                    if slice_header.redundant_pic_cnt == 0:
                        first_slice_header = None
                        if primary_slice_headers:
                            first_slice_header = primary_slice_headers[0]

                        # Detect one of a range of conditions that indicate this slice belongs to the
                        # next frame's primary coded picture
                        # See spec section 7.4.1.2.4 Detection of the first VCL NAL unit of a primary coded picture
                        if (first_slice_header is not None and
                                (slice_header.pic_parameter_set_id != first_slice_header.pic_parameter_set_id or
                                    slice_header.frame_num != first_slice_header.frame_num or
                                    slice_header.field_pic_flag != first_slice_header.field_pic_flag or
                                    (slice_header.field_pic_flag and
                                        slice_header.bottom_field_flag != first_slice_header.bottom_field_flag) or
                                    (slice_header.nal_ref_idc != first_slice_header.nal_ref_idc and
                                        (slice_header.nal_ref_idc != 0 or first_slice_header.nal_ref_idc != 0)) or
                                    slice_header.idr_pic_flag != first_slice_header.idr_pic_flag or
                                    (slice_header.idr_pic_flag == 1 and
                                        slice_header.idr_pic_id != first_slice_header.idr_pic_id) or
                                    (sps.pic_order_cnt_type == 0 and
                                        (slice_header.pic_order_cnt_lsb != first_slice_header.pic_order_cnt_lsb or
                                            slice_header.delta_pic_order_cnt_bottom != first_slice_header.delta_pic_order_cnt_bottom)) or
                                    (sps.pic_order_cnt_type == 1 and
                                        (slice_header.delta_pic_order_cnt_0 != first_slice_header.delta_pic_order_cnt_0 or
                                            slice_header.delta_pic_order_cnt_1 != first_slice_header.delta_pic_order_cnt_1)))):
                            have_start_next_frame = True
                            break

                        primary_slice_headers.append(slice_header)

                elif (primary_slice_headers and
                        (nal_unit_type == NALUnitTypes.ACCESS_UNIT_DELIMITER or
                            nal_unit_type == NALUnitTypes.SEQUENCE_PARAMETER_SET or
                            nal_unit_type == NALUnitTypes.PICTURE_PARAMETER_SET or
                            nal_unit_type == NALUnitTypes.SEI or
                            (nal_unit_type >= 15 and nal_unit_type <= 18))):
                    have_start_next_frame = True
                    break

                elif nal_unit_type == NALUnitTypes.SEQUENCE_PARAMETER_SET:
                    rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                    sps = self._parse_sps(rbsp_bits)
                    self.sps_sets[sps.seq_parameter_set_id] = sps

                elif nal_unit_type == NALUnitTypes.PICTURE_PARAMETER_SET:
                    rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                    pps = self._parse_pps(rbsp_bits)
                    self.pps_sets[pps.pic_parameter_set_id] = pps

                assert(offset is not None)
                nalu_byte_offsets.append(offset//8)
                offset = next_offset

            if have_start_next_frame:
                frame_info = None
                if primary_slice_headers:
                    frame_info = self._extract_frame_info(primary_slice_headers)

                # The NALU offsets assumes 3-byte start codes but the start of the frame should have 4 and
                # so the next frame start should be at next_offset - 1
                assert(offset is not None)
                frame_size = offset//8
                if frame_size > 0 and frame_data[frame_size - 1] == 0:
                    frame_size -= 1

                return (frame_size, nalu_byte_offsets, frame_info)
            else:
                return insufficient_data_return

        except ReadError:
            # Insufficient data to detect the start of the next frame
            return insufficient_data_return

    def parse_frame_info(self,
                         frame_data: bytes,
                         nalu_byte_offsets: Optional[Iterable[int]] = None) -> Optional[FrameInfo]:
        """Parse flow information from the frame is possible

        The nalu_byte_offsets offsets are at the start code prefix.

        :param frame_data: frame data bytes
        :param nalu_byte_offsets: list of NALU byte offsets
        :returns: FrameInfo if the frame contains primary slices and the active SPS is available, else None
        :raises ValueError: if a parse failure occurs
        """
        frame_bits = BitStream(bytes=frame_data)

        if nalu_byte_offsets is None:
            nalu_offsets = self._get_nalu_offsets(frame_bits)
        else:
            # change byte offsets to bit offsets iterator
            nalu_offsets = (offset*8 for offset in nalu_byte_offsets)

        offset = next(nalu_offsets, None)
        if offset is None:
            raise ValueError("No NALUs in H.264 frame")

        # Parse the active SPS and primary slice header.
        primary_slice_headers = []
        for next_offset in chain(nalu_offsets, [frame_bits.len]):
            nal_unit_type = self._parse_nal_unit_type(frame_bits[offset:next_offset])

            if (nal_unit_type == NALUnitTypes.CODED_SLICE_NON_IDR_PICT or
                    nal_unit_type == NALUnitTypes.CODED_SLICE_DATA_PART_A or
                    nal_unit_type == NALUnitTypes.CODED_SLICE_IDR_PICT):
                # Parse the slice header
                rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                slice_header = self._parse_slice_header(rbsp_bits)

                # Stop if not a primary slice header
                if slice_header.redundant_pic_cnt != 0:
                    break

                primary_slice_headers.append(slice_header)

            elif nal_unit_type <= NALUnitTypes.CODED_SLICE_IDR_PICT:
                # No primary slices
                break

            elif nal_unit_type == NALUnitTypes.SEQUENCE_PARAMETER_SET:
                rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                sps = self._parse_sps(rbsp_bits)
                self.sps_sets[sps.seq_parameter_set_id] = sps

            elif nal_unit_type == NALUnitTypes.PICTURE_PARAMETER_SET:
                rbsp_bits = self._parse_rbsp_bits(frame_bits[offset:next_offset])
                pps = self._parse_pps(rbsp_bits)
                self.pps_sets[pps.pic_parameter_set_id] = pps

            offset = next_offset

        if primary_slice_headers:
            return self._extract_frame_info(primary_slice_headers)
        else:
            return None

    def _extract_frame_info(self,
                            primary_slice_headers: List[SliceHeader]) -> Optional[FrameInfo]:
        """Extract frame info from the parsed SPS

        :param primary_slice_headers: the primary slice headers
        :returns: a FrameInfo if the active SPS is available, else None
        """
        if not primary_slice_headers:
            return None

        # Get the active SPS
        if primary_slice_headers[0].pic_parameter_set_id in self.pps_sets:
            pps_id = primary_slice_headers[0].pic_parameter_set_id
            pps = self.pps_sets[pps_id]
            if pps.seq_parameter_set_id in self.sps_sets:
                sps = self.sps_sets[pps.seq_parameter_set_id]
        if not sps:
            return None

        frame_info = FrameInfo()

        frame_info.profile = sps.profile_idc
        frame_info.flags = sps.flags
        frame_info.level = sps.level_idc
        if sps.bit_depth_luma_minus8 is not None:
            frame_info.bit_depth = sps.bit_depth_luma_minus8 + 8

        frame_info.coded_width = (sps.pic_width_in_mbs_minus1 + 1) * 16
        frame_info.coded_height = (sps.pic_height_in_map_units_minus1 + 1) * 16 * (2 - sps.frame_mbs_only_flag)

        if sps.chroma_array_type == 0:
            crop_unit_x = 1
            crop_unit_y = 2 - sps.frame_mbs_only_flag
        else:
            if sps.chroma_array_type == 1:
                sub_width_c = 2
                sub_height_c = 2
            elif sps.chroma_array_type == 2:
                sub_width_c = 2
                sub_height_c = 1
            else:  # sps.chroma_array_type == 3
                sub_width_c = 1
                sub_height_c = 1
            crop_unit_x = sub_width_c
            crop_unit_y = sub_height_c * (2 - sps.frame_mbs_only_flag)

        x_offset = crop_unit_x * sps.frame_crop_left_offset
        y_offset = crop_unit_y * sps.frame_crop_top_offset

        frame_info.width = frame_info.coded_width - crop_unit_x * sps.frame_crop_right_offset - x_offset
        frame_info.height = frame_info.coded_height - crop_unit_y * sps.frame_crop_bottom_offset - y_offset

        frame_info.sample_aspect_ratio = self._get_sample_aspect_ratio(sps)

        if sps.timing_info_present_flag:
            if sps.time_scale == 0 or sps.num_units_in_tick == 0:
                raise ValueError("Invalid timing info: time_scale={}, num_units_in_tick={}".format(
                    sps.time_scale, sps.num_units_in_tick
                ))

            # NOTE: this doesn't implement section D.2.2 of H.264 spec. and explanation surrounding Table E-6
            delta_tfi_divisor = 2
            if primary_slice_headers[0].field_pic_flag:
                delta_tfi_divisor = 1

            frame_info.frame_rate = Fraction(sps.time_scale, sps.num_units_in_tick * delta_tfi_divisor)
            frame_info.fixed_frame_rate = sps.fixed_frame_rate_flag != 0

        # If all primary slices are an I type then this is a key frame
        for slice_header in primary_slice_headers:
            frame_info.key_frame = slice_header.slice_type in [2, 4, 7, 9]  # I, SI, I2, SI2
            if not frame_info.key_frame:
                break

        return frame_info

    def _get_sample_aspect_ratio(self, sps: SPS) -> Optional[Fraction]:
        """Return the sample aspect ratio"""
        aspect_ratios = [
            (0, 1),
            (1, 1),
            (12, 11),
            (10, 11),
            (16, 11),
            (40, 33),
            (24, 11),
            (20, 11),
            (32, 11),
            (80, 33),
            (18, 11),
            (15, 11),
            (64, 33),
            (160, 99),
            (4, 3),
            (3, 2),
            (2, 1),
        ]

        if sps.aspect_ratio_idc == 255:  # extended SAR
            return Fraction(sps.sar_width, sps.sar_height)
        elif sps.aspect_ratio_idc < len(aspect_ratios):
            return Fraction(aspect_ratios[sps.aspect_ratio_idc][0], aspect_ratios[sps.aspect_ratio_idc][1])
        else:
            return None

    def _parse_nal_unit_type(self, bits: BitStream) -> int:
        """Peek NALU for NAL Unit Type

        :param bits: NALU bits
        :returns: NAL Unit Type
        """
        self._parse_start_code_prefix(bits)

        bits.read('uint:1')  # forbidden_zero_bit
        bits.read('uint:2')  # nal_ref_idc
        nal_unit_type = bits.read('uint:5')

        return nal_unit_type

    def _parse_sps(self, rbsp_bits: BitStream) -> SPS:
        """Parse SPS NALU

        :param bits: RBSP bits
        :returns: parsed SPS
        :raises ValueError: if a parse failure occurs
        """
        sps = SPS()

        rbsp_bits.read('uint:1')  # forbidden_zero_bit
        rbsp_bits.read('uint:2')  # nal_ref_idc
        rbsp_bits.read('uint:5')  # nal_unit_type

        sps.profile_idc = rbsp_bits.read('uint:8')
        sps.flags = rbsp_bits.read('uint:8')  # constraint_set0...set5_flag + reserved_zero_2bits
        sps.level_idc = rbsp_bits.read('uint:8')
        sps.seq_parameter_set_id = rbsp_bits.read('ue')
        if sps.seq_parameter_set_id > 31:
            raise ValueError("seq_parameter_set_id exceeds maximum 31")
        if sps.profile_idc in [100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135]:
            sps.chroma_format_idc = rbsp_bits.read('ue')
            if sps.chroma_format_idc > 3:
                raise ValueError("chroma_format_idc exceeds maximum 3")
            if sps.chroma_format_idc == 3:
                sps.separate_colour_plane_flag = rbsp_bits.read('uint:1')
            if sps.separate_colour_plane_flag == 0:
                sps.chroma_array_type = sps.chroma_format_idc
            else:
                sps.chroma_array_type = 0
            sps.bit_depth_luma_minus8 = rbsp_bits.read('ue')
            if sps.bit_depth_luma_minus8 > 6:
                raise ValueError("bit_depth_luma_minus8 exceeds maximum 6")
            sps.bit_depth_chroma_minus8 = rbsp_bits.read('ue')
            if sps.bit_depth_chroma_minus8 > 6:
                raise ValueError("bit_depth_chroma_minus8 exceeds maximum 6")
            rbsp_bits.read('uint:1')  # qpprime_y_zero_transform_bypass_flag
            seq_scaling_matrix_present_flag = rbsp_bits.read('uint:1')
            if seq_scaling_matrix_present_flag:
                num_scaling_lists = 8 if sps.chroma_format_idc != 3 else 12
                for i in range(num_scaling_lists):
                    seq_scaling_list_present_flag = rbsp_bits.read('uint:1')
                    if seq_scaling_list_present_flag:
                        size = 4*4 if i < 6 else 8*8
                        last_scale = 8
                        next_scale = 8
                        for j in range(size):
                            if next_scale != 0:
                                delta_scale = rbsp_bits.read('se')
                                next_scale = (last_scale + delta_scale + 256) % 256
                            last_scale = last_scale if next_scale == 0 else next_scale
        sps.log2_max_frame_num_minus4 = rbsp_bits.read('ue')
        sps.pic_order_cnt_type = rbsp_bits.read('ue')
        if sps.pic_order_cnt_type == 0:
            sps.log2_max_pic_order_cnt_lsb_minus4 = rbsp_bits.read('ue')
        elif sps.pic_order_cnt_type == 1:
            sps.delta_pic_order_always_zero_flag = rbsp_bits.read('uint:1')
            rbsp_bits.read('se')  # offset_for_non_ref_pic
            rbsp_bits.read('se')  # offset_for_top_to_bottom_field
            num_ref_frames_in_pic_order_cnt_cycle = rbsp_bits.read('ue')
            if num_ref_frames_in_pic_order_cnt_cycle > 255:
                raise ValueError("num_ref_frames_in_pic_order_cnt_cycle exceeds maximum 255")
            for i in range(num_ref_frames_in_pic_order_cnt_cycle):
                rbsp_bits.read('se')  # offset_for_ref_frame[i]
        rbsp_bits.read('ue')  # max_num_ref_frames
        rbsp_bits.read('uint:1')  # gaps_in_frame_num_value_allowed_flag
        sps.pic_width_in_mbs_minus1 = rbsp_bits.read('ue')
        sps.pic_height_in_map_units_minus1 = rbsp_bits.read('ue')
        sps.frame_mbs_only_flag = rbsp_bits.read('uint:1')
        if not sps.frame_mbs_only_flag:
            rbsp_bits.read('uint:1')  # mb_adaptive_frame_field_flag
        rbsp_bits.read('uint:1')  # direct_8x8_inference_flag
        frame_cropping_flag = rbsp_bits.read('uint:1')
        if frame_cropping_flag:
            sps.frame_crop_left_offset = rbsp_bits.read('ue')
            sps.frame_crop_right_offset = rbsp_bits.read('ue')
            sps.frame_crop_top_offset = rbsp_bits.read('ue')
            sps.frame_crop_bottom_offset = rbsp_bits.read('ue')
        sps.vui_parameters_present_flag = rbsp_bits.read('uint:1')
        if sps.vui_parameters_present_flag:
            aspect_ratio_present_flag = rbsp_bits.read('uint:1')
            if aspect_ratio_present_flag:
                sps.aspect_ratio_idc = rbsp_bits.read('uint:8')
                if sps.aspect_ratio_idc == 255:  # 255 == extended SAR
                    sps.sar_width = rbsp_bits.read('uint:16')
                    sps.sar_height = rbsp_bits.read('uint:16')
            overscan_info_present_flag = rbsp_bits.read('uint:1')
            if overscan_info_present_flag:
                rbsp_bits.read('uint:1')  # overscan_appropriate_flag
            sps.video_signal_type_present_flag = rbsp_bits.read('uint:1')
            if sps.video_signal_type_present_flag:
                sps.video_format = rbsp_bits.read('uint:3')
                rbsp_bits.read('uint:1')  # video_full_range_flag
                sps.colour_description_present_flag = rbsp_bits.read('uint:1')
                if sps.colour_description_present_flag:
                    sps.colour_primaries = rbsp_bits.read('uint:8')
                    sps.transfer_characteristics = rbsp_bits.read('uint:8')
                    sps.matrix_coefficients = rbsp_bits.read('uint:8')
            chroma_loc_info_present_flag = rbsp_bits.read('uint:1')
            if chroma_loc_info_present_flag:
                rbsp_bits.read('ue')  # chroma_sample_loc_type_top_field
                rbsp_bits.read('ue')  # chroma_sample_loc_type_bottom_field
            sps.timing_info_present_flag = rbsp_bits.read('uint:1')
            if sps.timing_info_present_flag:
                sps.num_units_in_tick = rbsp_bits.read('uint:32')
                sps.time_scale = rbsp_bits.read('uint:32')
                sps.fixed_frame_rate_flag = rbsp_bits.read('uint:1')

        # Ignore the rest

        return sps

    def _parse_pps(self, rbsp_bits: BitStream) -> PPS:
        """Parse PPS NALU

        :param bits: RBSP bits
        :returns: parsed PPS
        :raises ValueError: if a parse failure occurs
        """
        pps = PPS()

        rbsp_bits.read('uint:1')  # forbidden_zero_bit
        rbsp_bits.read('uint:2')  # nal_ref_idc
        rbsp_bits.read('uint:5')  # nal_unit_type

        pps.pic_parameter_set_id = rbsp_bits.read('ue')
        pps.seq_parameter_set_id = rbsp_bits.read('ue')
        rbsp_bits.read('uint:1')  # entropy_coding_mode_flag
        pps.bottom_field_pic_order_in_frame_present_flag = rbsp_bits.read('uint:1')
        num_slice_groups_minus1 = rbsp_bits.read('ue')
        if num_slice_groups_minus1 > 0:
            slice_group_map_type = rbsp_bits.read('ue')
            if slice_group_map_type == 0:
                for _ in range(0, num_slice_groups_minus1 + 1):
                    rbsp_bits.read('ue')  # run_length_minus1[]
            elif slice_group_map_type == 2:
                for _ in range(0, num_slice_groups_minus1):
                    rbsp_bits.read('ue')  # top_left[]
                    rbsp_bits.read('ue')  # bottom_right[]
            elif slice_group_map_type == 3 or slice_group_map_type == 4 or slice_group_map_type == 5:
                rbsp_bits.read('uint:1')  # slice_group_change_direction_flag
                rbsp_bits.read('ue')  # slice_group_change_rate_minus1
            elif slice_group_map_type == 6:
                pic_size_in_map_units_minus1 = rbsp_bits.read('ue')
                for _ in range(0, pic_size_in_map_units_minus1 + 1):
                    value = pic_size_in_map_units_minus1 + 1
                    bits_required = 63
                    while bits_required and not (value & (1 << bits_required)):
                        bits_required -= 1
                    rbsp_bits.read('uint:{}'.format(bits_required))  # slice_group_id[]
        rbsp_bits.read('ue')  # num_ref_idx_l0_default_active_minus1
        rbsp_bits.read('ue')  # num_ref_idx_l1_default_active_minus1
        rbsp_bits.read('uint:1')  # weighted_pred_flag
        rbsp_bits.read('uint:2')  # weighted_bipred_idc
        rbsp_bits.read('se')  # pic_init_qp_minus26
        rbsp_bits.read('se')  # pic_init_qs_minus26
        rbsp_bits.read('se')  # chroma_qp_index_offset
        rbsp_bits.read('uint:1')  # deblocking_filter_control_present_flag
        rbsp_bits.read('uint:1')  # constrained_intra_pred_flag
        pps.redundant_pic_cnt_present_flag = rbsp_bits.read('uint:1')

        # Ignore the rest

        return pps

    def _parse_slice_header(self, rbsp_bits: BitStream) -> SliceHeader:
        """Parse slice header NALU

        :param bits: RBSP bits
        :returns: parsed slice header
        :raises ValueError: if a parse failure occurs
        """
        slice_header = SliceHeader()

        rbsp_bits.read('uint:1')  # forbidden_zero_bit
        slice_header.nal_ref_idc = rbsp_bits.read('uint:2')
        slice_header.nal_unit_type = rbsp_bits.read('uint:5')

        slice_header.idr_pic_flag = 1 if slice_header.nal_unit_type == NALUnitTypes.CODED_SLICE_IDR_PICT else 0

        rbsp_bits.read('ue')  # first_mb_in_slice
        slice_header.slice_type = rbsp_bits.read('ue')
        slice_header.pic_parameter_set_id = rbsp_bits.read('ue')

        try:
            # Get the PPS referenced by the Slice Header, which in turns references an SPS
            pps = self.pps_sets[slice_header.pic_parameter_set_id]
            sps = self.sps_sets[pps.seq_parameter_set_id]
        except KeyError:
            raise UnavailableParamSets()

        if sps.separate_colour_plane_flag:
            rbsp_bits.read('uint:2')  # colour_plane_id
        slice_header.frame_num = rbsp_bits.read('uint:{}'.format(sps.log2_max_frame_num_minus4 + 4))
        if not sps.frame_mbs_only_flag:
            slice_header.field_pic_flag = rbsp_bits.read('uint:1')
            if slice_header.field_pic_flag:
                slice_header.bottom_field_flag = rbsp_bits.read('uint:1')
        if slice_header.idr_pic_flag:
            slice_header.idr_pic_id = rbsp_bits.read('ue')
        if sps.pic_order_cnt_type == 0:
            slice_header.pic_order_cnt_lsb = rbsp_bits.read('uint:{}'.format(sps.log2_max_pic_order_cnt_lsb_minus4 + 4))
            if pps.bottom_field_pic_order_in_frame_present_flag and not slice_header.field_pic_flag:
                slice_header.delta_pic_order_cnt_bottom = rbsp_bits.read('se')
        if sps.pic_order_cnt_type == 1 and not sps.delta_pic_order_always_zero_flag:
            slice_header.delta_pic_order_cnt_0 = rbsp_bits.read('se')
            if pps.bottom_field_pic_order_in_frame_present_flag and not slice_header.field_pic_flag:
                slice_header.delta_pic_order_cnt_1 = rbsp_bits.read('se')
        if pps.redundant_pic_cnt_present_flag:
            slice_header.redundant_pic_cnt = rbsp_bits.read('ue')

        # Ignore the rest

        return slice_header

    def _get_nalu_offsets(self, bits: BitStream) -> Iterator[int]:
        """Returns a generator of NALU offsets in the frame

        The offsets are at the prefix 0x000001.

        :param bits: the frame bits
        :returns: a generator of bit offsets
        """
        return bits.findall('0x000001', bytealigned=True)

    def _parse_rbsp_bits(self, bits: BitStream) -> BitStream:
        """Return raw byte sequence payload that excludes emulation prevention bytes

        :param bits: the NALU bits
        :returns: the raw byte sequence payload
        """
        self._parse_start_code_prefix(bits)
        rbsp_start = bits.pos

        emu_offsets = bits.findall('0x000003', bytealigned=True)
        emu_offset = next(emu_offsets, None)
        if emu_offset is None:
            return bits

        rbsp_bits = bits[rbsp_start:emu_offset+2*8]
        for next_emu_offset in emu_offsets:
            rbsp_bits.append(bits[emu_offset+3*8:next_emu_offset+2*8])
            emu_offset = next_emu_offset
        rbsp_bits.append(bits[emu_offset+3*8:])

        return rbsp_bits

    def _parse_start_code_prefix(self, bits: BitStream) -> List[int]:
        """Parse the 3 or 4 byte start code prefix

        :param bits: the NALU bits
        :returns: the start code prefix bytes
        """
        start_code_prefix = bits.readlist('3*uint:8')  # start code prefix
        if start_code_prefix == [0x00, 0x00, 0x00]:
            # we get this if the NALU offsets were provided and the start code prefix is 4 bytes
            start_code_prefix.append(bits.read('uint:8'))
        if start_code_prefix[-1] != 0x01 or start_code_prefix[-2] != 0x00 or start_code_prefix[-3] != 0x00:
            raise ValueError("Invalid NALUs start code prefix")

        return start_code_prefix
