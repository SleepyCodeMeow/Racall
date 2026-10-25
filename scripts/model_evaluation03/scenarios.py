"""Small synthetic scenarios, each using the production application API."""

from __future__ import annotations

import hashlib
from uuid import uuid4


def source_selection(session, names, note=None):
    return {
        "source_ids": [session.sources[name]["id"] for name in names],
        "note_ids": [note["id"]] if note else [],
    }


def core(session, baseline):
    for case in baseline:

        def run(case=case):
            answer = session.api(session.base + "/ask", "POST", {"question": case["question"]})
            return session.review(answer, case)

        session.run_case("core-" + case["id"], run)


def context(session):
    config = session.cases["context"]
    selection = source_selection(session, ["mission-en.md"])
    thread = session.chat("Source context and follow-up", selection)

    def initial():
        turn = session.turn(thread, config["initial"])
        assert turn["status"] == "completed" and turn["context_info"]["history_turns"] == 0
        session.historical = {"thread": thread, "turn": turn}
        return {
            "turn": turn,
            "review": session.review(
                turn["answer"], {"patterns": config["initial_patterns"]}, snapshot=turn["context_snapshot"]
            ),
        }

    session.run_case("context-source-initial", initial)

    def followup():
        turn = session.turn(thread, config["followup"])
        assert turn["status"] == "completed" and turn["context_info"]["history_turns"] == 1
        return {
            "turn": turn,
            "review": session.review(
                turn["answer"], {"patterns": config["followup_patterns"]}, snapshot=turn["context_snapshot"]
            ),
        }

    session.run_case("context-source-followup", followup)

    def exclusion():
        before = len(session.guard.calls)
        empty = session.chat("Explicitly empty context", {"source_ids": [], "note_ids": []})
        empty_turn = session.turn(empty, "When will Marigold launch?")
        assert not empty_turn["answer"]["validated"] and empty_turn["context_info"]["history_turns"] == 0
        station = source_selection(session, ["station-ru.md"])
        session.api(session.base + f"/chats/{thread['id']}/context", "PUT", station)
        changed = session.turn(thread, "When will Marigold launch?")
        assert changed["context_info"]["history_turns"] == 0 and changed["context_info"]["history_truncated"]
        assert not changed["answer"]["validated"], "Excluded mission leaked into station-only context"
        foreign = session.api("/notebooks", "POST", {"title": "Isolation boundary"})
        response = session.client.put(
            f"/api/notebooks/{foreign['id']}/chats/{empty['id']}/context", json=selection
        )
        assert response.status_code in {400, 404}
        assert len(session.guard.calls) == before, "Empty/excluded context caused inference"
        return {
            "empty": empty_turn,
            "changed": changed,
            "cross_notebook_status": response.status_code,
            "zero_provider_calls": True,
        }

    session.run_case("context-empty-excluded-isolated", exclusion)
    note_config = session.cases["note"]
    note = session.note(note_config["title"], note_config["revision1"])
    note_thread = session.chat("Saved note revisions", source_selection(session, [], note))

    def note_answer(note, expected):
        turn = session.turn(note_thread, note_config["question"])
        assert turn["status"] == "completed" and turn["context_info"]["note_count"] == 1
        assert turn["context_info"]["source_count"] == 0
        assert all(
            citation.get("kind") == "note" and citation["version"] == note["revision"]
            for citation in turn["answer"]["citations"]
        )
        return {
            "turn": turn,
            "review": session.review(
                turn["answer"], {"patterns": [expected]}, snapshot=turn["context_snapshot"]
            ),
        }

    first = {}

    def note_first():
        value = note_answer(note, note_config["expected_revision1"])
        first.update(value)
        return value

    session.run_case("context-note-revision1", note_first)
    note = session.note(note_config["title"], note_config["revision2"], previous=note)
    session.current_note = note
    session.run_case("context-note-revision2", lambda: note_answer(note, note_config["expected_revision2"]))

    def restored():
        before = len(session.guard.calls)
        previous = session.api(session.base + f"/chats/{note_thread['id']}")
        session.restart()
        reopened = session.api(session.base + f"/chats/{note_thread['id']}")
        assert reopened == previous and reopened["context"] == source_selection(session, [], note)
        assert reopened["turns"][0] == first["turn"]
        session.provenance(first["turn"]["answer"], first["turn"]["context_snapshot"])
        assert len(session.guard.calls) == before
        return {
            "selection": reopened["context"],
            "old_note_citation_preserved": True,
            "service_restart_without_inference": True,
        }

    session.run_case("context-restart-selection-history", restored)


