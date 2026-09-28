"""Numerical audio, HTTP, and interrupted-run contract tests (no browser needed)."""
import base64
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import wave

import numpy as np

from .describe import BANDS, TIMES, analyze, describe, embed, f0_midi, sensitivity
from .explore import SEARCH_VERSION, diverse, migrate, restore
from .field import calibrate, dims_per_axis, perceptual_weights, plane, spread_plane
from .match import load_wav, match
from .server import Handler, ThreadingHTTPServer
from .synth import ANCHORS, DEFAULT, SR, VERSION, features, measure, render, validate_vector, wav_bytes


def record(vector):
    audio, metrics, descriptor, _ = analyze(vector)
    return {'vector': list(vector), 'metrics': metrics, 'descriptor': descriptor}


class SoundTests(unittest.TestCase):
    def test_deterministic_and_wav_roundtrip(self):
        x = render(DEFAULT)
        self.assertTrue(np.array_equal(x, render(DEFAULT)))
        with wave.open(io.BytesIO(wav_bytes(x))) as file:
            self.assertEqual(file.getframerate(), SR)
            self.assertEqual(file.getnchannels(), 1)
            y = np.frombuffer(file.readframes(file.getnframes()), dtype='<i2') / 32767
        np.testing.assert_allclose(x, y, atol=1/32767)

    def test_extremes_are_finite_bounded_and_end_at_zero(self):
        rng = np.random.default_rng(83)
        vectors = [np.zeros(10), np.ones(10), *rng.uniform(0, 1, (32, 10))]
        for vector in vectors:
            for midi in [48, 72, 84]:
                x = render(vector, midi)
                self.assertTrue(np.isfinite(x).all())
                self.assertLessEqual(np.abs(x).max(), .62001)
                self.assertEqual(x[0], 0)
                self.assertEqual(x[-1], 0)
                self.assertGreater(measure(x)['rms'], .005)

    def test_pitch_transposes_without_transposing_decay(self):
        low, high = render(DEFAULT, 60), render(DEFAULT, 72)
        self.assertEqual(len(low), len(high))
        def strongest(x):
            power = np.abs(np.fft.rfft(x * np.hanning(len(x)))); power[0] = 0
            return np.argmax(power) * SR / len(x)
        self.assertAlmostEqual(strongest(high) / strongest(low), 2, delta=.015)

    def test_small_moves_are_continuous_and_dimensions_audible_in_signal(self):
        original = render(DEFAULT)
        for i in range(10):
            nearby = list(DEFAULT); nearby[i] += 1e-5
            x = render(nearby); n = min(len(x), len(original))
            relative = np.linalg.norm(x[:n] - original[:n]) / np.linalg.norm(original[:n])
            self.assertLess(relative, .03, f'dimension {i} discontinuity')
            far = list(DEFAULT); far[i] = .9 if DEFAULT[i] < .5 else .1
            y = render(far); n = min(len(y), len(original))
            self.assertGreater(np.linalg.norm(y[:n] - original[:n]) / np.linalg.norm(original[:n]), .01)

    def test_starters_cover_different_measured_sounds(self):
        points = [features(measure(render(v))) for _, v in ANCHORS]
        for i in range(len(points)):
            for j in range(i):
                self.assertGreater(np.linalg.norm(points[i] - points[j]), .1)

    def test_bad_recipes_rejected(self):
        for bad in [[0]*9, [False]*10, [float('nan')]*10, [2]*10, ['.5']*10]:
            with self.assertRaises(ValueError): validate_vector(bad)


