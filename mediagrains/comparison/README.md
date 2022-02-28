# Grain Comparison Submodule
The Grain comparison submodule adds comparison capabiltiies that are more
nuanced than the simple equality comparison provided by the grain class
itself.
We can compare two grains or compare the outputs of two grain iterators.
The submodule also allows for refinement of comparisons.
Refinements include:
* Excluding some attributes from affecting the comparison result
* Expressing expected differences between attributes values
* Checking that PSNR comparisons meet a threshold

Please see the options section for more information on refinements.

## Basic Usage Examples

### Comparing two grains with compare_grain

The function compare_grain is the main interface for comparing two grains.

An example to create and compare two grains that do not match:

```python
>>> from fractions import Fraction
>>> from uuid import uuid1
>>> from mediagrains.comparison import compare_grain
>>> from mediatimestamp import TimeValue
>>> from mediagrains.patterngenerators.video import LumaSteps
>>> src_id = uuid1()
>>> flow_id = uuid1()
>>> ls = LumaSteps(src_id, flow_id, 1920, 1080)
>>> tv_a = TimeValue(1, rate=Fraction(25))
>>> a = ls.get(tv_a)
>>> tv_b = TimeValue(5, rate=Fraction(25))
>>> b = ls.get(tv_b)
>>> cp_res = compare_grain(a, b)
>>> print(cp_res)
❌   Grains do not match
  ✅   <a/b>.grain_type == 'video'
  ✅   <a/b>.source_id == UUID('9d0a2518-8f39-11ec-bcdd-737806a40a30')
  ✅   <a/b>.flow_id == UUID('a1269208-8f39-11ec-bcdd-737806a40a30')
  ✅   <a/b>.rate == Fraction(25, 1)
  ✅   <a/b>.duration == Fraction(1, 25)
  ✅   <a/b>.length == 6220800
  ❌   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('-0:160000000'), not the expected mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0')
  ❌   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('-0:160000000'), not the expected mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0')
  ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ✅   Lists match
    ✅   len(<a/b>.timelabels) == 0
  ✅   <a/b>.format == CogFrameFormat.U8_444
  ✅   <a/b>.width == 1920
  ✅   <a/b>.height == 1080
  ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
  ✅   Binary data <a/b>.data are equal
```

The object returned by compare_grain is truthy if the comparison matched and
falsy if it didn't, in addition the object has a detailed human readable
summary of the differences between the grains obtainable by calling str on it.
In addition any access to an attribute of this object that is possessed by
grains (e.g. .creation_timestamp, .data, .length) will provide another object
that behaves similarly but represents only that attribute and any
attributes/entries it contains. Each such object at any level in the tree can
be tested as a boolean and can also have .excluded() called on it, which will
return True if the original comparison excluded that attribute.

By default creation_timestamp is excluded from altering the result of the
comparison.

Note that if you are comparing grains where the binary data does not
match the binary data of the grains may be printed to the output.

### Comparing two grain iterators with compare_grains_pairwise

Using the compare_grains_pairwise function we can compare two iterators which
produce grains pairwise. Each grain from iterator `a` will be compared against
the corresponding grain in iterator `b`. The comparison will end when any grain
fails to match. If one iterator runs out of grains the comparison will end.
If both run out at the same time and all grains matches then this is
considered a succesful match, any other situation is an unsuccessful match.
The parameter `return_last_only` can be set to True to return only the
description of the last comparison, instead of all comparisons performed.
If False, all compared Grains will be retained, which may require significant
memory if the Grain iterators are long.

An example to create and compare two grain iterators with a differing length
of grains:

