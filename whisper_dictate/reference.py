from __future__ import annotations

# Reference passages for calibration.  Each is a human-readable paragraph
# (with normal capitalisation and punctuation) stored verbatim; the scoring
# module applies normalisation at scoring time so the passage never needs to
# be pre-processed here.
#
# Passage design goals
# --------------------
# * Dense clusters of acoustically-confusable word pairs for the target
#   language so that a misconfigured model produces visible WER and targeted
#   hotwords or VAD changes produce measurable improvement.
# * German: schaute/scharrte/scharte, Scherbe/Schärfe, Karte/scharte,
#   acht/acht, scharf/scharf, schauen/Schauen.
# * English: shard/chart/charred, shore/sure, chart/start, word/ward.
# * Natural prose so the passage can be read aloud at a normal pace.

REFERENCE_PASSAGES: dict[str, str] = {
    "de": (
        "Er schaute durch das Fenster und sah eine Scherbe auf dem Boden liegen. "
        "Die Schärfe der Kante überraschte ihn, als er sie vorsichtig aufhob. "
        "Sie scharrte mit dem Fuß über den Kies und schaute dabei nachdenklich zur Seite. "
        "Auf der Karte war die Straße klar eingezeichnet, aber er schaute trotzdem zweimal hin. "
        "Die alte Scherbe war scharf und die Scharte im Rand zeigte, wie alt sie war. "
        "Er schaute auf die Uhr und bemerkte, dass er acht Minuten zu spät war. "
        "Sie schartete das Holz mit einem Messer und schaute dann, wie es aussah. "
        "Die Karte lag auf dem Tisch, und er schaute sie genau an, bevor er aufbrach."
    ),
    "en": (
        "She found a shard of glass near the shore and picked it up carefully. "
        "The chart on the wall showed the data clearly, but the shard distracted her. "
        "He was sure the shore was close, though the charred wood suggested a fire had passed. "
        "The word on the chart was hard to read from across the ward. "
        "She held the shard up to the light and compared it to the chart in her hand. "
        "The shore stretched far to the north, and the charred remains of a boat lay at its edge. "
        "He checked the chart twice before writing the final word in the report. "
        "The ward was quiet except for the sound of the shore in the distance."
    ),
}
