"""
Rocky JARVIS HUD — Phase 7.

Features:
  - Typing animation for Rocky's responses
  - Live mic waveform visualizer
  - Pulsing status dot
  - Dynamic info bar (shows weather, vision summaries, etc.)
  - Glassmorphism + drag-to-move
  - Observation nudge display
"""

import os
import math
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint,
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient

# ── Status maps ────────────────────────────────────────────────────────────────
_STATUS_COLORS = {
    "IDLE":      "#1a3a4a",
    "LISTENING": "#00dcff",
    "THINKING":  "#6060ff",
    "SPEAKING":  "#00ff9f",
    "STANDBY":   "#2a2a3a",
}
_STATUS_TEXT = {
    "IDLE":      "IDLE",
    "LISTENING": "LISTENING",
    "THINKING":  "PROCESSING",
    "SPEAKING":  "SPEAKING",
    "STANDBY":   "STANDBY",
}

# ── Waveform ───────────────────────────────────────────────────────────────────
class WaveformWidget(QWidget):
    BAR_COUNT = 24
    BAR_W     = 3
    BAR_GAP   = 2
    MAX_H     = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars   = [0.05] * self.BAR_COUNT
        self._target = [0.05] * self.BAR_COUNT
        self._active = False
        self._tick   = 0
        total_w = self.BAR_COUNT * (self.BAR_W + self.BAR_GAP)
        self.setFixedSize(total_w, self.MAX_H + 4)
        t = QTimer(self)
        t.timeout.connect(self._step)
        t.start(40)

    def set_active(self, active: bool):
        self._active = active

    def set_level(self, level: float):
        if not self._active:
            return
        mid = self.BAR_COUNT // 2
        for i in range(self.BAR_COUNT):
            dist = abs(i - mid) / mid
            noise = random.uniform(0.0, 0.2)
            self._target[i] = max(0.05, level * (1 - dist * 0.4) + noise)

    def _step(self):
        self._tick += 1
        for i in range(self.BAR_COUNT):
            if self._active:
                drift = math.sin(self._tick * 0.12 + i * 0.45) * 0.08
                self._target[i] = max(0.04, min(1.0, self._target[i] + drift))
            else:
                self._target[i] = 0.04 + math.sin(self._tick * 0.05 + i * 0.3) * 0.02
            self._bars[i] += (self._target[i] - self._bars[i]) * 0.25
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        for i, level in enumerate(self._bars):
            bar_h = max(2, int(level * self.MAX_H))
            x = i * (self.BAR_W + self.BAR_GAP)
            y = (h - bar_h) // 2
            alpha = min(255, int(60 + level * 195))
            # Gradient from cyan to teal across bars
            r = int(0 + (i / self.BAR_COUNT) * 20)
            g = int(180 + (i / self.BAR_COUNT) * 40)
            b = 255
            p.setBrush(QColor(r, g, b, alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, self.BAR_W, bar_h, 2, 2)
        p.end()


# ── Status dot ─────────────────────────────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#1a3a4a")
        self._alpha = 200
        self._up    = False
        self.setFixedSize(10, 10)
        t = QTimer(self)
        t.timeout.connect(self._pulse)
        t.start(35)

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)
        self.update()

    def _pulse(self):
        step = 6
        self._alpha = (self._alpha + step) if self._up else (self._alpha - step)
        if self._alpha >= 255:
            self._alpha = 255
            self._up = False
        if self._alpha <= 80:
            self._alpha = 80
            self._up = True
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlpha(self._alpha)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 10, 10)
        p.end()


