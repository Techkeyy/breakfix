from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .git_project import load_change
from .product import analyze_change, reproduce
from .provider import DirectProvider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="breakfix",
        description="Find and prove change-induced failures with bounded targeted experiments.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="check local project and provider prerequisites")
    doctor.add_argument("project", nargs="?", type=Path, default=Path.cwd())

    analyze = commands.add_parser("analyze", help="analyze one selected Git change")
    analyze.add_argument("project", type=Path)
    analyze.add_argument("--task", default=None)
    analyze.add_argument("--test-command", default=None)
    analyze.add_argument("--change-kind", choices=("working-tree", "commit", "range", "branch"), default="working-tree")
    analyze.add_argument("--reference", default=None)
    analyze.add_argument("--output-dir", type=Path, default=None)
    analyze.add_argument("--max-experiments", type=int, default=3)

    replay = commands.add_parser("reproduce", help="replay a confirmed break from saved evidence")
    replay.add_argument("evidence", type=Path)

    reduce = commands.add_parser("reduce", help="attempt a bounded reduced reproduction")
    reduce.add_argument("evidence", type=Path)

    propose = commands.add_parser("propose-fix", help="propose a reviewed candidate patch")
    propose.add_argument("evidence", type=Path)

    apply = commands.add_parser("apply-fix", help="apply a reviewed patch to an evidence snapshot")
    apply.add_argument("evidence", type=Path)
    apply.add_argument("--approved", action="store_true", help="record explicit human approval")

    verify = commands.add_parser("verify-fix", help="verify an approved patch")
    verify.add_argument("evidence", type=Path)

    serve = commands.add_parser("serve", help="serve the local evidence review interface")
    serve.add_argument("--evidence-dir", type=Path, default=Path.cwd() / "evidence")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _doctor(project: Path) -> int:
    checks = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "git": shutil.which("git") is not None,
        "project_exists": project.exists(),
        "git_repository": False,
        "provider": "not configured",
        "BREAKFIX_PROVIDER": "PRESENT" if os.environ.get("BREAKFIX_PROVIDER") else "UNSET",
        "BREAKFIX_DEEPSEEK_API_KEY": "PRESENT" if os.environ.get("BREAKFIX_DEEPSEEK_API_KEY") else "UNSET",
        "BREAKFIX_MODEL": "PRESENT" if os.environ.get("BREAKFIX_MODEL") else "UNSET",
        "BREAKFIX_REASONING_EFFORT": "PRESENT" if os.environ.get("BREAKFIX_REASONING_EFFORT") else "UNSET",
    }
    try:
        provider = DirectProvider()
        checks["provider"] = provider.provider
        checks["provider_credential"] = "PRESENT" if provider.api_key else "UNSET"
    except Exception as exc:
        checks["provider"] = f"error: {type(exc).__name__}"
    try:
        load_change(project)
        checks["git_repository"] = True
    except Exception:
        checks["git_repository"] = False
    print(json.dumps(checks, indent=2))
    return 0 if checks["project_exists"] and checks["git_repository"] and checks["git"] else 1


def _analyze(args: argparse.Namespace) -> int:
    snapshot = load_change(
        args.project,
        task=args.task,
        test_command=args.test_command,
        change_kind=args.change_kind,
        reference=args.reference,
    )
    run_id = "analysis-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or (snapshot.project_root / "evidence" / run_id)
    result = analyze_change(snapshot, output, max_experiments=args.max_experiments)
    print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.outcome not in {"ERROR", "UNSUPPORTED"} else 2


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "doctor":
        return _doctor(args.project.resolve())
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "reproduce":
        print(json.dumps(reproduce(args.evidence), indent=2))
        return 0
    if args.command == "reduce":
        from .reducer import reduce_reproduction

        print(json.dumps(reduce_reproduction(args.evidence), indent=2))
        return 0
    if args.command == "propose-fix":
        from .fixes import propose_fix

        print(json.dumps(propose_fix(args.evidence), indent=2))
        return 0
    if args.command == "apply-fix":
        from .fixes import apply_fix

        print(json.dumps(apply_fix(args.evidence, approved=args.approved), indent=2))
        return 0
    if args.command == "verify-fix":
        from .fixes import verify_fix

        print(json.dumps(verify_fix(args.evidence), indent=2))
        return 0
    if args.command == "serve":
        from .web import serve

        serve(args.host, args.port, args.evidence_dir.resolve())
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
