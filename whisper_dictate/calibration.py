from __future__ import annotations

import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from .config import Config
from .model import DecodeSettings, WhisperEngine
from .reference import REFERENCE_PASSAGES
from .scoring import ScoreResult, score

_log = logging.getLogger(__name__)


class CalibrationWindow(QWidget):
    """In-app calibration window for tuning transcription accuracy.

    Displays a reference passage for the active language; the user records
    it, the app scores Word Error Rate and shows a colour-highlighted diff,
    and the user can tune hotwords / VAD / normalisation, re-run on the same
    audio, and save the settings to config.
    """

    result_ready = pyqtSignal(float, str)  # wer, transcription

    def __init__(
        self,
        engine: WhisperEngine,
        config: Config,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._config = config
        self._language = config.active_language
        self._recorded_audio = None  # np.ndarray | None

        self._setup_ui()
        self.setWindowTitle("Calibration")
        self.resize(640, 520)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Reference passage
        passage_label = QLabel("Read the following passage aloud:")
        passage_label.setWordWrap(True)
        root.addWidget(passage_label)

        self._passage_view = QLabel(REFERENCE_PASSAGES.get(self._language, ""))
        self._passage_view.setWordWrap(True)
        self._passage_view.setTextFormat(Qt.TextFormat.PlainText)
        self._passage_view.setStyleSheet(
            "background: #1e1e1e; color: #dddddd; padding: 8px; border-radius: 4px;"
        )
        root.addWidget(self._passage_view)

        # Record / Stop button row
        rec_row = QHBoxLayout()
        self._record_btn = QPushButton("Record")
        self._record_btn.clicked.connect(self._on_record_clicked)
        rec_row.addWidget(self._record_btn)
        rec_row.addStretch()
        root.addLayout(rec_row)

        # Result panel
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(self._result_label)

        # Settings area
        settings_label = QLabel("Decode settings:")
        root.addWidget(settings_label)

        self._hotwords_edit = QLineEdit()
        self._hotwords_edit.setPlaceholderText(
            "hotwords (space-separated words to boost)"
        )
        self._hotwords_edit.setText(
            self._config.hotwords.get(self._language, "")
        )
        root.addWidget(self._hotwords_edit)

        flags_row = QHBoxLayout()
        self._vad_check = QCheckBox("VAD filter")
        self._vad_check.setChecked(self._config.vad_filter)
        flags_row.addWidget(self._vad_check)

        self._normalize_check = QCheckBox("Normalize audio")
        self._normalize_check.setChecked(self._config.normalize_audio)
        flags_row.addWidget(self._normalize_check)
        flags_row.addStretch()
        root.addLayout(flags_row)

        # Re-run / Save row
        action_row = QHBoxLayout()
        self._rerun_btn = QPushButton("Re-run")
        self._rerun_btn.setEnabled(False)
        self._rerun_btn.clicked.connect(self._on_rerun_clicked)
        action_row.addWidget(self._rerun_btn)

        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save_clicked)
        action_row.addWidget(self._save_btn)
        action_row.addStretch()
        root.addLayout(action_row)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_record_clicked(self) -> None:
        if not hasattr(self, "_recorder") or self._recorder is None:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self) -> None:
        from .audio import AudioRecorder
        if not hasattr(self, "_recorder") or self._recorder is None:
            self._recorder = AudioRecorder(self)
            self._recorder.amplitude_ready.connect(self._on_amplitude)
            self._record_btn.setText("Stop")
            self._recorder.start()

    def stop_recording(self) -> None:
        if hasattr(self, "_recorder") and self._recorder is not None:
            self._recorded_audio = self._recorder.stop()
            self._recorder = None
            self._record_btn.setText("Record")
            self._set_buttons_busy(True)
            self._transcribe(self._recorded_audio)

    def _on_rerun_clicked(self) -> None:
        if self._recorded_audio is not None:
            self._set_buttons_busy(True)
            self._transcribe(self._recorded_audio)

    def _on_save_clicked(self) -> None:
        lang = self._language
        self._config.hotwords[lang] = self._hotwords_edit.text()
        self._config.vad_filter = self._vad_check.isChecked()
        self._config.normalize_audio = self._normalize_check.isChecked()
        self._config.save()

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _current_settings(self) -> DecodeSettings:
        return DecodeSettings(
            hotwords=self._hotwords_edit.text(),
            vad_filter=self._vad_check.isChecked(),
            normalize=self._normalize_check.isChecked(),
        )

    def _transcribe(self, audio) -> None:
        settings = self._current_settings()
        self._engine.transcribe(
            audio,
            self._language,
            settings=settings,
            on_result=self._on_result,
            on_failed=self._on_failed,
        )

    def _on_amplitude(self, value: float) -> None:
        pass  # waveform widget would consume this

    def _on_result(self, text: str) -> None:
        self._set_buttons_busy(False)
        self._rerun_btn.setEnabled(True)
        passage = REFERENCE_PASSAGES.get(self._language, "")
        result = score(passage, text)
        self._render_result(result, text)
        self.result_ready.emit(result.wer, text)

    def _on_failed(self) -> None:
        self._set_buttons_busy(False)
        self._result_label.setText(
            "<span style='color:#ff6060;'>No speech detected — try again.</span>"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_buttons_busy(self, busy: bool) -> None:
        self._record_btn.setEnabled(not busy)
        self._rerun_btn.setEnabled(not busy)
        self._save_btn.setEnabled(not busy)

    def _render_result(self, result: ScoreResult, hypothesis: str) -> None:
        wer_pct = result.wer * 100
        parts = [f"<b>WER: {wer_pct:.1f}%</b><br/>"]

        # Build per-word colour-coded diff
        for tag, i1, i2, j1, j2 in result.opcodes:
            if tag == "equal":
                for w in result.ref_words[i1:i2]:
                    parts.append(f"<span style='color:#4cde8f;'>{w}</span> ")
            elif tag == "replace":
                for w in result.hyp_words[j1:j2]:
                    parts.append(f"<span style='color:#ffb000;'>{w}</span> ")
            elif tag == "delete":
                for w in result.ref_words[i1:i2]:
                    parts.append(f"<span style='color:#ff6060;'>[{w}]</span> ")
            elif tag == "insert":
                for w in result.hyp_words[j1:j2]:
                    parts.append(f"<span style='color:#8888ff;'>+{w}</span> ")

        self._result_label.setText("".join(parts))
