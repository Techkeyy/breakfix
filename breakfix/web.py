from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


def _load_runs(evidence_root: Path) -> list[dict]:
    runs = []
    if not evidence_root.is_dir():
        return runs
    for path in evidence_root.iterdir():
        if not path.is_dir():
            continue
        summary = path / "analysis.json"
        smoke = path / "smoke-summary.json"
        final = path / "final-summary.json"
        canonical = path / "canonical-demo-result.json"
        if summary.is_file():
            payload = json.loads(summary.read_text(encoding="utf-8"))
            payload["run_id"] = path.name
            runs.append(payload)
        elif smoke.is_file():
            payload = json.loads(smoke.read_text(encoding="utf-8"))
            payload["run_id"] = path.name
            runs.append(payload)
        elif final.is_file():
            payload = json.loads(final.read_text(encoding="utf-8"))
            payload["run_id"] = path.name
            payload["outcome"] = payload.get("primary_gate")
            payload["purpose"] = "Final independent evaluation"
            runs.append(payload)
        elif canonical.is_file():
            payload = json.loads(canonical.read_text(encoding="utf-8"))
            payload["run_id"] = path.name
            payload["outcome"] = (payload.get("verification") or {}).get("status")
            payload["purpose"] = "Canonical end-to-end demo"
            runs.append(payload)
    return sorted(runs, key=lambda item: item.get("run_id", ""), reverse=True)


def _index_html(runs: list[dict]) -> str:
    cards = []
    for run in runs:
        outcome = run.get("outcome") or ("PASS" if run.get("passed") else "FAIL")
        selected = run.get("selected_experiments", [])
        if not selected and isinstance(run.get("cases"), list):
            selected = [f"{case.get('case_id')}: {', '.join(case.get('selected_experiments', []))}" for case in run["cases"]]
        cards.append(
            "<article class='card'>"
            f"<div class='eyebrow'>{html.escape(run.get('run_id', 'run'))}</div>"
            f"<h2>{html.escape(str(outcome))}</h2>"
            f"<p>{html.escape(str(run.get('task', run.get('purpose', 'BreakFix analysis'))))}</p>"
            f"<div class='chips'>{''.join('<span>' + html.escape(str(item)) + '</span>' for item in selected) or '<span>No experiments selected</span>'}</div>"
            "</article>"
        )
    if not cards:
        cards.append("<div class='empty'>Run <code>breakfix analyze &lt;project&gt;</code> to see evidence here.</div>")
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BreakFix evidence</title><style>
:root{color-scheme:dark;font-family:Inter,ui-sans-serif,system-ui,sans-serif;background:#0d1117;color:#e6edf3}
body{margin:0;background:radial-gradient(circle at 15% 0,#1b2a3e 0,transparent 35%),#0d1117;min-height:100vh}
main{max-width:1050px;margin:0 auto;padding:48px 24px}.brand{letter-spacing:.16em;text-transform:uppercase;color:#7ee787;font-size:12px;font-weight:700}
h1{font-size:clamp(34px,6vw,64px);line-height:1;margin:14px 0 12px;max-width:700px} .lede{color:#9da7b3;max-width:650px;font-size:17px;line-height:1.6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-top:34px}.card,.empty{border:1px solid #263242;border-radius:16px;background:#111923;padding:22px;box-shadow:0 12px 34px #0003}
.eyebrow{color:#8b949e;font:12px ui-monospace,SFMono-Regular,monospace;overflow-wrap:anywhere}.card h2{margin:12px 0 8px;color:#7ee787;font-size:25px}.card p{color:#b7c1cc;line-height:1.5;min-height:48px}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chips span{border:1px solid #35506a;border-radius:999px;padding:6px 9px;color:#a5d6ff;font-size:12px}.empty{color:#9da7b3;margin-top:34px}
code{color:#a5d6ff}</style></head><body><main>
<div class="brand">BreakFix / proof over guesses</div><h1>Change-aware failure proof.</h1>
<p class="lede">Review selected changes, ranked assumptions, targeted executions, and reproducible evidence. The model proposes probes; deterministic execution decides the outcome.</p>
<section class="grid">""" + "".join(cards) + """</section></main></body></html>"""


def serve(host: str, port: int, evidence_root: Path) -> None:
    evidence_root = evidence_root.resolve()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            runs = _load_runs(evidence_root)
            if parsed.path == "/":
                self._send(200, "text/html; charset=utf-8", _index_html(runs).encode("utf-8"))
            elif parsed.path == "/api/runs":
                self._send(200, "application/json", json.dumps(runs).encode("utf-8"))
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found")

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"BreakFix UI: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
