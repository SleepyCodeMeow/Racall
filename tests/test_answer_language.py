import pytest
from on_knowledge.answer_language import language_instruction, language_mismatch, question_language


@pytest.mark.parametrize(("question", "expected"), [
    ("What exact temperatures has the Лис station already measured?", "en"),
    ("Who leads the Алина Морозова project?", "en"),
    ("Compare Marigold and the Лис station schedules.", "en"),
    ("Когда запустят Marigold?", "ru"),
    ("КОГДА ЗАПУСК MARIGOLD?", "ru"),
    ("WHO LEADS THE ЛИС STATION?", "en"),
    ("Кто руководит Marigold?", "ru"),
    ("Какие точные температуры уже измерила станция Лис?", "ru"),
    ("Дата запуска Marigold?", "ru"),
    ("Лис", "en"),
    ("Алина Морозова", "en"),
    ("АЛИНА МОРОЗОВА", "en"),
    ("ЛИС", "en"),
    ("Mira Chen", "en"),
    ("12 USD / RTX 3080", "en"),
    ("Что обозначает `the when and how`?", "ru"),
    ('What does "что когда где и как" mean?', "en"),
    ("Что означает «What when where and how»?", "ru"),
    ("What is the launch date? Answer in Russian.", "ru"),
    ("Когда запуск? Ответь на английском.", "en"),
    ('What does "Answer in Russian" mean?', "en"),
])
def test_question_language_follows_prose_not_names_or_embedded_data(question, expected):
    assert question_language(question) == expected


@pytest.mark.parametrize("text", [
    "Фактические результаты работы ещё не получены.",
    "Никаких фактических научных результатов или измеренных температур не сообщалось.",
])
def test_recorded_russian_abstentions_mismatch_english_question(text):
    assert language_mismatch(text, "en")
    assert not language_mismatch(text, "ru")


@pytest.mark.parametrize(("text", "expected"), [
    ("The Лис station has not reported any measured temperatures.", "en"),
    ("Станция Marigold ещё не начала работу.", "ru"),
    ("Алина Морозова", "en"),
    ("Mira Chen", "ru"),
    ("USD 120,000 / 40 kW / 2030-11-12 / RTX 3080", "ru"),
    ("The Who", "ru"),
    ('The source says "Фактические результаты работы ещё не получены".', "en"),
    ("В источнике указано: «The mission has not launched yet».", "ru"),
    ("`what is the date`", "ru"),
])
def test_names_numbers_code_and_verbatim_quotes_are_not_language_failures(text, expected):
    assert not language_mismatch(text, expected)


def test_opposite_english_prose_is_detected_in_russian_answer():
    assert language_mismatch("The mission has not launched yet.", "ru")


def test_explicit_instructions_preserve_evidence_and_names():
    for language, name in [("en", "English"), ("ru", "Russian (русский)")]:
        instruction = language_instruction(language)
        assert name in instruction
        assert "every claim text and uncertainty message" in instruction
        assert "evidence IDs, and verbatim quotations" in instruction
