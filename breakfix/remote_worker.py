"""Container entrypoint for the hosted BreakFix deployment.

This module deliberately delegates all product decisions to the existing
BreakFix services.  The surrounding API only supplies a checked-out public
project and persists the resulting evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .diffing import make_diff
from .evidence import write_json
from .fixes import apply_fix, propose_fix, verify_fix
from .git_project import ChangeSnapshot, load_change
from .product import analyze_change


def _canonical_snapshot(project: Path, task: str | None) -> ChangeSnapshot:
    sample = project / "examples" / "independent_sample"
    before = sample / "before" / "app.py"
    after = sample / "after"
    if not before.is_file() or not (after / "app.py").is_file():
        raise RuntimeError("canonical demo files are missing from the checked-out repository")
    return ChangeSnapshot(
        project_root=after,
        change_kind="independent-acceptance-sample",
        reference="examples/independent_sample",
        diff=make_diff(before, after / "app.py"),
        changed_files=("app.py",),
        task=task or "Add a mean to the summary while preserving safe behavior.",
        test_command="python -m unittest discover -s tests -v",
    )


def _snapshot(project: Path, request: dict) -> ChangeSnapshot:
    if request.get("demo"):
        return _canonical_snapshot(project, request.get("task"))
    change = request.get("change") or {}
    return load_change(
        project,
        task=request.get("task"),
        test_command=request.get("test_command"),
        change_kind=change.get("kind", "commit"),
        reference=change.get("reference"),
    )


def _write_result(evidence: Path, payload: dict) -> None:
    write_json(evidence / "worker-result.json", payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="breakfix-remote-worker")
    parser.add_argument("--mode", choices=("analyze", "propose-fix", "apply-fix", "verify-fix"), required=True)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args(argv)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)

    try:
        if args.mode == "analyze":
            if args.project is None or args.request is None:
                raise RuntimeError("analyze requires --project and --request")
            request = json.loads(args.request.read_text(encoding="utf-8"))
            snapshot = _snapshot(args.project.resolve(), request)
            result = analyze_change(snapshot, evidence)
            _write_result(evidence, {"ok": True, "mode": args.mode, "analysis": result.as_dict()})
            return 0
        if args.mode == "propose-fix":
            result = propose_fix(evidence)
        elif args.mode == "apply-fix":
            result = apply_fix(evidence, approved=True)
        else:
            result = verify_fix(evidence)
        _write_result(evidence, {"ok": True, "mode": args.mode, "result": result})
        return 0
    except Exception as exc:  # the API records this as an explicit job error
        _write_result(evidence, {"ok": False, "mode": args.mode, "error_code": type(exc).__name__, "error": str(exc)[:1000]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
