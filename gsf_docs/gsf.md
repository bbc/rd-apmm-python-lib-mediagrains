# Grain Sequence Format

**Version 8.0**

A Grain Sequence Format (GSF) file contains a sequence of grains from one or more flows. It has the mimetype application/x-ips-gsf and a filename typically uses the suffix `.gsf`.

The GSF file uses version **2.0** of the [SSB format](ssb.md) that defines the base file structure and data types.


## General File Structure

Each file begins with a 12 octet [SSB header](ssb.md#general-file-structure):

| Name          | Data       | Type     | Size     |
|---------------|------------|----------|----------|
| signature     | "SSBB"     | Tag      | 4 octets |
| file_type     | "grsg"     | Tag      | 4 octets |
| major_version | 0x0008     | Unsigned | 2 octets |
| minor_version | 0x0000     | Unsigned | 2 octets |

The current GSF version is 8.0. See the [SSB Versioning ](ssb.md#versioning) section for a description of how versioning works from a reader's perspective.

Every GSF file starts with a single [head](#head-block) block, which itself contains other types of blocks, followed by a (possibly empty) sequence of [grai](#grai-block) blocks and finally a [grai](#grai-block) terminator block.

The [grai](#grai-block) terminator block has the block *size* set to 0 (and no content) which signals to readers that the GSF stream has ended. It is typically used by readers when receiving a GSF stream where the sender does not know the duration beforehand and has set *count* in [segm](#segm-block) to -1.

As such the overall structure of the file is (count shown in brackets):

* File header
* [head](#head-block) (1): file identify and creation time
    * [segm](#segm-block) (0..*): segment info
        * [tag](#tag-block) (0..*): segment tags
    * [tag](#tag-block) (0..*): file tags
* [grai](#grai-block) (0..*): grain info and data
    * [gbhd](#gbhd-block) (0..1): grain header
        * [tils](#tils-block) (0..1): time labels
        * [vghd](#vghd-block) (0..1): video grain header
            * [comp](#comp-block) (0..1): video component info
        * [cghd](#cghd-block) (0..1): coded video grain header
            * [unof](#unof-block) (0..1): unit offsets in coded data
        * [aghd](#aghd-block) (0..1): audio grain header
        * [cahd](#cahd-block) (0..1): coded audio grain header
        * [eghd](#eghd-block) (0..1): data grain header
    * [grdt](#grdt-block) (1): grain data
* [grai](#grai-block) (0..1): terminator block


## "head" Block

The unique "head" block consists of a standard block header

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "head"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by some special header fields:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| id            |            | UUID     | 16 octets |
| created       |            | DateTime | 7 octets  |

Where *id* is a UUID identifying the file itself, and *created* is a timestamp identifying when the file was laid down.

The "head" block then contains any number of [segm](#segm-block) and [tag](#tag-block) blocks (with any other blocks in-between).

## "segm" Block

Each [segm](#segm-block) block describes a segment within the file. Each segment contains a number of grains, but the actual grain data is not included in this block, which is more of an *index* of segments.

It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "segm"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by some special header fields:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| local_id      |            | Unsigned | 2 octets  |
| id            |            | UUID     | 16 octets |
| count         |            | Signed   | 8 octets  |

where *local_id* is a numerical identifier for the segment, which is unique within the file, *id* is a UUID for the segment, and *count* is the number of grains considered part of this segment or -1 to indicate the number of grains is unknown. The *id* could be used to transfer and persist a global unique identifier for the segment but it is generally not used as the GSF (segment) is a transient representation for the grains. A segment, which is defined locally by the *local_id*, contains grains from a single flow.

## "tag " Block

Each [tag](#tag-block) block contains a 'tag' used to provide user extensible metadata for the immediate parent block - the [segm](#segm-block) and [grai](#grai-block) block. Each such tag is a pair of strings, referred to as the *key* and *val*.

It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "tag "     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by two variable length string fields, one for *key* and one for *val*:

| Name          | Data       | Type         | Size      |
|---------------|------------|--------------|-----------|
| key           |            | VarString    | variable  |
| val           |            | VarString    | variable  |

where the maximum string length for either *key* or *val* is 65535 octets. Note that the VarString *size* includes 2 octets to encode the string length.

A [tag](#tag-block) block will not have any child blocks.

## "grai" Block

Each [grai](#grai-block) block contains the actual data for a grain. Every grain in every segment in the file is represented by such a block.

It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "grai"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by a single field containing the *local_id* of the segment to which the grain belongs (and a segment contains grains of a single flow, all using the same *local_id*):

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| local_id      |            | Unsigned | 2 octets  |

It is then followed by a [gbhd](#gbhd-block) block and then a [grdt](#grdt-block) block (with any other blocks in-between). Note that an empty grain type still requires a (empty) [grdt](#grdt-block) block.

## "gbhd" Block

Each [gbhd](#gbhd-block) block contains the metadata for a grain header. It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "gbhd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the fields of the common grain header:

| Name          | Data       | Type         | Size      |
|---------------|------------|--------------|-----------|
| src_id        |            | UUID         | 16 octets |
| flow_id       |            | UUID         | 16 octets |
| origin_ts     |            | Timestamp    | 11 octets |
| sync_ts       |            | Timestamp    | 11 octets |
| rate          |            | Rational     | 8 octets  |
| duration      |            | Rational     | 8 octets  |

The *src_id* is the source identifier for the grains, *flow_id* is the flow identifier, *origin_ts* is the origin timestamp, *sync_ts* is the synchronisation timestamp, *rate* is the grain rate and *duration* is the grain duration. The *sync_ts* field is not used in practice.

The [gbhd](#gbhd-block) block then contains (in any order and with any other blocks in-between) an optional [tils](#tils-block) block, and a mandatory block for the non-empty grain types:

* Video Grain: a [vghd](#vghd-block) block.
* Coded Video Grain: a [cghd](#cghd-block) block.
* Audio Grain: an [aghd](#aghd-block) block.
* Coded Audio Grain: a [cahd](#cahd-block) block.
* Event Grain: an [eghd](#eghd-block) block.
* Empty Grain: no block.

## "tils" Block

Each [tils](#tils-block) block contains tagged time labels for the grain it exists in. If the grain has none then this block should be ommitted. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "tils"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the number of time labels:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| num_labels    |            | Unsigned | 2 octets  |

Then, for each label the following data:

| Name          | Data       | Type      | Size      |
|---------------|------------|-----------|-----------|
| label         |            | Timelabel | 29 octets |

## "vghd" Block

Each [vghd](#vghd-block) block contains the header data for a video grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "vghd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the grain data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| format        |            | Unsigned | 4 octets  |
| layout        |            | Unsigned | 4 octets  |
| width         |            | Unsigned | 4 octets  |
| height        |            | Unsigned | 4 octets  |
| extension     |            | Unsigned | 4 octets  |
| aspect_ratio  |            | Rational | 8 octets  |
| pixel\_aspect_ratio  |            | Rational | 8 octets  |

followed by an optional [comp](#comp-block) block (with any other blocks in-between).

The *format* and *layout* parameters are enumerated values as defined in [cogenums.py](../mediagrains/cogenums.py). The values originated from the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* (from the `CogFrameFormat` enum class) are:

| Name              | Enumeration   |
|-------------------|---------------|
| ALPHA_U8_1BIT     | 0x1080        |
| U8_444            | 0x2000        |
| U8_422            | 0x2001        |
| U8_420            | 0x2003        |
| U8_444_RGB        | 0x2010        |
| ALPHA_U8          | 0x2080        |
| YUYV              | 0x2100        |
| UYVY              | 0x2101        |
| AYUV              | 0x2102        |
| RGB               | 0x2104        |
| RGBx              | 0x2110        |
| xRGB              | 0x2111        |
| BGRx              | 0x2112        |
| xBGR              | 0x2113        |
| RGBA              | 0x2114        |
| ARGB              | 0x2115        |
| BGRA              | 0x2116        |
| ABGR              | 0x2117        |
| S16_444_10BIT     | 0x2804        |
| S16_444_10BIT_RGB | 0x2814        |
| S16_422_10BIT     | 0x2805        |
| S16_420_10BIT     | 0x2807        |
| ALPHA_S16_10BIT   | 0x2884        |
| v210              | 0x2906        |
| S16_444_12BIT     | 0x3004        |
| S16_444_12BIT_RGB | 0x3014        |
| S16_422_12BIT     | 0x3005        |
| S16_420_12BIT     | 0x3007        |
| ALPHA_S16_12BIT   | 0x3084        |
| S16_444           | 0x4004        |
| S16_444_RGB       | 0x4014        |
| S16_422           | 0x4005        |
| S16_420           | 0x4007        |
| ALPHA_S16         | 0x4084        |
| v216              | 0x4105        |
| S32_444           | 0x8008        |
| S32_444_RGB       | 0x8018        |
| S32_422           | 0x8009        |
| S32_420           | 0x800b        |
| ALPHA_S32         | 0x8088        |
| UNKNOWN           | 0xfffffffe    |
| INVALID           | 0xffffffff    |

The current set of known *layouts* (from the `CogFrameLayout` enum class) are:

| Name            | Enumeration   |
|-----------------|---------------|
| FULL_FRAME      | 0x00          |
| SEPARATE_FIELDS | 0x01          |
| SINGLE_FIELD    | 0x02          |
| MIXED_FIELDS    | 0x03          |
| SEGMENTED_FRAME | 0x04          |
| UNKNOWN         | 0xfffffffe    |

The *width* and *height* are the video dimensions, *extension* is the number of pixels to edge extend the frame by, *aspect_rate* is the display aspect ratio (eg. 4:3 or 16:9) and *pixel_aspect_ratio* is the pixel aspect ratio (eg. 1:1, 12:11).

## "comp" Block

Each [comp](#comp-block) block contains the component sizes for a video grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "comp"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the number of components (usually either 1 or 3):

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| num_comps     |            | Unsigned | 2 octets  |

Then, for each component the following data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| width         |            | Unsigned | 4 octets  |
| height        |            | Unsigned | 4 octets  |
| stride        |            | Unsigned | 4 octets  |
| length        |            | Unsigned | 4 octets  |

where *width* is the number of samples per line, *height* is the number of lines, *stride* is the number of octets between the start of each line and the start of the next, and *length* is the number of octets from the start of the data for this component to the start of the data for the next component or the end of the grain data.

## "cghd" Block

Each [cghd](#cghd-block) block contains the header data for a coded video grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "cghd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the grain data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| format        |            | Unsigned | 4 octets  |
| layout        |            | Unsigned | 4 octets  |
| origin_width  |            | Unsigned | 4 octets  |
| origin_height |            | Unsigned | 4 octets  |
| coded_width   |            | Unsigned | 4 octets  |
| coded_height  |            | Unsigned | 4 octets  |
| key_frame     |            | Boolean  | 1 octet   |
| temporal_offset |            | Signed | 4 octets  |

The *format* and *layout* parameters are enumerated values as defined in [cogenums.py](../mediagrains/cogenums.py). The values originated from the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* (from the `CogFrameFormat` enum class) are:

| Name          | Enumeration   |
|---------------|---------------|
| MJPEG         | 0x0200        |
| DNxHD         | 0x0201        |
| MPEG2         | 0x0202        |
| AVCI          | 0x0203        |
| H264          | 0x0204        |
| DV            | 0x0205        |
| D10           | 0x0206        |
| VC2           | 0x0207        |
| VP8           | 0x0208        |
| H265          | 0x0209        |
| UNKNOWN       | 0xfffffffe    |
| INVALID       | 0xffffffff    |

The *layouts* are the same as those described in the [vghd](#vghd-block) block. The *origin_width* and *origin_height* are the original frame dimensions that were input to the encoder and is the output of the decoder after applying any clipping. The *coded_width* and *coded_height* are the frame dimensions used to encode from, eg. including padding to meet the fixed macroblock size requirement. The *key_frame* is set to true if the video frame is a key frame, eg. an I-frame. The *temporal_offset* is the offset between display and stored order for inter-frame coding schemes (offset = display - stored).

The [cghd](#cghd-block) block is followed by an optional [unof](#unof-block) block (with any other blocks in-between).

## "unof" Block

Each [unof](#unof-block) block contains the offsets from the start of the data section for coded units within a coded grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "unof"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the number of unit offset:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| num_units     |            | Unsigned | 2 octets  |

Then, for each component the following data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| unit_offset   |            | Unsigned | 4 octets  |

this information is optional, and not meaningful for all coded formats.

## "aghd" Block

Each [aghd](#aghd-block) block contains the header data for an audio grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "aghd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the grain data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| format        |            | Unsigned | 4 octets  |
| channels      |            | Unsigned | 2 octets  |
| samples       |            | Unsigned | 4 octets  |
| sample_rate   |            | Unsigned | 4 octets  |

The *format* parameter enumerated values are defined in [cogenums.py](../mediagrains/cogenums.py). The values originated from the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* (from the `CogAudioFormat` class) are:

| Name               | Enumeration   |
|--------------------|---------------|
| S16_PLANES         | 0x00          |
| S16_PAIRS          | 0x01          |
| S16_INTERLEAVED    | 0x02          |
| S24_PLANES         | 0x04          |
| S24_PAIRS          | 0x05          |
| S24_INTERLEAVED    | 0x06          |
| S32_PLANES         | 0x08          |
| S32_PAIRS          | 0x09          |
| S32_INTERLEAVED    | 0x0a          |
| S64_INVALID        | 0x0c          |
| FLOAT_PLANES       | 0x18          |
| FLOAT_PAIRS        | 0x19          |
| FLOAT_INTERLEAVED  | 0x1a          |
| DOUBLE_PLANES      | 0x2c          |
| DOUBLE_PAIRS       | 0x2d          |
| DOUBLE_INTERLEAVED | 0x2e          |
| INVALID            | 0xffffffff    |

The *channels* is the number of audio channels, *samples* is the number of (multi-channel) audio samples and *sample_rate* is the audio sample rate.

## "cahd" Block

Each [cahd](#cahd-block) block contains the header data for a coded audio grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "cahd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the grain data:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| format        |            | Unsigned | 4 octets  |
| channels      |            | Unsigned | 2 octets  |
| samples       |            | Unsigned | 4 octets  |
| priming       |            | Unsigned | 4 octets  |
| remainder     |            | Unsigned | 4 octets  |
| sample_rate   |            | Unsigned | 4 octets  |

The *format* parameter enumerated values are defined in [cogenums.py](../mediagrains/cogenums.py). The values originated from the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* (from the `CogAudioFormat` enum class) are:

| Name    | Enumeration   |
|---------|---------------|
| MP1     | 0x200         |
| AAC     | 0x201         |
| OPUS    | 0x202         |
| INVALID | 0xffffffff    |

The *channels* is the number of audio channels, *samples* is the number of (multi-channel) audio samples, *priming* is the number of samples at the start of the grain that were used for encoder priming, *remainder* is the number of samples at the end of the grain that were required to complete the encoding frame and *sample_rate* is the audio sample rate. The *priming* and *remainder* are additional audio samples used in the encoding and may be discarded after decoding to allow seamless stitching of contiguous audio fragments for example.

## "eghd" Block

Each [eghd](#eghd-block) block contains the header data for an event grain. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "eghd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by an empty octet:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| type          |            | Unsigned | 1 octet   |

The event payload *type* identifies the encoding and/or content for the event data. The *type* 0x00 is currently recognised and defines a JSON encoding following the schema defined in the [Content Container library](https://github.com/bbc/rd-ips-core-lib-contentcontainer).

## "grdt" Block

Each [grdt](#grdt-block) block contains the raw data of a grain of any type. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "grdt"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the data components of the grain, copied byte-for-byte from the grain, in order. An empty grain type has *size* set to 8, ie. there is no data.
