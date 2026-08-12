"""Learning-method guide shown before the hands-on trial starts."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class ExperienceGuideView(QtWidgets.QWidget):
    """Explain the complete learning loop before opening trial content."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        edition_id = str(getattr(getattr(main_window, "edition", None), "edition_id", "gaokao"))
        self.is_junior = edition_id.removeprefix("trial_") == "zhongkao"
        self.setObjectName("experience_guide_view")
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:#f4f7fb; border:none; }")
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f4f7fb;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(34, 28, 34, 38)
        layout.setSpacing(18)

        layout.addWidget(self._hero())
        layout.addWidget(self._problem_section())
        layout.addWidget(self._start_paths_section())
        layout.addWidget(self._focus_funnel_section())
        layout.addWidget(self._learning_resources_section())
        layout.addWidget(self._personal_vocabulary_section())
        layout.addWidget(self._verification_section())
        layout.addWidget(self._learning_loop_section())
        layout.addStretch()

        scroll.setWidget(page)
        root.addWidget(scroll)

    def _hero(self):
        frame = QtWidgets.QFrame()
        frame.setObjectName("guide_hero")
        frame.setStyleSheet(
            "QFrame#guide_hero { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #1d4ed8, stop:1 #0ea5e9); border-radius:16px; }"
        )
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(28, 23, 28, 23)
        layout.setSpacing(8)
        title = QtWidgets.QLabel(
            "初中核心词汇，从准初一预习到初三中考"
            if self.is_junior else "高中3800词，从准高一预习到高三备考")
        title.setStyleSheet(
            "color:white; font-size:27px; font-weight:700; background:transparent;")
        subtitle = QtWidgets.QLabel(
            (("适用：准初一｜初一｜初二｜初三　　用途：提前预习｜课内同步｜中考备考\n"
             if self.is_junior else
             "适用：准高一｜高一｜高二｜高三　　用途：提前预习｜课内同步｜高考备考\n") +
            "先用高效方法建立记忆，再通过闯关识别薄弱词，并把课内外生词持续加入个人词库。"
            )
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "color:#e0f2fe; font-size:15px; background:transparent;")
        edition_name = getattr(
            getattr(self.main_window, "edition", None), "display_name", "英语词汇")
        badge = QtWidgets.QLabel(f"当前学习内容：{edition_name}")
        badge.setStyleSheet(
            "color:white; font-size:13px; font-weight:600; background:rgba(255,255,255,45); "
            "border:1px solid rgba(255,255,255,85); border-radius:10px; padding:6px 11px;"
        )
        badge.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(5)
        layout.addWidget(badge)
        return frame

    def _problem_section(self):
        frame, layout = self._section_frame(
            "三大核心",
            "背得快、找得准、补得全",
            "英语词汇学习不只是反复看词表：需要先建立清楚的记忆联系，再验证是否真正掌握，"
            "还要能随时补充课本、课堂、作业、试卷和阅读中的个人生词。",
        )
        statement = QtWidgets.QLabel(
            "高效记忆：主题场景、词根、音形拼读、同义反义　｜　"
            "闯关识弱：自动找出不会和不稳定的词　｜　"
            "自主登记：建立自己的课内外生词库"
        )
        statement.setWordWrap(True)
        statement.setStyleSheet(
            "border:none; color:#1e3a8a; background:#eff6ff; border-radius:9px; "
            "font-size:14px; font-weight:700; padding:12px;"
        )
        layout.addWidget(statement)
        return frame

    def _start_paths_section(self):
        if self.is_junior:
            level_name, range_text = "初中核心词汇", "准初一到初三"
            stage_defs = (
                ("准初一　提前预习", "先认识初中核心词汇", ["优先使用主题场景和音形拼读建立印象", "按小组学习，不急于一次完成全部词汇", "通过简单闯关逐步适应初中英语"], "#f5f3ff", "#7c3aed"),
                ("初一　课程同步", "配合课本和课堂持续背诵", ["用提分速记学习当前课程相关词汇", "课堂、作业和课本生词随时自主登记", "阶段性闯关检查是否能够独立拼写"], "#eff6ff", "#2563eb"),
                ("初二　积累补弱", "扩大词汇量并找出薄弱部分", ["继续完成初中核心词汇的系统积累", "用普通闯关筛出不会和不稳定的单词", "返回对应记忆分类集中巩固错词"], "#ecfdf5", "#047857"),
                ("初三　中考备考", "完整复习并反复验证", ["按初中核心词汇查漏补缺", "通过完整闯关建立个人薄弱词范围", "错词清空后开始下一轮完整复测"], "#fff7ed", "#c2410c"),
            )
        else:
            level_name, range_text = "高中3800词", "准高一到高三"
            stage_defs = (
                ("准高一　提前预习", "先认识高中核心词汇", ["优先使用主题场景和音形拼读建立印象", "按小组学习，不急于一次完成全部3800词", "通过简单闯关逐步适应高中词汇"], "#f5f3ff", "#7c3aed"),
                ("高一　课程同步", "配合课本和课堂持续背诵", ["用提分速记提前学习当前课程相关词汇", "课堂、作业和课本生词随时自主登记", "阶段性闯关检查是否能够独立拼写"], "#eff6ff", "#2563eb"),
                ("高二　积累补弱", "扩大词汇量并找出薄弱部分", ["继续完成高中3800词的系统积累", "用普通闯关筛出不会和不稳定的单词", "返回对应记忆分类并集中巩固错词"], "#ecfdf5", "#047857"),
                ("高三　高考备考", "完整复习并反复验证", ["按高中3800词完成系统复习和查漏补缺", "通过完整闯关建立个人薄弱词范围", "错词清空后开始下一轮完整复测"], "#fff7ed", "#c2410c"),
            )
        frame, layout = self._section_frame(
            "按阶段使用",
            f"同一套{level_name}，在不同年级解决不同问题",
            f"不是建立四套不同词表，而是根据{range_text}的学习任务，选择更适合自己的使用顺序。",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        stages = tuple(self._route_card(*definition) for definition in stage_defs)
        for index, card in enumerate(stages):
            grid.addWidget(card, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        return frame

    def _focus_funnel_section(self):
        frame, layout = self._section_frame(
            "看效果",
            "学习范围逐轮缩小，把时间集中在真正不会的单词上",
            "下面是学习范围变化示意。实际数量由每位学生的闯关结果自动形成。",
        )
        funnel = QtWidgets.QVBoxLayout()
        funnel.setSpacing(6)
        levels = [
            ("完整分级词表", "先学习或直接筛查", 760, "#dbeafe", "#1d4ed8"),
            ("第一轮个人错词表", "只保留本轮答错和不稳定的单词", 610, "#cffafe", "#0e7490"),
            ("下一轮再次出现的错词", "范围继续缩小", 455, "#ffedd5", "#c2410c"),
            ("完整一轮没有新错词", "当前范围基本掌握", 315, "#dcfce7", "#15803d"),
        ]
        for index, (title, subtitle, width, background, color) in enumerate(levels):
            bar = QtWidgets.QLabel(f"{title}　｜　{subtitle}")
            bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            bar.setFixedWidth(width)
            bar.setMinimumHeight(38)
            bar.setWordWrap(True)
            bar.setStyleSheet(
                f"border:1px solid {color}; border-radius:9px; background:{background}; "
                f"color:{color}; font-size:13px; font-weight:700; padding:5px;"
            )
            funnel.addWidget(bar, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            if index < len(levels) - 1:
                arrow = QtWidgets.QLabel("↓")
                arrow.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                arrow.setStyleSheet(
                    "border:none; color:#64748b; font-size:18px; font-weight:700;")
                funnel.addWidget(arrow)
        layout.addLayout(funnel)
        note = QtWidgets.QLabel(
            "不是让学生把几千个单词一遍遍全部重背，而是让已经掌握的快速通过，把有限时间留给真正不会的内容。"
        )
        note.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        note.setStyleSheet(
            "border:none; color:#7c2d12; background:#fff7ed; border-radius:8px; "
            "font-size:13px; font-weight:600; padding:9px;"
        )
        layout.addWidget(note)
        return frame

    def _section_frame(self, step, title, intro):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet(
            "QFrame { background:white; border:1px solid #dce5f0; border-radius:13px; }")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(12)
        header = QtWidgets.QHBoxLayout()
        step_label = QtWidgets.QLabel(step)
        step_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        step_label.setFixedSize(64, 28)
        step_label.setStyleSheet(
            "border:none; border-radius:8px; background:#dbeafe; color:#1d4ed8; "
            "font-size:13px; font-weight:700;"
        )
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            "border:none; color:#111827; font-size:20px; font-weight:700;")
        header.addWidget(step_label)
        header.addWidget(title_label)
        header.addStretch()
        intro_label = QtWidgets.QLabel(intro)
        intro_label.setWordWrap(True)
        intro_label.setStyleSheet(
            "border:none; color:#475569; font-size:14px; line-height:21px;")
        layout.addLayout(header)
        layout.addWidget(intro_label)
        return frame, layout

    def _learning_resources_section(self):
        frame, layout = self._section_frame(
            "学习工具",
            "先用高效方法记忆，再使用词表辅助查看",
            "提分速记负责建立单词之间的联系；普通词表负责完整浏览和搜索，两者共同完成背词准备。",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        resources = [
            (
                "初中词汇提分速记" if self.is_junior else "3800词提分速记",
                "按主题场景、词根、音形拼读和同义反义组织适合关联记忆的单词。",
                "用处：不再面对一张没有联系的长词表，先建立清楚、简单的记忆线索。",
            ),
            (
                "初中核心词汇表" if self.is_junior else "高中3800词表",
                ("浏览完整初中词汇；支持搜索、中英对照、只看英文和只看中文。"
                 if self.is_junior else
                 "浏览完整高中词汇；支持搜索、中英对照、只看英文和只看中文。"),
                "用处：查看完整学习范围，并辅助查找和复习具体单词。",
            ),
            (
                "常用短语表",
                "按核心和扩展短语查看释义与例句，并可切换中英文显示方式。",
                "用处：不仅认识单词，还能掌握真实搭配和常用表达。",
            ),
            (
                "不规则动词表",
                "集中查看动词原形、过去式、过去分词和中文含义。",
                "用处：减少阅读、写作和语法中的动词变化错误。",
            ),
            (
                "自主录入词表",
                "录入学校作业、试卷错词和课外阅读中的生词；支持中英对照、只看英语和只看中文。",
                "用处：把统一词库与学生自己的学习内容放在一起管理。",
            ),
        ]
        for index, values in enumerate(resources):
            grid.addWidget(self._info_card(*values), index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        return frame

    def _verification_section(self):
        frame, layout = self._section_frame(
            "验证工具",
            "再验证是否真正掌握",
            "看过不等于掌握。通过输入答案和默写验证，系统才能判断哪些内容需要继续巩固。",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        verification = [
            (
                "词汇闯关验证",
                "根据中文、词性或提示主动输入英文答案，不能只凭眼熟判断。",
                "验证：能否独立回忆并准确拼写单词。",
            ),
            (
                "短语与不规则动词验证",
                "短语按关卡练习；不规则动词填写过去式和过去分词。",
                "验证：能否正确使用搭配和动词变化。",
            ),
            (
                "错词打印默写验证",
                "错词积累后，生成看英默中、看中默英等纸质练习表。",
                "验证：脱离电脑后是否仍能完成学校式默写。",
            ),
        ]
        for index, values in enumerate(verification):
            grid.addWidget(self._info_card(*values), 0, index)
            grid.setColumnStretch(index, 1)
        layout.addLayout(grid)
        return frame

    def _personal_vocabulary_section(self):
        frame, layout = self._section_frame(
            "个人扩展",
            "内置分级词库之外，建立自己的长期个人词库",
            "考试词表解决系统学习范围；阅读理解、课堂、作业、试卷和课外阅读中遇到的生词，"
            "则可以通过自主录入功能长期积累和单独训练。",
        )
        flow = QtWidgets.QHBoxLayout()
        flow.setSpacing(8)
        nodes = [
            ("发现生词", "来自阅读、课堂或试卷"),
            ("自主录入", "填写英文和中文释义"),
            ("个人词汇表", "随时查看和修改"),
            ("自主录入闯关", "单独训练个人生词"),
            ("持续积累", "让词库跟随真实学习扩展"),
        ]
        for index, (title, subtitle) in enumerate(nodes):
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame { background:#fff7ed; border:1px solid #fdba74; border-radius:9px; }")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(9, 9, 9, 9)
            title_label = QtWidgets.QLabel(title)
            title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            title_label.setStyleSheet(
                "border:none; color:#9a3412; font-size:13px; font-weight:700;")
            subtitle_label = QtWidgets.QLabel(subtitle)
            subtitle_label.setWordWrap(True)
            subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            subtitle_label.setStyleSheet(
                "border:none; color:#7c2d12; font-size:11px;")
            card_layout.addWidget(title_label)
            card_layout.addWidget(subtitle_label)
            flow.addWidget(card, 1)
            if index < len(nodes) - 1:
                arrow = QtWidgets.QLabel("→")
                arrow.setStyleSheet(
                    "border:none; color:#f97316; font-size:19px; font-weight:700;")
                flow.addWidget(arrow)
        layout.addLayout(flow)
        statement = QtWidgets.QLabel(
            "自主录入不是体验限制功能。体验用户和正式用户都可以建立、保存并训练自己的个人词汇。"
        )
        statement.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        statement.setWordWrap(True)
        statement.setStyleSheet(
            "border:none; color:#047857; background:#ecfdf5; border-radius:8px; "
            "font-size:13px; font-weight:700; padding:9px;"
        )
        layout.addWidget(statement)
        return frame

    def _learning_loop_section(self):
        frame, layout = self._section_frame(
            "推荐方法",
            ("初中词汇提分速记应该这样使用"
             if self.is_junior else "3800词提分速记应该这样使用"),
            "不要从头硬背整张词表，也不用一次看很多。先选择适合当前单词的记忆分类，每次只学一个小组。",
        )
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        methods = (
            (
                "1　主题场景为主",
                "进入提分速记后默认从主题场景开始",
                "按身体、学校、交通、科学等明确主题建立单词之间的联系。",
            ),
            (
                "2　规律记忆为辅",
                "词根、音形拼读和同义反义按需选择",
                "只有符合明显规律的单词才使用这些方法，不要求每个单词硬套。",
            ),
            (
                "3　每次只学一组",
                "使用上一组和下一组连续学习",
                "先看懂当前组为什么放在一起，再记英语、发音和中文含义。",
            ),
            (
                "4　马上主动回忆",
                "点击“本组掌握验证”隐藏英语",
                "根据中文主动回忆整组英文；完成后恢复显示，再进入下一组。",
            ),
        )
        for index, values in enumerate(methods):
            grid.addWidget(self._info_card(*values), index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        loop_hint = QtWidgets.QLabel(
            "完成若干记忆小组后，再进入普通闯关识别薄弱词；课内外遇到的新词随时加入自主登记。"
        )
        loop_hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        loop_hint.setWordWrap(True)
        loop_hint.setStyleSheet(
            "border:none; color:#0f766e; background:#ecfdf5; border-radius:8px; "
            "font-size:13px; font-weight:600; padding:9px;"
        )
        layout.addWidget(loop_hint)
        return frame

    def _operation_section(self):
        frame, layout = self._section_frame(
            "操作说明",
            "每个环节具体怎样使用",
            "体验时按照以下步骤操作，就能亲手走完一遍学习闭环。",
        )
        rows = [
            (
                "A　学习单词",
                "进入词汇表，使用搜索和中英文显示方式浏览；错词积累后可生成错词打印表。",
                "先建立印象，明确本次准备掌握的内容。",
            ),
            (
                "B　第一轮普通闯关",
                "基础较好可以直接开始；基础薄弱先完成初步背诵。根据提示输入答案，答错后完成纠正。",
                "全面筛查当前会的和不会的单词。",
            ),
            (
                "C　背诵个人错词表",
                "答错内容自动进入错词表。先使用错词表查看、隐藏中英文或打印，集中背诵自己的错词。",
                "学习范围从完整词表缩小到真正不会的单词。",
            ),
            (
                "D　错词闯关巩固",
                "进入错词闯关集中练习；连续答对 3 次后自动移出错词表。",
                "把时间集中用在真正不会的内容上。",
            ),
            (
                "E　开始下一轮验证",
                "错词表清空后适当间隔，再次进行完整普通闯关；重新找出遗忘和掌握不稳定的单词。",
                "一直循环到完整一轮不产生新错词。",
            ),
        ]
        for title, operation, purpose in rows:
            layout.addWidget(self._operation_row(title, operation, purpose))
        return frame

    def _trial_entry_section(self):
        frame = QtWidgets.QFrame()
        frame.setObjectName("trial_entry")
        frame.setStyleSheet(
            "QFrame#trial_entry { background:#eff6ff; border:1px solid #93c5fd; "
            "border-radius:14px; }"
        )
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 22)
        layout.setSpacing(9)
        title = QtWidgets.QLabel("选择适合自己的起点，进入完整学习体验")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "border:none; color:#1e3a8a; font-size:20px; font-weight:700;")
        text = QtWidgets.QLabel(
            "基础薄弱先从词汇表学习；基础较好直接通过普通闯关筛查。两条路线都会进入个人错词的精准巩固循环。"
        )
        text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("border:none; color:#475569; font-size:14px;")
        button_style = (
            "QPushButton { background:#2563eb; color:white; border:none; border-radius:10px; "
            "font-size:15px; font-weight:700; padding:0 20px; }"
            "QPushButton:hover { background:#1d4ed8; }"
        )
        weak_button = QtWidgets.QPushButton("基础较弱：从词汇表学习  →")
        weak_button.setObjectName("btn_trial_from_word_list")
        strong_button = QtWidgets.QPushButton("基础较好：直接普通闯关  →")
        strong_button.setObjectName("btn_trial_from_challenge")
        for button in (weak_button, strong_button):
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(44)
            button.setMinimumWidth(245)
            button.setStyleSheet(button_style)
        weak_button.clicked.connect(self._enter_trial_from_word_list)
        strong_button.clicked.connect(self._enter_trial_from_challenge)
        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(14)
        button_row.addStretch()
        button_row.addWidget(weak_button)
        button_row.addWidget(strong_button)
        button_row.addStretch()
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addSpacing(4)
        layout.addLayout(button_row)
        return frame

    def _route_card(self, title, subtitle, steps, background, accent):
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{background}; border:1px solid {accent}; border-radius:11px; }}")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(17, 15, 17, 16)
        layout.setSpacing(7)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            f"border:none; color:{accent}; font-size:16px; font-weight:700;")
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setStyleSheet(
            "border:none; color:#1f2937; font-size:14px; font-weight:600;")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        for step in steps:
            label = QtWidgets.QLabel("• " + step)
            label.setWordWrap(True)
            label.setStyleSheet(
                "border:none; color:#475569; font-size:13px; padding-left:3px;")
            layout.addWidget(label)
        layout.addStretch()
        return card

    def _info_card(self, title, operation, purpose):
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame { background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; }")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 14)
        layout.setSpacing(7)
        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            "border:none; color:#1e3a8a; font-size:15px; font-weight:700;")
        operation_label = QtWidgets.QLabel("怎么使用：" + operation)
        operation_label.setWordWrap(True)
        operation_label.setStyleSheet(
            "border:none; color:#475569; font-size:13px; line-height:19px;")
        purpose_label = QtWidgets.QLabel(purpose)
        purpose_label.setWordWrap(True)
        purpose_label.setStyleSheet(
            "border:none; color:#334155; font-size:13px; font-weight:600; line-height:19px;")
        layout.addWidget(title_label)
        layout.addWidget(operation_label)
        layout.addWidget(purpose_label)
        return card

    def _flow_node(self, number, title, subtitle):
        node = QtWidgets.QFrame()
        node.setMinimumHeight(84)
        node.setStyleSheet(
            "QFrame { background:#f8fafc; border:1px solid #bfdbfe; border-radius:10px; }")
        layout = QtWidgets.QVBoxLayout(node)
        layout.setContentsMargins(7, 8, 7, 8)
        layout.setSpacing(3)
        number_label = QtWidgets.QLabel(number)
        number_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        number_label.setStyleSheet(
            "border:none; color:#2563eb; font-size:12px; font-weight:700;")
        title_label = QtWidgets.QLabel(title)
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "border:none; color:#1f2937; font-size:13px; font-weight:700;")
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(
            "border:none; color:#64748b; font-size:11px;")
        layout.addWidget(number_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return node

    def _operation_row(self, title, operation, purpose):
        row = QtWidgets.QFrame()
        row.setStyleSheet(
            "QFrame { background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; }")
        layout = QtWidgets.QGridLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setHorizontalSpacing(14)
        title_label = QtWidgets.QLabel(title)
        title_label.setMinimumWidth(125)
        title_label.setStyleSheet(
            "border:none; color:#1d4ed8; font-size:14px; font-weight:700;")
        operation_label = QtWidgets.QLabel(operation)
        operation_label.setWordWrap(True)
        operation_label.setStyleSheet(
            "border:none; color:#334155; font-size:13px;")
        purpose_label = QtWidgets.QLabel(purpose)
        purpose_label.setWordWrap(True)
        purpose_label.setStyleSheet(
            "border:none; color:#0f766e; font-size:12px; font-weight:600;")
        layout.addWidget(title_label, 0, 0, 2, 1)
        layout.addWidget(operation_label, 0, 1)
        layout.addWidget(purpose_label, 1, 1)
        layout.setColumnStretch(1, 1)
        return row

    def _enter_trial_from_word_list(self):
        self.main_window._safe_nav_to_word_list()

    def _enter_trial_from_challenge(self):
        if getattr(self.main_window, "vocab_ctrl", None) is not None:
            self.main_window.vocab_ctrl.switch_challenge_mode("regular")
        self.main_window.stack.setCurrentIndex(0)
