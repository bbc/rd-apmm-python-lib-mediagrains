# Mediagrains Library Changelog

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
