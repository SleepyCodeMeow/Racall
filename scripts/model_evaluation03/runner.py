"""CLI gating and phase orchestration; no implicit model requests on import."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_fixture():
    cases = json.loads((ROOT / "evals/release03/cases.json").read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "evals/release02/cases.json").read_text(encoding="utf-8"))
    assert len(baseline) == 10 and len({case["id"] for case in baseline}) == 10
    assert len(list((ROOT / "evals/release02/sources").glob("*.md"))) == 4
    assert {case["kind"] for case in cases["jobs"]} == {
        "research",
        "summary",
        "study_guide",
        "review_questions",
    }
    for case in [*baseline, *cases["jobs"]]:
        assert case["question"]
        for pattern in case.get("patterns", []):
            re.compile(pattern)
    return cases, baseline


def manifest():
    files = {}
    roots = [
        ROOT / "apps/api/on_knowledge",
        ROOT / "scripts/model_evaluation03",
        ROOT / "evals/release02",
        ROOT / "evals/release03",
    ]
    for folder in roots:
        for file in sorted(folder.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                files[file.relative_to(ROOT).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    files["scripts/evaluate_release03.py"] = hashlib.sha256(
        (ROOT / "scripts/evaluate_release03.py").read_bytes()
    ).hexdigest()
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    return {
        "git_head": commit,
        "files": files,
        "manifest_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Explicitly permit live local model requests")
    parser.add_argument(
        "--model", help="Existing, owner-prepared Ollama alias; never downloaded/created here"
    )
    parser.add_argument(
        "--source-model", default="gemma4:12b", help="Also guard this original model tag against digest drift"
    )
    parser.add_argument(
        "--output", type=Path, help="New output directory; existing directories are never overwritten"
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/v1")
    parser.add_argument("--phase", choices=["core", "context", "studio", "lifecycle", "all"], default="core")
    parser.add_argument("--max-calls", type=int, default=80)
    parser.add_argument("--minutes", type=int, default=45)
    args = parser.parse_args(argv)
    cases, baseline = load_fixture()
    if not args.run:
        print(
            "Validated 10 baseline cases, 4 generation presets and context/lifecycle fixtures. No model or runtime requests made."
        )
        return 0
    if not args.model or not args.output:
        parser.error("--run requires explicit --model and --output")
    if not 1 <= args.max_calls <= 80 or not 1 <= args.minutes <= 45:
        parser.error("Limits must be within 1..80 calls and 1..45 minutes")
    from .guard import LiveGuard, local_endpoint, timestamp, write_json

    try:
        endpoint = local_endpoint(args.endpoint)
    except ValueError as error:
        parser.error(str(error))
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    # This process has no need to read or write the owner's OS credential store.
    os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"
    sys.path.insert(0, str(ROOT / "apps/api"))
    import keyring
    import keyring.backends.null

    keyring.set_keyring(keyring.backends.null.Keyring())
    from . import scenarios
    from .session import EvaluationSession

    guard = LiveGuard(args.output, endpoint, args.model, args.source_model, args.max_calls, args.minutes)
    environment = {
        "started_at": timestamp(),
        "phase": args.phase,
        "endpoint": endpoint,
        "model": guard.model,
        "source_model": guard.source_model,
        "max_calls": args.max_calls,
        "minutes": args.minutes,
        "source": manifest(),
        "review_rubric": cases["review_rubric"],
        "generation_parameters": "No thinking, temperature, token or alias options are overridden.",
        "model_management": "No create/pull/delete/unload API is used by this runner.",
    }
    write_json(args.output / "environment.json", environment)
    session = EvaluationSession(ROOT, args.output, guard, cases)
    status, error = "completed_contract_checks_manual_review_pending", None
    try:
        with guard.instrument():
            session.start()
            try:
                session.prepare()
                for phase in ("core", "context", "studio", "lifecycle"):
                    if args.phase in {phase, "all"}:
                        if phase == "core":
                            scenarios.core(session, baseline)
                        else:
                            getattr(scenarios, phase)(session)
                guard.wait_idle()
            finally:
                session.close()
    except BaseException as caught:
        status, error = "stopped_incomplete", f"{type(caught).__name__}: {caught}"
        print(error, file=sys.stderr, flush=True)
    finally:
        session.save(status=status, error=error)
        environment.update(
            finished_at=timestamp(),
            digests=guard.digests,
            completion_calls=len(guard.calls),
            status=status,
            error=error,
        )
        write_json(args.output / "environment.json", environment)
    print("Saved synthetic evidence to " + str(args.output), flush=True)
    print("Factual quality remains manual_pending; this runner does not approve publication.")
    return 0 if error is None else 1
