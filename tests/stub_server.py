from __future__ import annotations
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        stub = self.server.stub
        stub.calls += 1
        status, body = stub.next_response()
        payload = (json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list))
                   else str(body)).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args) -> None:#屏蔽噪音
        return


class StubServer:
    def __init__(self) -> None:
        self.calls = 0
        self._responses: list[tuple[int, object]] = []
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._httpd.stub = self
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> "StubServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def base_url(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}/chat/completions"

    def enqueue(self, status: int, body: object) -> None:
        self._responses.append((status, body))

    def next_response(self) -> tuple[int, object]:
        if self._responses:
            return self._responses.pop(0)
        return 200, {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    def __enter__(self) -> "StubServer":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