class DescriptorTests(unittest.TestCase):
    def test_grid_is_bounded_level_invariant_and_deterministic(self):
        x = render(DEFAULT)
        grid = np.array(describe(x)['grid'])
        self.assertEqual(grid.shape, (BANDS * TIMES,))
        # Windows average several frames, so the loudest cell sits a little under 0.
        self.assertTrue(np.all(grid <= 0) and np.all(grid >= -1) and grid.max() > -.2)
        np.testing.assert_allclose(describe(x)['grid'], describe(x * .25)['grid'], atol=1e-12)
        self.assertEqual(len(embed(measure(x), grid)), 4 + BANDS * TIMES)
        with self.assertRaises(ValueError): embed(measure(x), grid[:-1])

    def test_descriptor_separates_starters_more_than_scalars_alone(self):
        points = [analyze(v)[3] for _, v in ANCHORS]
        for i in range(len(points)):
            for j in range(i):
                self.assertGreater(np.linalg.norm(points[i] - points[j]), .15)

    def test_pitch_estimate_follows_the_note(self):
        for midi in [48, 55, 60, 67, 72, 84]:
            for _, v in ANCHORS:
                self.assertEqual(f0_midi(render(v, midi)), midi)
        self.assertEqual(f0_midi(np.zeros(1000)), 60)

    def test_sensitivity_flags_audible_dimensions(self):
        s = sensitivity(DEFAULT)
        self.assertEqual(s.shape, (10,))
        self.assertTrue(np.all(s >= 0))
        self.assertGreater(s[1], s[8], 'ring is more audible than bloom at Porcelain')


class FieldTests(unittest.TestCase):
    def test_spread_controls_dimensions_per_axis(self):
        rng = np.random.default_rng(5)
        for k in range(1, 11):
            spread = (k - 1) / 9
            self.assertEqual(dims_per_axis(spread), k)
            for _ in range(100):
                u, v = spread_plane(spread, rng)
                self.assertAlmostEqual(np.linalg.norm(u), 1); self.assertAlmostEqual(np.linalg.norm(v), 1)
                self.assertAlmostEqual(float(u @ v), 0)
                self.assertEqual(int((np.abs(u) > 1e-9).sum()), k)
                self.assertLessEqual(int((np.abs(v) > 1e-9).sum()), min(10, 2 * k))
                if k == 1:
                    self.assertNotEqual(int(np.argmax(np.abs(u))), int(np.argmax(np.abs(v))))
                if k == 10:
                    self.assertGreater(np.abs(u).min() * np.sqrt(10), .3)
        self.assertEqual(dims_per_axis(.5), 6, 'half rounds up, as JS Math.round does')

    def test_weights_and_calibration(self):
        rng = np.random.default_rng(6)
        w = perceptual_weights([1, 1, 1, 1, 1, .01, .01, .01, .01, 0])
        self.assertTrue(np.all(w[:5] < w[5:]) and w.max() <= 2 and w.min() >= .5)
        u, _ = spread_plane(1, rng, w)
        self.assertGreater(np.abs(u[5:]).min(), np.abs(u[:5]).max())
        with self.assertRaises(ValueError): spread_plane(1, rng, [0] * 10)
        radius, distances = calibrate(DEFAULT, spread_plane(1, rng))
        self.assertTrue(.3 <= radius <= 2 and len(distances) == 2 and all(d > 0 for d in distances))
        suggestion = plane(DEFAULT, rng, spread=0, perceptual=True)
        self.assertEqual(len(suggestion['sensitivity']), 10)
        self.assertEqual(suggestion['spread'], 0)


class MatchTests(unittest.TestCase):
    def test_recovers_a_rendered_recipe_and_its_pitch(self):
        target = load_wav(wav_bytes(render(ANCHORS[3][1], 67)))
        midi, results = match(target, journal=Path('/nonexistent'), keep=1, refine=1, evaluations=20)
        self.assertEqual(midi, 67)
        self.assertLess(results[0]['distance'], .05)
        self.assertLess(results[0]['distance'], results[0]['start_distance'] + 1e-9)
        validate_vector(results[0]['vector'])

    def test_wav_loading_rules(self):
        with self.assertRaises(ValueError): load_wav(b'not a wav')
        with self.assertRaises(ValueError): load_wav(wav_bytes(np.zeros(4000)))
        with self.assertRaises(ValueError): load_wav(b'RIFF' + b'\0' * (9 * 1024 * 1024))
        x = load_wav(wav_bytes(np.concatenate([np.zeros(SR), render(DEFAULT), np.zeros(4 * SR)])))
        self.assertLessEqual(len(x), 3 * SR)
        self.assertAlmostEqual(float(np.max(np.abs(x))), .5, places=3)
        self.assertGreater(np.abs(x[:int(.02 * SR)]).max(), 0, 'leading silence trimmed')


