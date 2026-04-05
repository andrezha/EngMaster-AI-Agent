import json
import os
import random
import re
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel
from parsers.reading_parser import parse_reading_txt

class ExamManager:
    def __init__(self, main_window):
        self.mw = main_window
        self.ui = main_window.page_gaokao_widget 
        
        # 1. 初始化变量
        self.current_type = "阅读理解" 
        self.user_selections = {} 
        self.current_q = None

        # 2. 比例调整
        main_layout = self.ui.layout()
        if main_layout and hasattr(main_layout, 'setStretch'):
            main_layout.setStretch(0, 6) 
            main_layout.setStretch(1, 4)
            print("🚀 [OK] 界面 6:4 比例调整完成")

        # 右侧垂直布局比例调整 (上方题目/选项 7 : 下方解析 3)
        right_v_layout = self.ui.gk_result_panel.parentWidget().layout()
        if right_v_layout and hasattr(right_v_layout, 'setStretch'):
            right_v_layout.setStretch(0, 7)
            right_v_layout.setStretch(1, 3)
            print("🚀 [OK] 右侧垂直 7:3 比例调整完成")

        # 3. 绑定信号
        self.ui.btn_gk_next.clicked.connect(self.load_and_render)
        self.ui.btn_gk_submit.clicked.connect(self.check_score)
        
        # 4. 初始导航高亮
        self.update_nav_highlight()

        # 5. 绑定题型选择按钮
        self.ui.gk_btn_reading.clicked.connect(lambda: self.switch_topic("阅读理解"))
        self.ui.gk_btn_cloze.clicked.connect(lambda: self.switch_topic("完形填空"))
        self.ui.gk_btn_seven_five.clicked.connect(lambda: self.switch_topic("七选五"))
        self.ui.gk_btn_grammar.clicked.connect(lambda: self.switch_topic("语法填空"))

        # 清空初始界面显示
        self.ui.gk_question_body.clear()
        self.ui.gk_result_panel.clear()
        self.ui.gk_ai_display.clear()

    def clear_answer_area(self):
        """清空答题区域的旧组件"""
        target_area = self.mw.findChild(QWidget, "gk_answer_content")
        if target_area:
            layout = target_area.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget(): child.widget().deleteLater()

    def switch_topic(self, topic_name):
        """切换题型并加载新题"""
        self.clear_answer_area()
        self.current_type = topic_name
        self.update_nav_highlight()
        self.load_and_render()

    def load_and_render(self):
        """加载数据并渲染界面 (带 Debug 打印)"""
        self.ui.gk_question_body.clear()
        print("\n" + "="*30)
        print("🚀 [Step 1] 开始触发加载逻辑...")
        self.user_selections = {}
        self.ui.gk_result_panel.clear()
        self.ui.gk_ai_display.clear()
        self.current_q = None

        # 清空按钮区域
        self.clear_answer_area()
                    
        # 题型切换重置：滚动条置顶
        if hasattr(self.ui, 'gk_answer_scroll'):
            self.ui.gk_answer_scroll.verticalScrollBar().setValue(0)
        if hasattr(self.ui, 'gk_question_body'):
            self.ui.gk_question_body.verticalScrollBar().setValue(0)
        
        # 1. 路径探测
        base_path = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(base_path, "data", self.current_type)
        print(f"📂 [Step 2] 正在扫描路径: {data_path}")
        
        if not os.path.exists(data_path):
            print("❌ 错误：路径不存在！")
            self.ui.gk_question_body.setHtml(f"<div style='font-size:16px; color:#e74c3c;'>❌ 错误：<b>{self.current_type}</b> 路径不存在！</div>")
            return
        
        files = [f for f in os.listdir(data_path) if f.endswith(".txt")]
        print(f"📊 [Step 3] 发现 TXT 文件数量: {len(files)}")
        
        if not files:
            print("❌ 错误：文件夹里没有 .txt 文件！")
            self.ui.gk_question_body.setHtml(f"<div style='font-size:16px; color:#e74c3c;'>❌ 错误：<b>{self.current_type}</b> 题库中尚未生成 TXT 文件！</div>")
            return
        
        # 2. 读取探测
        target = random.choice(files)
        target_path = os.path.join(data_path, target)
        print(f"📖 [Step 4] 随机选中文件: {target}")
        
        print(f"\n[TARGET_FILE] {target}")
        print("-" * 40)
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parsed_data = parse_reading_txt(content)
            print(f"✅ [Step 5] TXT 解析成功！")
            
            # 【数据结构对齐】：兼容原有的 current_q 结构
            self.current_q = {
                'passage': parsed_data.get('passage', ''),
                'items': [],
                'original_analysis': parsed_data.get('original_analysis', '')
            }
            
            for item in parsed_data.get('items', []):
                raw_content = item.get('content', '')
                q_id = item.get('q_id', item.get('id', ''))
                
                print(f"[RAW_CONTENT] {repr(raw_content)}")
                
                # 容错处理：将全角 ． 替换为半角 .
                clean_content = raw_content.replace('．', '.')
                
                q_text = ""
                options = []
                
                # 物理切割选项
                posA = clean_content.find("A.")
                posB = clean_content.find("B.")
                posC = clean_content.find("C.")
                posD = clean_content.find("D.")
                
                print(f"[POSITIONS] A:{posA}, B:{posB}, C:{posC}, D:{posD}")
                
                if posA != -1 and posB != -1 and posC != -1 and posD != -1 and posA < posB < posC < posD:
                    # 切分题干：位置 A 之前的所有内容直接设为 q_text
                    q_text = clean_content[:posA].strip()
                    
                    # 选项切分
                    optA = clean_content[posA:posB].strip()
                    optB = clean_content[posB:posC].strip()
                    optC = clean_content[posC:posD].strip()
                    optD = clean_content[posD:].strip()
                    
                    options = [optA, optB, optC, optD]
                else:
                    # 兜底逻辑：没找齐四个选项或顺序错乱
                    print(f"[WARNING] 题目解析异常，请检查 TXT 格式！")
                    q_text = clean_content.strip()
                    options = []
                
                print(f"[SPLIT_RESULT] q_text: {q_text}")
                print(f"[SPLIT_RESULT] options: {options}")
                print("-" * 40)
                
                self.current_q['items'].append({
                    'q_id': q_id,
                    'q_text': q_text,
                    'options': options,
                    'answer': item.get('answer', '')
                })
            
            # 检查关键字段是否存在
            passage = self.current_q.get('passage', '')
            items = self.current_q.get('items', [])
            print(f"📝 [Step 6] 内容检查: 文章长度={len(passage)}, 题目数量={len(items)}")
            
        except Exception as e:
            print(f"❌ [Error] 读取文件崩溃: {e}")
            return

        # 3. UI 渲染
        print("🎨 [Step 8] 开始调用渲染 UI 函数...")
        
        # 解析年份和卷区
        file_name_no_ext = target.replace(".txt", "")
        parts = file_name_no_ext.split("_")
        year = parts[0] if len(parts) > 0 else "未知"
        
        if len(parts) > 1 and parts[1] == "47":
            # 如果是 2015_47 特殊文件，强行补齐标题格式
            normalized_cat = "全国新课标Ⅰ卷"
        else:
            category = parts[1] if len(parts) > 1 else ""
            # 规范化处理
            normalized_cat = category.strip("()（）")
            if "新课标" in normalized_cat:
                normalized_cat = "全国新课标Ⅰ卷"
            
        # 提取篇目并清洗正文
        raw_passage = self.current_q.get('passage', '文章加载失败')
        p_lines = raw_passage.splitlines()
        
        p_text_lines = []
        title_str = ""
        
        if self.current_type == "阅读理解":
            passage_letter = ""
            found_letter = False
            for line in p_lines:
                stripped = line.strip()
                if not found_letter and stripped.upper() in ['A', 'B', 'C', 'D']:
                    passage_letter = stripped.upper()
                    found_letter = True
                    continue
                p_text_lines.append(line)
            title_str = f"{year}年高考英语 {normalized_cat} 阅读 {passage_letter}篇"
        else:
            p_text_lines = p_lines
            title_str = f"{year}年高考英语 {normalized_cat} {self.current_type}"
            
        p_text = '\n'.join(p_text_lines).strip()
        p_text_html = p_text.replace('\n', '<br>')
        
        # 最终标题拼接
        html_output = (
            f"<h2 style='text-align: center; color: #2c3e50;'>{title_str}</h2>"
            f"<hr>"
            f"<div style='font-size:16px; line-height:1.7; color:#2c3e50;'>{p_text_html}</div>"
        )
        self.ui.gk_question_body.setHtml(html_output)
        
        self.render_question_ui()
        print("🏁 [Step 9] 渲染流程全部执行完毕")
        print("="*30 + "\n")

    def render_question_ui(self):
        """动态生成答题按钮 (全域组件搜索版)"""
        target_area = self.mw.findChild(QWidget, "gk_answer_content")

        if not target_area:
            print("❌ 严重错误：在整个界面中都找不到 'gk_answer_content'！")
            return

        layout = target_area.layout()
        if layout is None:
            layout = QVBoxLayout(target_area)
            target_area.setLayout(layout)

        # 增加间距与边距
        layout.setSpacing(15)
        layout.setContentsMargins(10, 20, 10, 20)
        
        # 固定高度限制，提供足够的 min-height，让选项能根据大小自动撑开无需频繁滚动
        target_area.setMinimumHeight(300)

        # 彻底清空
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        # 渲染题目
        items = self.current_q.get('items', [])
        for item in items:
            qid = item.get('q_id')
            qtext = item.get('q_text', '') 
            opts = item.get('options', []) 
            
            # 显示题干
            q_label = QLabel(f"<b>{qid}. {qtext}</b>")
            q_label.setWordWrap(True)
            layout.addWidget(q_label)
            
            # 显示按钮行
            row = QWidget()
            row_lay = QVBoxLayout(row)
            row_lay.setContentsMargins(20, 5, 20, 15) # 缩进一下选项
            for i, opt_content in enumerate(opts):
                btn = QPushButton(opt_content)
                btn.setCheckable(True)
                btn.setStyleSheet("""
                    QPushButton { text-align: left; padding: 8px; border: 1px solid #ccc; border-radius: 4px; background-color: white; }
                    QPushButton:checked { background-color: #3498db; color: white; border: 1px solid #2980b9; }
                """)
                btn.clicked.connect(lambda checked, q=qid, c=chr(65+i), b=btn: self.on_choice_click(q, c, b))
                row_lay.addWidget(btn)
            layout.addWidget(row)
            
        layout.addStretch()

    def on_choice_click(self, qid, choice, btn):
        """记录用户选择并取消同题其他按钮"""
        parent = btn.parentWidget()
        for child in parent.findChildren(QPushButton):
            if child != btn and child.isCheckable():
                child.setChecked(False)
        self.user_selections[qid] = choice

    def check_score(self):
        """判分与 3:7 比例展示解析"""
        if not self.current_q: return
        
        correct_count = 0
        items = self.current_q.get('items', [])
        total = len(items)
        if total == 0:
            return
        
        res_details = ""

        for item in items:
            qid = item.get('q_id')
            ans = item.get('answer', '').strip().upper()
            user_ans = self.user_selections.get(qid, "未做")
            
            if not ans:
                res_details += f"<p>第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:#e67e22;'>未知 (题库未录入)</b></p>"
            else:
                color = "#27ae60" if user_ans == ans else "#e74c3c"
                if user_ans == ans: correct_count += 1
                res_details += f"<p>第{qid}题：你的选择 <b>{user_ans}</b> | 正确答案 <b style='color:{color};'>{ans}</b></p>"

        # 1. 渲染左侧结果 (30% 高度)
        score_html = f"<h3>得分：{correct_count}/{total} (仅计算已知答案的题目)</h3>" + res_details
        self.ui.gk_result_panel.setHtml(f"<div style='padding:10px;'>{score_html}</div>")
        
        # 已在初始化中统一配置右侧垂直布局比例为 4:6，此处不再硬编码 3:7

        # 3. 渲染右侧 AI 解析 (70% 高度)
        analysis = self.current_q.get('original_analysis', '').strip()
        if not analysis:
            analysis = "<span style='color:#7f8c8d;'>暂无本地解析。您可以到【解析】页面呼叫 AI 老师为您详细讲解！</span>"
            
        self.ui.gk_ai_display.setHtml(f"""
            <div style='background:#fdf6ec; padding:15px; border-radius:8px;'>
                <h4 style='color:#e67e22; margin-top:0;'>📖 题目深度解析</h4>
                <div style='line-height:1.6;'>{analysis}</div>
            </div>
        """)

    def update_nav_highlight(self):
        """顶部菜单按钮高亮控制"""
        btn_map = {
            "阅读理解": "gk_btn_reading", "完形填空": "gk_btn_cloze",
            "语法填空": "gk_btn_grammar", "七选五": "gk_btn_seven_five",
            "短文改错": "gk_btn_correction", "写作续写": "gk_btn_writing"
        }
        for type_name, obj_name in btn_map.items():
            btn = getattr(self.ui, obj_name, None)
            if btn:
                if type_name == self.current_type:
                    btn.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 5px;")
                else:
                    btn.setStyleSheet("background-color: transparent; color: #333; padding: 5px;")

