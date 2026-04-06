Goal
- Remove pygame/numpy dependencies and switch playback to python-rtmidi-driven MIDI output while keeping ABC/LilyPond workflows intact.

Approach
- Replace tone synthesis and pygame mixer usage with mido + python-rtmidi output-port playback.
- Keep ABC parsing and LilyPond-to-MIDI conversion logic; route playback through MIDI out instead of generated waveforms.
- Auto-use the first available MIDI out port; if none are available, surface an error and stop.
- Update dependencies, docs, and tests to reflect the new backend.

Tasks
- Playback refactor: update rappa.py to send MIDI events via mido/python-rtmidi instead of pygame/numpy audio; handle port discovery and emit a clear error when no outputs exist (no port-selection change).
- Dependency cleanup: remove pygame and numpy from pyproject.toml; add python-rtmidi; ensure import guards/errors are clear.
- Docs: revise README usage/requirements to describe MIDI-out playback and device expectations; note python-rtmidi install.
- Tests: adjust or add coverage if playback interfaces change; keep LilyPond conversion tests passing.
- CLI/user flow: confirm ABC/LilyPond/MIDI paths still work; allow progress output in CLI; suppress progress in MCP server paths.

Open Questions
- Any minimum python-rtmidi version or platform-specific notes to call out?

Acceptance Criteria
- No pygame or numpy runtime dependency in code or pyproject; python-rtmidi added.
- MIDI playback uses an OS MIDI output port; when none is available, the tool fails gracefully with a clear message.
- MCP server playback emits no progress indicators; CLI playback may show progress.
- README documents the new playback method and dependency changes.
- Existing LilyPond conversion tests still pass; new/updated tests cover the MIDI-out path as appropriate.
