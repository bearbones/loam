# Feature plans for the Clockwork Chamber

Specs written 2026-09-17 at the close of the motion-design session, for the
next agent to implement. Each is sized for one focused session, follows the
`docs/clockwork-todos.md` shape (where, problem, work, acceptance) and names
the files it touches. They are independent unless a plan says otherwise;
the suggested order is the one below. Every plan ends the same way: rulers
green on both assets (`docs/articulated-arms.md`, "Rulers"), a render or
clip shown to the operator, a dated `LOG.md` entry, a commit of only the
files the work touched — never the uncommitted `soundgarden/` changes.

**Claiming a plan (two sessions now work this tree at once):** before
starting one, append a `**Claimed …**` line to its file naming your session
and the time, and commit that file alone; check the file for a claim before
you start. Done plans get a `**Status …**` line the same way.

The build order and the traps (rail cache, absolute `--score=` paths, zsh
quoting, `show`) are in `docs/clockwork-build.md`, `docs/articulated-arms.md`
and the project memory; read `docs/motion-design.md` first — the operator's
direction is the *contrast* between clicky, stepped, ratcheted motion with
recoil, and smooth, precise servo motion, and every plan here serves it.

**Current goal (2026-10-03): [the players](../goals/the-players.md).** The
operator's direction after watching the film: articulated, fluid, anticipatory
player arms. That means fingered harp hands in Salzedo's grammar, mallets that
swing on a hinge and ride the bounce, a rake that swings like a pendulum, and
drivers on every joint. Its milestones (M0–M11) are claimed and marked done in
the goal's own table, and they follow the claiming rule above. Where it
reframes the stepped-against-servo contrast below, the goal wins.

| Plan | What it delivers | Size |
|---|---|---|
| [assembly-shudder](assembly-shudder.md) | the blow shakes the instrument stand, the rail and its gantry — not only the arm | M |
| [hinged-hammer](hinged-hammer.md) | the hammer arms strike with a flipped, checked hammer head instead of a dropped mallet | L |
| [leadscrew-servo-drive](leadscrew-servo-drive.md) | pick and rake carriages ride a leadscrew (the servo's mechanism), mallets keep rack, pinion and pawl | L |
| [ratchet-tooth-profile](ratchet-tooth-profile.md) | trapezoid teeth on pinion and rack, a pawl that drops to the root, a real click | M |
| [pawl-follow-ups](pawl-follow-ups.md) | the roller turns, the click has a sound, the pawl rests on a detent | S |
| [contrast-reel](contrast-reel.md) | one command renders the stepped-vs-servo comparison clip the operator asked for | S |
| [planner-uses-the-motion](planner-uses-the-motion.md) | `loam/score.py` derives travel and approach times from the vocabularies instead of per-index constants | M |
| [rail-cache-key](rail-cache-key.md) | the rail search re-plans when the motion or the linkage changes | S |
| [string-look-next](string-look-next.md) | wound bass strings, anisotropic highlights, contact shadows at eyelets and bridges | M |
| [wrist-and-tool-detail](wrist-and-tool-detail.md) | the wrist socket's collar and set screw, the mallet's wrapped head, the plectrum's shim | S |