```python
>>> from fractions import Fraction
>>> from uuid import uuid1
>>> from mediagrains.comparison import compare_grains_pairwise
>>> from mediatimestamp import CountRange
>>> from mediagrains.patterngenerators.video import LumaSteps
>>> src_id = uuid1()
>>> flow_id = uuid1()
>>> ls = LumaSteps(src_id, flow_id, 1920, 1080)
>>> cr_a = CountRange(0,2)
>>> itr_a = ls.__getitem__(cr_a)
>>> cr_b = CountRange(0,4)
>>> itr_b = ls.__getitem__(cr_b)
>>> cp_res = compare_grains_pairwise(itr_a, itr_b)
>>> print(cp_res)
❌   Iterators differ first at entry 3
  ✅   Grains match
    ✅   <a/b>.grain_type == 'video'
    ✅   <a/b>.source_id == UUID('956bb418-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.flow_id == UUID('98dfa85c-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.rate == Fraction(25, 1)
    ✅   <a/b>.duration == Fraction(1, 25)
    ✅   <a/b>.length == 6220800
    ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   Lists match
      ✅   len(<a/b>.timelabels) == 0
    ✅   <a/b>.format == CogFrameFormat.U8_444
    ✅   <a/b>.width == 1920
    ✅   <a/b>.height == 1080
    ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
    ✅   Binary data <a/b>.data are equal
  ✅   Grains match
    ✅   <a/b>.grain_type == 'video'
    ✅   <a/b>.source_id == UUID('956bb418-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.flow_id == UUID('98dfa85c-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.rate == Fraction(25, 1)
    ✅   <a/b>.duration == Fraction(1, 25)
    ✅   <a/b>.length == 6220800
    ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   Lists match
      ✅   len(<a/b>.timelabels) == 0
    ✅   <a/b>.format == CogFrameFormat.U8_444
    ✅   <a/b>.width == 1920
    ✅   <a/b>.height == 1080
    ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
    ✅   Binary data <a/b>.data are equal
  ✅   Grains match
    ✅   <a/b>.grain_type == 'video'
    ✅   <a/b>.source_id == UUID('956bb418-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.flow_id == UUID('98dfa85c-8f41-11ec-bcdd-737806a40a30')
    ✅   <a/b>.rate == Fraction(25, 1)
    ✅   <a/b>.duration == Fraction(1, 25)
    ✅   <a/b>.length == 6220800
    ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
    ✅   Lists match
      ✅   len(<a/b>.timelabels) == 0
    ✅   <a/b>.format == CogFrameFormat.U8_444
    ✅   <a/b>.width == 1920
    ✅   <a/b>.height == 1080
    ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
    ✅   Binary data <a/b>.data are equal
  ❌   a does not exist, but b == VideoGrain({'@_ns': 'urn:x-ipstudio:ns:0.1', 'grain': {'grain_type': 'video', 'source_id': '956bb418-8f41-11ec-bcdd-737806a40a30', 'flow_id': '98dfa85c-8f41-11ec-bcdd-737806a40a30', 'origin_timestamp': '0:120000000', 'sync_timestamp': '0:120000000', 'creation_timestamp': '1645027286:373768448', 'rate': {'numerator': 25, 'denominator': 1}, 'duration': {'numerator': 1, 'denominator': 25}, 'cog_frame': {'format': 8192, 'width': 1920, 'height': 1080, 'layout': 0, 'extension': 0, 'components': [{'stride': 1920, 'offset': 0, 'width': 1920, 'height': 1080, 'length': 2073600}, {'stride': 1920, 'offset': 2073600, 'width': 1920, 'height': 1080, 'length': 2073600}, {'stride': 1920, 'offset': 4147200, 'width': 1920, 'height': 1080, 'length': 2073600}]}}},< binary data of length 6220800 >)
  ...
  >>> cp_res = compare_grains_pairwise(itr_a, itr_b, return_last_only=True)
  ...
```

The object returned by compare_grains_pairwise will evaluate as True if the
iterators matched, and False if they did not. In addition it has a rich
description of the comparisons performed which is accessible by calling str
on it. The object itself is an ordered container containing matcher objects
representing the differences between the grains, and these can be accessed
via the standard [n] index notation, and len() will return the number of
such result objects are present.

Note that if you are comparing grains where the binary data does not
match the binary data of the grains may be printed to the output, but
in this case the mismatch is because for one iterator there is no data,
and such the mismatch is reported, but the binary data is not output.

## Options
The attributes that are needed to be compared to achieve a result
can be modified by making use of the mediagrains.comparison.options.

Options can be passed to comparisons which are constructed using the objects
Exclude, Include, and ExpectedDifference. These three objects provide a
convenient (and similar) interface. By accessing attributes of these objects
that have the same names as attributes of the objects to be compared you can
identify which attributes to refer to.
For a VIDEOGRAIN these attributes will be along the lines of grain_type,
source_id, flow_id, rate, duration, length and so on, as you can see in the
print statements of comparisons above. These attributes will differ for
other grains such as EVENTGRAIN and CODED_AUDIOGRAIN.

If an Include and an Exclude are used for the same attribute then the Exclude
takes precedence. 

### Inclusion
For example the option `options.Include.creation_timestamp` is an option that
causes the comparison operation to not ignore any differences in the
creation_timestamp member of the compared objects.

At present the only real use for Include is to override the default behaviour
that ignores creation_timestamp differences.

```python
>>> from mediagrains.comparison import options
>>> print(compare_grain(a, b, options.Include.creation_timestamp))
...
```

### Exclusion
To exclude an attribute from affecting the comparison result, use
`options.Include.attr` to mark an attribute as not important.

For example if we are not interested in comparing the grains data:

