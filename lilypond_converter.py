from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import tempfile
from typing import Optional

import ly.document
import ly.music
from ly.music import event as music_event
from ly.music import items
from ly.pitch import rel2abs
import mido
from mido import Message, MetaMessage, MidiFile, MidiTrack


NOTE_OFFSETS = [0, 2, 4, 5, 7, 9, 11]


def pitch_to_midi(pitch) -> int:
    """Convert ly.pitch.Pitch to MIDI note number."""
    # pitch.alter is stored in quarter-step units (e.g., sharp = 0.5), so multiply
    # by 2 to convert to semitone offsets and round to the nearest integer.
    semitone_from_alter = int(round(float(pitch.alter * 2)))
    base = 12 * (pitch.octave + 4)
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


class LilypondEventCollector(music_event.Events):
    def __init__(self, ticks_per_beat: int):
        super().__init__()
        self.ticks_per_beat = ticks_per_beat
        self.events: list[TimedEvent] = []

    def traverse(self, node, time, scaling):
        if isinstance(node, items.Durable):
            tick_scale = _tick_scale(self.ticks_per_beat)
            start_ticks = int(round(time * tick_scale))
            duration_fraction = node.duration[0] * node.duration[1] * scaling
            duration_ticks = max(1, int(round(duration_fraction * tick_scale)))
            midi_note = None
            if isinstance(node, items.Note) and getattr(node, "pitch", None):
                midi_note = pitch_to_midi(node.pitch)
            if isinstance(
                node, (items.Note, items.Rest, items.Skip, items.Q, items.DrumNote, items.Unpitched)
            ):
                self.events.append(TimedEvent(start=start_ticks, duration=duration_ticks, note=midi_note))
        return super().traverse(node, time, scaling)


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
    except Exception:
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

    timeline: list[tuple[int, str, int]] = []
    for event in collector.events:
        if event.note is None:
            continue
        timeline.append((event.start, "on", event.note))
        timeline.append((event.start + event.duration, "off", event.note))

    timeline.sort(key=lambda e: (e[0], 0 if e[1] == "off" else 1))

    last_tick = 0
    for tick, kind, note in timeline:
        delta = max(0, tick - last_tick)
        if kind == "on":
            track.append(Message("note_on", note=note, velocity=64, time=delta))
        else:
            track.append(Message("note_off", note=note, velocity=64, time=delta))
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