def studio(session):
    note = getattr(session, "current_note", None)
    if note is None:
        note_config = session.cases["note"]
        note = session.note(note_config["title"], note_config["revision1"])
    completed = []
    for case in session.cases["jobs"]:

        def run(case=case):
            selection = source_selection(session, case["sources"], note if case.get("note") else None)
            queued = session.submit(case["kind"], case["question"], selection, case["language"])
            duplicate = session.api(
                session.base + "/jobs",
                "POST",
                {
                    "request_id": queued["request_id"],
                    "kind": case["kind"],
                    "question": case["question"],
                    "language": case["language"],
                    "context": selection,
                },
            )
            assert duplicate["id"] == queued["id"], "Duplicate submission started another job"
            job = session.terminal(queued)
            material = session.material(job)
            exported = session.api(session.base + f"/materials/{material['id']}/export", raw=True)
            assert exported.text == material["body"] and "text/markdown" in exported.headers["content-type"]
            filename = session.output / (case["id"] + ".md")
            filename.write_bytes(exported.content)
            for citation in material["answer"]["citations"]:
                quoted_lines = "\n".join("> " + line for line in citation["quote"].splitlines())
                assert citation["quote"] in material["body"] or quoted_lines in material["body"], (
                    "Export lost an unchanged source quotation"
                )
            completed.append(material)
            return {
                "job": job,
                "material": material,
                "export_sha256": hashlib.sha256(exported.content).hexdigest(),
                "review": session.review(material["answer"], case, snapshot=job["context"]),
            }

        session.run_case(case["id"], run)

    def retain():
        before = len(session.guard.calls)
        material = completed[-1]
        copied = session.api(session.base + f"/materials/{material['id']}/copy", "POST")
        assert copied["body"] == material["body"]
        edited = session.note(copied["title"], copied["body"] + "\n\nMy independent edit.", previous=copied)
        assert session.api(session.base + f"/materials/{material['id']}") == material
        session.restart()
        for item in completed:
            assert session.api(session.base + f"/materials/{item['id']}") == item
        assert len(session.guard.calls) == before
        return {
            "material_ids": [item["id"] for item in completed],
            "editable_copy": edited["id"],
            "originals_unchanged": True,
            "service_restart_without_replay": True,
        }

    session.run_case("materials-export-copy-reopen", retain)


