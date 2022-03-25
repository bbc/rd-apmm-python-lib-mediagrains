# Grain Sequence Format

A Grain Sequence Format (GSF) file contains a sequence of grains from one or more flows. It has the mimetype application/x-ips-gsf and a filename typically uses the suffix `.gsf`.

The GSF file uses the [SSB format](ssb.md) that defines the base file structure and data types.


## General File Structure

Each file begins with a 12 octet [SSB header](ssb.md#SSBHeader):

| Name          | Data       | Type     | Size     |
|---------------|------------|----------|----------|
| signature     | "SSBB"     | Tag      | 4 octets |
| file_type     | "grsg"     | Tag      | 4 octets |
| major_version | 0x0007     | Unsigned | 2 octets |
| minor_version | 0x0000     | Unsigned | 2 octets |

The current GSF version is 7.0.

Every GSF file contains a single "head" block, which itself contains other types of block, followed by a (possibly empty) sequence of "grai" blocks and finally a "grai" terminator block.

The "grai" terminator block has the block *size* set to 0 (and no content) which signals to readers that the GSF stream has ended. It is typically used by readers when receiving a GSF stream where the sender does not know the duration beforehand and has set *count* in "segm" to -1.

As such the overall structure of the file is:

* File header (12 octets)
* "head" block
    * block header
    * head header (id, and timestamp)
    * "segm" blocks (optional, repeatable)
        * block header
        * segm header (local_id, id, count)
        * "tag " blocks (optional, repeatable)
    * "tag " blocks (optional, repeatable)
* "grai" blocks (optional, repeatable)
    * block header
    * grai header (local_id)
    * "gbhd" block
        * block header
        * gbhd header (src_id, flow_id, origin_ts, sync_ts, rate, duration)
        * "tils" block (optional)
            * block header
            * timelabel count
            * timelabel (repeatable)
        * "vghd" block (if video grain)
            * block header
            * vghd header (format, layout, etc ...)
            * "comp" block (optional)
                * block header
                * comp count
                * comp (repeatable)
        * "cghd" block (if coded video grain)
            * block header
            * cghd header (format, layout, etc ...)
            * "unof" block (optional)
                * block header
                * unof count
                * unof (repeatable)
        * "aghd" block (if audio grain)
            * block header
            * aghd header (format, rate, etc ...)
        * "cahd" block (if coded audio grain)
            * block header
            * cahd header (format, rate, etc ...)
        * "eghd" block (if data grain)
            * block header
            * eghd header (type)
    * "grdt" block
        * block header
        * raw data
* "grai" terminator block
    * block header with size 0


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
| created       |            | Timestamp| 7 octets  |

Where *id* is a UUID identifying the file itself, and *created* is a timestamp identifying when the file was laid down.

After this the "head" block contains a sequence of "segm", which is followed by "tag " blocks.

## "segm" Block

Each "segm" block describes a segment within the file. Each segment contains a number of grains, but the actual grain data is not included in this block, which is more of an *index* of segments.

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

Each "tag " block contains a 'tag' used to provide user extensible metadata for the immediate parent block. Each such tag is a pair of strings, referred to as the *key* and *val*.

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

A "tag " block will not have any child blocks.

## "grai" Block

Each "grai" block contains the actual data for a grain. Every grain in every segment in the file is represented by such a block.

It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "grai"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by a single field containing the *local_id* of the segment to which the grain belongs:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| local_id      |            | Unsigned | 2 octets  |

and then followed by a "gbhd" block and then a "grdt" block. Note that an empty grain type still requires a (empty) "grdt" block.

## "gbhd" Block

Each "gbhd" block contains the metadata for a grain header. It begins with a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "gbhd"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the fields of the common grain header:

| Name          | Data       | Type         | Size      |
|---------------|------------|--------------|-----------|
| src_id        |            | UUID         | 16 octets |
| flow_id       |            | UUID         | 16 octets |
| (deprecated)  | 0x00 * 16  | FixByteArray | 16 octets |
| origin_ts     |            | IPPTimestamp | 10 octets |
| sync_ts       |            | IPPTimestamp | 10 octets |
| rate          |            | Rational     | 8 octets  |
| duration      |            | Rational     | 8 octets  |

The *src_id* is the source identifier for the grains, *flow_id* is the flow identifier, *origin_ts* is the origin timestamp, *sync_ts* is the synchronisation timestamp, *rate* is the grain rate and *duration* is the grain duration. A deprecated property is currently present in the data and should be set to all zeros. The deprecated property is likely to be removed when moving to the next *major_version*.

The "gbhd" block is followed by an optional "tils" block, and then an additional mandatory block for the non-empty grain types:

* Video Grain: a "vghd" block.
* Coded Video Grain: a "cghd" block.
* Audio Grain: an "aghd" block.
* Coded Audio Grain: a "cahd" block.
* Event Grain: an "eghd" block.
* Empty Grain: no block.

## "tils" Block

Each "tils" block contains tagged time labels for the grain it exists in. If the grain has none then this block should be ommitted. It consists of a standard block header:

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

Each "vghd" block contains the header data for a video grain. It consists of a standard block header:

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

followed by an optional "comp" block.

The *format* and *layout* parameters are enumerated values as used in the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* taken from [CogFrameLayout](https://github.com/bbc/rd-ips-core-lib-cog2/blob/master/cog/cogframe.h#L41) are:

| Name          | Enumeration   |
|---------------|---------------|
| U8_444        | 0x2000        |
| U8_422        | 0x2001        |
| U8_420        | 0x2003        |
| S16_444       | 0x4004        |
| S16_422       | 0x4005        |
| S16_420       | 0x4007        |
| S16_444_10BIT | 0x2804        |
| S16_422_10BIT | 0x2805        |
| S16_420_10BIT | 0x2807        |
| S16_444_12BIT | 0x3004        |
| S16_422_12BIT | 0x3005        |
| S16_420_12BIT | 0x3007        |
| S32_444       | 0x8008        |
| S32_422       | 0x8009        |
| S32_420       | 0x800b        |
| YUYV          | 0x2100        |
| UYVY          | 0x2101        |
| AYUV          | 0x2102        |
| RGB           | 0x2104        |
| v216          | 0x4105        |
| v210          | 0x2906        |
| RGBx          | 0x2110        |
| xRGB          | 0x2111        |
| BGRx          | 0x2112        |
| xBGR          | 0x2113        |
| RGBA          | 0x2114        |
| ARGB          | 0x2115        |
| BGRA          | 0x2116        |
| ABGR          | 0x2117        |
| UNKNOWN       | 0xfffffffe    |
| INVALID       | 0xffffffff    |

The current set of known *layouts* taken from the [CogFrameLayout enum](https://github.com/bbc/rd-ips-core-lib-cog2/blob/master/cog/cogframe.h#L107) are:

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

Each "comp" block contains the component sizes for a video grain. It consists of a standard block header:

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

Each "cghd" block contains the header data for a coded video grain. It consists of a standard block header:

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

The *format* and *layout* parameters are enumerated values as used in the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known (compressed) *formats* taken from the [CogFrameLayout enum](https://github.com/bbc/rd-ips-core-lib-cog2/blob/master/cog/cogframe.h#L41) are:

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
| UNKNOWN       | 0xfffffffe    |
| INVALID       | 0xffffffff    |

The *layouts* is the same as that described in the "vghd" block. The *origin_width* and *origin_height* are the original frame dimensions that were input to the encoder and is the output of the decoder after applying any clipping. The *coded_width* and *coded_height* are the frame dimensions used to encode from, eg. including padding to meet the fixed macroblock size requirement. The *key_frame* is set to true if the video frame is a key frame, eg. an I-frame. The *temporal_offset* is the offset between display and stored order for inter-frame coding schemes (offset = display - stored).

The "cghd" block is followed by an optional "unof" block.

## "unof" Block

Each "unof" block contains the offsets from the start of the data section for coded units within a coded grain. It consists of a standard block header:

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

Each "aghd" block contains the header data for an audio grain. It consists of a standard block header:

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

The *format* parameter are enumerated values as used in the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known *formats* taken from the [CogAudioFormat enum](https://github.com/bbc/rd-ips-core-lib-cog2/blob/master/cog/cogaudio.h#L23) are:

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

Each "cahd" block contains the header data for a coded audio grain. It consists of a standard block header:

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

The *format* parameter are enumerated values as used in the [COG library](https://github.com/bbc/rd-ips-core-lib-cog2). The current set of known (compressed) *formats* taken from the [CogAudioFormat enum](https://github.com/bbc/rd-ips-core-lib-cog2/blob/master/cog/cogaudio.h#L23) are:

| Name    | Enumeration   |
|---------|---------------|
| MP1     | 0x200         |
| AAC     | 0x201         |
| OPUS    | 0x202         |
| INVALID | 0xffffffff    |

The *channels* is the number of audio channels, *samples* is the number of (multi-channel) audio samples, *priming* is the number of samples at the start of the grain that were used for encoder priming, *remainder* is the number of samples at the end of the grain that were required to complete the encoding frame and *sample_rate* is the audio sample rate. The *priming* and *remainder* are additional audio samples used in the encoding and may be discarded after decoding to allow seamless stitching of contiguous audio fragments for example.

## "eghd" Block

Each "eghd" block contains the header data for an event grain. It consists of a standard block header:

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

Each "grdt" block contains the raw data of a grain of any type. It consists of a standard block header:

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "grdt"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

followed by the data components of the grain, copied byte-for-byte from the grain, in order. An empty grain type has *size* set to 8, ie. there is no data.
