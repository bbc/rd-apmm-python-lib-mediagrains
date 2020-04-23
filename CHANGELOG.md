# Mediagrains Library Changelog

## 2.9.3
- Handle EOFError in `wrap_in_gsf` command line tools.

## 2.9.2
- Allow stdin as a valid input file for the tools

## 2.9.1
- Fix a bug where the `--samples_per_grain` option in `wrap_audio_in_gsf` wasn't honoured.

## 2.9.0
- Added CogAudioFormat.UNKNOWN which was erroneously missing from enum
- Add a flag for compairing grain iterators without retaining all grains in memory.

## 2.8.5
- Unpin mediatimestamp and mediajson

## 2.8.4
- Pin back versions of mediatimestamp and mediajson

## 2.8.3
- Bugfix: Numpy VideoGrain length should be the bytes length, not the array length.

## 2.8.2
- Removed code that used asyncio in synchronous calls to decode gsf and replaced it with a purely synchronous version.
  It turned out that since asyncio is fundementally incompatible with some third party libraries (eg. gevent) we need
  a code path that doesn't make any use of it.

## 2.8.1
- Added a bypass so that when wrapping a BytesIO in an Async wrapper unnecessary and potentially costly threads aren't spawned

## 2.8.0
- Switched to using asynctest for testing asynchronous code
- Made asynchronous IO wrappers that wrap synchronous IO do so using an executor thread pool
- Added support for automatically wrapping synchronous files in asynchronous wrappers to use them in gsf encoder
- Added bypass to wrap BytesIO in a lighter weight wrapper to prevent timing irregularities

## 2.7.2
- Bugfix: Restore behaviour whereby grains can be added to a segment object during an active progressive encode

## 2.7.1
- Bugfix: Restore behaviour whereby `gsf.GSFEncoder.dump` calls `gsf.GSFEncoder.start_dump` and `gsf.GSFEncoder.end_dump`
  (this matters if subclasses have overridden these methods)

## 2.7.0
- Dropped all support for Python2.7
- Moved python3.6 specific submodules in tree
- Added `GrainWrapper` class to wrap raw essence in Grains.
- Added `wrap_video_in_gsf` and `wrap_audio_in_gsf` tools to generate GSF files from raw essence.
- Added `extract_from_gsf` and `gsf_probe` tools to extract essence and metadata from GSF files.
- Added MyPy as a dependency
- Deprecated old asyncio code from v2.6
- Added Asynchronous GSFEncoding using the standard Encoder in a context-manager type workflow.
- Added Asynchronous GSFDecoding using the standard Decoder in a context-manager type workflow.

## 2.6.0
- Added support for async methods to gsf decoder in python 3.6+
- Added `Grain.origin_timerange` method.
- Added `Grain.normalise_time` method.
- Added `Colourbars` test signal generator
- Added `MovingBarOverlay` for test signal generators
- Added `mediagrains.numpy` sublibrary for handling video grains as numpy arrays, in python 3.6+
- Added `PSNR` option to grain compare.
- Support for converting between all uncompressed video grain formats added to `mediagrains.numpy`
- This is the last release that will support python 2.7 (apart from bugfixes)

## 2.5.3
- BUGFIX: IOBytes doesn't quite fulfil bytes-like contracts, but can be converted to something that does

## 2.5.2
- Remove dependency on enum34 for versions of python >= 3.4

## 2.5.1
- Fix restoring bytestream position when lazy loading bytes.

## 2.5.0
- Added ability to filter GSFDecoder output based on local ids

## 2.4.0
- Added ability for GSFDecoder to return grains with lazy loading
  bytes data

## 2.3.4
- Switch to using immutable timestamps throughout

## 2.3.3
- Allow build to run on a wider selection of agents.

## 2.3.2
- Added Jenkins trigger to rebuild master every day.

## 2.3.1
- Added upload of pydoc docs to Jenkinsfile

## 2.3.0
- Added Silence to test signal generation
- Added sample_rate option for audio test signal generators
- Added Tone test signal generator which can generate a vaiety of frequencies

## 2.2.0
- Added 1K Tone to test signal generation

## 2.1.0
- Added support for comparison of grains against other grains with a
  variety of options and detailed output when there are differences.

## 2.0.1
- Accept TimeOffsets as grain timestamps, to work around oddities in JSON
  parsing behaviour.

## 2.0.0
- GSFEncoder does not buffer grains once they have been written
- GSFEncoderSegment does not provide access to buffered grains

## 1.1.1
- Updated README.md

## 1.1.0
- GSFDecoder.grains() with skip_data=True positions stream pointer after data before yielding

## 1.0.0
- Initial Release version

## 0.4.0
- Add new `final_origin_timestamp` method to grains to make some logic
   simpler.
- Changed dependencies for timestamps to `mediatimestamp`.

## 0.3.1
- Fix GSFDecoder.decode() to not require a parameter when used with `file_data`
  in constructor.

## 0.3.0
- Rewrote GSFDecoder to use a BytesIO (or similar) to read the GSF data from,
  be more object-oriented and make heavy use of grain context managers (while
  preserving original behaviour)
- Added `grains()` generator to GSFDecoder, with an option to skip grain data.

## 0.2.2
- Added Jenkinsfile for CI
- Changed Makefile to use library template example, add more Debian build options

## 0.2.1
- Added step option to testsignalgenerator

## 0.2.0
- Added first test signal generator: LumaSteps
- Added copy and deepcopy implementations to grain classes

## 0.1.1
- Bugfix: fixed bug that caused offset not to be set in video grains extracted from gsf.
- Bugfix: fixed behaviour when gsf deserialising video grains without values set for pixel and source aspect ratios.

## 0.1.0
- initial commit. Library for mediagrains and gsf serialisation/deserialisation.