class PrototypeTests(unittest.TestCase):
    """B (sinusoidal + residual) and C (learned latent) are prototypes; these pin their contracts."""

    def test_stft_round_trip_and_griffin_lim(self):
        from .stft import stft, istft, griffin_lim
        x = render(DEFAULT)
        np.testing.assert_allclose(istft(stft(x), len(x)), x, atol=1e-9)
        y = griffin_lim(np.abs(stft(x)), len(x), iterations=8)
        self.assertEqual(len(y), len(x)); self.assertTrue(np.isfinite(y).all())

    def test_sms_resynthesis_keeps_identity_and_morph_hits_its_ends(self):
        from .sms import analyze as sms_analyze, synthesize, morph
        grids = {name: np.array(describe(render(v))['grid']) for name, v in ANCHORS}
        models = {name: sms_analyze(render(v)) for name, v in ANCHORS}
        for name, model in models.items():
            self.assertGreaterEqual(len(model['partials']), 5)
            self.assertAlmostEqual(model['f0'], 261.63, delta=3)
            y = synthesize(model)
            self.assertTrue(np.isfinite(y).all() and np.abs(y).max() <= 1)
            own = np.linalg.norm(grids[name] - describe(y)['grid'])
            others = min(np.linalg.norm(grids[other] - describe(y)['grid']) for other in grids if other != name)
            self.assertLess(own, others, f'{name} resynthesis drifted to another starter')
        a, b = models['Porcelain'], models['Small alloy']
        self.assertAlmostEqual(morph(a, b, 0)['f0'], a['f0']); self.assertAlmostEqual(morph(a, b, 1)['f0'], b['f0'])
        half = morph(a, b, .5)
        self.assertEqual(len(half['partials']), max(len(a['partials']), len(b['partials'])))
        low, high = synthesize(a, midi=48), synthesize(a, midi=60)
        self.assertLess(f0_midi(low), f0_midi(high))

    def test_latent_autoencoder_beats_the_mean_and_decodes(self):
        from .latent import Autoencoder, dataset, decode_audio, nearest_recipes, pca_baseline
        grids, vectors = dataset(160, seed=3)
        model = Autoencoder(seed=1).fit(grids[:128], epochs=120)
        test = grids[128:]
        mse = lambda a: float(((a - test) ** 2).mean())
        self.assertLess(mse(model.reconstruct(test)), mse(grids[:128].mean(axis=0)) * .8)
        self.assertEqual(model.encode(test).shape, (len(test), 6))
        audio = decode_audio(model.decode(model.encode(test[:1]))[0], seconds=.5, iterations=6)
        self.assertEqual(len(audio), SR // 2); self.assertTrue(np.isfinite(audio).all())
        for vector in nearest_recipes(test[0], grids, vectors, 2):
            validate_vector(vector)
        self.assertIsNotNone(pca_baseline(grids)(test[0]))
        with tempfile.TemporaryDirectory() as tmp:
            model.save(Path(tmp) / 'm.npz')
            np.testing.assert_allclose(Autoencoder.load(Path(tmp) / 'm.npz').encode(test), model.encode(test))

    def test_tone_profile_recovers_harmonics_stretch_and_survives_resynthesis(self):
        from loam import hz
        from .tone import from_vector, partial_frequencies, profile, synthesize, vector
        t = np.arange(int(1.5 * SR)) / SR
        levels = np.array([0, -6, -3, -12, -20, -15, -30, -25], float)
        for stretch in (0.0, 1e-3):
            x = sum(10 ** (a / 20) * np.sin(2 * np.pi * f * t) for f, a in zip(partial_frequencies(hz(60), stretch, 8), levels))
            tone = profile(x)
            self.assertAlmostEqual(tone['f0'], hz(60), delta=1.5)
            self.assertAlmostEqual(np.log10(tone['stretch'] + 1e-5), np.log10(stretch + 1e-5), delta=.1)
            np.testing.assert_allclose(tone['harmonics'][:8], levels, atol=1.5)
            self.assertLess(max(tone['noise']), -40)
            again = profile(synthesize(tone))
            np.testing.assert_allclose(again['harmonics'][:8], levels, atol=2)
            self.assertAlmostEqual(again['f0'], tone['f0'], delta=1.5)
        v = vector(tone)
        self.assertEqual(v.shape, (89,)); self.assertTrue(((v >= -1) & (v <= 1)).all())
        back = from_vector(v, tone['f0'])
        np.testing.assert_allclose(back['harmonics'], tone['harmonics'], atol=1e-9)
        self.assertAlmostEqual(np.log10(back['stretch'] + 1e-5), np.log10(tone['stretch'] + 1e-5), delta=.05)
        low, high = synthesize(tone, midi=48), synthesize(tone, midi=72)
        self.assertLess(profile(low)['f0'], profile(high)['f0'])
        with self.assertRaises(ValueError):
            from_vector(np.zeros(10))

    def test_tone_corpus_and_latent_cover_loam_sources(self):
        from .tone import Autoencoder, HARMONICS, BANDS, build_corpus, corpus_sources, mixup
        names, vectors, f0s = build_corpus(count_soundgarden=40, seed=5)
        self.assertGreater(len(names), 100)
        self.assertEqual(vectors.shape[1], HARMONICS + BANDS + 1)
        self.assertTrue(np.isfinite(vectors).all() and (f0s > 30).all())
        self.assertTrue(any(n.startswith('flute') for n in names) and any(n.startswith('pad') for n in names))
        train = np.vstack([vectors[:-20], mixup(vectors[:-20], 100)])
        model = Autoencoder(sizes=(vectors.shape[1], 48, 6), seed=1).fit(train, epochs=100)
        test = vectors[-20:]
        mse = lambda a: float(((a - test) ** 2).mean())
        self.assertLess(mse(model.reconstruct(test)), mse(train.mean(axis=0)) * .8)
        decoded = model.decode(model.encode(test[:1]))[0]
        self.assertTrue(((decoded >= -1) & (decoded <= 1)).all())


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.library = Path('/nonexistent/soundgarden-test-seeds.json')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def test_static_and_library_are_self_contained(self):
        for path in ['/', '/app.js', '/space.js', '/style.css']:
            with urlopen(self.url + path) as r:
                self.assertEqual(r.status, 200)
                self.assertIn("default-src 'self'", r.headers['Content-Security-Policy'])
        data = json.load(urlopen(self.url + '/api/library'))
        self.assertEqual(len(data['seeds']), 4)

    def test_render_matches_offline_engine(self):
        req = Request(self.url + '/api/render', data=json.dumps({'vector':DEFAULT, 'notes':[60,72]}).encode(), headers={'Content-Type':'application/json'})
        data = json.load(urlopen(req))
        self.assertEqual(base64.b64decode(data['samples']['60']), wav_bytes(render(DEFAULT)))
        self.assertEqual(data['version'], VERSION)

    def test_malformed_and_cross_origin_requests_rejected(self):
        cases = [({'vector': DEFAULT, 'notes':[False]}, {}, 400),
                 ({'vector': DEFAULT, 'notes':[60]*14}, {}, 400),
                 ({'vector': DEFAULT, 'notes':[60]}, {'Origin':'https://example.com'}, 403),
                 ({'vector': DEFAULT, 'notes':[60]}, {'Host':'example.com'}, 403)]
        for payload, headers, expected in cases:
            req = Request(self.url + '/api/render', data=json.dumps(payload).encode(), headers=headers)
            with self.assertRaises(HTTPError) as error: urlopen(req)
            self.assertEqual(error.exception.code, expected)

    def test_plane_endpoint_returns_a_measured_field(self):
        req = Request(self.url + '/api/plane', data=json.dumps({'center': DEFAULT, 'spread': 0, 'perceptual': True}).encode(), headers={'Content-Type':'application/json'})
        data = json.load(urlopen(req))
        axes = np.array(data['axes'])
        self.assertEqual(axes.shape, (2, 10))
        self.assertEqual(int((np.abs(axes[0]) > 1e-9).sum()), 1)
        self.assertTrue(.3 <= data['radius'] <= 2 and len(data['sensitivity']) == 10)
        for bad in [{'center': DEFAULT, 'spread': 3}, {'center': DEFAULT, 'perceptual': 'yes'}, {'center': [1]*9}]:
            req = Request(self.url + '/api/plane', data=json.dumps(bad).encode(), headers={'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as error: urlopen(req)
            self.assertEqual(error.exception.code, 400)

    def test_match_endpoint_accepts_wav_and_rejects_noise(self):
        req = Request(self.url + '/api/match', data=wav_bytes(render(ANCHORS[1][1], 55)), headers={'Content-Type':'audio/wav'})
        data = json.load(urlopen(req))
        self.assertEqual(data['midi'], 55)
        self.assertTrue(1 <= len(data['seeds']) <= 3)
        for seed in data['seeds']:
            validate_vector(seed['vector']); self.assertEqual(seed['source'], 'Matched')
        req = Request(self.url + '/api/match', data=b'garbage', headers={'Content-Type':'audio/wav'})
        with self.assertRaises(HTTPError) as error: urlopen(req)
        self.assertEqual(error.exception.code, 400)


class RunnerTests(unittest.TestCase):
    def run_explorer(self, output, trials):
        subprocess.run([sys.executable, '-m', 'soundgarden.explore', '--output', str(output), '--minutes', '1', '--max-trials', str(trials), '--keep', '3'], check=True, capture_output=True)

    def test_resume_equals_uninterrupted_and_recovers_partial_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            full, resumed = Path(tmp)/'full', Path(tmp)/'resumed'
            self.run_explorer(full, 8); self.run_explorer(resumed, 3)
            with (resumed/'trials.jsonl').open('ab') as f: f.write(b'{"trial":')
            self.run_explorer(resumed, 8)
            self.assertEqual((full/'trials.jsonl').read_bytes(), (resumed/'trials.jsonl').read_bytes())
            a,b = [json.loads((p/'seeds.json').read_text()) for p in [full,resumed]]
            self.assertEqual(a['seeds'], b['seeds'])
            self.assertEqual(a['trials'], 8)
            self.assertEqual(len(a['seeds']), 3)

    def test_diversity_keeps_unique_representatives(self):
        candidates = [record(v) for _, v in ANCHORS]
        selected = diverse(candidates, 3)
        self.assertEqual(len(selected), 3)
        self.assertEqual(len({tuple(c['vector']) for c in selected}), 3)

    def test_legacy_journal_migrates_only_when_it_still_reproduces(self):
        legacy = [{'trial': i, 'vector': v, 'metrics': measure(render(v)), 'accepted': True} for i, (_, v) in enumerate(ANCHORS)]
        records = json.loads(json.dumps(legacy))
        self.assertTrue(migrate(records))
        self.assertTrue(all('descriptor' in r for r in records))
        self.assertFalse(migrate(records), 'already migrated records are left alone')
        tampered = json.loads(json.dumps(legacy)); tampered[0]['metrics']['centroid_hz'] *= 1.01
        with self.assertRaises(ValueError): migrate(tampered)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / 'trials.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in legacy))
            (output / 'run.json').write_text(json.dumps({'version': VERSION, 'seed': 7, 'implementation_sha256': 'old', 'numpy_version': np.__version__, 'sample_rate': SR}))
            self.run_explorer(output, len(legacy) + 1)
            manifest = json.loads((output / 'run.json').read_text())
            self.assertEqual(manifest['search_version'], SEARCH_VERSION)
            migrated = [json.loads(line) for line in (output / 'trials.jsonl').read_text().splitlines()]
            self.assertEqual(len(migrated), len(legacy) + 1)
            self.assertTrue(all('descriptor' in r for r in migrated))
            (output / 'run.json').write_text(json.dumps({**manifest, 'seed': 8}))
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_explorer(output, len(legacy) + 2)

    def test_sigterm_publishes_a_resumable_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            process = subprocess.Popen([sys.executable, '-m', 'soundgarden.explore', '--output', tmp, '--minutes', '1', '--pause-ms', '100', '--battery-min', '0'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    journal = output / 'trials.jsonl'
                    if journal.exists() and len(journal.read_text().splitlines()) >= 2:
                        break
                    if process.poll() is not None:
                        self.fail(process.communicate()[1].decode())
                    time.sleep(.025)
                else:
                    self.fail('Runner did not checkpoint within ten seconds')
                process.terminate()
                _, errors = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, errors.decode())
                library = json.loads((output / 'seeds.json').read_text())
                self.assertGreaterEqual(library['trials'], 2)
                self.assertGreater(len(library['seeds']), 0)
                self.run_explorer(output, library['trials'] + 2)
                resumed = json.loads((output / 'seeds.json').read_text())
                self.assertEqual(resumed['trials'], library['trials'] + 2)
            finally:
                if process.poll() is None:
                    process.kill(); process.communicate()


if __name__ == '__main__':
    unittest.main()
