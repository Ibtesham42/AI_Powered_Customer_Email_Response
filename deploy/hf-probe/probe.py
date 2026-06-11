"""Mail-egress probe for Hugging Face Spaces (stdlib only).

Answers ONE question: can this container open outbound IMAP/SMTP connections
to Gmail? It never logs in and needs no credentials — a TLS handshake plus the
server greeting proves the network path end to end.

Serves results as JSON over HTTP (Spaces must serve HTTP to stay "Running");
every GET re-runs the probe live.

Verdict rule:
  PASS  -> imap.gmail.com:993 AND smtp.gmail.com:465 both reachable
           (the app uses exactly these: IMAP4_SSL + SMTP_SSL:465)
  FAIL  -> either is blocked. smtp:587 is probed too, for diagnosis only —
           the app does not use STARTTLS, so 587-only is still a FAIL.
"""

import json
import socket
import ssl
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 7860  # Spaces default app port

TARGETS = [
    ("imap.gmail.com", 993, "imap-ssl", True),  # required
    ("smtp.gmail.com", 465, "smtp-ssl", True),  # required
    ("smtp.gmail.com", 587, "smtp-starttls-greeting", False),  # diagnostic
]


def check(host: str, port: int, kind: str, timeout: float = 10.0) -> dict:
    result = {"target": f"{host}:{port}", "kind": kind, "ok": False}
    started = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            if kind.endswith("ssl"):
                ctx = ssl.create_default_context()
                with ctx.wrap_socket(sock, server_hostname=host) as tls:
                    greeting = tls.recv(256).decode(errors="replace").strip()
            else:
                # 587 talks plaintext first (STARTTLS later) — the greeting
                # alone proves reachability.
                greeting = sock.recv(256).decode(errors="replace").strip()
        result["ok"] = True
        result["greeting"] = greeting[:120]
    except Exception as exc:  # noqa: BLE001 - report every failure mode
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["seconds"] = round(time.time() - started, 2)
    return result


def run_probe() -> dict:
    results = [check(h, p, k) for h, p, k, _required in TARGETS]
    required_ok = all(
        r["ok"]
        for r, (_h, _p, _k, required) in zip(results, TARGETS, strict=True)
        if required
    )
    return {
        "verdict": "PASS" if required_ok else "FAIL",
        "meaning": (
            "Outbound IMAP(993)+SMTP(465) work — the zero-budget HF Space "
            "plan is viable."
            if required_ok
            else "Mail egress is blocked — use the fallback plan "
            "(own PC + Cloudflare Tunnel). See docs/runbooks/zero-budget-pilot.md."
        ),
        "checks": results,
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib API name
        body = json.dumps(run_probe(), indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quieter logs
        pass


if __name__ == "__main__":
    # Run once at startup so the verdict also lands in the Space build logs.
    print(json.dumps(run_probe(), indent=2), flush=True)
    print(f"probe serving on :{PORT} — GET / re-runs it live", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
