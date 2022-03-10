from typing import TypeAlias
from .AudioGrain import AudioGrain, size_for_audio_format
from .VideoGrain import VideoGrain
from .CodedAudioGrain import CodedAudioGrain
from .CodedVideoGrain import CodedVideoGrain
from .EventGrain import EventGrain
from .Grain import Grain
from .BaseGrain import BaseGrain, attributes_for_grain_type, new_attributes_for_grain_type

# Provide aliases for backwards compatibility with older versions that used separate grain constructors

AUDIOGRAIN: TypeAlias = AudioGrain
VIDEOGRAIN: TypeAlias = VideoGrain
CODEDAUDIOGRAIN: TypeAlias = CodedAudioGrain
CODEDVIDEOGRAIN: TypeAlias = CodedVideoGrain
EVENTGRAIN: TypeAlias = EventGrain
GRAIN: TypeAlias = Grain
BASEGRAIN: TypeAlias = BaseGrain


__all__ = ["Grain", "VideoGrain", "CodedVideoGrain", "AudioGrain", "CodedAudioGrain", "EventGrain", "BaseGrain",
           "GRAIN", "VIDEOGRAIN", "CODEDVIDEOGRAIN", "AUDIOGRAIN", "CODEDAUDIOGRAIN", "EVENTGRAIN", "BASEGRAIN",
           "attributes_for_grain_type", "new_attributes_for_grain_type", "size_for_audio_format"]
