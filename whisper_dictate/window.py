from __future__ import annotations

import enum
import math
from PyQt6.QtWidgets import QWidget, QLabel, QStackedWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPaintEvent, QMouseEvent, QBrush

from .config import Config


REC_DOT_COLOR = "#ff3030"
REC_DOT_RADIUS = 4
REC_DOT_WIDGET_WIDTH = 12
REC_DOT_PULSE_INTERVAL_MS = 33
REC_DOT_PULSE_PERIOD_MS = 1000
REC_DOT_OPACITY_MIN = 0.3
REC_DOT_OPACITY_MAX = 1.0


class AppState(enum.Enum):
    LOADING = "loading"
    IDLE = "idle"
    RECORDING = "recording"
    SUCCESS = "success"
    FAILURE = "failure"
    LOAD_FAILED = "load_failed"


class WaveformWidget(QWidget):
    _BAR_COUNT = 16

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: list[float] = [0.0] * self._BAR_COUNT

    def reset(self) -> None:
        self._bars = [0.0] * self._BAR_COUNT
        self.update()

    def push_amplitude(self, value: float) -> None:
        self._bars.pop(0)
        self._bars.append(max(0.0, min(1.0, value)))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#4cde8f"), 2))

        w, h = self.width(), self.height()
        step = w / self._BAR_COUNT
        cy = h / 2.0

        for i, amp in enumerate(self._bars):
            bh = max(2.0, amp * (h - 4))
            x = int(i * step + step / 2)
            painter.drawLine(x, int(cy - bh / 2), x, int(cy + bh / 2))


class RecDotWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(REC_DOT_WIDGET_WIDTH)
        self.pulse_phase: float = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(REC_DOT_PULSE_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    def start_pulse(self) -> None:
        self.pulse_phase = 0.0
        self._timer.start()

    def stop_pulse(self) -> None:
        self._timer.stop()
        self.update()

    def _tick(self) -> None:
        delta = REC_DOT_PULSE_INTERVAL_MS / REC_DOT_PULSE_PERIOD_MS
        self.pulse_phase = (self.pulse_phase + delta) % 1.0
        self.update()

    def _current_opacity(self) -> float:
        return REC_DOT_OPACITY_MIN + (REC_DOT_OPACITY_MAX - REC_DOT_OPACITY_MIN) * (
            0.5 + 0.5 * math.sin(2.0 * math.pi * self.pulse_phase)
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._timer.isActive():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(REC_DOT_COLOR)
        color.setAlphaF(self._current_opacity())
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        cx = self.width() // 2
        cy = self.height() // 2
        painter.drawEllipse(QPoint(cx, cy), REC_DOT_RADIUS, REC_DOT_RADIUS)


class _ClickableLabel(QLabel):
    def __init__(self, on_click, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_click()
            event.accept()
        else:
            super().mousePressEvent(event)


class FloatingWindow(QWidget):
    became_idle = pyqtSignal()

    def __init__(self, config: Config) -> None:
        super().__init__()
        self._config = config
        self._drag_pos: QPoint | None = None
        self._state = AppState.LOADING
        self._bg_color = QColor("#2d2d2d")

        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._on_flash_done)

        self._setup_ui()
        self._apply_state(AppState.LOADING)
        self.move(config.window_position["x"], config.window_position["y"])

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(96, 38)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet("background: transparent;")

        self._label = _ClickableLabel(self._cycle_language, "", self._stack)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: white; font: bold 13px; letter-spacing: 2px; background: transparent;"
        )
        self._stack.addWidget(self._label)   # index 0

        self._waveform = WaveformWidget(self._stack)
        self._stack.addWidget(self._waveform)  # index 1

        layout.addWidget(self._stack)

    def _apply_state(self, state: AppState) -> None:
        self._state = state
        if state == AppState.LOADING:
            self._label.setText("...")
            self._stack.setCurrentIndex(0)
            self._bg_color = QColor("#2d2d2d")
        elif state == AppState.IDLE:
            self._label.setText(self._config.active_language.upper())
            self._stack.setCurrentIndex(0)
            self._bg_color = QColor("#222222")
        elif state == AppState.RECORDING:
            self._waveform.reset()
            self._stack.setCurrentIndex(1)
            self._bg_color = QColor("#0d1b2a")
        elif state == AppState.SUCCESS:
            self._label.setText(self._config.active_language.upper())
            self._stack.setCurrentIndex(0)
            self._bg_color = QColor("#1a6b35")
            self._flash_timer.start(500)
        elif state == AppState.FAILURE:
            self._label.setText(self._config.active_language.upper())
            self._stack.setCurrentIndex(0)
            self._bg_color = QColor("#6b1a1a")
            self._flash_timer.start(500)
        elif state == AppState.LOAD_FAILED:
            self._label.setText("ERR")
            self._stack.setCurrentIndex(0)
            self._bg_color = QColor("#6b1a1a")
        self.update()

    def _on_flash_done(self) -> None:
        self._apply_state(AppState.IDLE)
        self.became_idle.emit()

    def _cycle_language(self) -> None:
        if self._state != AppState.IDLE:
            return
        langs = self._config.languages
        idx = langs.index(self._config.active_language)
        self._config.active_language = langs[(idx + 1) % len(langs)]
        self._label.setText(self._config.active_language.upper())
        self._config.save()

    @property
    def state(self) -> AppState:
        return self._state

    def set_state(self, state: AppState) -> None:
        if self._state != state:
            self._apply_state(state)

    def push_amplitude(self, value: float) -> None:
        if self._state == AppState.RECORDING:
            self._waveform.push_amplitude(value)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def closeEvent(self, event) -> None:
        pos = self.pos()
        self._config.window_position = {"x": pos.x(), "y": pos.y()}
        self._config.save()
        super().closeEvent(event)
