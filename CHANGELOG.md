# Mediagrains Library Changelog

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
