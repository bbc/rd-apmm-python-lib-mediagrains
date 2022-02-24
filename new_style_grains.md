# New Style Grains
As of version x.y, there is a new, more Pythonic grains interface available. The 'old way' (by importing `grain_constructors`) is still supported, but is marked deprecated; they now only serve as 'adapters' to the 'new style' classes.

The new interface can be accessed by importing `mediagrains.grains` or `mediagrains.numpy.numpy_grains`, but once the 'old way' is fully deprecated it should be possible to directly import. Type aliases (e.g. `VIDEOGRAIN`) are also still present for compatibility.

## Differences
Once the new `mediagrains.grains` has been imported, the constructors are broadly the same. The primary difference is that the `src_id_or_meta` and `flow_id_or_data` arguments have been removed from the new style as that is not pythonic.
Instead, it is preferred that all arguments be given by keywords, however for some compatibility's sake, it is possible to call a grain constructor in the form:
```py
VideoGrain(meta, data)
```
However, `VideoGrain(src_id, flow_id)` will not work, and must be called with named parameters.

The `format` and `layout` parameters have been removed due to their ammbiguity, and have been replaced with `cog_frame_format`, `cog_audio_format`, and `cog_frame_layout` parameters.
The constructors also no longer accept `source_id` as a parameter, preferring to use `src_id`. However, it is possible to access or set `source_id` as getters and setters are provided.

## Tests
Currently, most tests are doubled up -- using the 'old' methods of instantiation, and the 'new'. This is to ensure any changes will work in both ways. All the 'new' style tests feature `_newcode` in the test file name.