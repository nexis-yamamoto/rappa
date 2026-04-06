Goal
- Add support for LilyPond \DrumStaff / \drummode percussion so drum parts render to GM percussion instead of being skipped.

Approach
- Detect drum contexts during LilyPond event extraction and route them to MIDI channel 10 (index 9).
- Map a minimal drum-name set to General MIDI percussion note numbers; warn/drop when unmapped. Target names: bd, sn, hh, hhc, hho, cymc, toml, tomm, tomh.
- Keep core timing/tempo handling unchanged; emit drum note_on/note_off events with default velocity.
- Update docs and tests to describe and verify percussion handling.

Tasks
- Event parsing: extend lilypond_converter.py to recognize DrumStaff/drummode contexts and preserve percussion events.
- Drum mapping: add a mapping table for bd/sn/hh/hhc/hho/cymc/toml/tomm/tomh to GM notes; apply during event creation; warn/drop unmapped names.
- MIDI rendering: ensure drum events use channel 9 and produce note_on/note_off with durations/velocity.
- Tests: add \DrumStaff samples in test_lilypond_converter.py to confirm mapped/unmapped behavior.
- Docs: update README to note percussion support, mapping, and limitations (velocity/dynamics still minimal).

Technical Considerations
- Simultaneous notes (chords) `< ... >`:
  - Drums often play simultaneously (e.g., bass drum + hi-hat). LilyPond uses `<bd hh>`.
  - The parser must correctly map drum names inside chord notation, not just single notes.
  - Recommendation: Include test cases for simultaneous hits like `<bd hh>4`.
- Parallel parts `<< ... >>`:
  - "Adding a percussion part" implies playing melody and drums simultaneously.
  - The converter must correctly interpret `<< \new Staff { ... } \new DrumStaff { ... } >>` parallel structures and output multi-track MIDI.
  - Critical: If the current converter assumes a "single melody line", this will be the most significant refactoring point.

Open Questions
- Any velocity/accent handling needed beyond a fixed default?

Acceptance Criteria
- DrumStaff/drummode events are converted to MIDI drums on channel 9 using the documented minimal mapping (bd/sn/hh/hhc/hho/cymc/toml/tomm/tomh).
- Unmapped drum names fail gracefully (warning/drop) without crashing other parts.
- Tests cover drum mapping and unmapped-name behavior.
- README documents percussion support, the supported name list, and current limitations.