def lifecycle(session):
    selection = source_selection(session, ["mission-en.md"])
    if not hasattr(session, "historical"):

        def initial():
            thread = session.chat("Historical launch date", selection)
            turn = session.turn(thread, "When is Marigold scheduled to launch?")
            assert turn["status"] == "completed"
            session.historical = {"thread": thread, "turn": turn}
            return {
                "turn": turn,
                "review": session.review(
                    turn["answer"],
                    {"patterns": ["October 18|18 October", "2030"]},
                    snapshot=turn["context_snapshot"],
                ),
            }

        session.run_case("lifecycle-historical-answer", initial)

    def cancelled():
        before = len(session.guard.calls)
        material_ids = {item["id"] for item in session.api(session.base + "/materials")}
        running = session.submit("summary", "The approved Marigold mission details.", selection)
        active_call = session.guard.wait_writer(before)
        queued = session.submit("study_guide", "The approved Marigold schedule and inventory.", selection)
        assert session.api(session.base + "/jobs/" + queued["id"])["status"] == "queued"
        session.guard.expected_interrupt = True
        try:
            assert session.api(session.base + f"/jobs/{queued['id']}/cancel", "POST")["status"] == "cancelled"
            assert (
                session.api(session.base + f"/jobs/{running['id']}/cancel", "POST")["status"] == "cancelled"
            )
            session.guard.wait_idle()
        finally:
            session.guard.expected_interrupt = False
        assert session.guard.calls[active_call - 1]["status"] == "cancelled", (
            "Did not interrupt an in-flight production completion"
        )
        assert {item["id"] for item in session.api(session.base + "/materials")} == material_ids
        assert len(session.guard.calls) == before + 1, (
            "Queued cancellation or cancelled writer advanced to another model phase"
        )
        return {
            "running": session.api(session.base + "/jobs/" + running["id"]),
            "queued": session.api(session.base + "/jobs/" + queued["id"]),
            "transport_call": active_call,
            "late_result_fenced": True,
            "provider_gpu_stop": "not claimed",
        }

    session.run_case("lifecycle-running-and-queued-cancel", cancelled)

    def interrupted():
        before = len(session.guard.calls)
        job = session.submit("summary", "The approved Marigold schedule, budget and sensors.", selection)
        active_call = session.guard.wait_writer(before)
        session.guard.expected_interrupt = True
        try:
            session.restart()
        finally:
            session.guard.expected_interrupt = False
        persisted = session.api(session.base + "/jobs/" + job["id"])
        assert persisted["status"] == "interrupted" and "result" not in persisted
        assert len(session.guard.calls) == before + 1, "Service restart replayed inference"
        assert session.guard.calls[active_call - 1]["status"] == "cancelled"
        session.interrupted = persisted
        return {"job": persisted, "transport_call": active_call, "restart_replay": False}

    session.run_case("lifecycle-running-restart-no-replay", interrupted)

    def replace_retry():
        source = session.sources["mission-en.md"]
        old_version = source["version"]
        previous_turn = session.historical["turn"]
        old_original = session.api(
            session.base + f"/sources/{source['id']}/versions/{old_version}/original", raw=True
        ).content
        replacement = session.root / "evals/release02/mission-en-revision2.md"
        response = session.client.put(
            "/api" + session.base + "/sources/" + source["id"],
            files={"file": (replacement.name, replacement.read_bytes(), "text/markdown")},
        )
        assert response.is_success, response.text
        current = session.wait(lambda: session.ready_source(source["id"]))
        assert current["version"] == hashlib.sha256(replacement.read_bytes()).hexdigest() != old_version
        session.sources["mission-en.md"] = current
        retry = session.api(
            session.base + f"/jobs/{session.interrupted['id']}/retry", "POST", {"request_id": str(uuid4())}
        )
        assert retry["id"] != session.interrupted["id"] and retry["retry_of"] == session.interrupted["id"]
        assert (
            retry["context"]["selection"] == selection
            and retry["context"]["sources"][0]["version"] == current["version"]
        )
        job = session.terminal(retry)
        material = session.material(job)
        assert all(citation["version"] == current["version"] for citation in material["answer"]["citations"])
        old_download = session.api(
            session.base + f"/sources/{source['id']}/versions/{old_version}/original", raw=True
        ).content
        assert old_download == old_original
        reopened = session.api(session.base + f"/chats/{session.historical['thread']['id']}")
        assert reopened["turns"][0] == previous_turn
        session.provenance(previous_turn["answer"], previous_turn["context_snapshot"])
        return {
            "job": job,
            "material": material,
            "old_source_sha256": hashlib.sha256(old_download).hexdigest(),
            "historical_turn_preserved": True,
            "review": session.review(
                material["answer"], {"patterns": ["November 22|22 November", "2030"]}, snapshot=job["context"]
            ),
        }

    session.run_case("lifecycle-source-v2-explicit-retry", replace_retry)

    def current_answer():
        thread = session.chat("Current launch date", selection)
        turn = session.turn(thread, "When is Marigold scheduled to launch according to the current plan?")
        assert turn["status"] == "completed"
        return {
            "turn": turn,
            "review": session.review(
                turn["answer"],
                {"patterns": ["November 22|22 November", "2030"], "forbidden": ["October 18"]},
                snapshot=turn["context_snapshot"],
            ),
        }

    session.run_case("lifecycle-current-v2-answer", current_answer)
