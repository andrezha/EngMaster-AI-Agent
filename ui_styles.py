"""Shared typography and interaction styles for EngMaster."""

from PySide6 import QtCore, QtGui, QtWidgets


UI_FONT_FAMILY = "Microsoft YaHei UI"


class _ClickableCursorFilter(QtCore.QObject):
    """Give enabled buttons a hand cursor and disabled buttons an arrow."""

    _WATCHED_EVENTS = {
        QtCore.QEvent.Type.Polish,
        QtCore.QEvent.Type.Show,
        QtCore.QEvent.Type.EnabledChange,
    }

    def eventFilter(self, watched, event):
        if (isinstance(watched, QtWidgets.QAbstractButton)
                and event.type() in self._WATCHED_EVENTS):
            cursor = (
                QtCore.Qt.CursorShape.PointingHandCursor
                if watched.isEnabled()
                else QtCore.Qt.CursorShape.ArrowCursor
            )
            watched.setCursor(cursor)
        return False


def apply_application_ui_baseline(app):
    """Apply one Chinese-capable font and automatic button cursors app-wide."""
    font = QtGui.QFont(UI_FONT_FAMILY, 10)
    font.setWeight(QtGui.QFont.Weight.Normal)
    app.setFont(font)
    baseline = (
        'QWidget { font-family:"Microsoft YaHei UI","Microsoft YaHei",sans-serif; }'
        'QMenu, QToolTip { font-family:"Microsoft YaHei UI","Microsoft YaHei",sans-serif; }'
    )
    if baseline not in app.styleSheet():
        app.setStyleSheet(app.styleSheet() + baseline)
    cursor_filter = getattr(app, "_engmaster_cursor_filter", None)
    if cursor_filter is None:
        cursor_filter = _ClickableCursorFilter(app)
        app.installEventFilter(cursor_filter)
        app._engmaster_cursor_filter = cursor_filter
    return cursor_filter


PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background:#2563eb; color:#ffffff; border:1px solid #2563eb;
        border-radius:8px; padding:0 16px; font-weight:600;
    }
    QPushButton:hover { background:#1d4ed8; border-color:#1d4ed8; }
    QPushButton:pressed { background:#1e40af; border-color:#1e40af; }
    QPushButton:disabled {
        background:#e5e7eb; color:#9ca3af; border-color:#d1d5db;
    }
"""


PRIMARY_TOOLBUTTON_STYLE = """
    QToolButton {
        background:#2563eb; color:#ffffff; border:1px solid #2563eb;
        border-radius:8px; padding:0 14px; font-size: 14px; font-weight:600;
    }
    QToolButton:hover { background:#1d4ed8; border-color:#1d4ed8; }
    QToolButton:pressed { background:#1e40af; border-color:#1e40af; }
    QToolButton:disabled {
        background:#e5e7eb; color:#9ca3af; border-color:#d1d5db;
    }
"""

SUCCESS_TOOLBUTTON_STYLE = """
    QToolButton {
        background:#16a34a; color:#ffffff; border:1px solid #16a34a;
        border-radius:8px; padding:0 14px; font-size: 14px; font-weight:600;
    }
    QToolButton:hover { background:#15803d; border-color:#15803d; }
    QToolButton:pressed { background:#166534; border-color:#166534; }
    QToolButton:disabled { background:#bbf7d0; color:#f0fdf4; border-color:#bbf7d0; }
"""


SECONDARY_BUTTON_STYLE = """
    QPushButton {
        background:#ffffff; color:#334155; border:1px solid #cbd5e1;
        border-radius:8px; padding:0 12px; font-weight:600;
    }
    QPushButton:hover {
        background:#eff6ff; color:#1d4ed8; border-color:#60a5fa;
    }
    QPushButton:pressed {
        background:#dbeafe; color:#1e40af; border-color:#3b82f6;
    }
    QPushButton:disabled {
        background:#f1f5f9; color:#94a3b8; border-color:#e2e8f0;
    }
"""


DANGER_BUTTON_STYLE = """
    QPushButton {
        background:#ffffff; color:#b91c1c; border:1px solid #fca5a5;
        border-radius:7px; padding:0 10px; font-weight:600;
    }
    QPushButton:hover { background:#fee2e2; color:#991b1b; border-color:#ef4444; }
    QPushButton:pressed { background:#fecaca; border-color:#dc2626; }
"""


CHECKABLE_BUTTON_STYLE = """
    QPushButton {
        background:#ffffff; color:#334155; border:1px solid #cbd5e1;
        border-radius:8px; padding:0 12px; font-weight:600;
    }
    QPushButton:hover {
        background:#eff6ff; color:#1d4ed8; border-color:#60a5fa;
    }
    QPushButton:pressed { background:#dbeafe; border-color:#3b82f6; }
    QPushButton:checked {
        background:#2563eb; color:#ffffff; border-color:#2563eb;
        font-weight:600;
    }
    QPushButton:checked:hover {
        background:#1d4ed8; color:#ffffff; border-color:#1d4ed8;
    }
    QPushButton:disabled {
        background:#f1f5f9; color:#94a3b8; border-color:#e2e8f0;
    }
"""


CLICKABLE_LABEL_STYLE = """
    QLabel {
        background:#ffffff; color:#1d4ed8; border:1px solid #93c5fd;
        border-radius:7px; padding:6px 10px; font-size:13px;
        font-weight:600;
    }
    QLabel:hover {
        background:#dbeafe; color:#1e40af; border-color:#3b82f6;
    }
"""


def tab_button_style(active: bool) -> str:
    if active:
        return (
            "QPushButton { background:#2563eb; color:#ffffff; border:1px solid #2563eb; "
            "border-radius:8px; padding:0 12px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#1d4ed8; border-color:#1d4ed8; }"
            "QPushButton:pressed { background:#1e40af; border-color:#1e40af; }"
        )
    return (
        "QPushButton { background:#ffffff; color:#334155; border:1px solid #cbd5e1; "
        "border-radius:8px; padding:0 12px; font-size:14px; font-weight:600; }"
        "QPushButton:hover { background:#eff6ff; color:#1d4ed8; border-color:#60a5fa; }"
        "QPushButton:pressed { background:#dbeafe; color:#1e40af; border-color:#3b82f6; }"
        "QPushButton:disabled { background:#f1f5f9; color:#94a3b8; border-color:#e2e8f0; }"
    )
