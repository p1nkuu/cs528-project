#!/usr/bin/env python3
"""
Gesture Game Server
Receives gesture predictions from the ML classifier and forwards them to the browser game via SSE.
Run this alongside your main.py (update UI_SERVER_URL = "http://localhost:8000/predict")
"""

from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import queue
import os

gesture_queue = queue.Queue(maxsize=50)
clients = []
clients_lock = threading.Lock()

GAME_HTML_PATH = os.path.join(os.path.dirname(__file__), "game.html")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        if self.path == "/" or self.path == "/game":
            self._serve_game()
        elif self.path == "/events":
            self._sse_stream()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/predict":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                action = data.get("action", "").strip().lower()
                print(f"[DEBUG] Raw body: {body}")
                print(f"[DEBUG] Parsed action: '{action}'")
                print(f"[DEBUG] Active SSE clients: {len(clients)}")
                if action:
                    print(f"  → Gesture received: {action}")
                    # Broadcast to all SSE clients
                    with clients_lock:
                        dead = []
                        msg = f"data: {json.dumps({'action': action})}\n\n"
                        for q in clients:
                            try:
                                q.put_nowait(msg)
                            except queue.Full:
                                dead.append(q)
                        for q in dead:
                            clients.remove(q)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "bad request"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_game(self):
        try:
            with open(GAME_HTML_PATH, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Game HTML not found. Make sure beat_saber_game.html is in the same directory.")

    def _sse_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._cors_headers()
        self.end_headers()

        q = queue.Queue(maxsize=50)
        with clients_lock:
            clients.append(q)

        try:
            # Send initial ping
            self.wfile.write(b"data: {\"action\": \"ping\"}\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    self.wfile.write(msg.encode())
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with clients_lock:
                if q in clients:
                    clients.remove(q)


if __name__ == "__main__":
    port = 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"╔══════════════════════════════════════╗")
    print(f"║   Gesture Game Server running!       ║")
    print(f"║   Game:    http://localhost:{port}/      ║")
    print(f"║   Predict: POST /predict             ║")
    print(f"╚══════════════════════════════════════╝")
    print(f"\nWaiting for gestures from your classifier...")
    print(f"Make sure main.py has: UI_SERVER_URL = 'http://localhost:{port}/predict'\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")