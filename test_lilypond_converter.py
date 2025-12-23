import mido
import pytest
import warnings

from lilypond_converter import lilypond_to_midifile, DRUM_CHANNEL, DRUM_NAME_TO_MIDI


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


def _extract_notes_with_channel(track: mido.MidiTrack):
    """Return list of (note, channel, duration_ticks) from note_on/note_off pairs."""
    events = []
    on_times = {}
    current_time = 0
    for msg in track:
        current_time += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            on_times[(msg.note, msg.channel)] = current_time
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            start = on_times.pop((msg.note, msg.channel), None)
            if start is not None:
                events.append((msg.note, msg.channel, current_time - start))
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


def test_drummode_basic_mapping():
    """Test that drummode notes are correctly mapped to GM percussion and use channel 9."""
    ly_text = r"\drummode { bd4 sn hh cymc }"
    mid = lilypond_to_midifile(ly_text)
    track = mid.tracks[0]
    notes = _extract_notes_with_channel(track)
    
    # Check that all notes use drum channel (9)
    assert all(channel == DRUM_CHANNEL for _, channel, _ in notes)
    
    # Check that drum names are mapped correctly
    expected_notes = [
        DRUM_NAME_TO_MIDI["bd"],   # 36 - Bass Drum
        DRUM_NAME_TO_MIDI["sn"],   # 38 - Snare
        DRUM_NAME_TO_MIDI["hh"],   # 42 - Closed Hi-Hat
        DRUM_NAME_TO_MIDI["cymc"], # 49 - Crash Cymbal
    ]
    assert [n for n, _, _ in notes] == expected_notes
    
    # Check that all notes have positive duration
    assert all(dur > 0 for _, _, dur in notes)


def test_drummode_chord_simultaneous_hits():
    """Test that drum chords (simultaneous hits) are handled correctly."""
    ly_text = r"\drummode { <bd hh>4 <sn hho>4 }"
    mid = lilypond_to_midifile(ly_text)
    track = mid.tracks[0]
    notes = _extract_notes_with_channel(track)
    
    # All notes should use drum channel (9)
    assert all(channel == DRUM_CHANNEL for _, channel, _ in notes)
    
    # Should have 4 notes total (2 chords x 2 notes each)
    assert len(notes) == 4
    
    # Expected notes in order of appearance
    expected_notes = [
        DRUM_NAME_TO_MIDI["bd"],   # 36 - Bass Drum
        DRUM_NAME_TO_MIDI["hh"],   # 42 - Closed Hi-Hat
        DRUM_NAME_TO_MIDI["sn"],   # 38 - Snare
        DRUM_NAME_TO_MIDI["hho"],  # 46 - Open Hi-Hat
    ]
    assert [n for n, _, _ in notes] == expected_notes


def test_parallel_staff_and_drumstaff():
    """Test parallel parts with Staff and DrumStaff."""
    ly_text = r"""
    << 
      \new Staff { c'4 d' }
      \new DrumStaff \drummode { bd4 sn }
    >>
    """
    mid = lilypond_to_midifile(ly_text)
    track = mid.tracks[0]
    notes = _extract_notes_with_channel(track)
    
    # Should have 4 notes: 2 melody + 2 drums
    assert len(notes) == 4
    
    # Check melody notes (channel 0)
    melody_notes = [(n, ch) for n, ch, _ in notes if ch == 0]
    assert melody_notes == [(60, 0), (62, 0)]  # C4, D4
    
    # Check drum notes (channel 9)
    drum_notes = [(n, ch) for n, ch, _ in notes if ch == DRUM_CHANNEL]
    assert drum_notes == [
        (DRUM_NAME_TO_MIDI["bd"], DRUM_CHANNEL),
        (DRUM_NAME_TO_MIDI["sn"], DRUM_CHANNEL),
    ]


def test_drummode_unmapped_name_warning():
    """Test that unmapped drum names emit a warning and are skipped."""
    ly_text = r"\drummode { bd4 unknowndrum sn }"
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mid = lilypond_to_midifile(ly_text)
        
        # Check that a warning was emitted for the unknown drum
        warning_messages = [str(warning.message) for warning in w]
        assert any("unknowndrum" in msg for msg in warning_messages)
    
    track = mid.tracks[0]
    notes = _extract_notes_with_channel(track)
    
    # Only bd and sn should be in the output (unknowndrum is skipped)
    assert len(notes) == 2
    assert [n for n, _, _ in notes] == [
        DRUM_NAME_TO_MIDI["bd"],
        DRUM_NAME_TO_MIDI["sn"],
    ]


def test_all_supported_drum_names():
    """Test that all documented drum names are correctly mapped."""
    # All drum names from the issue requirement
    supported_drums = ["bd", "sn", "hh", "hhc", "hho", "cymc", "toml", "tomm", "tomh"]
    
    for drum_name in supported_drums:
        ly_text = f"\\drummode {{ {drum_name}4 }}"
        mid = lilypond_to_midifile(ly_text)
        track = mid.tracks[0]
        notes = _extract_notes_with_channel(track)
        
        assert len(notes) == 1, f"Expected 1 note for {drum_name}"
        note, channel, _ = notes[0]
        assert channel == DRUM_CHANNEL, f"Expected drum channel for {drum_name}"
        assert note == DRUM_NAME_TO_MIDI[drum_name], f"Wrong mapping for {drum_name}"
