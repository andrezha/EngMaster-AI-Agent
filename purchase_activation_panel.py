"""Reusable, in-page purchase and activation workflow."""

from PySide6 import QtCore, QtWidgets

from ui_styles import PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE


class PurchaseActivationPanel(QtWidgets.QFrame):
    """Show all first-purchase steps without a machine-code dialog."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setObjectName("purchase_activation_panel")
        self.setStyleSheet(
            "QFrame#purchase_activation_panel { background:#ffffff; "
            "border:1px solid #dbe3ef; border-radius:11px; }")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 15)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("淘宝客服信息与正式版激活")
        title.setStyleSheet(
            "border:none; color:#0f172a; font-size:17px; font-weight:700;")
        detail = QtWidgets.QLabel(
            "请先在淘宝商品页面选择版本规格并完成付款。客服只根据已付款订单中的商品规格发放对应权限。")
        detail.setWordWrap(True)
        detail.setStyleSheet("border:none; color:#64748b; font-size:13px;")
        layout.addWidget(title)
        layout.addWidget(detail)

        manual_notice = QtWidgets.QLabel(
            "客服人工核验说明：订单付款后，请发送订单卡片和客服核验信息。"
            "客服需要人工核对付款状态、商品规格和授权记录，激活码不会自动即时发送，"
            "请耐心等待淘宝客服处理，请勿重复提交或重复下单。")
        manual_notice.setObjectName("purchase_manual_review_notice")
        manual_notice.setWordWrap(True)
        manual_notice.setStyleSheet(
            "border:1px solid #f59e0b; color:#92400e; background:#fffbeb; "
            "border-radius:8px; padding:9px 11px; font-size:13px; font-weight:600;")
        layout.addWidget(manual_notice)

        if getattr(self.main_window, "license_entitlements", frozenset()):
            upgrade_notice = QtWidgets.QLabel(
                "升级购买提示：升级流程与首次购买相同。客服将在原有权限基础上生成新的累计激活码，"
                "新激活码会同时保留原有版本和本次新增版本。")
            upgrade_notice.setObjectName("purchase_upgrade_notice")
            upgrade_notice.setWordWrap(True)
            upgrade_notice.setStyleSheet(
                "border:1px solid #60a5fa; color:#1e40af; background:#eff6ff; "
                "border-radius:8px; padding:9px 11px; font-size:13px; font-weight:600;")
            layout.addWidget(upgrade_notice)

        layout.addWidget(self._step_label("1", "粘贴已付款的淘宝订单号（必填）"))
        order_row = QtWidgets.QHBoxLayout()
        order_row.setSpacing(8)
        self.order_input = QtWidgets.QLineEdit()
        self.order_input.setObjectName("purchase_order_number")
        self.order_input.setPlaceholderText("请粘贴淘宝订单号")
        self.order_input.setClearButtonEnabled(True)
        self.order_input.setMaxLength(32)
        self.order_input.setMinimumHeight(38)
        self.order_input.setToolTip("订单号用于客服核对买家、付款状态和购买版本")
        self.paste_order_button = QtWidgets.QPushButton("粘贴订单号")
        self.paste_order_button.setObjectName("btn_paste_purchase_order")
        self.paste_order_button.setMinimumHeight(38)
        self.paste_order_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.paste_order_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.paste_order_button.clicked.connect(self._paste_order_number)
        order_row.addWidget(self.order_input, 1)
        order_row.addWidget(self.paste_order_button)
        layout.addLayout(order_row)

        layout.addWidget(self._step_label(
            "2", "将订单号和本机识别码组合成唯一客服核验信息，复制后发送给淘宝客服"))
        machine_row = QtWidgets.QHBoxLayout()
        machine_row.setSpacing(8)
        self.machine_input = QtWidgets.QLineEdit(
            self.main_window.get_purchase_machine_id())
        self.machine_input.setObjectName("purchase_machine_id")
        self.machine_input.setReadOnly(True)
        self.machine_input.setMinimumHeight(38)
        self.machine_input.setToolTip("此识别码用于生成仅适用于当前电脑的激活码")
        self.copy_machine_button = QtWidgets.QPushButton("生成并复制客服核验信息")
        self.copy_machine_button.setObjectName("btn_copy_purchase_machine_id")
        self.copy_machine_button.setMinimumHeight(38)
        self.copy_machine_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.copy_machine_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.copy_machine_button.clicked.connect(self._copy_machine_id)
        machine_row.addWidget(self.machine_input, 1)
        machine_row.addWidget(self.copy_machine_button)
        layout.addLayout(machine_row)

        layout.addWidget(self._step_label("3", "粘贴淘宝客服发送的激活码"))
        activation_row = QtWidgets.QHBoxLayout()
        activation_row.setSpacing(8)
        self.activation_input = QtWidgets.QLineEdit()
        self.activation_input.setObjectName("purchase_activation_code")
        self.activation_input.setPlaceholderText("在这里粘贴完整激活码")
        self.activation_input.setClearButtonEnabled(True)
        self.activation_input.setMinimumHeight(40)
        self.activate_button = QtWidgets.QPushButton("立即激活")
        self.activate_button.setObjectName("btn_purchase_flow_activate")
        self.activate_button.setMinimumHeight(40)
        self.activate_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.activate_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.activate_button.clicked.connect(self._activate)
        self.activation_input.returnPressed.connect(self._activate)
        activation_row.addWidget(self.activation_input, 1)
        activation_row.addWidget(self.activate_button)
        layout.addLayout(activation_row)

        consent_row = QtWidgets.QHBoxLayout()
        self.notice_checkbox = QtWidgets.QCheckBox(
            "我已阅读并同意《用户须知与免责声明》")
        self.notice_checkbox.setObjectName("purchase_notice_consent")
        self.notice_checkbox.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.notice_button = QtWidgets.QPushButton("查看用户须知")
        self.notice_button.setObjectName("btn_purchase_view_notice")
        self.notice_button.setFlat(True)
        self.notice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.notice_button.setStyleSheet(
            "QPushButton { color:#2563eb; border:none; text-decoration:underline; "
            "font-size:13px; } QPushButton:hover { color:#1d4ed8; }")
        self.notice_button.clicked.connect(self.main_window.show_user_notice_page)
        consent_row.addWidget(self.notice_checkbox)
        consent_row.addWidget(self.notice_button)
        consent_row.addStretch(1)
        layout.addLayout(consent_row)

        self.status_label = QtWidgets.QLabel(
            "先填写淘宝订单号，再生成并复制客服核验信息。发送时还需附上订单卡片，客服将核对付款状态和商品规格。")
        self.status_label.setObjectName("purchase_flow_status")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "border:none; color:#64748b; background:#f8fafc; "
            "border-radius:7px; padding:8px 10px; font-size:13px;")
        layout.addWidget(self.status_label)

    @staticmethod
    def _step_label(number, text):
        label = QtWidgets.QLabel(f"{number}. {text}")
        label.setStyleSheet(
            "border:none; color:#334155; font-size:14px; font-weight:700; ")
        return label

    def _copy_machine_id(self):
        order_number = self._normalized_order_number()
        if order_number is None:
            return
        if not order_number:
            self._show_error("请先粘贴已付款的淘宝订单号，再生成并复制客服核验信息。")
            self.order_input.setFocus()
            return
        customer_info = (
            "EngMaster客服核验信息\n"
            f"淘宝订单号：{order_number}\n"
            f"本机识别码：{self.machine_input.text()}\n"
            "请核对我发送的淘宝订单卡片、付款状态和商品规格，"
            "并按该订单规格生成对应的累计激活码。"
        )
        QtWidgets.QApplication.clipboard().setText(customer_info)
        self.status_label.setText(
            "客服信息已复制。请从已付款的对应淘宝订单联系卖家，并同时发送订单卡片；"
            "不要只从店铺首页发送机器码。")
        self.status_label.setStyleSheet(
            "border:none; color:#166534; background:#f0fdf4; "
            "border-radius:7px; padding:8px 10px; font-size:13px;")

    def _paste_order_number(self):
        self.order_input.setText(
            QtWidgets.QApplication.clipboard().text().strip())
        self.order_input.setFocus()

    def _normalized_order_number(self):
        value = "".join(self.order_input.text().split())
        if not value:
            return ""
        if not value.isascii() or not value.isdigit() or not 8 <= len(value) <= 32:
            self._show_error("淘宝订单号格式不正确，请复制订单详情中的数字订单号。")
            self.order_input.setFocus()
            return None
        self.order_input.setText(value)
        return value

    def _activate(self):
        code = self.activation_input.text().strip()
        if not code:
            self._show_error("请先粘贴客服发送的完整激活码。")
            return
        if not self.notice_checkbox.isChecked():
            self._show_error("请先阅读并勾选同意《用户须知与免责声明》。")
            return
        self.activate_button.setEnabled(False)
        ok, message = self.main_window.activate_code_from_page(code)
        self.activate_button.setEnabled(True)
        if ok:
            self.status_label.setText(message)
            self.status_label.setStyleSheet(
                "border:none; color:#166534; background:#f0fdf4; "
                "border-radius:7px; padding:8px 10px; font-size:13px; font-weight:600;")
            self.activation_input.clear()
        else:
            self._show_error(message)

    def _show_error(self, message):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            "border:none; color:#b91c1c; background:#fef2f2; "
            "border-radius:7px; padding:8px 10px; font-size:13px;")
