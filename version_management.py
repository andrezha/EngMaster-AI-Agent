"""In-app version management page for formal and trial editions."""

from PySide6 import QtCore, QtWidgets

from edition_config import EDITIONS, RELEASED_EDITION_IDS, is_trial_edition
from purchase_activation_panel import PurchaseActivationPanel
from purchase_config import TAOBAO_BUTTON_STYLE


class VersionManagementView(QtWidgets.QWidget):
    EDITION_ORDER = ("zhongkao", "gaokao", "cet4", "cet6", "kaoyan")

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("version_management_view")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)

        title = QtWidgets.QLabel("英语正式版管理与购买")
        title.setStyleSheet("color:#0f172a; font-size:25px; font-weight:700;")
        subtitle = QtWidgets.QLabel(
            "查看各英语正式版的开放状态和已有授权；购买版本统一在淘宝商品规格中选择。"
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#64748b; font-size:14px;")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        purchase_guide = QtWidgets.QLabel(
            "如何购买\n"
            "1. 点击下方“前往淘宝购买”，在淘宝商品规格中选择版本并付款。\n"
            "2. 粘贴淘宝订单号，将订单号和本机识别码组合成唯一客服核验信息。\n"
            "3. 从已付款的对应订单联系卖家，发送订单卡片和复制的客服核验信息。\n"
            "4. 客服人工核对订单号、付款状态和商品规格，请耐心等待处理。\n"
            "5. 收到累计激活码后，回到本页粘贴并立即激活。"
        )
        purchase_guide.setObjectName("formal_purchase_guide")
        purchase_guide.setWordWrap(True)
        purchase_guide.setStyleSheet(
            "color:#6d28d9; background:#f5f3ff; border:1px solid #c4b5fd; "
            "border-radius:9px; padding:11px 14px; font-size:14px; font-weight:600;"
        )
        outer.addWidget(purchase_guide)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 2, 8, 12)
        self.content_layout.setSpacing(14)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll, 1)
        self.refresh()

    def refresh(self):
        self._clear_layout(self.content_layout)

        current = self.main_window.edition
        entitlements = frozenset(getattr(
            self.main_window, "license_entitlements", frozenset()))
        status = QtWidgets.QLabel(
            f"当前正在使用：{current.product_title}"
        )
        status.setObjectName("version_management_current")
        status.setWordWrap(True)
        status.setStyleSheet(
            "color:#1d4ed8; background:#eff6ff; border:1px solid #93c5fd; "
            "border-radius:9px; padding:10px 13px; font-size:14px; font-weight:600;"
        )
        self.content_layout.addWidget(status)

        self.content_layout.addWidget(self._section_title(
            "正式版", "正式版学习数据与体验数据分开保存；切换版本前会自动保存当前进度。"))

        store_button = QtWidgets.QPushButton("前往淘宝购买 · 版本请在商品规格中选择")
        store_button.setObjectName("btn_open_taobao_store")
        store_button.setMinimumHeight(42)
        store_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        store_button.setStyleSheet(TAOBAO_BUTTON_STYLE)
        store_button.clicked.connect(
            lambda checked=False: self.main_window.open_taobao_purchase())
        self.content_layout.addWidget(store_button)

        purchase_options = QtWidgets.QLabel(
            "淘宝购买规格说明\n"
            "可购买单个英语版本，也可选择包含多个版本的组合规格，一次购买多个版本。\n"
            "示例：\n"
            "• 单版本：高考英语3800词版\n"
            "• 双版本组合：初中英语词汇版＋高考英语3800词版\n"
            "• 四六级组合：大学英语四级版＋大学英语六级版\n"
            "• 多版本组合：以淘宝商品页面实际提供的规格为准\n"
            "当前只有高考英语正式版开放购买，开发中的版本及相关组合暂不销售。"
        )
        purchase_options.setObjectName("taobao_purchase_options_notice")
        purchase_options.setWordWrap(True)
        purchase_options.setStyleSheet(
            "color:#7c2d12; background:#fff7ed; border:1px solid #fdba74; "
            "border-radius:9px; padding:11px 13px; font-size:13px; line-height:1.5;")
        self.content_layout.addWidget(purchase_options)

        self.purchase_panel = PurchaseActivationPanel(self.main_window)
        self.formal_grid = QtWidgets.QGridLayout()
        self.formal_grid.setHorizontalSpacing(10)
        self.formal_grid.setVerticalSpacing(10)
        self._formal_cards = []
        self._formal_columns = None
        for edition_id in self.EDITION_ORDER:
            config = EDITIONS[edition_id]
            is_current = current.edition_id == edition_id
            card = self._edition_card(
                edition_id, config, entitlements, is_current)
            self._formal_cards.append(card)
        self.content_layout.addLayout(self.formal_grid)
        self._relayout_formal_cards()
        self.content_layout.addWidget(self.purchase_panel)
        self.content_layout.addStretch()

    def _edition_card(self, edition_id, config, entitlements, is_current):
        released = edition_id in RELEASED_EDITION_IDS
        unlocked = edition_id in entitlements
        mode = "developing" if not released else ("unlocked" if unlocked else "purchase")
        colors = {
            "developing": ("#fffbeb", "#b45309", "#fde68a"),
            "unlocked": ("#ecfdf5", "#15803d", "#86efac"),
            "purchase": ("#f5f3ff", "#6d28d9", "#c4b5fd"),
        }
        background, color, border = colors[mode]
        card = QtWidgets.QFrame()
        card.setObjectName(f"formal_edition_card_{edition_id}")
        card.setMinimumHeight(104)
        card.setStyleSheet(
            f"QFrame {{ background:{background}; border:1px solid {border}; "
            "border-radius:10px; }")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(13, 11, 13, 12)
        layout.setSpacing(7)

        title = QtWidgets.QLabel(config.product_title)
        title.setWordWrap(True)
        title.setStyleSheet(
            f"border:none; color:{color}; font-size:15px; font-weight:700;")
        layout.addWidget(title)

        state_button = QtWidgets.QPushButton()
        state_button.setObjectName(f"btn_manage_formal_{edition_id}")
        state_button.setMinimumHeight(34)
        state_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        state_button.setStyleSheet(self._choice_style(mode))
        if not released:
            state_button.setText("开发中 · 暂未开放购买")
            state_button.setEnabled(False)
        elif unlocked and is_current:
            state_button.setText("当前已解锁")
            state_button.setEnabled(False)
        elif unlocked:
            state_button.setText("已解锁 · 进入学习")
            state_button.clicked.connect(
                lambda checked=False, key=edition_id:
                self.main_window.request_version_from_management(key))
        else:
            state_button.setText("当前可购买")
            state_button.setEnabled(False)
        layout.addWidget(state_button)

        return card

    def _clear_layout(self, layout):
        """Remove nested grid widgets before rebuilding the status page."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
                child_layout.deleteLater()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "formal_grid"):
            QtCore.QTimer.singleShot(0, self._relayout_formal_cards)

    def _relayout_formal_cards(self):
        if not hasattr(self, "_formal_cards"):
            return
        available_width = min(
            self.scroll.viewport().width(), max(0, self.width() - 40))
        columns = 1 if available_width < 620 else 2
        if columns == self._formal_columns:
            return
        self._formal_columns = columns
        for card in self._formal_cards:
            self.formal_grid.removeWidget(card)
        for index, card in enumerate(self._formal_cards):
            self.formal_grid.addWidget(card, index // columns, index % columns)

    def _relayout_formal_buttons(self):
        """Compatibility alias for existing diagnostics."""
        self._relayout_formal_cards()

    @staticmethod
    def _section_title(title, detail):
        label = QtWidgets.QLabel(f"{title}\n{detail}")
        label.setWordWrap(True)
        label.setStyleSheet(
            "color:#334155; background:white; border:1px solid #e2e8f0; "
            "border-radius:9px; padding:10px 13px; font-size:14px; font-weight:600;"
        )
        return label

    @staticmethod
    def _choice_style(mode, inactive=False):
        colors = {
            "trial": ("#eff6ff", "#2563eb", "#93c5fd"),
            "unlocked": ("#ecfdf5", "#15803d", "#86efac"),
            "purchase": ("#f5f3ff", "#6d28d9", "#c4b5fd"),
            "current": ("#ecfdf5", "#15803d", "#86efac"),
            "developing": ("#fffbeb", "#b45309", "#fde68a"),
        }
        background, color, border = colors.get(mode, colors["trial"])
        if inactive and mode == "trial":
            background, color, border = "#e2e8f0", "#64748b", "#cbd5e1"
        return (
            f"QPushButton {{ text-align:left; padding:0 15px; background:{background}; "
            f"color:{color}; border:1px solid {border}; border-radius:9px; "
            "font-size:14px; font-weight:600; }"
            f"QPushButton:disabled {{ background:{background}; color:{color}; "
            f"border:1px solid {border}; }}"
            "QPushButton:hover:enabled { background:#dbeafe; color:#1d4ed8; "
            "border-color:#3b82f6; }"
            "QPushButton:pressed:enabled { background:#bfdbfe; border-color:#2563eb; }"
        )
