from __future__ import annotations

from whisper_dictate.scoring import normalize, score


def test_normalize_lowercases_text():
    words = normalize("Hello World")
    assert words == ["hello", "world"]


def test_normalize_strips_punctuation():
    words = normalize("Hello, World!")
    assert words == ["hello", "world"]


def test_normalize_preserves_umlauts():
    # Umlauts are case-folded (ä→ä, ö→ö, ü→ü, Ü→ü) not stripped.
    # ß casefolds to "ss" per Unicode standard; both sides normalized consistently.
    words = normalize("Schäfte Straße")
    assert words == ["schäfte", "strasse"]


def test_score_perfect_match_returns_wer_zero():
    result = score("Hello world", "Hello world")
    assert result.wer == 0.0


def test_score_one_substitution_german_confusable():
    # "schaute" misheard as "scharrte" — one substitution out of one reference word.
    result = score("schaute", "scharrte")
    assert result.wer == 1.0


def test_score_one_substitution_english_confusable():
    # "shard" misheard as "chart" — one substitution out of one reference word.
    result = score("shard", "chart")
    assert result.wer == 1.0


def test_score_counts_insertions():
    # Hypothesis has two extra words; reference has one word; WER = 2/1 = 2.0.
    result = score("hello", "hello extra word")
    assert result.wer == 2.0


def test_score_counts_deletions():
    # One word deleted from a two-word reference; WER = 1/2 = 0.5.
    result = score("hello world", "hello")
    assert result.wer == 0.5


