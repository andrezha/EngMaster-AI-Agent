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
        "页面支持常见笔记本窗口和最大化显示。窗口较小时可向下滚动；如果仍看不到，请适当扩大窗口。",
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
        "先在任务栏查找已经打开的英思成窗口，不要连续双击重复启动。",
    ),
    (
        "怎样切换英语版本或增加权限？",
        "点击左侧顶部的“免费体验”选择体验级别；点击“正式版管理与购买”切换已解锁英语正式版，并查看购买和授权状态。",
    ),
    (
        "怎样购买英语正式版？",
        "从免费体验点击“前往购买正式版”，进入正式版管理页面；点击统一的“前往淘宝购买”，在淘宝商品规格中选择初中版、高中版或组合版本并付款。普通买家填写淘宝订单号；朋友或测试人员可填写客服提供的登记号。生成客服核验信息后发送给对应客服。客服需要人工核对，请耐心等待；收到累计激活码后回到软件粘贴并立即激活。升级购买采用相同流程，新码会保留原有权限并加入新增权限。",
    ),
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
        edition_id = str(getattr(getattr(main_window, "edition", None), "edition_id", "gaokao"))
        junior = edition_id.removeprefix("trial_") == "zhongkao"
        self.setObjectName("quick_overview_view")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        page, layout = _public_page(
            "60秒了解英思成",
            ("面向准初一、初一、初二和初三学生：一套初中核心词汇，覆盖提前预习、课内同步和中考备考。"
             if junior else
             "面向准高一、高一、高二和高三学生：一套高中3800词，覆盖提前预习、课内同步和高考备考。"),
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

        computer_title = QtWidgets.QLabel(
            "从准初一预习到初三中考，每个阶段都有明确用法"
            if junior else "从准高一预习到高三备考，每个阶段都有明确用法")
        computer_title.setStyleSheet(
            "color:#991b1b; font-size:21px; font-weight:700; background:transparent;")
        layout.addWidget(computer_title)

        audience_cards = QtWidgets.QGridLayout()
        audience_cards.setHorizontalSpacing(12)
        audience_cards.setVerticalSpacing(12)
        audience_defs = ((
            ("准初一", "提前预习", "提前认识初中核心词汇，进入初中后更从容。", "#f5f3ff", "#7c3aed"),
            ("初一", "课程同步", "配合课本和课堂持续背诵，打好初中词汇基础。", "#eff6ff", "#2563eb"),
            ("初二", "积累补弱", "继续扩充词汇，并通过闯关找出薄弱部分。", "#ecfdf5", "#047857"),
            ("初三", "中考备考", "系统复习初中核心词汇，反复验证掌握情况。", "#fff7ed", "#c2410c"),
        ) if junior else (
            ("准高一", "提前预习", "提前认识高中核心词汇，进入高中后更从容。", "#f5f3ff", "#7c3aed"),
            ("高一", "课程同步", "配合课本和课堂持续背诵，打好高中词汇基础。", "#eff6ff", "#2563eb"),
            ("高二", "积累补弱", "继续扩充词汇，并通过闯关找出薄弱部分。", "#ecfdf5", "#047857"),
            ("高三", "高考备考", "系统复习高中3800词，反复验证掌握情况。", "#fff7ed", "#c2410c"),
        ))
        for index, definition in enumerate(audience_defs):
            audience_cards.addWidget(
                self._route(*definition), index // 2, index % 2)
        audience_cards.setColumnStretch(0, 1)
        audience_cards.setColumnStretch(1, 1)
        layout.addLayout(audience_cards)

        shared_value = QtWidgets.QFrame()
        shared_value.setStyleSheet(
            "QFrame { background:#ecfdf5; border:2px solid #34d399; border-radius:12px; }")
        shared_layout = QtWidgets.QVBoxLayout(shared_value)
        shared_layout.setContentsMargins(18, 11, 18, 12)
        shared_layout.setSpacing(4)
        shared_title = QtWidgets.QLabel(
            "三个学习目的，一套初中核心词汇"
            if junior else "三个学习目的，一套高中3800词")
        shared_title.setStyleSheet(
            "border:none; color:#047857; font-size:15px; font-weight:700;")
        shared_text = QtWidgets.QLabel(
            "提前预习　｜　课内同步背诵　｜　中考系统备考"
            if junior else "提前预习　｜　课内同步背诵　｜　高考系统备考"
        )
        shared_text.setWordWrap(True)
        shared_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        shared_text.setStyleSheet(
            "border:none; color:#065f46; font-size:13px; font-weight:700;")
        shared_layout.addWidget(shared_title)
        shared_layout.addWidget(shared_text)
        layout.addWidget(shared_value)

        product_value = QtWidgets.QLabel(
            "背得快：高效记忆　｜　找得准：闯关识弱　｜　补得全：自主登记"
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
        routes.setHorizontalSpacing(12)
        core_defs = (
            ("高效记忆", "让单词先形成联系", "通过主题场景、词根、音形拼读和同义反义，建立更清楚的记忆线索。", "#f5f3ff", "#7c3aed"),
            ("闯关识弱", "找出真正不会的词", "主动输入英文答案，把不会和掌握不稳定的单词自动整理进个人错词表。", "#eff6ff", "#2563eb"),
            ("自主登记", "补充自己的学习范围", "课本、课堂、作业、试卷和阅读中遇到的生词，可以收进个人词库继续训练。", "#ecfdf5", "#047857"),
        )
        for index, definition in enumerate(core_defs):
            routes.addWidget(self._route(*definition), 0, index)
            routes.setColumnStretch(index, 1)
        layout.addLayout(routes)

        loop = QtWidgets.QFrame()
        loop.setStyleSheet(
            "QFrame { background:white; border:1px solid #dce5f0; border-radius:12px; }")
        loop_layout = QtWidgets.QVBoxLayout(loop)
        loop_layout.setContentsMargins(18, 13, 18, 14)
        loop_title = QtWidgets.QLabel("推荐学习方法")
        loop_title.setStyleSheet(
            "border:none; color:#111827; font-size:17px; font-weight:700;")
        methods = QtWidgets.QHBoxLayout()
        methods.setSpacing(10)
        method_defs = (
            ("① 先选记忆分类", "默认从主题场景开始，也可以选择词根、音形拼读或同义反义。", "#f5f3ff", "#7c3aed"),
            ("② 每次只学一组", "理解当前小组的联系，使用“本组掌握验证”隐藏英语并主动回忆。", "#eff6ff", "#2563eb"),
            ("③ 再用闯关识弱", "完成若干小组后进入普通闯关，把不会和不稳定的词自动筛出来。", "#ecfdf5", "#047857"),
        )
        for title, text, background, accent in method_defs:
            methods.addWidget(
                self._route(
                    title,
                    "初中词汇提分速记" if junior else "3800词提分速记",
                    text, background, accent),
                1,
            )
        hint = QtWidgets.QLabel(
            "自主登记用于随时补充课本、课堂、作业、试卷和阅读生词；它可以和上述方法同时使用。"
        )
        hint.setWordWrap(True)
        hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("border:none; color:#64748b; font-size:12px;")
        loop_layout.addWidget(loop_title)
        loop_layout.addLayout(methods)
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
            "学生可以掌握自己的实际进度，家长也可以了解当天完成了多少有效训练。"
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
            ("开始高效记忆", self.main_window._safe_nav_to_scientific_memory),
            ("开始闯关识弱", self._open_regular_challenge),
            ("自主登记生词", self.main_window._safe_nav_to_self_register),
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
            "内置分级词库负责阶段性复习范围，自主录入词库负责学生自己的新单词。",
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
                    "软件支持常见笔记本窗口和最大化显示，可根据使用习惯调整窗口大小。",
                    "未激活时直接进入分级体验；已有授权时只会进入激活码包含的正式版本。",
                    "首次进入会自动显示“60秒快速了解”，先认识适用年级、三大核心功能和推荐学习方法。",
                    "使用左侧菜单进入词汇表、词汇闯关、自主录入、短语或不规则动词功能。",
                    "需要帮助时，随时打开左侧的四个学习帮助页面。",
                ],
                "选择版本后即可开始本次学习；帮助页面对所有用户开放。",
                [
                    "窗口较小时，页面内容会调整排列；需要时可向下滚动或适当扩大窗口。",
                    "关闭软件不会清空已经正常保存的错词、个人词库和学习记录。",
                ],
            ),
            (
                "免费体验版",
                "按自己的学习阶段选择30词体验；未激活和已激活用户都能进入",
                "未激活时直接进入；已激活时点击左侧“免费体验”",
                [
                    "未检测到正式授权时，软件直接进入体验中心，不要求先输入机器码，也不弹体验级别选择框。",
                    "体验中心只显示已经开放正式版所对应的体验入口。",
                    "已经激活正式版的用户，也可以从版本入口进入体验中心进行演示。",
                    "每类提供难度匹配的30词；打开免费体验中心可查看体验范围和建议顺序。",
                    "先查看体验词汇表，再进入普通词汇闯关筛查不会的单词。",
                    "答错词自动进入体验错词表，可以继续进行错词背诵和错词闯关。",
                    "体验版还提供常用短语和常用不规则动词的表格、普通闯关与错词闯关。",
                    "当前开放初中英语和高中3800词体验；以后正式版开放时，对应体验同步开放。",
                    "体验版的进度、错词和轮次记录独立保存，不与正式版混合。",
                    "需要正式完整词库时，点击体验页底部“前往购买正式版”，进入统一购买管理页面。",
                    "体验页不显示机器码和激活框，购买与客服处理集中在正式版管理页面完成。",
                    "已激活用户从体验版点击“返回正式版”，无需再次输入激活码。",
                ],
                "体验版可以完整验证学习流程，但不包含任何考试版本的正式完整词库。",
                [
                    "体验词汇从对应正式词库中选取，保证体验内容与发布版同步。",
                    "购买后正式数据重新建立，体验数据不会自动混入或覆盖正式版本。",
                ],
            ),
            (
                "选择英语版本",
                "在一个程序中进入已经正式开放的英语词汇版本",
                "左侧顶部 → 免费体验／正式版管理与购买",
                [
                    "点击“免费体验”后，可进入当前已开放正式版对应的30词体验。",
                    "点击“正式版管理与购买”后，可切换已解锁英语正式版，并查看未解锁或开发中状态。",
                    "每个正式版本分别显示已解锁、可购买或开发中状态。",
                    "点击统一的“前往淘宝购买”，软件打开淘宝商品页；购买版本完全由用户在淘宝商品规格中选择。",
                    "淘宝商品可以提供单版本或组合版本规格；组合规格可一次购买多个已经开放的正式版。",
                    "普通买家填写淘宝订单号；朋友或测试人员填写客服提供的登记号。",
                    "点击“生成并复制客服核验信息”，将订单号和机器码信息发送给对应客服。",
                    "客服按订单号核对对应登记记录后生成权限；机器码本身不代表购买版本。",
                    "客服采用人工核验，激活码不会自动即时发送，请耐心等待淘宝客服处理，不要重复下单。",
                    "取得客服提供的单机激活码后，回到页面粘贴并点击“立即激活”。",
                    "初中英语和高中3800词是当前 V1.0 已开放购买的正式版；激活后显示绿色“已解锁”。",
                    "四级、六级和考研正式版标记为“开发中”，暂不开放购买和进入。",
                    "体验版与正式版一一对应，体验数据不会混入对应正式版。",
                    "购买初中版、高中版或组合版后，输入客服提供的单机激活码完成本地激活。",
                    "进入主界面后，词汇表和闯关名称会按照所选版本显示。",
                    "软件会记住本次选择，下次启动自动进入上次使用的版本。",
                ],
                "当前 V1.0 的正式授权已开放初中英语和高中3800词；程序结构保留以后增加版本的能力。",
                [
                    "激活和追加权限都在本机离线验证，不需要联网。",
                    "后续正式版本开放时，新增权限仍会采用累计激活方式保留已有权限。",
                    "升级购买与首次购买流程相同；客服核对新订单后生成同时包含原权限和新增权限的新累计激活码。",
                    "各版本的内置词库、短语、错词和学习进度分别保存。",
                ],
            ),
            (
                "词汇提分速记",
                "按可靠的主题、构词或音形联系分组记忆单词",
                "左侧菜单 → 初中词汇提分速记／3800词提分速记",
                [
                    "进入后先显示主题场景、词根记忆、音形拼读和同义反义四种分类总入口。体验版进入任一分类目录时，购买入口都会紧邻当前分类标题显示。",
                    "先在目录中选择一个主题或记忆组；可以使用顶部搜索框查找主题、分组或单词。",
                    "打开分组后，先理解组内单词为什么放在一起，再结合音标、中文含义进行记忆。",
                    "点击“本主题掌握验证”或当前方法对应的验证按钮，页面会隐藏英文并保留音标和中文。",
                    "根据提示主动回忆英文；检查完成后点击“取消验证”恢复显示。",
                    "使用“上一组”“下一组”连续学习，也可以返回目录改用其他记忆方法。",
                ],
                "提分速记用于建立可靠联系，不代替完整词表和闯关；学完若干小组后应进入普通词汇闯关验证。",
                [
                    "主题场景只收录主题明确、能够自然归类的词，不会为了覆盖整张词表而硬塞抽象词或功能词。",
                    "同一个单词不一定适合所有记忆方法；目录中没有出现不代表它不属于当前版本词表。",
                    "初中版与高中版使用各自独立的主题目录，数据互不混用。",
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
                    "进入页面后确认输入框、确认按钮和下一题区域均可见；窗口较小时可向下滚动。",
                    "选择普通词汇闯关，阅读中文释义、词性和页面提示。",
                    "不查看词汇表，独立输入英文答案并提交。",
                    "答对后进入下一题；答错后先查看系统显示的正确答案。",
                    "按照提示重新输入正确答案完成纠正，不能直接跳过当前题。",
                    "首次答错的单词会自动进入个人错词表。",
                    "点击下一题继续，直到本轮全部单词完成并自动保存轮次结果。",
                ],
                "普通闯关会把整张大词表逐步筛选为只属于自己的错词范围。",
                [
                    "看不到“确认／下一题”时，可向下滚动或适当扩大窗口。",
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
                "内置词库负责阶段性复习范围，自主录入词库负责学习者自己的新增生词。",
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
        window_notice = QtWidgets.QFrame()
        window_notice.setObjectName("window_display_notice")
        window_notice.setStyleSheet(
            "QFrame { background:#fef2f2; border:2px solid #ef4444; border-radius:10px; }")
        notice_layout = QtWidgets.QVBoxLayout(window_notice)
        notice_layout.setContentsMargins(16, 9, 16, 10)
        notice_layout.setSpacing(3)
        notice_title = QtWidgets.QLabel("窗口显示与滚动说明")
        notice_title.setStyleSheet(
            "border:none; color:#b91c1c; font-size:15px; font-weight:700;")
        notice_text = QtWidgets.QLabel(
            "页面支持常见笔记本窗口和最大化显示，并会根据窗口宽度调整排列。"
            "窗口较小时，可使用页面滚动条查看下方内容。"
        )
        notice_text.setWordWrap(True)
        notice_text.setStyleSheet("border:none; color:#7f1d1d; font-size:12px;")
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)
        layout.addWidget(window_notice)

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
    """Public record for version, copyright, and required third-party licenses."""

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
            "查看软件版本、权利说明及依法需要保留的第三方许可证。",
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
        self.tabs.addTab(data_tab, "必要第三方许可")
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
