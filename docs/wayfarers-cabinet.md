# The Wayfarer’s Cabinet

A playable collection of twenty acoustic chamber instruments and five imaginary shipboard synthesizers. Each instrument has a stereo solo and an animated, self-contained glTF model. The acoustic builds are workshop interpretations. The tunings and short pieces were written for these mechanisms.

| Family | Instruments and selection IDs |
| --- | --- |
| Plucked strings | Mothwing Oud (`oud`), Rain-Chart Koto (`koto`), Ferryman’s Kora (`kora`), Heather Mountain Dulcimer (`dulcimer`) |
| Bowed and wheel-driven strings | Courier’s Nyckelharpa (`nyckelharpa`), Frostvein Fiddle (`hardanger`), Candlewheel Gurdy (`gurdy`) |
| Air and reeds | Root Lantern shakuhachi (`shakuhachi`), Cloud Stair Siku (`siku`), Reed Citadel sheng (`sheng`), Night-Watch Pipes (`uilleann`), Vesper Serpent (`serpent`), Quayside Bandoneon (`bandoneon`) |
| Bars, tines, skins, vessels and glass | Orchard Balafon (`balafon`), Bottle-Star Mbira (`mbira`), Caravan Tabla (`tabla`), Tide-Clock Kulintang (`kulintang`), River-Mouth Udu (`udu`), Tideglass Armonica (`armonica`), Eclipse Handpan (`handpan`) |
| Shipboard synthesizers | Magnetar Flux Organ (`magnetar`), Periapsis Ribbon (`periapsis`), Vacuum Choir (`choir`), Cryotape Echoplex (`cryotape`), Pulsar Navigation Loom (`pulsar`) |

## Play the gallery

Use Godot 4.7. On a fresh checkout, fetch the model files with Git LFS and import the project once.

```sh
git lfs pull
godot --headless --path harness --import
godot --path harness -- --cabinet
godot --path harness -- --instrument=armonica
```

The gallery advances automatically. A named instrument plays its solo once. Use the selector or arrow keys to change instruments, Space to pause or resume, Home to replay, and D to toggle between the wide and detail views. Pass `--view=wide` for a fixed framing or `--clean` to hide the controls and titles. The model, moving mechanisms, and stereo recording all follow the same score clock.

## Compose with the sounds

`loam.cabinet.INSTRUMENTS` gives the available IDs, reference MIDI pitches, tempo and phrase. `note` takes an instrument ID, zero-based playing position, duration in seconds, velocity from 0 to 1, and take 0 or 1. It returns mono float32 samples at `loam.SR` with the voice’s natural release. A held note’s duration controls its gate. Plucked strings and percussion ring out after the attack.

```python
from scipy.io.wavfile import write
from loam import SR
from loam.cabinet import INSTRUMENTS, note

instrument = INSTRUMENTS["koto"]
lane = instrument.pitches.index(67)
write("koto-g.wav", SR, note(instrument.id, lane, duration=.7, velocity=.85))
```

The SFZ download has 25 patches and 394 mono samples covering 197 positions. Each patch alternates two takes per position. The pitched instruments map intervening keys to a nearby reference pitch. The tabla and udu map strokes to individual MIDI keys. The bowed, wind and sustained synth patches have crossfaded sustain loops. The struck and plucked patches let the body ring out. Extract the archive with its directory structure intact and load an instrument’s `.sfz` in an SFZ player.

The model archive contains ordinary GLBs with embedded colour, normal and roughness maps, baked tangents, and a `Recital` animation. The accompanying `catalog.json` gives the attacks, playing positions, durations and velocities in score time.

## Build another performance

The phrases in `loam/cabinet.py` use zero-based playing positions and lengths in beats. For example, `0+4/1 2/.5 -/.5` sounds a two-note chord for one beat, plays position 2 for half a beat, then rests for half a beat. Edit an instrument’s phrase or tempo and rebuild its audio and motion. The audio builder also writes the sampler archive.

```sh
python3 songs/wayfarers_cabinet.py
python3 tools/build_cabinet.py koto
godot --headless --path harness --import
godot --headless --path harness -s dev/test_cabinet.gd -- --silent
```

Omit the instrument IDs from the model builder to regenerate the whole cabinet and its workbench. Run `python3 tools/render_cabinet.py` to create the chaptered recital, atlas, model download and individual solo-film archive under `render/cabinet/`. Add `--instrument koto` to render just that solo under `render/cabinet/solos/`. The renderer needs the WAV masters from the audio builder and uses the repository’s offscreen Godot/FFmpeg path. `--jobs` controls the number of simultaneous captures.