# ── Main HUD window ────────────────────────────────────────────────────────────
class RockyWindow(QWidget):

    def __init__(self, signals):
        super().__init__()
        self._signals  = signals
        self._drag_pos = QPoint()

        # Typing animation state
        self._type_full_text = ""
        self._type_idx       = 0
        self._type_timer     = QTimer(self)
        self._type_timer.timeout.connect(self._type_step)

        self._init_window()
        self._build_ui()
        self._load_styles()
        self._connect_signals()
        self._fade_in()

    def _init_window(self):
        self.setObjectName("RockyWindow")
        self.setWindowTitle("Rocky")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(460)
        self.setMaximumWidth(520)
        # Bottom-right of screen
        from PyQt6.QtWidgets import QApplication
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.width() - 540, geo.height() - 420)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        panel = QFrame(self)
        panel.setObjectName("mainPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 18, 24, 22)
        layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self._dot = StatusDot(panel)
        header.addWidget(self._dot)
        header.addSpacing(8)

        self._status_lbl = QLabel("IDLE", panel)
        self._status_lbl.setObjectName("statusLabel")
        header.addWidget(self._status_lbl)
        header.addStretch()

        brand = QLabel("R O C K Y", panel)
        brand.setObjectName("brandLabel")
        header.addWidget(brand)
        header.addStretch()

        self._close_btn = QPushButton("×", panel)
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(26, 26)
        self._close_btn.clicked.connect(self.close)
        header.addWidget(self._close_btn)
        layout.addLayout(header)

        # ── Divider ───────────────────────────────────────────────────────────
        layout.addSpacing(10)
        div = QFrame(panel)
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)
        layout.addSpacing(12)

        # ── Waveform ──────────────────────────────────────────────────────────
        wave_row = QHBoxLayout()
        wave_row.addStretch()
        self._wave = WaveformWidget(panel)
        wave_row.addWidget(self._wave)
        wave_row.addStretch()
        layout.addLayout(wave_row)
        layout.addSpacing(16)

        # ── User text ─────────────────────────────────────────────────────────
        user_row = QHBoxLayout()
        user_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        prefix_u = QLabel("YOU", panel)
        prefix_u.setObjectName("prefixLabel")
        self._user_lbl = QLabel("...", panel)
        self._user_lbl.setObjectName("userLabel")
        self._user_lbl.setWordWrap(True)
        user_row.addWidget(prefix_u)
        user_row.addSpacing(12)
        user_row.addWidget(self._user_lbl, 1)
        layout.addLayout(user_row)
        layout.addSpacing(12)

        # ── AI response ───────────────────────────────────────────────────────
        ai_row = QHBoxLayout()
        ai_row.setAlignment(Qt.AlignmentFlag.AlignTop)
        prefix_r = QLabel("ROCKY", panel)
        prefix_r.setObjectName("prefixRocky")
        self._ai_lbl = QLabel("...", panel)
        self._ai_lbl.setObjectName("aiLabel")
        self._ai_lbl.setWordWrap(True)
        self._ai_lbl.setMinimumHeight(52)
        ai_row.addWidget(prefix_r)
        ai_row.addSpacing(12)
        ai_row.addWidget(self._ai_lbl, 1)
        layout.addLayout(ai_row)
        layout.addSpacing(8)

        # ── Dynamic Info Bar (weather, research results, vision) ──────────────
        div2 = QFrame(panel)
        div2.setObjectName("divider")
        div2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div2)
        layout.addSpacing(8)

        info_row = QHBoxLayout()
        info_prefix = QLabel("ℹ", panel)
        info_prefix.setObjectName("infoPrefix")
        self._info_lbl = QLabel("Systems nominal.", panel)
        self._info_lbl.setObjectName("infoLabel")
        self._info_lbl.setWordWrap(True)
        info_row.addWidget(info_prefix)
        info_row.addSpacing(8)
        info_row.addWidget(self._info_lbl, 1)
        layout.addLayout(info_row)

        outer.addWidget(panel)

    def _load_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        try:
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def _connect_signals(self):
        self._signals.status_changed.connect(self._on_status)
        self._signals.user_text.connect(self._on_user)
        self._signals.ai_text.connect(self._on_ai)
        self._signals.wave_tick.connect(self._on_wave)
        self._signals.info_text.connect(self._on_info)
        self._signals.observation.connect(self._on_observation)

    # ── Signal slots ──────────────────────────────────────────────────────────
    def _on_status(self, status: str):
        self._status_lbl.setText(_STATUS_TEXT.get(status, status))
        self._dot.set_color(_STATUS_COLORS.get(status, "#1a3a4a"))
        self._wave.set_active(status == "LISTENING")

    def _on_user(self, text: str):
        self._user_lbl.setText(text)

    def _on_ai(self, text: str):
        self._type_timer.stop()
        self._type_full_text = text
        self._type_idx = 0
        self._ai_lbl.setText("")
        self._type_timer.start(18)

    def _type_step(self):
        self._type_idx += 1
        self._ai_lbl.setText(self._type_full_text[:self._type_idx])
        if self._type_idx >= len(self._type_full_text):
            self._type_timer.stop()

    def _on_wave(self, level: float):
        self._wave.set_level(level)

    def _on_info(self, text: str):
        self._info_lbl.setText(text)

    def _on_observation(self, text: str):
        """Show observer nudge in info bar with distinct styling."""
        self._info_lbl.setText(f"💡 {text}")

    # ── Fade-in ────────────────────────────────────────────────────────────────
    def _fade_in(self):
        eff  = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(900)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ── Drag ──────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(e.globalPosition().toPoint() - self._drag_pos)
