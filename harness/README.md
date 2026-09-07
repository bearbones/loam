# harness — a Godot debug visual for a loam score export

Reads what `songs/chamber.py` exports (`render/chamber/score.json`,
`stems/*.wav`, `shapes.f32`) at runtime — no import step — and shows
the machine playing: the annotated track (lanes, ticks, arm motion
spans, cues, playhead on the audio clock) over the strings vibrating
with the shape clips the PDE baked, arms sliding along their plans,
bars flashing, the chamber glowing with its stem envelope.

    python3 songs/chamber.py                  # render + export first
    godot --path harness                      # play it
    godot --path harness -- --score=/abs/path/score.json
    godot --headless --path harness -s dev/test_load.gd   # HARNESS: PASS
    SHOT=/tmp/x.png godot --path harness      # one frame at 48 s, quit

Keys: space play/pause · Home restart · ←/→ seek 2 s · Z/X zoom the
track · 1..9 mute stem N · S screenshot.

Not the game: no arms with IK, no cameras, no materials. The point
is that everything drawn here comes from the score, and the score
came from the thing that decided every note.
