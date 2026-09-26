"""Opt-in evaluation of a configured provider using synthetic documents only."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run", action="store_true", help="Explicitly allow requests to the configured model"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Existing knowledge directory containing settings.json; user documents are not read",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixture = ROOT / "evals/release02"
    cases = json.loads((fixture / "cases.json").read_text(encoding="utf-8"))
    assert len({c["id"] for c in cases}) == len(cases)
    files = sorted((fixture / "sources").glob("*.md"))
    assert len(files) == 4
    for case in cases:
        assert case["question"] and (case.get("patterns") or case.get("unknown"))
        for pattern in case.get("patterns", []):
            re.compile(pattern)
    if not args.run:
        print(f"Validated {len(files)} synthetic sources and {len(cases)} questions. No model requests made.")
        return
    if not args.data_dir:
        parser.error("--run requires --data-dir pointing to configured Racall settings")
    settings = json.loads((args.data_dir / "settings.json").read_text(encoding="utf-8"))
    if not settings.get("model"):
        parser.error("Configure a model in Racall first")
    from on_knowledge.knowledge import Knowledge
    from on_knowledge.storage import Store, write_json

    output = args.output or ROOT / "test-results" / (
        "model-eval-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=False)
    store = Store(output / "isolated-knowledge")
    write_json(
        store.root / "settings.json",
        {k: settings[k] for k in ("base_url", "model", "embedding_model") if k in settings},
    )
    knowledge = Knowledge(store)
    notebook = store.create_notebook("Synthetic 0.2 evaluation")["id"]
    results = []
    try:
        for file in files:
            source = knowledge.sources.repository.stage(notebook, file.name, file.read_bytes())
            knowledge.ingest(notebook, source["id"])
            status = store.source(notebook, source["id"])
            if status["status"] != "ready":
                raise RuntimeError("Fixture import failed: " + status.get("error", "unknown"))
        for case in cases:
            print("Evaluating " + case["id"], flush=True)
            try:
                answer = knowledge.answer(notebook, case["question"])
                text = " ".join(c["text"] for c in answer["claims"])
                flags = []
                if any(not re.search(p, text, re.I) for p in case.get("patterns", [])):
                    flags.append("Expected fact pattern missing: manually inspect wording and completeness")
                if any(word.lower() in text.lower() for word in case.get("forbidden", [])):
                    flags.append("Forbidden injected answer text appeared")
                if len({c["source_id"] for c in answer["citations"]}) < case.get("min_sources", 0):
                    flags.append("Not all required sources were cited")
                if case.get("unknown"):
                    flags.append(
                        "Manual check: no invented sponsor, measurements or results; a cited statement of absence is allowed"
                    )
                results.append({**case, "answer": answer, "review_flags": flags, "human_verdict": "pending"})
            except Exception as error:
                results.append({**case, "error": str(error), "human_verdict": "pending"})
            write_json(
                output / "results.json",
                {"model": settings["model"], "provider": settings["base_url"], "results": results},
            )
    finally:
        knowledge.executor.shutdown(wait=True)
    print("Saved reviewable results to " + str(output / "results.json"))
    print("Human review is required; string checks do not establish answer quality.")


if __name__ == "__main__":
    main()
