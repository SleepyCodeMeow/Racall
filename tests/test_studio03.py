import pytest
from on_knowledge.features.studio.generator import NoEvidence, UnverifiedMaterial, generate_material


class StudioProvider:
    def __init__(self, *, reject=False, block=None):
        self.calls = []
        self.reject = reject
        self.block = block

    def complete(self, system, data):
        self.calls.append((system, data))
        if "evidence critic" in system:
            return {"supported_claim_ids": [] if self.reject else [item["claim_id"] for item in data["claims"]]}
        if self.block:
            self.block()
        russian = data["answer_language"] == "ru"
        text = "Кодовое имя проекта — Marigold." if russian else "The project codename is Marigold."
        item = {"text": text, "evidence_ids": ["E1"]}
        if data["format"] == "study_guide":
            return {"sections": [{"title": "Проект" if russian else "Project", "items": [item]}]}
        if data["format"] == "review_questions":
            return {"questions": [{"question": "Как называется проект?" if russian else "What is the codename?",
                                    "answer": text, "evidence_ids": ["E1"]}]}
        return {"items": [item]}


@pytest.fixture
def evidence():
    return [{"id": "canonical-source-version-passage", "source_id": "source-id", "version": "v1",
             "title": "Project notes", "quote": "The project codename is Marigold.",
             "location": {"page": 2, "element": 0, "offset_start": 0, "offset_end": 33}}]


@pytest.mark.parametrize("kind", ["summary", "study_guide", "review_questions"])
@pytest.mark.parametrize("language", ["en", "ru"])
def test_three_formats_keep_canonical_citations_and_exact_quotes(monkeypatch, evidence, kind, language):
    provider = StudioProvider()
    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", lambda settings: provider)
    stages = []
    result = generate_material(kind, "", "Material", language, evidence, {}, lambda: None,
                               lambda stage, detail=None: stages.append(stage))
    answer = result["answer"]
    assert answer["validated"] is True
    assert answer["claims"][0]["evidence_ids"] == [evidence[0]["id"]]
    assert answer["citations"][0] == {**evidence[0], "number": 1}
    assert "> " + evidence[0]["quote"] in result["body"]
    assert "[1]" in result["body"]
    assert ("Источники" if language == "ru" else "Sources") in result["body"]
    assert ("стр. 2" if language == "ru" else "page 2") in result["body"]
    assert "offset_start" not in result["body"]
    assert stages == ["writer", "critic"] and len(provider.calls) == 2
    if kind == "study_guide":
        assert provider.calls[1][1]["claims"][0]["text"].startswith("Проект\n" if language == "ru" else "Project\n")
    if kind == "review_questions":
        assert "?\n" in provider.calls[1][1]["claims"][0]["text"]


def test_no_evidence_never_constructs_a_provider(monkeypatch):
    def forbidden(settings):
        pytest.fail("An empty selection must never invoke a provider")
    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", forbidden)
    with pytest.raises(NoEvidence):
        generate_material("summary", "", "Summary", "en", [], {}, lambda: None, lambda *args: None)


def test_rejected_claims_do_not_become_materials(monkeypatch, evidence):
    provider = StudioProvider(reject=True)
    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", lambda settings: provider)
    with pytest.raises(UnverifiedMaterial):
        generate_material("summary", "", "Summary", "en", evidence, {}, lambda: None, lambda *args: None)
    assert len(provider.calls) == 2  # A valid rejection is final, not another paid writer/critic loop.


def test_wrong_language_repair_is_bounded(monkeypatch, evidence):
    class EnglishOnly(StudioProvider):
        def complete(self, system, data):
            self.calls.append((system, data))
            return {"items": [{"text": "The project is the one with the codename Marigold.",
                               "evidence_ids": ["E1"]}]}
    provider = EnglishOnly()
    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", lambda settings: provider)
    with pytest.raises(UnverifiedMaterial):
        generate_material("summary", "", "Summary", "ru", evidence, {}, lambda: None, lambda *args: None)
    assert len(provider.calls) == 2


def test_unknown_evidence_labels_never_reach_critic(monkeypatch, evidence):
    class InventedCitation(StudioProvider):
        def complete(self, system, data):
            self.calls.append((system, data))
            return {"items": [{"text": "Invented", "evidence_ids": ["E999"]}]}
    provider = InventedCitation()
    monkeypatch.setattr("on_knowledge.features.studio.generator.completion_provider", lambda settings: provider)
    with pytest.raises(UnverifiedMaterial):
        generate_material("summary", "", "Summary", "en", evidence, {}, lambda: None, lambda *args: None)
    assert len(provider.calls) == 1
