# Sequence Store Binary Format

**Version 2.0**

The Sequence Store Binary (SSB) format is a basic format for binary encoding data for storage or transfer. It is the basis for the storage segment data files as well as the [Grain Sequence Format (GSF)](gsf.md) used for external storage and transfer. A SSB file would typically use the filename suffix `.ssb`, but some file types would have their own preferred suffix, eg. `.gsf` for GSF.

The format uses Little Endian (low order byte first) encoding.

In the following code a value surrounded by double quotes indicates a literal string (ie. a sequence of bytes in order) which must be written, whilst a string not surrounded by quotes indicates the name of a variable which will be described elsewhere. A literal integer can be shown in Hex format if preceded with 0x.


## Data Types

A number of data types are defined for the SSB format structures and the data it contains. The table below defines the data types in terms of a *Name*, set of *Members* for structured types, *Size* in octets for the type and individual members and a *Description*. The *Description* for the *Members* will define the type used for the *Member*.

| Name          | Member      | Size (octets)  | Description                                                    |
|---------------|-------------|----------------|----------------------------------------------------------------|
| Tag           |             | 4              | An identifier consisting of 4 ASCII characters. The identifier |
|               |             |                | might be unique globally (e.g. *file_type*) or locally         |
| Unsigned      |             | 1 to 8         | An unsigned integer                                            |
| Signed        |             | 1 to 8         | A two's-complement signed integer                              |
| Boolean       |             | 1              | 0 is false and 1 is true. Readers must treat a non-0 as true   |
| Rational      |             | 8              | An unsigned rational number. A null value is where the         |
|               |             |                | Numerator equals 0. Readers need to be aware that the          |
|               |             |                | Denominator can also be 0 and treat it as null or invalid.     |
|               | Numerator   | 4              | *Unsigned* numerator                                           |
|               | Denominator | 4              | *Unsigned* denominator                                         |
| UUID          |             | 16             | 16 octets of a Universal Unique Identifier                     |
| Timestamp     |             | 11             | Timestamp with nanosecond resolution                           |
|               | Sign        | 1              | A *Boolean* indicating whether the timestamp is                |
|               |             |                | positive (true) or negative (false) signed.                    |
|               | Seconds     | 6              | *Unsigned* seconds                                             |
|               | Nanoseconds | 4              | *Unsigned* nanoseconds                                         |
| FixString     |             | Fixed size     | UTF-8 encoded string with a fixed size specified by the        |
|               |             |                | property definition. The String is terminated by a null (0)    |
|               |             |                | character or by the end of the fixed size value                |
| VarString     |             | 2 + Length     | UTF-8 encoded string with size equal to the Length value       |
|               | Length      | 2              | *Unsigned* string length                                       |
|               | Value       | Length         | A *FixString* with fixed size equal to Length                  |
| Timecode      |             | 13             | A media timecode                                               |
|               | Count       | 4              | *Unsigned* count of frames since midnight                      |
|               | Rate        | 8              | *Rational* timecode rate                                       |
|               | Drop        | 1              | *Boolean* drop frame timecode flag                             |
| Timelabel     |             | 29             | Timelabel containing a tag and a timecode                      |
|               | Tag         | 16             | A *FixString* with fixed size equal to 16. The tag used to     |
|               |             |                | identify the origination of the timecode for example           |
|               | Timecode    | 13             | A Timecode                                                     |
| DateTime      |             | 7              | A date-time structure with seconds resolution and timezone set |
|               |             |                | to UTC. A null date-time can be indicated by using a 0 value   |
|               |             |                | for all members.                                               |
|               | Year        | 2              | *Signed* year                                                  |
|               | Month       | 1              | *Unsigned* month, 1 - 12                                       |
|               | Day         | 1              | *Unsigned* day of month, 1 - 31                                |
|               | Hour        | 1              | *Unsigned* hour of day, 0 - 23                                 |
|               | Minute      | 1              | *Unsigned* minute, 0 - 59                                      |
|               | Second      | 1              | *Unsigned* second, 0 - 59                                      |
| VarByteArray  |             | 4 + Length     | A variable size array of *Unsigned* with size 1.               |
|               | Length      | 4              | *Unsigned* data length                                         |
|               | Value       | Length         | Array of bytes with size equal to Length                       |
| FixByteArray  |             | Fixed size     | A fixed size array of *Unsigned* with size 1. The fixed size   |
|               |             |                | is provided by the property definition                         |


## General File Structure

A SSB file starts with a 12 octet file header of the form:

| Name          | Data       | Type     | Size     |
|---------------|------------|----------|----------|
| signature     | "SSBB"     | Tag      | 4 octets |
| file_type     |            | Tag      | 4 octets |
| major_version |            | Unsigned | 2 octets |
| minor_version |            | Unsigned | 2 octets |

The *signature* "SSBB" identifies the file to be a SSB file.

The *file_type* identifies the type of content in the file. For example, the GSF file uses the type "grsg" and the essence file in a storage segment uses the type "esse". The *file_type* provides an indication to a reader of what it can expect to find in the file.

The rest of the file consists of a number of sequential "blocks". Each block begins with an 8-octet block header of the form:

| Name          | Data       | Type     | Size     |
|---------------|------------|----------|----------|
| tag           |            | Tag      | 4 octets |
| size          |            | Unsigned | 4 octets |

Where *tag* is a four-character string identifying the type of block, and *size* is a 32-bit unsigned integer containing the size of the data in the block *including the 8-octet block header*.

The block header is immediately followed by the block payload, the format of which is defined for the individual types of block. Some blocks are structured to consist of an initial header followed by a list of sequential subblocks, identified in the same way.

SSB file type specifications may define specific ordering of blocks, but by default blocks can appear in any order. SSB file type specifications may define whether a block must directly follow another block, but by default any number of other blocks can be placed in-between.


## Versioning

The format version is split into a *major_version* and *minor_version*. This information is used by a reader to determine whether it supports the file or not. The *major_version* changes when a change is made to the format that would break readers, i.e. a reader would fail to parse the file or fail to interpret the data correctly. The *minor_version* changes when a change is made to the format that does not break readers. It indicates that there is potentially additional information in the file that is not essential to understanding and using the contents of the file.

Block could contain more properties than a reader expects. Blocks could contain sub-blocks that a reader does not recognise. The reader must ignore the additional properties and blocks, e.g. by skipping over them using the parent block's size information. The presence of additional data can be signalled by the *minor_version* in the file header or by a parent block including some indication of a local extension. A file type can therefore be extended without breaking existing reader implementations.


## "fill" Block

The [fill](#fill-block) block is used to reserve space for overwriting later or to position blocks at certain offsets in the file. It consists of a standard block header

| Name          | Data       | Type     | Size      |
|---------------|------------|----------|-----------|
| tag           | "fill"     | Tag      | 4 octets  |
| size          |            | Unsigned | 4 octets  |

The data can be anything but is typically set to all zeros. A reader must ignore a [fill](#fill-block) block.
