"""Public quick-start and operation-manual pages for every user."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


_PAGE_BG = "#f4f7fb"

COMMON_QUESTIONS = (
    (
        "体验版为什么不能打印？",
        "体验版保留打印下拉菜单，用来说明正式版支持的打印范围，但不能生成打印文件。正式版仅开放个人错词、短语错词和不规则动词错词打印，完整资料不开放打印。",
    ),
    (
        "词表为什么只显示英语或只显示中文？",
        "先检查词表上方是否选择了“只看英语”或“只看中文”。需要恢复完整内容时，点击“中英对照”即可。",
    ),
    (
        "为什么看不到确认或下一题按钮？",
        "先点击窗口右上角的最大化按钮。窗口未最大化、分辨率较低或系统显示缩放较大时，页面下方控件可能暂时不在可见区域。",
    ),
    (
        "答错后为什么不能直接跳到下一题？",
        "请按照页面提示重新输入正确答案完成本题纠正，然后再进入下一题。",
    ),
    (
        "纠正一次后为什么仍在错词表？",
        "纠正只代表完成当前题目，不等于已经掌握。单词需要在错词闯关中连续答对3次后才会移出错词表。",
    ),
    (
        "错词清空后为什么又出现以前的单词？",
        "下一轮普通闯关会重新验证全部单词；再次答错说明已经遗忘，系统会正常将其重新加入错词表。",
    ),
    (
        "自主录入闯关为什么没有内容？",
        "请先进入“自主登记单词”页面，至少录入一个英语单词和中文解释。",
    ),
    (
        "程序为什么提示已经运行？",
        "先在任务栏查找已经打开的 EngMaster 窗口，不要连续双击重复启动。",
    ),
    (
        "怎样切换英语版本或增加权限？",
        "点击左侧顶部的“免费体验”选择体验级别；点击“正式版管理与购买”切换已解锁英语正式版，并查看购买和授权状态。",
    ),
    (
        "怎样购买英语正式版？",
        "从免费体验点击“前往购买正式版”，进入正式版管理页面；点击统一的“前往淘宝购买”，在淘宝商品规格中选择单版本或组合版本并付款。当前只有高考英语正式版开放，其他组合将在相关版本完成后上线。普通买家填写淘宝订单号；朋友或测试人员可填写客服提供的登记号。生成客服核验信息后发送给对应客服。客服需要人工核对，请耐心等待；收到累计激活码后回到软件粘贴并立即激活。升级购买采用相同流程，新码会保留原有权限并加入新增权限。",
    ),
)


class LearningLoopDiagram(QtWidgets.QWidget):
    """Compact flowchart that makes the repeated mistake-learning cycle visible."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("learning_loop_diagram")
        self.setMinimumHeight(485)
        self.setAccessibleName("推荐学习循环流程图")
        self.setAccessibleDescription(
            "词表学习或直接筛查，进入普通词汇闯关，再依次进行个人错词表背诵、"
            "错词闯关和下一轮普通闯关；有新错词则返回错词表继续循环，无新错词则完成当前范围。"
        )

    @staticmethod
    def _rect(center_x, top, width, height):
        return QtCore.QRectF(center_x - width / 2, top, width, height)

    @staticmethod
    def _draw_arrow(painter, start, end, color="#64748b", width=2.2):
        pen = QtGui.QPen(QtGui.QColor(color), width)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(start, end)
        direction = start - end
        length = max(1.0, (direction.x() ** 2 + direction.y() ** 2) ** 0.5)
        unit_x, unit_y = direction.x() / length, direction.y() / length
        side_x, side_y = -unit_y, unit_x
        arrow_size = 8.0
        point_1 = end + QtCore.QPointF(
            unit_x * arrow_size + side_x * arrow_size * 0.55,
            unit_y * arrow_size + side_y * arrow_size * 0.55,
        )
        point_2 = end + QtCore.QPointF(
            unit_x * arrow_size - side_x * arrow_size * 0.55,
            unit_y * arrow_size - side_y * arrow_size * 0.55,
        )
        painter.setBrush(QtGui.QColor(color))
        painter.drawPolygon(QtGui.QPolygonF([end, point_1, point_2]))

    @staticmethod
    def _draw_node(painter, rect, title, subtitle, background, border):
        painter.setPen(QtGui.QPen(QtGui.QColor(border), 1.6))
        painter.setBrush(QtGui.QColor(background))
        painter.drawRoundedRect(rect, 10, 10)
        title_font = QtGui.QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QtGui.QColor(border))
        title_rect = QtCore.QRectF(rect.left() + 8, rect.top() + 9, rect.width() - 16, 22)
        painter.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignCenter, title)
        detail_font = QtGui.QFont()
        detail_font.setPointSize(8)
        painter.setFont(detail_font)
        painter.setPen(QtGui.QColor("#475569"))
        detail_rect = QtCore.QRectF(rect.left() + 8, rect.top() + 32, rect.width() - 16, rect.height() - 38)
        painter.drawText(
            detail_rect,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
            subtitle,
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        width = float(self.width())
        center_x = width * 0.43
        node_width = min(410.0, max(300.0, width * 0.4))
        node_height = 55.0
        regular = self._rect(center_x, 12, node_width, node_height)
        mistakes = self._rect(center_x, 88, node_width, node_height)
        mistake_challenge = self._rect(center_x, 164, node_width, node_height)
        next_round = self._rect(center_x, 240, node_width, node_height)
        decision = self._rect(center_x, 316, node_width, node_height)
        complete = self._rect(center_x, 407, node_width, node_height)
        return_x = min(width - 34.0, regular.right() + 175.0)

        loop_area = QtCore.QRectF(
            mistakes.left() - 25, mistakes.top() - 23,
            return_x - mistakes.left() + 45, decision.bottom() - mistakes.top() + 44)
        painter.setPen(QtGui.QPen(QtGui.QColor("#fecaca"), 1.4))
        painter.setBrush(QtGui.QColor("#fffafa"))
        painter.drawRoundedRect(loop_area, 14, 14)
        loop_font = QtGui.QFont()
        loop_font.setPointSize(10)
        loop_font.setBold(True)
        painter.setFont(loop_font)
        painter.setPen(QtGui.QColor("#b91c1c"))
        painter.drawText(
            QtCore.QRectF(loop_area.left() + 12, loop_area.top() + 2, 150, 22),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "重复循环训练区",
        )

        self._draw_node(painter, regular, "① 普通词汇闯关", "完整筛查：答错词自动进入个人错词表", "#eff6ff", "#2563eb")
        self._draw_node(painter, mistakes, "② 背诵个人错词表", "只集中学习本轮不会和不稳定的单词", "#fff7ed", "#c2410c")
        self._draw_node(painter, mistake_challenge, "③ 错词闯关至清空", "针对错词反复练习，连续答对后移出", "#f5f3ff", "#7c3aed")
        self._draw_node(painter, next_round, "④ 下一轮普通词汇闯关", "重新验证全部单词，检查是否真正记住", "#ecfdf5", "#059669")
        self._draw_node(painter, decision, "⑤ 这一轮还有新错词吗？", "有：继续循环　　没有：完成当前范围", "#fefce8", "#ca8a04")
        self._draw_node(painter, complete, "当前词表基本掌握", "完整一轮没有产生新错词", "#ecfdf5", "#15803d")

        gap = 7.0
        for upper, lower in (
            (regular, mistakes),
            (mistakes, mistake_challenge),
            (mistake_challenge, next_round),
            (next_round, decision),
        ):
            self._draw_arrow(
                painter,
                QtCore.QPointF(upper.center().x(), upper.bottom() + gap),
                QtCore.QPointF(lower.center().x(), lower.top() - gap),
            )
        self._draw_arrow(
            painter,
            QtCore.QPointF(decision.center().x(), decision.bottom() + gap),
            QtCore.QPointF(complete.center().x(), complete.top() - gap),
            "#15803d",
            2.5,
        )

        return_pen = QtGui.QPen(QtGui.QColor("#dc2626"), 2.6)
        return_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        return_pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(return_pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        return_path = QtGui.QPainterPath(QtCore.QPointF(decision.right() + gap, decision.center().y()))
        return_path.lineTo(return_x, decision.center().y())
        return_path.lineTo(return_x, mistakes.center().y())
        painter.drawPath(return_path)
        self._draw_arrow(
            painter,
            QtCore.QPointF(return_x, mistakes.center().y()),
            QtCore.QPointF(mistakes.right() + gap, mistakes.center().y()),
            "#dc2626",
            2.6,
        )

        label_font = QtGui.QFont()
        label_font.setPointSize(10)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QtGui.QColor("#dc2626"))
        painter.drawText(
            QtCore.QRectF(decision.right() + 16, decision.center().y() - 25,
                          return_x - decision.right() - 22, 22),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            "有新错词：回到②",
        )
        painter.setPen(QtGui.QColor("#15803d"))
        painter.drawText(
            QtCore.QRectF(center_x + 18, decision.bottom() + 8, 125, 24),
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "没有新错词：完成",
        )


def _public_page(title, subtitle):
    page = QtWidgets.QWidget()
    page.setStyleSheet(f"background:{_PAGE_BG};")
    root = QtWidgets.QVBoxLayout(page)
    root.setContentsMargins(32, 25, 32, 30)
    root.setSpacing(15)
    hero = QtWidgets.QFrame()
    hero.setStyleSheet(
        "QFrame { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
        "stop:0 #1d4ed8, stop:1 #0ea5e9); border-radius:15px; }"
    )
    hero_layout = QtWidgets.QVBoxLayout(hero)
    hero_layout.setContentsMargins(25, 20, 25, 20)
    title_label = QtWidgets.QLabel(title)
    title_label.setStyleSheet(
        "border:none; color:white; font-size:26px; font-weight:700; background:transparent;")
    subtitle_label = QtWidgets.QLabel(subtitle)
    subtitle_label.setWordWrap(True)
    subtitle_label.setStyleSheet(
        "border:none; color:#e0f2fe; font-size:14px; background:transparent;")
    hero_layout.addWidget(title_label)
    hero_layout.addWidget(subtitle_label)
    root.addWidget(hero)
    return page, root


class QuickOverviewView(QtWidgets.QWidget):
    """A one-screen explanation shown automatically on first launch."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("quick_overview_view")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        page, layout = _public_page(
            "60秒了解 EngMaster",
            "面向初高中、大学四六级和考研学习者：把手机里容易被打断的碎片化背词，变成电脑上可验证、可追踪的完整训练。",
        )

        standalone = QtWidgets.QFrame()
        standalone.setObjectName("standalone_assurance_card")
        standalone.setStyleSheet(
            "QFrame#standalone_assurance_card { background:#eff6ff; "
            "border:2px solid #60a5fa; border-radius:13px; }")
        standalone_layout = QtWidgets.QVBoxLayout(standalone)
        standalone_layout.setContentsMargins(19, 13, 19, 14)
        standalone_layout.setSpacing(7)
        standalone_title = QtWidgets.QLabel("单机版 · 免安装：让学习环境更简单，也更让人放心")
        standalone_title.setStyleSheet(
            "border:none; color:#1e3a8a; font-size:18px; font-weight:700;")
        standalone_intro = QtWidgets.QLabel(
            "下载一个程序文件，双击即可运行；不需要为学习注册账号，也不需要把手机和社交平台作为学习入口。"
            "正式版激活在本机完成，词表学习、闯关、错词巩固和进度查看也都可以离线使用。"
        )
        standalone_intro.setWordWrap(True)
        standalone_intro.setStyleSheet(
            "border:none; color:#334155; font-size:13px; font-weight:600;")
        standalone_layout.addWidget(standalone_title)
        standalone_layout.addWidget(standalone_intro)

        benefit_row = QtWidgets.QHBoxLayout()
        benefit_row.setSpacing(8)
        benefits = [
            ("免安装", "无需复杂安装流程\n下载后直接运行"),
            ("本地激活", "机器码与激活码\n在本机完成验证"),
            ("减少干扰", "没有消息、聊天\n短视频信息流入口"),
            ("记录在本机", "错词与学习进度\n主要保存在电脑"),
        ]
        for heading, detail in benefits:
            card = QtWidgets.QLabel(f"{heading}\n{detail}")
            card.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            card.setStyleSheet(
                "border:1px solid #bfdbfe; border-radius:9px; background:white; "
                "color:#1e40af; font-size:12px; font-weight:700; padding:8px 6px;")
            benefit_row.addWidget(card, 1)
        standalone_layout.addLayout(benefit_row)

        standalone_note = QtWidgets.QLabel(
            "说明：下载程序或以后主动获取更新时需要网络；程序启动、正式版激活和日常学习均无需联网。"
            "学习数据保存在本机，请自行备份重要记录。"
        )
        standalone_note.setWordWrap(True)
        standalone_note.setStyleSheet(
            "border:none; color:#64748b; font-size:11px;")
        standalone_layout.addWidget(standalone_note)
        layout.addWidget(standalone)

        computer_title = QtWidgets.QLabel("不同学习阶段，都有一个共同问题：手机很难只用来学习")
        computer_title.setStyleSheet(
            "color:#991b1b; font-size:21px; font-weight:700; background:transparent;")
        layout.addWidget(computer_title)

        audience_cards = QtWidgets.QGridLayout()
        audience_cards.setHorizontalSpacing(14)
        audience_cards.addWidget(self._route(
            "初中／高中：学生与家长",
            "家长关心：孩子到底有没有真正完成训练？",
            "孩子拿着手机背词，下一刻可能切到消息、短视频或游戏。家长看不到实际训练量，"
            "孩子也容易在反复切换中失去专注。电脑端把学习放回固定场景，并留下每轮数量、时间和错词记录。",
            "#fff7ed", "#c2410c"), 0, 0)
        audience_cards.addWidget(self._route(
            "大学四六级／考研：学习者本人",
            "自己关心：今天是否完成了真正有效的一轮？",
            "本想用手机背十分钟单词，却被通知、聊天或短视频带走；快速划过很多词，"
            "也难判断自己是否会拼。电脑端减少应用切换，用实体键盘主动作答，并用轮次记录监督自己的进度。",
            "#f5f3ff", "#6d28d9"), 0, 1)
        audience_cards.setColumnStretch(0, 1)
        audience_cards.setColumnStretch(1, 1)
        layout.addLayout(audience_cards)

        shared_value = QtWidgets.QFrame()
        shared_value.setStyleSheet(
            "QFrame { background:#ecfdf5; border:2px solid #34d399; border-radius:12px; }")
        shared_layout = QtWidgets.QVBoxLayout(shared_value)
        shared_layout.setContentsMargins(18, 11, 18, 12)
        shared_layout.setSpacing(4)
        shared_title = QtWidgets.QLabel("电脑端的共同价值：不是年龄定位，而是训练方式的改变")
        shared_title.setStyleSheet(
            "border:none; color:#047857; font-size:15px; font-weight:700;")
        shared_text = QtWidgets.QLabel(
            "固定学习场景　｜　较大显示区域　｜　实体键盘主动拼写　｜　完整轮次验证　｜　"
            "错词自动集中　｜　训练结果留痕"
        )
        shared_text.setWordWrap(True)
        shared_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        shared_text.setStyleSheet(
            "border:none; color:#065f46; font-size:13px; font-weight:700;")
        shared_layout.addWidget(shared_title)
        shared_layout.addWidget(shared_text)
        layout.addWidget(shared_value)

        product_value = QtWidgets.QLabel(
            "你获得的不只是一张电子词表，而是一套能发现不会、集中错词、反复验证并记录进度的系统词汇训练工具。"
        )
        product_value.setWordWrap(True)
        product_value.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        product_value.setStyleSheet(
            "color:white; background:#b91c1c; border-radius:10px; "
            "font-size:15px; font-weight:700; padding:12px 16px;")
        layout.addWidget(product_value)

        computer_hint = QtWidgets.QLabel(
            "手机适合随时查看，电脑更适合系统训练；使用任何屏幕都应保持适当距离并注意休息，错词积累后也可以生成错词打印表进行纸质背诵和默写。"
        )
        computer_hint.setWordWrap(True)
        computer_hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        computer_hint.setStyleSheet(
            "color:#64748b; background:transparent; font-size:12px; padding:0 6px;")
        layout.addWidget(computer_hint)

        routes = QtWidgets.QGridLayout()
        routes.setHorizontalSpacing(14)
        routes.addWidget(self._route(
            "单词基础较弱",
            "先用词汇表学习",
            "使用中英对照、隐藏英语或隐藏中文完成初步记忆，再通过闯关筛查错词。",
            "#eff6ff", "#1d4ed8"), 0, 0)
        routes.addWidget(self._route(
            "单词基础较好",
            "直接普通闯关",
            "已经会的快速通过；答错和掌握不稳定的自动进入个人错词表。",
            "#ecfdf5", "#047857"), 0, 1)
        routes.setColumnStretch(0, 1)
        routes.setColumnStretch(1, 1)
        layout.addLayout(routes)

        loop = QtWidgets.QFrame()
        loop.setStyleSheet(
            "QFrame { background:white; border:1px solid #dce5f0; border-radius:12px; }")
        loop_layout = QtWidgets.QVBoxLayout(loop)
        loop_layout.setContentsMargins(18, 13, 18, 14)
        loop_title = QtWidgets.QLabel("推荐学习循环")
        loop_title.setStyleSheet(
            "border:none; color:#111827; font-size:17px; font-weight:700;")
        flow = LearningLoopDiagram(loop)
        hint = QtWidgets.QLabel(
            "关键不是只练一次：下一轮如果再次产生错词，就回到个人错词表继续循环；"
            "直到完整一轮没有新错词，才说明当前范围基本掌握。"
        )
        hint.setWordWrap(True)
        hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("border:none; color:#64748b; font-size:12px;")
        loop_layout.addWidget(loop_title)
        loop_layout.addWidget(flow)
        loop_layout.addWidget(hint)
        layout.addWidget(loop)

        personal = QtWidgets.QFrame()
        personal.setStyleSheet(
            "QFrame { background:#fff7ed; border:1px solid #fdba74; border-radius:12px; }")
        personal_layout = QtWidgets.QHBoxLayout(personal)
        personal_layout.setContentsMargins(18, 13, 18, 13)
        personal_text = QtWidgets.QLabel(
            "个人词库扩展：阅读理解、课堂、作业或试卷中遇到的新单词，可以录入自己的词汇表并进行自主录入闯关。"
        )
        personal_text.setWordWrap(True)
        personal_text.setStyleSheet(
            "border:none; color:#9a3412; font-size:13px; font-weight:700;")
        personal_layout.addWidget(personal_text, 1)
        layout.addWidget(personal)

        record = QtWidgets.QFrame()
        record.setStyleSheet(
            "QFrame { background:#f0fdf4; border:1px solid #86efac; border-radius:12px; }")
        record_layout = QtWidgets.QVBoxLayout(record)
        record_layout.setContentsMargins(18, 11, 18, 12)
        record_layout.setSpacing(4)
        record_title = QtWidgets.QLabel("学习过程有记录")
        record_title.setStyleSheet(
            "border:none; color:#166534; font-size:14px; font-weight:700;")
        record_text = QtWidgets.QLabel(
            "每轮都会记录开始与结束时间、有效学习时长、验证数量和错词数量。"
            "初高中生家长可以了解孩子当天的实际训练情况；大学四六级和考研学习者可以用来掌握进度、自我监督。"
        )
        record_text.setWordWrap(True)
        record_text.setStyleSheet("border:none; color:#475569; font-size:12px;")
        record_hint = QtWidgets.QLabel("在词汇闯关页面点击“第几轮／本轮进度”即可查看最近50轮记录。")
        record_hint.setWordWrap(True)
        record_hint.setStyleSheet("border:none; color:#15803d; font-size:12px; font-weight:600;")
        record_layout.addWidget(record_title)
        record_layout.addWidget(record_text)
        record_layout.addWidget(record_hint)
        layout.addWidget(record)

        actions = QtWidgets.QHBoxLayout()
        actions.setSpacing(10)
        action_defs = [
            ("基础较弱：从词汇表开始", self.main_window._safe_nav_to_word_list),
            ("基础较好：直接普通闯关", self._open_regular_challenge),
            ("录入我自己的生词", self.main_window._safe_nav_to_self_register),
        ]
        for text, callback in action_defs:
            actions.addWidget(self._action_button(text, callback))
        layout.addLayout(actions)

        more = QtWidgets.QHBoxLayout()
        more.addStretch()
        learning = QtWidgets.QPushButton("查看完整学习方法")
        operation = QtWidgets.QPushButton("查看软件操作说明")
        for button in (learning, operation):
            button.setFixedHeight(32)
            button.setStyleSheet(
                "QPushButton { background:white; color:#2563eb; border:1px solid #93c5fd; "
                "border-radius:8px; padding:0 13px; font-size:12px; }"
                "QPushButton:hover { background:#eff6ff; }"
            )
            more.addWidget(button)
        learning.clicked.connect(self.main_window.show_learning_guide)
        operation.clicked.connect(self.main_window.show_operation_guide)
        layout.addLayout(more)
        layout.addStretch()
        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _route(self, title, subtitle, text, background, accent):
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{background}; border:1px solid {accent}; border-radius:11px; }}")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(17, 13, 17, 14)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            f"border:none; color:{accent}; font-size:16px; font-weight:700;")
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setStyleSheet(
            "border:none; color:#1f2937; font-size:14px; font-weight:600;")
        text_label = QtWidgets.QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("border:none; color:#475569; font-size:13px;")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addWidget(text_label)
        return card

    def _action_button(self, text, callback):
        button = QtWidgets.QPushButton(text + "  →")
        button.setMinimumHeight(42)
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton { background:#2563eb; color:white; border:none; border-radius:9px; "
            "font-size:13px; font-weight:700; padding:0 14px; }"
            "QPushButton:hover { background:#1d4ed8; }"
        )
        button.clicked.connect(callback)
        return button

    def _open_regular_challenge(self):
        if getattr(self.main_window, "vocab_ctrl", None) is not None:
            self.main_window.vocab_ctrl.switch_challenge_mode("regular")
        self.main_window.stack.setCurrentIndex(0)


class OperationGuideView(QtWidgets.QWidget):
    """Task-oriented software manual, separate from learning methodology."""

    BASIC_SECTIONS = [
        (
            "词汇表学习",
            "查看、背诵和筛选内置分级词汇",
            "左侧菜单 → 当前版本词汇表",
            [
                "使用搜索框查找指定单词。",
                "选择“中英对照”同时查看单词和释义。",
                "选择“只看中文”或隐藏英语，根据中文回忆英文拼写。",
                "选择“只看英语”或隐藏中文，根据英文回忆含义。",
                "错词积累后，可在错词表中生成打印表或默写表。",
            ],
            "词汇表用于学习和背诵；是否真正掌握，需要再进入普通词汇闯关验证。",
        ),
        (
            "普通词汇闯关",
            "完整筛查当前版本中的已会和不会单词",
            "左侧菜单 → 当前版本词汇闯关 → 普通词汇闯关",
            [
                "阅读中文、词性或页面提示。",
                "在输入框中独立输入英文答案并确认。",
                "答错后查看正确答案，再输入正确答案完成纠正。",
                "完成当前一轮后继续下一轮复测。",
            ],
            "答错和掌握不稳定的单词会自动进入个人错词表。",
        ),
        (
            "错词表与错词闯关",
            "先集中背诵个人错词，再进行针对性训练",
            "词汇表中的“错词表”／词汇闯关中的“错词闯关”",
            [
                "普通闯关答错后，系统自动建立错词表。",
                "先打开错词表查看、隐藏中英文或生成打印表进行背诵。",
                "再进入错词闯关，集中训练这些单词。",
                "单词连续答对 3 次后自动从错词表移除。",
                "错词表清空后，重新开始下一轮普通词汇闯关。",
            ],
            "错词表清空代表本轮错词完成巩固，不代表永久不会遗忘。",
        ),
        (
            "轮次学习记录",
            "查看实际闯关数量、有效学习时长和错词变化",
            "词汇闯关页面 → 点击“第几轮／本轮进度”提示栏",
            [
                "进入普通词汇闯关、错词闯关或自主录入闯关。",
                "点击页面中的“第几轮／本轮进度／本轮错词”提示栏。",
                "在弹出的记录窗口中选择要查看的闯关类型。",
                "查看每轮的开始时间、结束时间、有效学习时长、验证总数和本轮错词。",
                "初高中家长可以按日期了解孩子当天的实际训练情况；其他学习者可以据此自我监督。",
            ],
            "每种闯关保留最近50轮；进行中的一轮也会显示当前进度。",
        ),
        (
            "自主录入单词",
            "把阅读、课堂、作业和试卷中的生词建立为个人词库",
            "左侧菜单 → 自主登记单词",
            [
                "在“英语单词”输入框填写英文。",
                "在“中文解释”输入框填写含义。",
                "点击“录入”保存到个人词汇表。",
                "使用“中英对照”“只看英语”或“只看中文”进行查看和背诵。",
                "需要时可以修改或删除已经录入的内容。",
                "个人词汇可用于自主录入闯关；完整个人词表暂不提供打印。",
            ],
            "自主词库保存在本机，可以随着真实学习内容不断扩展。",
        ),
        (
            "自主录入闯关",
            "只训练自己录入的个人生词",
            "当前版本词汇闯关 → 自主录入闯关",
            [
                "先在“自主登记单词”页面至少录入一个单词。",
                "进入词汇闯关，选择“自主录入闯关”。",
                "根据个人释义提示输入英文答案。",
                "新增或修改个人词汇后，数量会同步更新。",
            ],
            "内置分级词库负责考试范围，自主录入词库负责学生自己的新单词。",
        ),
        (
            "短语与不规则动词",
            "训练常用搭配和动词变化",
            "左侧菜单 → 常用短语/常用不规则动词闯关",
            [
                "短语表可在核心短语和扩展短语之间切换，并选择中英对照、只看英语或只看中文。",
                "不规则动词表可选择完整对照、看原形默变化或只看中文。",
                "短语闯关中选择核心或扩展关卡。",
                "根据中文提示输入对应英文短语。",
                "不规则动词闯关中填写过去式和过去分词。",
                "答错内容会进入相应错词表进行复习。",
            ],
            "短语、动词和错词进度按照当前英语版本分别保存。",
        ),
        (
            "打印与默写",
            "把软件学习与纸质背诵、学校听写结合",
            "词汇表 → 错词表 → 生成错词打印表",
            [
                "先进入需要复习的错词表。",
                "选择普通对照、看英默中或看中默英。",
                "按需要选择分栏和输出设置。",
                "生成文件后进行纸质背诵或默写。",
            ],
            "体验版不生成打印文件，下拉菜单仅展示正式版可打印范围。正式版仅输出个人错词、短语错词和不规则动词错词；完整资料打印暂不开放。",
        ),
    ]

    @staticmethod
    def _sections():
        """Detailed task manual: purpose, path, full steps, outcome and cautions."""
        return [
            (
                "第一次使用",
                "完成窗口、版本和帮助页面的基本设置",
                "启动软件后",
                [
                    "点击窗口右上角的最大化按钮，建议始终在最大化窗口下学习。",
                    "未激活时直接进入分级体验；已有授权时只会进入激活码包含的正式版本。",
                    "首次进入会自动显示“60秒快速了解”，先认识电脑端优势和推荐学习循环。",
                    "使用左侧菜单进入词汇表、词汇闯关、自主录入、短语或不规则动词功能。",
                    "需要帮助时，随时打开左侧的四个学习帮助页面。",
                ],
                "窗口最大化并选择版本后，即可开始本次学习；帮助页面对所有用户开放。",
                [
                    "找不到“确认／下一题”按钮时，首先检查窗口是否已经最大化。",
                    "关闭软件不会清空已经正常保存的错词、个人词库和学习记录。",
                ],
            ),
            (
                "免费体验版",
                "按自己的学习阶段选择30词体验；未激活和已激活用户都能进入",
                "未激活时直接进入；已激活时点击左侧“免费体验”",
                [
                    "未检测到正式授权时，软件直接进入体验中心，不要求先输入机器码，也不弹体验级别选择框。",
                    "体验中心页面常驻初中、高考、四级、六级和考研五个选择按钮，可随时直接切换。",
                    "已经激活正式版的用户，也可以从版本入口进入体验中心进行演示。",
                    "每类提供难度匹配的30词；打开免费体验中心可查看体验范围和建议顺序。",
                    "先查看体验词汇表，再进入普通词汇闯关筛查不会的单词。",
                    "答错词自动进入体验错词表，可以继续进行错词背诵和错词闯关。",
                    "体验版还提供常用短语和常用不规则动词的表格、普通闯关与错词闯关。",
                    "每类体验开放20条短语和15个不规则动词，用于体验完整操作；当前高考正式版提供完整内容。",
                    "五类体验的进度、错词和轮次记录分别保存，也不与正式版混合。",
                    "需要正式完整词库时，点击体验页底部“前往购买正式版”，进入统一购买管理页面。",
                    "体验页不显示机器码和激活框，购买与客服处理集中在正式版管理页面完成。",
                    "已激活用户从体验版点击“返回正式版”，无需再次输入激活码。",
                ],
                "体验版可以完整验证学习流程，但不包含任何考试版本的正式完整词库。",
                [
                    "体验词库按初中、高考、四级、六级和考研分类，避免难度不适合造成挫败感。",
                    "购买后正式数据重新建立，体验数据不会自动混入或覆盖正式版本。",
                ],
            ),
            (
                "选择英语版本",
                "在一个程序中进入初中、高考、四级、六级或考研词汇",
                "左侧顶部 → 免费体验／正式版管理与购买",
                [
                    "点击“免费体验”后，可选择初中、高考、大学四级、大学六级或考研30词体验。",
                    "点击“正式版管理与购买”后，可切换已解锁英语正式版，并查看未解锁或开发中状态。",
                    "每个正式版本分别显示已解锁、可购买或开发中状态。",
                    "点击统一的“前往淘宝购买”，软件打开淘宝商品页；购买版本完全由用户在淘宝商品规格中选择。",
                    "淘宝商品可以提供单版本或组合版本规格；组合规格可一次购买多个已经开放的正式版。",
                    "普通买家填写淘宝订单号；朋友或测试人员填写客服提供的登记号。",
                    "点击“生成并复制客服核验信息”，将订单号和机器码信息发送给对应客服。",
                    "客服按订单号核对对应登记记录后生成权限；机器码本身不代表购买版本。",
                    "客服采用人工核验，激活码不会自动即时发送，请耐心等待淘宝客服处理，不要重复下单。",
                    "取得客服提供的单机激活码后，回到页面粘贴并点击“立即激活”。",
                    "高考英语是当前 V1.0 唯一开放购买的正式版；激活后显示绿色“已解锁”。",
                    "初中、四级、六级和考研正式版标记为“开发中”，暂不开放购买和进入。",
                    "五个级别均可使用30词免费体验，体验数据不会混入高考正式版。",
                    "购买高考英语正式版后，输入客服提供的单机激活码完成本地激活。",
                    "进入主界面后，词汇表和闯关名称会按照所选版本显示。",
                    "软件会记住本次选择，下次启动自动进入上次使用的版本。",
                ],
                "当前 V1.0 的正式授权只开放高考英语；程序结构保留以后增加版本的能力。",
                [
                    "激活和追加权限都在本机离线验证，不需要联网。",
                    "后续正式版本开放时，新增权限仍会采用累计激活方式保留已有权限。",
                    "升级购买与首次购买流程相同；客服核对新订单后生成同时包含原权限和新增权限的新累计激活码。",
                    "各版本的内置词库、短语、错词和学习进度分别保存。",
                ],
            ),
            (
                "词汇表学习",
                "查看、搜索、背诵和筛选当前版本的内置分级词汇",
                "左侧菜单 → 当前版本词汇表",
                [
                    "先确认当前显示的是常规词表、错词表还是自主录入词表。",
                    "使用搜索框快速查找指定单词。",
                    "选择中英对照，同时查看英文和中文释义。",
                    "隐藏英语，根据中文回忆英文拼写；隐藏中文，根据英文回忆含义。",
                    "基础薄弱时先分段背诵；基础较好时可以直接进入普通闯关筛查。",
                    "错词积累后，可以生成错词打印表或默写表进行脱屏学习。",
                ],
                "词汇表负责学习和查看，是否真正掌握仍需通过普通词汇闯关验证。",
                [
                    "“看过”不代表会拼写，建议隐藏英语主动回忆，或直接闯关验证。",
                    "错词表和自主录入词表也可以在词汇表页面中查看。",
                ],
            ),
            (
                "普通词汇闯关",
                "完整筛查当前版本中已经会和仍不会的单词",
                "左侧菜单 → 当前版本词汇闯关 → 普通词汇闯关",
                [
                    "先把软件窗口最大化，确认输入框、确认按钮和下一题区域都能完整显示。",
                    "选择普通词汇闯关，阅读中文释义、词性和页面提示。",
                    "不查看词汇表，独立输入英文答案并提交。",
                    "答对后进入下一题；答错后先查看系统显示的正确答案。",
                    "按照提示重新输入正确答案完成纠正，不能直接跳过当前题。",
                    "首次答错的单词会自动进入个人错词表。",
                    "点击下一题继续，直到本轮全部单词完成并自动保存轮次结果。",
                ],
                "普通闯关会把整张大词表逐步筛选为只属于自己的错词范围。",
                [
                    "看不到“确认／下一题”时，请先点击右上角最大化按钮；非最大化窗口可能隐藏页面下方控件。",
                    "提示后重新输入正确答案属于纠正，不等于本题首次答对。",
                ],
            ),
            (
                "错词表与错词闯关",
                "先背诵个人错词，再通过针对性训练完成巩固",
                "词汇表中的错词表／词汇闯关中的错词闯关",
                [
                    "普通闯关答错后，系统自动把单词加入个人错词表。",
                    "先打开错词表，使用中英对照、隐藏中英文或打印表集中背诵。",
                    "完成初步记忆后，进入错词闯关。",
                    "根据提示独立输入答案；答错时，连续正确次数会重新计算。",
                    "单词连续答对3次后，系统自动将其从单词错词表移除。",
                    "错词表清空后，返回普通闯关开始下一轮完整验证。",
                ],
                "错词表清空只代表本轮错词完成巩固，下一轮负责检查是否遗忘。",
                [
                    "下一轮再次答错同一个词时，它会重新进入错词表，这是正常复测结果。",
                    "不要只反复刷错词；清空后必须回到普通闯关验证全部单词。",
                ],
            ),
            (
                "自主录入与闯关",
                "把真实学习中遇到的生词建立成个人词库并单独训练",
                "左侧菜单 → 自主登记单词／词汇闯关 → 自主录入闯关",
                [
                    "在英语单词输入框填写英文，在中文解释输入框填写含义。",
                    "点击录入并在个人词汇列表中检查保存结果。",
                    "根据背诵需要切换中英对照、只看英语或只看中文。",
                    "需要时可以修改英文、中文解释或删除已经录入的条目。",
                    "阅读理解、课堂、作业、试卷和课外阅读中的生词都可以持续加入。",
                    "返回词汇闯关页面，选择自主录入闯关。",
                    "根据自己填写的中文释义输入英文答案，完成个人词库训练。",
                ],
                "内置词库负责考试范围，自主录入词库负责学习者自己的新增生词。",
                [
                    "英语和中文解释都不能为空，录入前建议检查拼写。",
                    "自主词库为空时不能开始闯关，请先至少录入一个单词。",
                ],
            ),
            (
                "常用短语闯关",
                "按照关卡训练常用英语搭配，并建立短语错词表",
                "左侧菜单 → 常用短语／常用不规则动词闯关 → 常用短语闯关",
                [
                    "先选择要训练的核心关卡或拓展关卡。",
                    "每关50个左右，用户可以自行选择关卡，不必固定顺序。",
                    "根据中文提示输入完整英文短语。",
                    "答错后查看正确答案，并按照页面提示完成纠正。",
                    "答错短语进入短语错词表，可以再用短语错词闯关集中复习。",
                    "各关进度分别保存，切换关卡不会覆盖其他关卡。",
                ],
                "完成核心关卡后可以继续拓展关卡，短语错词统一进入当前版本错词表。",
                [
                    "页面显示的是本关进度和本关错词，不是全部短语总量。",
                    "高考、四级、六级和考研短语分别保存，便于以后独立扩展。",
                ],
            ),
            (
                "不规则动词闯关",
                "训练动词原形、过去式和过去分词的准确拼写",
                "常用短语／常用不规则动词闯关 → 常用不规则动词闯关",
                [
                    "切换到常用不规则动词闯关。",
                    "根据动词原形或页面提示，填写过去式和过去分词。",
                    "提交后同时检查两种变化形式是否正确。",
                    "答错后查看正确形式，并重新输入完成纠正。",
                    "错误项目进入不规则动词错词表。",
                    "进入相应错词闯关，反复训练仍不稳定的动词。",
                ],
                "不规则动词与短语分别记录进度和错词，不会混入普通单词错词表。",
                [
                    "过去式和过去分词都要填写完整，不能只填写其中一项。",
                    "词库认可的拼写变体会按照允许答案进行判断。",
                ],
            ),
            (
                "轮次学习记录",
                "查看实际闯关数量、有效学习时长和错词变化",
                "词汇闯关页面 → 点击第几轮／本轮进度／本轮错词提示栏",
                [
                    "进入普通词汇闯关、错词闯关或自主录入闯关。",
                    "点击页面中的轮次和进度提示栏，它不仅是显示文字，也是记录入口。",
                    "在弹出的记录窗口中选择要查看的闯关类型。",
                    "查看每轮状态、开始时间、结束时间和有效学习时长。",
                    "查看本轮验证总数、进行中进度和本轮错词数量。",
                    "初高中生家长可以按日期了解实际训练；四六级和考研用户可用于自我监督。",
                ],
                "每种闯关保留最近50轮，当前进行中的一轮也会显示实时进度。",
                [
                    "记录的是实际闯关过程，不只是软件是否被打开。",
                    "同一天完成多轮时，可以根据日期逐轮查看。",
                ],
            ),
            (
                "打印与默写",
                "把电脑训练与纸质背诵、学校听写和脱屏复习结合",
                "词汇表 → 错词表 → 生成错词打印表",
                [
                    "先进入词汇表并打开个人错词表。",
                    "选择个人错词、短语错词或不规则动词错词。",
                    "选择普通中英对照、看英默中或看中默英。",
                    "根据需要选择分栏和输出设置。",
                    "选择保存位置并生成文件。",
                    "打开生成文件进行打印、纸质背诵或学校式默写。",
                ],
                "体验版不支持打印，下拉菜单仅用于查看正式版可打印范围。正式版打印可以减少持续看屏幕的时间，并把软件筛查结果带到纸面复习。",
                [
                    "打印前确认错词表中已有需要复习的内容。",
                    "看中默英适合检查拼写，看英默中适合检查词义。",
                ],
            ),
        ]

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("operation_guide_view")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page, layout = _public_page(
            "软件操作说明",
            "按功能查看入口、完整步骤、结果保存和常见问题。学习理念与训练循环请查看“学习方法指南”。",
        )
        maximize_notice = QtWidgets.QFrame()
        maximize_notice.setObjectName("maximize_window_notice")
        maximize_notice.setStyleSheet(
            "QFrame { background:#fef2f2; border:2px solid #ef4444; border-radius:10px; }")
        notice_layout = QtWidgets.QVBoxLayout(maximize_notice)
        notice_layout.setContentsMargins(16, 9, 16, 10)
        notice_layout.setSpacing(3)
        notice_title = QtWidgets.QLabel("重要：建议最大化窗口使用")
        notice_title.setStyleSheet(
            "border:none; color:#b91c1c; font-size:15px; font-weight:700;")
        notice_text = QtWidgets.QLabel(
            "窗口没有最大化时，受屏幕大小、分辨率或系统显示缩放影响，闯关页面下方的“确认／下一题”按钮可能暂时不在可见区域。"
            "如果找不到按钮，请先点击窗口右上角的最大化按钮。"
        )
        notice_text.setWordWrap(True)
        notice_text.setStyleSheet("border:none; color:#7f1d1d; font-size:12px;")
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)
        layout.addWidget(maximize_notice)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.section_list = QtWidgets.QListWidget()
        self.section_list.setFixedWidth(230)
        self.section_list.setSpacing(3)
        self.section_list.setStyleSheet(
            "QListWidget { background:white; border:1px solid #dce5f0; border-radius:10px; "
            "padding:7px; font-size:14px; }"
            "QListWidget::item { min-height:38px; border-radius:7px; padding-left:10px; }"
            "QListWidget::item:selected { background:#2563eb; color:white; }"
            "QListWidget::item:hover:!selected { background:#eff6ff; }"
        )
        self.manual_stack = QtWidgets.QStackedWidget()
        for title, purpose, entrance, steps, result, tips in self._sections():
            self.section_list.addItem(title)
            self.manual_stack.addWidget(
                self._manual_page(title, purpose, entrance, steps, result, tips))
        self.section_list.currentRowChanged.connect(
            self.manual_stack.setCurrentIndex)
        self.section_list.setCurrentRow(0)
        splitter.addWidget(self.section_list)
        splitter.addWidget(self.manual_stack)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        outer.addWidget(page)

    def _manual_page(self, title, purpose, entrance, steps, result, tips):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #dce5f0; border-radius:11px; }")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(24, 21, 24, 22)
        layout.setSpacing(12)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            "border:none; color:#111827; font-size:22px; font-weight:700;")
        purpose_label = QtWidgets.QLabel("功能作用：" + purpose)
        purpose_label.setWordWrap(True)
        purpose_label.setStyleSheet(
            "border:none; color:#334155; font-size:14px; font-weight:600;")
        entrance_label = QtWidgets.QLabel("入口位置：" + entrance)
        entrance_label.setWordWrap(True)
        entrance_label.setStyleSheet(
            "border:none; color:#1d4ed8; background:#eff6ff; border-radius:8px; "
            "font-size:13px; padding:9px;"
        )
        steps_title = QtWidgets.QLabel("操作步骤")
        steps_title.setStyleSheet(
            "border:none; color:#111827; font-size:16px; font-weight:700;")
        layout.addWidget(title_label)
        layout.addWidget(purpose_label)
        layout.addWidget(entrance_label)
        layout.addWidget(steps_title)
        for index, step in enumerate(steps, 1):
            label = QtWidgets.QLabel(f"{index}. {step}")
            label.setWordWrap(True)
            label.setStyleSheet(
                "border:none; color:#475569; background:#f8fafc; border-radius:7px; "
                "font-size:13px; padding:8px 10px;"
            )
            layout.addWidget(label)
        result_label = QtWidgets.QLabel("完成后：" + result)
        result_label.setWordWrap(True)
        result_label.setStyleSheet(
            "border:none; color:#0f766e; background:#ecfdf5; border-radius:8px; "
            "font-size:13px; font-weight:600; padding:10px;"
        )
        layout.addWidget(result_label)
        tips_title = QtWidgets.QLabel("重要提示与常见疑问")
        tips_title.setStyleSheet(
            "border:none; color:#92400e; font-size:15px; font-weight:700;")
        layout.addWidget(tips_title)
        tips_text = QtWidgets.QLabel("\n".join(f"• {tip}" for tip in tips))
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet(
            "border:none; color:#78350f; background:#fffbeb; border-radius:8px; "
            "font-size:13px; padding:10px 12px;"
        )
        layout.addWidget(tips_text)
        layout.addStretch()
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(frame)
        return scroll


class InformationTextView(QtWidgets.QWidget):
    """Scrollable in-app document used for notices and version information."""

    def __init__(self, title, subtitle, text, object_name, parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page, layout = _public_page(title, subtitle)
        self.text_view = QtWidgets.QPlainTextEdit()
        self.text_view.setObjectName(object_name + "_text")
        self.text_view.setReadOnly(True)
        self.text_view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.text_view.setStyleSheet(
            "QPlainTextEdit { background:white; color:#334155; border:1px solid #dce5f0; "
            "border-radius:10px; padding:16px; "
            "font-family:'Microsoft YaHei UI','Microsoft YaHei'; "
            "font-size:14px; selection-background-color:#bfdbfe; }"
        )
        self.set_text(text)
        layout.addWidget(self.text_view, 1)
        outer.addWidget(page)

    def set_text(self, text):
        self.text_view.setPlainText(text or "")
        cursor = self.text_view.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.Start)
        self.text_view.setTextCursor(cursor)


class AboutCopyrightView(QtWidgets.QWidget):
    """Three-part public record for version, copyright, and data licenses."""

    def __init__(
            self, version_text, copyright_text, data_notice_text,
            license_documents=None, parent=None):
        super().__init__(parent)
        self.setObjectName("about_copyright_view")
        self.license_documents = dict(license_documents or {})
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page, layout = _public_page(
            "关于、版权与许可",
            "查看软件版本、权利说明、数据来源及第三方开放许可证。",
        )

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("about_copyright_tabs")
        self.tabs.setDocumentMode(True)
        self.version_text_view = self._text_view("about_version_text", version_text)
        self.copyright_text_view = self._text_view(
            "about_copyright_text", copyright_text)
        self.data_notice_text_view = self._text_view(
            "about_data_notice_text", data_notice_text)
        self.tabs.addTab(self.version_text_view, "版本与授权")
        self.tabs.addTab(self.copyright_text_view, "版权说明")

        data_tab = QtWidgets.QWidget()
        data_layout = QtWidgets.QVBoxLayout(data_tab)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(10)
        data_layout.addWidget(self.data_notice_text_view, 1)
        if self.license_documents:
            button_row = QtWidgets.QHBoxLayout()
            button_row.addStretch(1)
            for index, title in enumerate(self.license_documents):
                button = QtWidgets.QPushButton(f"查看{title}")
                button.setObjectName(f"btn_about_license_{index}")
                button.setMinimumHeight(38)
                button.clicked.connect(
                    lambda _checked=False, name=title: self.show_license_document(name)
                )
                button_row.addWidget(button)
            data_layout.addLayout(button_row)
        self.tabs.addTab(data_tab, "数据来源与第三方许可")
        layout.addWidget(self.tabs, 1)
        outer.addWidget(page)

    @staticmethod
    def _text_view(object_name, text):
        view = QtWidgets.QPlainTextEdit()
        view.setObjectName(object_name)
        view.setReadOnly(True)
        view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        view.setPlainText(text or "")
        view.setStyleSheet(
            "QPlainTextEdit { background:white; color:#334155; "
            "border:1px solid #dce5f0; border-radius:10px; padding:16px; "
            "font-family:'Microsoft YaHei UI','Microsoft YaHei'; font-size:14px; "
            "selection-background-color:#bfdbfe; }"
        )
        return view

    def set_version_text(self, text):
        self.version_text_view.setPlainText(text or "")

    def show_license_document(self, title):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(760, 600)
        layout = QtWidgets.QVBoxLayout(dialog)
        text_view = QtWidgets.QPlainTextEdit()
        text_view.setReadOnly(True)
        text_view.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        text_view.setPlainText(self.license_documents.get(title, "未找到许可证正文。"))
        layout.addWidget(text_view, 1)
        close_button = QtWidgets.QPushButton("关闭")
        close_button.clicked.connect(dialog.accept)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)
        dialog.exec()


class CommonQuestionsView(QtWidgets.QWidget):
    """Standalone FAQ page opened directly from the left navigation."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("common_questions_view")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        page, layout = _public_page(
            "常见问题",
            "遇到显示、闯关、错词或启动问题时，可以先在这里快速检查。",
        )

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 8, 12)
        content_layout.setSpacing(10)
        for question, answer in COMMON_QUESTIONS:
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame { background:white; border:1px solid #dce5f0; border-radius:10px; }"
            )
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(18, 13, 18, 14)
            card_layout.setSpacing(6)
            question_label = QtWidgets.QLabel(question)
            question_label.setWordWrap(True)
            question_label.setStyleSheet(
                "border:none; color:#1e3a8a; font-size:15px; font-weight:700;"
            )
            answer_label = QtWidgets.QLabel(answer)
            answer_label.setWordWrap(True)
            answer_label.setStyleSheet(
                "border:none; color:#475569; font-size:13px; line-height:1.6;"
            )
            card_layout.addWidget(question_label)
            card_layout.addWidget(answer_label)
            content_layout.addWidget(card)
        content_layout.addStretch()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        outer.addWidget(page)
