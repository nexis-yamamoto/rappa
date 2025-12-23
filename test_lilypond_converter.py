import mido
import pytest

from lilypond_converter import lilypond_to_midifile


def _extract_notes(track: mido.MidiTrack):
    """Return list of (note, duration_ticks) from note_on/note_off pairs."""
    events = []
    on_times = {}
    current_time = 0
    for msg in track:
        current_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            on_times[msg.note] = current_time
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            start = on_times.pop(msg.note, None)
            if start is not None:
                events.append((msg.note, current_time - start))
    return events


def test_lilypond_basic_notes_and_durations():
    ly_text = "\\relative c' { c4 d e f }"
    mid = lilypond_to_midifile(ly_text, tempo_fallback=120)
    track = mid.tracks[0]
    notes = _extract_notes(track)
    assert [n for n, _ in notes] == [60, 62, 64, 65]
    assert all(dur > 0 for _, dur in notes)


def test_lilypond_tempo_conversion():
    ly_text = "\\relative c' { \\tempo 4=90 c4 d }"
    mid = lilypond_to_midifile(ly_text, tempo_fallback=120)
    tempo_msgs = [m for m in mid.tracks[0] if m.type == "set_tempo"]
    assert tempo_msgs
    bpm = mido.tempo2bpm(tempo_msgs[0].tempo)
    assert bpm == pytest.approx(90, rel=0.01)
