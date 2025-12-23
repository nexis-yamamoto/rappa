# LilyPond Playback Plan

Goal: add LilyPond (.ly) playback by converting to MIDI and reusing the existing pygame-based synth pipeline, with CLI/MCP support and updated docs/deps.

## Approach
- Convert LilyPond to MIDI and reuse existing playback.
  - **Note**: Since LilyPond can express percussion parts etc. that standard ABC cannot, we will convert directly to MIDI instead of ABC.
- Implementation Strategy:
  - Use `python-ly` to parse LilyPond and `mido` to build MIDI messages.
  - Do NOT use `lilypond` CLI (to avoid external dependencies).
- Minimal first cut: notes and durations, honor tempo; skip dynamics/articulations initially.

## Tasks
1) Converter: add module to load .ly text or file, parse with `python-ly`, and produce a MIDI object or path.
2) CLI: extend detection in rappa.py to accept .ly or LilyPond text, route through converter then existing MIDI playback.
3) MCP: add a new tool `play_lilypond` that accepts LilyPond content and calls the converter + playback.
4) Deps/config: add `python-ly` in pyproject.toml.
5) Docs: update README with LilyPond usage examples and limitations.
6) Testing: sample .ly -> playback; ensure MIDI save still works; handle error reporting for bad LilyPond input.

## Open Questions
- Fidelity scope: do we need dynamics/instrument support now, or keep minimal? (Keep minimal for initial implementation)

## Acceptance (minimal viable)
- CLI: `python rappa.py path/to/score.ly` plays notes at correct tempo via existing synth.
- MCP: New tool `play_lilypond` accepts LilyPond content and plays it.
- README documents how to use, dependencies listed.
