"""Difficulty-matched free-trial center shown only in trial editions."""

from PySide6 import QtCore, QtWidgets
from ui_styles import SECONDARY_BUTTON_STYLE, tab_button_style
from edition_config import EDITIONS, RELEASED_EDITION_IDS


class TrialCenterView(QtWidgets.QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        audience_name = self.main_window.edition.display_name.removesuffix("体验")
        formal_id = self.main_window.edition.edition_id.removeprefix("trial_")
        junior = formal_id == "zhongkao"
        self.setObjectName("trial_center_view")

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f4f7fb;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 32)
        layout.setSpacing(16)

        hero = QtWidgets.QFrame()
        hero.setStyleSheet(
            "QFrame { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #7c3aed, stop:1 #2563eb); border-radius:16px; }"
        )
        hero_layout = QtWidgets.QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 21, 26, 22)
        title = QtWidgets.QLabel(
            "初中核心词汇，从准初一预习到初三中考"
            if junior else "高中3800词，从准高一预习到高三备考")
        title.setStyleSheet(
            "border:none; color:white; font-size:27px; font-weight:700; "
            "font-family:'Microsoft YaHei UI','Microsoft YaHei'; background:transparent;")
        subtitle = QtWidgets.QLabel(
            (("适用：准初一｜初一｜初二｜初三　　用途：提前预习｜课内同步｜中考备考\n"
             if junior else
             "适用：准高一｜高一｜高二｜高三　　用途：提前预习｜课内同步｜高考备考\n") +
            f"{audience_name}免费版用代表性内容体验“高效记忆、闯关识弱、自主登记”三大核心功能。"
            )
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "border:none; color:#ede9fe; font-size:14px; background:transparent;")
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        level_frame = QtWidgets.QFrame()
        level_frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #dbe3ee; border-radius:12px; }")
        level_layout = QtWidgets.QVBoxLayout(level_frame)
        level_layout.setContentsMargins(18, 14, 18, 16)
        level_layout.setSpacing(10)
        level_title = QtWidgets.QLabel("当前开放的免费体验")
        level_title.setStyleSheet(
            "border:none; color:#111827; font-size:17px; font-weight:700;")
        level_hint = QtWidgets.QLabel(
            "体验版与正式版一一对应；正式版开放后，对应体验才会同步开放。")
        level_hint.setWordWrap(True)
        level_hint.setStyleSheet("border:none; color:#64748b; font-size:13px;")
        level_layout.addWidget(level_title)
        level_layout.addWidget(level_hint)
        level_buttons = QtWidgets.QHBoxLayout()
        level_buttons.setSpacing(9)
        choices = [
            (f"trial_{edition_id}", f"{EDITIONS[edition_id].base_display_name}（30词）")
            for edition_id in RELEASED_EDITION_IDS
        ]
        for edition_id, label in choices:
            active = edition_id == self.main_window.edition.edition_id
            button = QtWidgets.QPushButton(
                f"✓ {label}（当前）" if active else label)
            button.setObjectName(f"btn_trial_level_{edition_id}")
            button.setMinimumHeight(42)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            if active:
                button.setStyleSheet(tab_button_style(True))
                button.setEnabled(False)
            else:
                button.setStyleSheet(tab_button_style(False))
                button.clicked.connect(
                    lambda checked=False, key=edition_id:
                    self.main_window.request_trial_level_switch(key))
            level_buttons.addWidget(button, 1)
        level_layout.addLayout(level_buttons)
        layout.addWidget(level_frame)

        status = QtWidgets.QFrame()
        status.setStyleSheet(
            "QFrame { background:white; border:1px solid #dbe3ee; border-radius:12px; }")
        status_layout = QtWidgets.QHBoxLayout(status)
        status_layout.setContentsMargins(18, 13, 18, 13)
        memory = QtWidgets.QLabel("背得快\n体验代表性记忆方法")
        challenge = QtWidgets.QLabel("找得准\n固定30词闯关识弱")
        personal = QtWidgets.QLabel("补得全\n自主登记最多30词")
        for label, color in (
            (memory, "#7c3aed"), (challenge, "#2563eb"), (personal, "#059669")
        ):
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(
                f"border:none; color:{color}; background:#f8fafc; border-radius:9px; "
                "font-size:14px; font-weight:700; padding:10px;")
            status_layout.addWidget(label, 1)
        layout.addWidget(status)

        section_title = QtWidgets.QLabel("免费体验三大核心功能")
        section_title.setStyleSheet(
            "color:#111827; font-size:19px; font-weight:700; background:transparent;")
        layout.addWidget(section_title)
        steps = QtWidgets.QGridLayout()
        steps.setHorizontalSpacing(12)
        steps.setVerticalSpacing(12)
        step_defs = [
            ("1", "高效记忆", "体验主题场景、词根、音形拼读和同义反义的代表内容，让单词先形成联系。", "#f5f3ff", "#7c3aed"),
            ("2", "闯关识弱", "用30个体验词主动拼写；不会和掌握不稳定的单词自动进入个人错词表。", "#eff6ff", "#2563eb"),
            ("3", "自主登记", "把课本、作业、试卷和阅读生词加入个人词库，再进行独立训练。", "#ecfdf5", "#047857"),
        ]
        for index, definition in enumerate(step_defs):
            steps.addWidget(self._step_card(*definition), 0, index)
        steps.setColumnStretch(0, 1)
        steps.setColumnStretch(1, 1)
        steps.setColumnStretch(2, 1)
        layout.addLayout(steps)

        isolation = QtWidgets.QFrame()
        isolation.setStyleSheet(
            "QFrame { background:#fffbeb; border:1px solid #fbbf24; border-radius:11px; }")
        isolation_layout = QtWidgets.QVBoxLayout(isolation)
        isolation_layout.setContentsMargins(17, 12, 17, 13)
        isolation_title = QtWidgets.QLabel("体验数据与正式版本完全隔离")
        isolation_title.setStyleSheet(
            "border:none; color:#92400e; font-size:15px; font-weight:700;")
        isolation_text = QtWidgets.QLabel(
            f"{audience_name}体验的进度、错词表和轮次记录单独保存；切换到其他体验级别也不会混在一起。"
            "购买正式版后，正式词库会建立独立学习进度，体验数据不会自动混入或覆盖正式数据。"
        )
        isolation_text.setWordWrap(True)
        isolation_text.setStyleSheet("border:none; color:#78350f; font-size:13px;")
        isolation_layout.addWidget(isolation_title)
        isolation_layout.addWidget(isolation_text)
        layout.addWidget(isolation)

        purchase = QtWidgets.QFrame()
        purchase.setObjectName("trial_purchase_entry")
        purchase.setStyleSheet(
            "QFrame#trial_purchase_entry { background:#eef2ff; "
            "border:1px solid #a5b4fc; border-radius:11px; }")
        purchase_layout = QtWidgets.QHBoxLayout(purchase)
        purchase_layout.setContentsMargins(17, 13, 17, 13)
        purchase_copy = QtWidgets.QLabel(
            ("正式版面向准初一至初三学生，开放完整初中核心词汇提分速记、"
             if junior else
             "正式版面向准高一至高三学生，开放完整高中3800词提分速记、")
            + "完整闯关识弱和持续学习记录。")
        purchase_copy.setWordWrap(True)
        purchase_copy.setStyleSheet(
            "border:none; color:#3730a3; font-size:14px; font-weight:600;")
        purchase_button = QtWidgets.QPushButton("前往购买正式版  →")
        purchase_button.setObjectName("btn_trial_go_purchase")
        purchase_button.setMinimumSize(185, 42)
        purchase_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        purchase_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        purchase_button.clicked.connect(self.main_window.request_trial_activation)
        purchase_layout.addWidget(purchase_copy, 1)
        purchase_layout.addWidget(purchase_button)
        layout.addWidget(purchase)
        layout.addStretch()
        scroll.setWidget(page)
        outer.addWidget(scroll)

    @staticmethod
    def _step_card(number, title, text, background, accent):
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{background}; border:1px solid {accent}; border-radius:11px; }}")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 13)
        heading = QtWidgets.QLabel(f"{number}　{title}")
        heading.setStyleSheet(
            f"border:none; color:{accent}; font-size:15px; font-weight:700;")
        detail = QtWidgets.QLabel(text)
        detail.setWordWrap(True)
        detail.setStyleSheet("border:none; color:#475569; font-size:13px;")
        layout.addWidget(heading)
        layout.addWidget(detail)
        return card

    @staticmethod
    def _action_button(text, name, callback):
        button = QtWidgets.QPushButton(text)
        button.setObjectName(name)
        button.setMinimumHeight(42)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        button.clicked.connect(callback)
        return button

    def _open_regular_challenge(self):
        if self.main_window.vocab_ctrl is not None:
            self.main_window.vocab_ctrl.switch_challenge_mode("regular")
        self.main_window.stack.setCurrentIndex(0)
