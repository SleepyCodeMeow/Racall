"""Keep generated EN/RU prose separate from the language of retrieved sources.

This deliberately small policy is not a general language detector. Grammatical
words provide a useful signal without treating a foreign proper name, acronym,
number, or quoted passage as a request to switch languages.
"""

from __future__ import annotations

import re
from typing import Literal

AnswerLanguage = Literal["en", "ru"]

_WORDS = re.compile(r"[A-Za-zА-Яа-яЁё]+")
_EMBEDDED_DATA = re.compile(
    r"```[\s\S]*?```|`[^`\n]*`|https?://\S+|"
    r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»|‘[^’\n]*’'
)
_CUES = {
    "en": frozenset(
        """
        a an the this that these those it its they their there
        is are was were be been has have had do does did
        will would can could should must not no already yet
        of to for from about and or with without in on at by as
        what when where who whose why how which
        tell explain compare summarize summarise describe list show give find
    """.split()
    ),
    "ru": frozenset(
        """
        это этот эта эти того этой те он она они его её их
        есть был была были будет будут бы ли не нет ещё уже
        в во на у из о об про по и или с со для без от до к ко
        что когда где кто почему как какой какая какие какого сколько чей чья
        чем чего кому зачем
        расскажи объясни сравни опиши перечисли покажи найди
    """.split()
    ),
}
_DIRECTIVE = re.compile(
    r"\b(?:answer|respond|reply|write)\s+(?:only\s+)?in\s+(english|russian)\b|"
    r"\b(?:ответь|отвечай|напиши|пиши)\s+(?:пожалуйста\s+)?"
    r"(?:на\s+)?(английском|русском|по-английски|по-русски)\b",
    re.IGNORECASE,
)


def _prose(text: str) -> str:
    return _EMBEDDED_DATA.sub(" ", text)


def _scores(text: str) -> dict[str, int]:
    # Case does not determine language, but an all-capital acronym or a
    # title-cased name in the middle of a sentence is not a grammatical cue.
    words = _WORDS.findall(text)
    eligible = {
        word.casefold()
        for index, word in enumerate(words)
        if not word.isupper() and (not word.istitle() or index == 0)
    }
    return {language: len(eligible & cues) for language, cues in _CUES.items()}


def question_language(question: str) -> AnswerLanguage:
    """Choose the requested prose language, defaulting ambiguous queries to EN.

    Only the question is examined, never source passages or UI preferences.
    Explicit language requests win; otherwise grammatical cues outweigh names.
    """
    prose = _prose(question)
    directives = list(_DIRECTIVE.finditer(prose))
    if directives:
        value = next(group for group in directives[-1].groups() if group).casefold()
        return "ru" if value in ("russian", "русском", "по-русски") else "en"
    # An entire uppercase question is emphasis, not a sequence of acronyms.
    # Normalize only for grammar scoring: preserving the original text below
    # keeps ambiguous uppercase names from becoming Russian noun phrases.
    scores = _scores(prose.casefold() if prose.isupper() else prose)
    if scores["ru"] > scores["en"]:
        return "ru"
    if scores["en"]:
        return "en"
    # A terse Russian query may contain only nouns, e.g. "Дата запуска
    # Marigold?". Several lowercase Cyrillic words signal prose; a bare
    # "Лис" or "Алина Морозова" stays ambiguous and uses the EN default.
    words = _WORDS.findall(prose)
    russian_prose = [word for word in words if re.fullmatch(r"[а-яё]+", word)]
    if russian_prose and words and re.fullmatch(r"[А-ЯЁ][а-яё]+", words[0]):
        russian_prose.append(words[0])
    return "ru" if len(russian_prose) >= 2 else "en"


def language_instruction(language: AnswerLanguage) -> str:
    """Instruction for generated prose; source quotations remain verbatim."""
    name = "Russian (русский)" if language == "ru" else "English"
    return (
        f"The required answer language is {name}. Write every claim text and uncertainty message "
        f"in {name}, even when evidence is in another language. Preserve proper names, code, "
        "evidence IDs, and verbatim quotations; these do not change the answer language. "
        "Do not copy a source sentence as your answer without translating its prose when needed."
    )


def language_mismatch(text: str, expected: AnswerLanguage) -> bool:
    """Flag clearly opposite EN/RU prose, not merely foreign characters.

    This is a conservative repair signal, not proof that a sentence is in the
    requested language. Very short or ambiguous text is deliberately accepted.
    Call it on generated claim/message text, never evidence or full JSON data.
    """
    scores = _scores(_prose(text))
    other = "ru" if expected == "en" else "en"
    return scores[other] >= 2 and scores[other] > scores[expected] + 1
