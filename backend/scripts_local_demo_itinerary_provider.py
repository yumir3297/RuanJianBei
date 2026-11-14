"""Synthetic localhost-only provider for isolated itinerary demos; not an AI model."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if os.environ.get("DEMO_SYNTHETIC_CONFIRM") != "1":
    raise SystemExit("Set DEMO_SYNTHETIC_CONFIRM=1; use only an isolated demo database.")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 1024 * 1024:
                raise ValueError("invalid size")
            payload = json.loads(self.rfile.read(size))
            user = json.loads(payload["messages"][-1]["content"])
            if user.get("request") in ("演示：增加十分钟休息", "演示：行程增加十分钟休息"):
                result = {"result": "operations", "operations": [{"type": "add_rest", "name": "演示休息", "duration_minutes": 10}]}
            else:
                result = {"result": "clarification", "question": "这是本地演示服务，请输入演示指令。"}
            response = json.dumps({"choices": [{"message": {"content": json.dumps(result, ensure_ascii=False)}}]}, ensure_ascii=False).encode()
        except (ValueError, KeyError, TypeError, IndexError):
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, _format, *_args):
        pass


if __name__ == "__main__":
    print("Synthetic itinerary provider listening on 127.0.0.1:18765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
