from datetime import datetime

from PySide6 import QtCore, QtWidgets


MODE_NAMES = {
    "regular": "高考3800词闯关",
    "mistake_list": "错词闯关",
    "self_register": "自主录入闯关",
    "phrase": "短语闯关",
    "phrase_mistake": "短语错词闯关",
    "irregular": "不规则动词闯关",
    "irregular_mistake": "不规则动词错词闯关",
}


def _format_time(value, legacy=False):
    if not value:
        return "升级前已开始" if legacy else "—"
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(value)


def _format_duration(seconds):
    seconds = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}小时{minutes}分钟"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def _format_start(record):
    if record.get("started_at"):
        return _format_time(record.get("started_at"))
    if record.get("started_before_tracking"):
        if record.get("tracking_started_at"):
            tracked_at = _format_time(record.get("tracking_started_at"))
            return f"升级前已开始（记录自 {tracked_at}）"
        return "升级前已开始（尚未开始计时）"
    return "尚未开始"


class RoundHistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent, learning_store, progress_provider=None):
        super().__init__(parent)
        self.learning_store = learning_store
        self.progress_provider = progress_provider or (lambda: {})
        self.setWindowTitle("轮次学习记录")
        self.resize(880, 520)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top_row = QtWidgets.QHBoxLayout()
        top_row.addWidget(QtWidgets.QLabel("闯关类型："))
        self.mode_combo = QtWidgets.QComboBox()
        for mode, name in MODE_NAMES.items():
            self.mode_combo.addItem(name, mode)
        self.mode_combo.currentIndexChanged.connect(self.refresh)
        top_row.addWidget(self.mode_combo)
        top_row.addStretch(1)
        hint = QtWidgets.QLabel("每种闯关保留最近50轮")
        hint.setStyleSheet("color:#6b7280;")
        top_row.addWidget(hint)
        layout.addLayout(top_row)

        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "轮次", "状态", "开始时间", "结束时间", "有效学习时长", "进度/总数", "本轮错词"
        ])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.table)

        close_button = QtWidgets.QPushButton("关闭")
        close_button.setFixedSize(100, 36)
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignRight)
        self.refresh()

    def select_mode(self, mode):
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)

    def refresh(self):
        mode = self.mode_combo.currentData()
        if not mode:
            return
        snapshot = self.learning_store.snapshot()
        mode_data = snapshot.get("modes", {}).get(mode, {})
        rows = list(reversed(mode_data.get("history", [])))
        ongoing = mode_data.get("ongoing")
        if isinstance(ongoing, dict):
            current = dict(ongoing)
            current["status"] = "ongoing"
            progress = self.progress_provider().get(mode, {})
            current["current"] = progress.get("current", 0)
            current["total"] = progress.get("total", current.get("total", 0))
            current["wrong"] = progress.get("wrong", 0)
            rows.insert(0, current)

        self.table.setRowCount(len(rows))
        for row_index, record in enumerate(rows):
            is_ongoing = record.get("status") == "ongoing"
            values = [
                f"第{record.get('round', 1)}轮",
                (
                    "待开始" if is_ongoing and not record.get("tracking_started_at")
                    else "进行中" if is_ongoing else "已完成"
                ),
                _format_start(record),
                "—" if is_ongoing else _format_time(record.get("ended_at")),
                _format_duration(record.get("active_seconds", 0)),
                (
                    f"{record.get('current', 0)} / {record.get('total', 0)}"
                    if is_ongoing else str(record.get("total", 0))
                ),
                str(record.get("wrong", 0)),
            ]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.table.setItem(row_index, column, item)


def show_round_history(parent, learning_store, current_mode, progress_provider=None):
    dialog = RoundHistoryDialog(parent, learning_store, progress_provider)
    dialog.select_mode(current_mode)
    dialog.exec()
