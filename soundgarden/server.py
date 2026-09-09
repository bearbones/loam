"""Loopback-only server. Run from the Loam root: python3 -m soundgarden.server."""
import argparse
from functools import lru_cache
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlsplit

from .synth import ANCHORS, DIMENSIONS, VERSION, encoded_sample, measure, render, validate_vector

WEB = Path(__file__).parent / "web"
DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "render/soundgarden/seeds.json"
RENDER_LOCK = threading.Lock()


@lru_cache(maxsize=128)
def sample(vector, midi):
    return encoded_sample(vector, midi)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body, kind="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if self.headers.get("Host") not in allowed:
            self.reply(403, {"error": "Use this app through its localhost address."})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{host}" for host in allowed}:
            self.reply(403, {"error": "Only the local Soundgarden page can render samples."})
            return False
        return True

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == "/api/library":
            seeds = [{"name": name, "vector": vector, "source": "Starter"} for name, vector in ANCHORS]
            warning = None
            try:
                if self.server.library.exists():
                    data = json.loads(self.server.library.read_text())
                    if data["version"] != VERSION:
                        raise ValueError("Library uses a different synthesis version.")
                    for seed in data["seeds"]:
                        validate_vector(seed["vector"])
                    seeds.extend(data["seeds"])
            except (OSError, ValueError, KeyError, TypeError):
                warning = "The generated library could not be loaded. Starter sounds are available."
            self.reply(200, {"version": VERSION, "dimensions": DIMENSIONS, "seeds": seeds, "warning": warning})
            return
        files = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/app.js": ("app.js", "text/javascript"),
                 "/space.js": ("space.js", "text/javascript"),
                 "/style.css": ("style.css", "text/css")}
        if path not in files:
            self.reply(404, {"error": "Not found"})
            return
        name, kind = files[path]
        self.reply(200, (WEB / name).read_bytes(), kind)

    def do_POST(self):
        if not self.local_request():
            return
        if self.path != "/api/render":
            self.reply(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384:
                raise ValueError("Render request is too large or empty.")
            data = json.loads(self.rfile.read(size))
            vector = tuple(validate_vector(data["vector"]).tolist())
            notes = data["notes"]
            if not isinstance(notes, list) or not 1 <= len(notes) <= 13:
                raise ValueError("Render between 1 and 13 notes.")
            if any(type(note) is not int or not 48 <= note <= 84 for note in notes):
                raise ValueError("Notes must be MIDI integers between 48 and 84.")
            with RENDER_LOCK:
                samples = {str(note): sample(vector, note) for note in set(notes)}
                metrics = measure(render(vector, 60))
            self.reply(200, {"samples": samples, "metrics": metrics, "version": VERSION})
        except (ValueError, KeyError, TypeError) as error:
            self.reply(400, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.library = args.library
    print(f"Soundgarden: http://127.0.0.1:{server.server_port} — Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
