from __future__ import annotations

import difflib
import unicodedata
from dataclasses import dataclass, field


def normalize(text: str) -> list[str]:
    """Lowercase, strip punctuation tokens, split on whitespace.

    Preserves umlauts and ß (uses Unicode casefold, not ASCII lower).
    """
    casefolded = text.casefold()
    words: list[str] = []
    for token in casefolded.split():
        # Strip leading/trailing punctuation characters from each token
        cleaned = token.strip(".,!?;:\"'()-[]{}…–—")
        if cleaned:
            words.append(cleaned)
    return words


@dataclass
class ScoreResult:
    """Result of a WER scoring operation."""

    wer: float
    # Aligned opcodes from SequenceMatcher over normalized word lists.
    # Each entry: (tag, i1, i2, j1, j2) where tag is one of
    # 'equal', 'replace', 'delete', 'insert'.
    opcodes: list[tuple[str, int, int, int, int]] = field(default_factory=list)
    ref_words: list[str] = field(default_factory=list)
    hyp_words: list[str] = field(default_factory=list)


def score(expected: str, actual: str) -> ScoreResult:
    """Compute WER between *expected* and *actual* after normalization.

    WER = (substitutions + deletions + insertions) / reference-word-count.
    Returns a :class:`ScoreResult` with the WER and aligned opcodes the UI
    can use to tag each word as ok / substituted / deleted / inserted.
    """
    ref = normalize(expected)
    hyp = normalize(actual)

    if not ref:
        # Edge case: empty reference — WER is undefined; return 0 or 1.
        return ScoreResult(wer=0.0 if not hyp else 1.0, ref_words=ref, hyp_words=hyp)

    matcher = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    opcodes = matcher.get_opcodes()

    errors = 0
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "replace":
            # max(ref_span, hyp_span) counts both substitutions and length mismatches
            errors += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            errors += i2 - i1
        elif tag == "insert":
            errors += j2 - j1

    wer = errors / len(ref)
    return ScoreResult(wer=wer, opcodes=opcodes, ref_words=ref, hyp_words=hyp)
