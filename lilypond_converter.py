from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import tempfile
from typing import Optional
import warnings

import ly.document
import ly.music
from ly.music import event as music_event
from ly.music import items
from ly.pitch import Pitch, rel2abs
import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack


NOTE_OFFSETS = [0, 2, 4, 5, 7, 9, 11]
SEMITONES_PER_OCTAVE = 12
MIDI_C4_OCTAVE_OFFSET = 4  # octave=1 (c') should yield MIDI note 60
QUARTER_STEPS_PER_SEMITONE = 2
OFF_PRIORITY = 0
ON_PRIORITY = 1
EVENT_OFF = "off"
EVENT_ON = "on"
DRUM_CHANNEL = 9  # MIDI channel 10 (0-indexed as 9) for percussion

# General MIDI percussion mapping (drum name → GM note number)
DRUM_NAME_TO_MIDI: dict[str, int] = {
    "bd": 36,    # Acoustic Bass Drum
    "sn": 38,    # Acoustic Snare
    "hh": 42,    # Closed Hi-Hat
    "hhc": 42,   # Closed Hi-Hat
    "hho": 46,   # Open Hi-Hat
    "cymc": 49,  # Crash Cymbal 1
    "toml": 45,  # Low Tom
    "tomm": 48,  # Hi-Mid Tom (mid tom)
    "tomh": 50,  # High Tom
}


def pitch_to_midi(pitch: Pitch) -> int:
    """Convert ly.pitch.Pitch to MIDI note number."""
    # pitch.alter is stored in quarter-step units (e.g., sharp = 0.5 = two quarter steps),
    # so multiply by 2 to convert to semitone offsets and round to the nearest integer.
    semitone_from_alter = int(round(pitch.alter * QUARTER_STEPS_PER_SEMITONE))
    base = SEMITONES_PER_OCTAVE * (pitch.octave + MIDI_C4_OCTAVE_OFFSET)
    note_number = base + NOTE_OFFSETS[pitch.note] + semitone_from_alter
    return max(0, min(127, note_number))


def _tick_scale(ticks_per_beat: int) -> int:
    # Fraction values are expressed in whole-note units; a quarter note is 1/4.
    return ticks_per_beat * 4


@dataclass
class TimedEvent:
    start: int
    duration: int
    note: Optional[int]
    channel: int = 0  # Default channel 0, use DRUM_CHANNEL (9) for drums


def _drum_name_to_midi(drum_name: str) -> Optional[int]:
    """Convert a LilyPond drum name to a GM percussion MIDI note number.
    
    Returns None and emits a warning if the drum name is not mapped.
    """
    midi_note = DRUM_NAME_TO_MIDI.get(drum_name)
    if midi_note is None:
        warnings.warn(
            f"Unmapped drum name '{drum_name}' - skipping this percussion event",
            category=UserWarning,
            stacklevel=2,
        )
    return midi_note


class LilypondEventCollector(music_event.Events):
    def __init__(self, ticks_per_beat: int):
        super().__init__()
        self.ticks_per_beat = ticks_per_beat
        self.events: list[TimedEvent] = []
        self._in_drum_mode = False  # Track if we're inside a DrumMode context

    def traverse(self, node: items.Item, time: Fraction | float, scaling: Fraction | float):
        # Track DrumMode context
        was_in_drum_mode = self._in_drum_mode
        if isinstance(node, items.DrumMode):
            self._in_drum_mode = True

        tick_scale = _tick_scale(self.ticks_per_beat)
        
        # Handle Chord elements containing DrumNotes
        if isinstance(node, items.Chord) and self._in_drum_mode:
            start_ticks = int(round(time * tick_scale))
            duration_fraction = node.duration[0] * node.duration[1] * scaling
            duration_ticks = max(1, int(round(duration_fraction * tick_scale)))
            # Extract all DrumNotes from the chord
            for child in node:
                if isinstance(child, items.DrumNote):
                    drum_name = str(child.token)
                    midi_note = _drum_name_to_midi(drum_name)
                    if midi_note is not None:
                        self.events.append(TimedEvent(
                            start=start_ticks,
                            duration=duration_ticks,
                            note=midi_note,
                            channel=DRUM_CHANNEL,
                        ))
        elif isinstance(node, items.Durable):
            start_ticks = int(round(time * tick_scale))
            duration_fraction = node.duration[0] * node.duration[1] * scaling
            duration_ticks = max(1, int(round(duration_fraction * tick_scale)))
            midi_note = None
            channel = 0
            
            if isinstance(node, items.DrumNote):
                # Handle individual drum notes (not in a chord)
                drum_name = str(node.token)
                midi_note = _drum_name_to_midi(drum_name)
                channel = DRUM_CHANNEL
            elif isinstance(node, items.Note) and getattr(node, "pitch", None):
                midi_note = pitch_to_midi(node.pitch)
            
            if isinstance(
                node, (items.Note, items.Rest, items.Skip, items.Q, items.DrumNote, items.Unpitched)
            ):
                self.events.append(TimedEvent(
                    start=start_ticks,
                    duration=duration_ticks,
                    note=midi_note,
                    channel=channel,
                ))
        
        result = super().traverse(node, time, scaling)
        
        # Restore DrumMode context after leaving
        if isinstance(node, items.DrumMode):
            self._in_drum_mode = was_in_drum_mode
        
        return result


