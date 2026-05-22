"""Тесты нечёткого распознавания wake word."""

from __future__ import annotations

import pytest

from jarvis.voice.wake_word import _fuzzy_find_wake_word


WAKE_WORDS = ["джарвис", "jarvis"]


@pytest.mark.parametrize(
    "text",
    [
        "Джарвис, сколько время",
        "джарис сколько время",
        "жарвис открой телеграм",
        "Джарвіс привет",
        "д жарвис что делаешь",
        "джарвес скажи",
        "джарвас помоги",
        "jarvis open chrome",
        "Jarvis, hello",
    ],
)
def test_fuzzy_wake_word_matches(text: str) -> None:
    result = _fuzzy_find_wake_word(text, WAKE_WORDS)
    assert result is not None, f"Wake word не найден в: {text!r}"
    matched, remaining = result
    assert len(remaining) > 0 or text.lower().strip() in WAKE_WORDS


@pytest.mark.parametrize(
    "text",
    [
        "сколько времени",
        "открой телеграм",
        "привет как дела",
        "",
    ],
)
def test_fuzzy_wake_word_no_false_positive(text: str) -> None:
    result = _fuzzy_find_wake_word(text, WAKE_WORDS)
    assert result is None, f"Ложное срабатывание на: {text!r}"


def test_fuzzy_remaining_text() -> None:
    result = _fuzzy_find_wake_word("джарвис сколько время", WAKE_WORDS)
    assert result is not None
    _, remaining = result
    assert "сколько" in remaining
    assert "время" in remaining
