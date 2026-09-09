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

from .explore import diverse, restore
from .server import Handler, ThreadingHTTPServer
from .synth import ANCHORS, DEFAULT, SR, VERSION, features, measure, render, validate_vector, wav_bytes


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
        candidates = [{'metrics':measure(render(v)), 'vector':v} for _,v in ANCHORS]
        selected = diverse(candidates, 3)
        self.assertEqual(len(selected), 3)
        self.assertEqual(len({tuple(c['vector']) for c in selected}), 3)

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