def _find_music_node(root: items.Item) -> Optional[items.Music]:
    for node in root.iter_depth():
        if isinstance(node, items.Music):
            return node
        if isinstance(node, items.Assignment):
            value = node.value()
            if isinstance(value, items.Music):
                return value
    return None


def _extract_tempo(root: items.Item, default_bpm: int) -> float:
    for tempo_node in root.find(items.Tempo):
        values = tempo_node.tempo()
        if values:
            base_fraction = tempo_node.fraction() or Fraction(1, 4)
            quarter_bpm = values[0] * (base_fraction / Fraction(1, 4))
            return float(quarter_bpm)
    return float(default_bpm)


def lilypond_to_midifile(
    lilypond_text: str,
    tempo_fallback: int = 120,
    ticks_per_beat: int = 480,
) -> MidiFile:
    """Convert LilyPond text to a mido.MidiFile."""
    document = ly.document.Document(lilypond_text)
    try:
        rel2abs.rel2abs(ly.document.Cursor(document))
    except (ValueError, RuntimeError):
        # Relative conversion failed; fall back to original pitches.
        pass

    music_document = ly.music.document(document)
    music_node = _find_music_node(music_document)
    if music_node is None:
        raise ValueError("Could not find music content in the LilyPond input.")

    tempo_bpm = _extract_tempo(music_document, tempo_fallback)
    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage("track_name", name="rappa LilyPond", time=0))
    track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo_bpm), time=0))

    collector = LilypondEventCollector(ticks_per_beat)
    collector.read(music_node)

    # Timeline: (tick, event_type, note, channel)
    timeline: list[tuple[int, str, int, int]] = []
    for event in collector.events:
        if event.note is None:
            continue
        timeline.append((event.start, EVENT_ON, event.note, event.channel))
        timeline.append((event.start + event.duration, EVENT_OFF, event.note, event.channel))

    timeline.sort(key=lambda e: (e[0], OFF_PRIORITY if e[1] == EVENT_OFF else ON_PRIORITY))

    last_tick = 0
    for tick, kind, note, channel in timeline:
        delta = max(0, tick - last_tick)
        if kind == EVENT_ON:
            track.append(Message("note_on", note=note, velocity=64, time=delta, channel=channel))
        else:
            track.append(Message("note_off", note=note, velocity=64, time=delta, channel=channel))
        last_tick = tick

    track.append(MetaMessage("end_of_track", time=0))
    return mid


def convert_lilypond_to_midi_path(
    lilypond_text: str,
    output_path: Optional[str] = None,
    tempo_fallback: int = 120,
    ticks_per_beat: int = 480,
) -> str:
    """Convert LilyPond text to a MIDI file saved on disk and return its path."""
    midi = lilypond_to_midifile(
        lilypond_text,
        tempo_fallback=tempo_fallback,
        ticks_per_beat=ticks_per_beat,
    )
    temp_path = None
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mid")
        temp_path = tmp.name
        output_path = temp_path
        tmp.close()
    try:
        midi.save(output_path)
    except Exception:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
        raise
    return output_path