```python
>>> from mediagrains.comparison import options
>>> print(compare_grain(a, b, options.Exclude.data))
✅   Grains match
  ✅   <a/b>.grain_type == 'video'
  ✅   <a/b>.source_id == UUID('c7603068-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.flow_id == UUID('ca95245a-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.rate == Fraction(25, 1)
  ✅   <a/b>.duration == Fraction(1, 25)
  ✅   <a/b>.length == 6220800
  ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ✅   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('-170:640600064'), not the expected mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0')
  ✅   Lists match
    ✅   len(<a/b>.timelabels) == 0
  ✅   <a/b>.format == CogFrameFormat.U8_444
  ✅   <a/b>.width == 1920
  ✅   <a/b>.height == 1080
  ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
  ◯   For speed reasons not comparing a.data and b.data when this would be excluded
```

Excluding grain data is common enough that there is a shortcut called
`CompareOnlyMetadata` to achieve the same result:

```python
>>> from mediagrains.comparison import options
>>> print(compare_grain(a, b, options.CompareOnlyMetadata))
...
```

### Expecting a difference between two values of an attribute
For integer and timestamp attributes it is also possible to use a second
type of option:
`options.ExpectedDifference.<attribute_name> == <value> (or >=, <, <=, >, !=)`
will set a criteria for succesful comparison on that attribute that is less
strict than the standard requirement that the values be equal to each other.

For example:

```python
>>> from mediagrains.comparison import options
>>> from mediatimestamp import TimeOffset
>>> print(compare_grain(a, b, options.Exclude.data, options.ExpectedDifference.sync_timestamp >= TimeOffset(64, 0)))
❌   Grains do not match
  ✅   <a/b>.grain_type == 'video'
  ✅   <a/b>.source_id == UUID('c7603068-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.flow_id == UUID('ca95245a-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.rate == Fraction(25, 1)
  ✅   <a/b>.duration == Fraction(1, 25)
  ✅   <a/b>.length == 6220800
  ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ❌   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0'), does not meet requirements set in options
  ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('-170:640600064'), not the expected mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0')
  ✅   Lists match
    ✅   len(<a/b>.timelabels) == 0
  ✅   <a/b>.format == CogFrameFormat.U8_444
  ✅   <a/b>.width == 1920
  ✅   <a/b>.height == 1080
  ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
  ◯   For speed reasons not comparing a.data and b.data when this would be excluded
...
>>> print(compare_grain(a, b, options.ExpectedDifference.creation_timestamp > TimeOffset(0, 64)))
...
```

The first comparison will compare the grains, ignoring differences in their
data payloads, but requires that instead of being equal the difference
between their sync_timestamps must be greater than or equal to 64 seconds. 

The second requires that (a.creation_timestamp - b.creation_timestamp)
to be greater than 64 nanoseconds.

### Comparing Peak signal-to-noise ratio to a threshold
To calculate and compare the PSNR values of audio and video grains to a
threshold we can make use of `options.PSNR.data`.
When the PSNR option is used, it takes the place of comparing the grains
binary data.

For example when calculating the PSNR of two VIDEOGRAINS and comparing:

```python
>>> from mediagrains.comparison import options
>>> print(compare_grain(a, b, options.PSNR.data < [5.0, 5.0, 5.0]))
❌   Grains do not match
  ✅   <a/b>.grain_type == 'video'
  ✅   <a/b>.source_id == UUID('c7603068-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.flow_id == UUID('ca95245a-8fd5-11ec-bcdd-737806a40a30')
  ✅   <a/b>.rate == Fraction(25, 1)
  ✅   <a/b>.duration == Fraction(1, 25)
  ✅   <a/b>.length == 6220800
  ✅   a.origin_timestamp - b.origin_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ✅   a.sync_timestamp - b.sync_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0') as expected
  ◯   a.creation_timestamp - b.creation_timestamp == mediatimestamp.immutable.TimeOffset.from_sec_nsec('-170:640600064'), not the expected mediatimestamp.immutable.TimeOffset.from_sec_nsec('0:0')
  ✅   Lists match
    ✅   len(<a/b>.timelabels) == 0
  ✅   <a/b>.format == CogFrameFormat.U8_444
  ✅   <a/b>.width == 1920
  ✅   <a/b>.height == 1080
  ✅   <a/b>.layout == CogFrameLayout.FULL_FRAME
  ❌   PSNR(a.data, b.data) == [6.03056287063678, 10.122001092250365, 9.676799710383513], does not meet requirements set in options
```

`options.PSNR.data` requires a comparator followed by a list of floats,
that represent the expected PSNR values for each component of the input
(e.g. Y, U, V planes for video or each audio channel).
It is not currently possible just to calculate and store the PSNR values
without setting some kind of comparison.