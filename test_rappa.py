import os
import tempfile
import pytest

from rappa import ABCPlayer, MIDIPortError, NOTE_FREQUENCIES


def test_parse_note_basic():
    """Test basic note parsing."""
    player = ABCPlayer(show_progress=False)
    
    # Basic notes
    freq, dur = player.parse_note('C')
    assert freq == pytest.approx(NOTE_FREQUENCIES['C'], rel=0.01)
    assert dur == 500  # BASE_DURATION
    
    freq, dur = player.parse_note('c')
    assert freq == pytest.approx(NOTE_FREQUENCIES['c'], rel=0.01)
    assert dur == 500


def test_parse_note_duration():
    """Test note duration parsing."""
    player = ABCPlayer(show_progress=False)
    
    # Longer duration
    freq, dur = player.parse_note('C2')
    assert dur == 1000  # 2 * BASE_DURATION
    
    # Shorter duration
    freq, dur = player.parse_note('C/2')
    assert dur == 250  # BASE_DURATION / 2


def test_parse_note_accidentals():
    """Test accidental parsing."""
    player = ABCPlayer(show_progress=False)
    
    # Sharp (should be higher than natural)
    freq_sharp, _ = player.parse_note('^C')
    freq_natural, _ = player.parse_note('C')
    assert freq_sharp > freq_natural
    
    # Flat (should be lower than natural)
    freq_flat, _ = player.parse_note('_D')
    freq_d, _ = player.parse_note('D')
    assert freq_flat < freq_d


def test_parse_note_rest():
    """Test rest parsing."""
    player = ABCPlayer(show_progress=False)
    
    freq, dur = player.parse_note('z')
    assert freq == 0
    assert dur == 500
    
    freq, dur = player.parse_note('z2')
    assert freq == 0
    assert dur == 1000


def test_frequency_to_midi_note():
    """Test frequency to MIDI note conversion."""
    player = ABCPlayer(show_progress=False)
    
    # A4 = 440Hz = MIDI note 69
    assert player.frequency_to_midi_note(440.0) == 69
    
    # C4 = ~261.63Hz = MIDI note 60
    assert player.frequency_to_midi_note(261.63) == 60
    
    # Rest (0 Hz) should return 0
    assert player.frequency_to_midi_note(0) == 0


def test_midi_note_to_frequency():
    """Test MIDI note to frequency conversion."""
    player = ABCPlayer(show_progress=False)
    
    # MIDI note 69 = 440Hz (A4)
    assert player.midi_note_to_frequency(69) == pytest.approx(440.0, rel=0.01)
    
    # MIDI note 60 = ~261.63Hz (C4)
    assert player.midi_note_to_frequency(60) == pytest.approx(261.63, rel=0.01)


def test_save_to_midi():
    """Test MIDI file saving."""
    player = ABCPlayer(show_progress=False)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp:
        temp_path = tmp.name
    
    try:
        player.save_to_midi("C D E", temp_path)
        assert os.path.exists(temp_path)
        
        # Verify it's a valid MIDI file
        import mido
        mid = mido.MidiFile(temp_path)
        assert len(mid.tracks) > 0
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_midi_port_error_on_play():
    """Test that MIDIPortError is raised when no MIDI port is available."""
    player = ABCPlayer(show_progress=False)
    
    # On a system without MIDI ports, this should raise MIDIPortError
    with pytest.raises(MIDIPortError):
        player.play("C D E")
