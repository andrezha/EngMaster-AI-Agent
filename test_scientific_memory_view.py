import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from scientific_memory_view import (
    MemoryTextLink,
    ScientificMemoryCatalog,
    ScientificMemoryView,
)


VOCABULARY_PATH = "assets/editions/gaokao/vocabulary.json"


class ScientificMemoryCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ScientificMemoryCatalog(VOCABULARY_PATH)

    def test_scene_groups_are_curated_small_scenes(self):
        record_ids = {row["record_id"] for row in self.catalog.words}
        scene_ids = [
            row["record_id"]
            for group in self.catalog.groups["scene"]
            for row in group.words
        ]
        self.assertEqual(len(self.catalog.words), 3800)
        self.assertEqual(len(scene_ids), 3800)
        self.assertEqual(len(set(scene_ids)), len(scene_ids))
        for group in self.catalog.groups["scene"]:
            self.assertLessEqual(len(group.words), 12)
            self.assertEqual(len(group.words), len(group.hints))
            self.assertTrue(group.parent)
            self.assertTrue({row["record_id"] for row in group.words} <= record_ids)

    def test_root_and_phonics_groups_only_use_master_vocabulary(self):
        record_ids = {row["record_id"] for row in self.catalog.words}
        self.assertGreaterEqual(len(self.catalog.groups["root"]), 10)
        self.assertGreaterEqual(len(self.catalog.groups["phonics"]), 7)
        for method in ("root", "phonics"):
            for group in self.catalog.groups[method]:
                self.assertGreaterEqual(len(group.words), 2)
                self.assertTrue(
                    {row["record_id"] for row in group.words} <= record_ids
                )

    def test_formal_root_and_phonics_catalogs_are_substantially_expanded(self):
        self.assertEqual(len(self.catalog.groups["root"]), 33)
        self.assertEqual(len(self.catalog.groups["phonics"]), 23)
        root_titles = {group.title for group in self.catalog.groups["root"]}
        phonics_titles = {group.title for group in self.catalog.groups["phonics"]}
        self.assertTrue(
            {"vis", "vid", "act", "cept", "ceive", "mit", "miss", "log", "logy"}
            <= root_titles
        )
        self.assertFalse(any("/" in title for title in root_titles))
        self.assertTrue(
            {"-ANCE", "-ITY", "-FUL", "-LESS", "-IST", "-IFY", "-OLOGY"}
            <= phonics_titles
        )

    def test_relations_are_authoritative_small_groups(self):
        record_ids = {row["record_id"] for row in self.catalog.words}
        synonyms = [g for g in self.catalog.groups["relations"] if "synonym:" in g.group_id]
        antonyms = [g for g in self.catalog.groups["relations"] if "antonym:" in g.group_id]
        self.assertEqual(len(synonyms), 15)
        self.assertEqual(len(antonyms), 48)
        for group in self.catalog.groups["relations"]:
            self.assertEqual(len(group.words), 2)
            self.assertTrue({row["record_id"] for row in group.words} <= record_ids)
        pairs = {
            frozenset(str(row["word"]).casefold() for row in group.words)
            for group in self.catalog.groups["relations"]
        }
        self.assertIn(frozenset(("begin", "start")), pairs)
        self.assertIn(frozenset(("alive", "dead")), pairs)
        self.assertNotIn(frozenset(("accommodation", "adjustment")), pairs)

    def test_every_word_has_pronunciation(self):
        self.assertTrue(all(str(row.get("pronunciation", "")).strip() for row in self.catalog.words))

    def test_common_high_school_meanings_are_not_misclassified(self):
        theme_by_record = {
            row["record_id"]: group.title.split(" · ", 1)[0]
            for group in self.catalog.groups["scene"]
            for row in group.words
        }
        row_by_word = {str(row["word"]).casefold(): row for row in self.catalog.words}
        expected = {
            "beard": "身体部位",
            "antique": "家具陈设",
            "beef": "食物饮料",
            "queen": "人物身份",
            "virus": "医疗健康",
            "cock": "动物世界",
            "come": "移动出行",
            "lid": "容器包装",
            "socket": "工具与设备",
            "online": "网络科技",
            "option": "选择决定",
            "chess": "体育运动",
            "cheat": "欺骗行为",
            "confucius": "人物身份",
            "church": "宗教场所",
            "cafeteria": "餐饮场所",
            "physics": "学科",
            "pronunciation": "语言技能",
            "explain": "通知解释",
            "big": "大小",
            "young": "年龄",
            "new": "新旧",
            "early": "早晚",
            "understand": "思考理解",
            "analyse": "分析判断",
            "gymnastics": "体育运动",
            "paperwork": "工作任务",
            "ambitious": "社交性格",
            "tired": "身体状态",
            "gardening": "家务生活",
            "rely": "依赖关系",
            "cheap": "价格价值",
            "safe": "安全危险",
            "female": "性别婚姻",
            "famous": "知名影响",
            "rich": "贫富",
        }
        for word, expected_theme in expected.items():
            self.assertEqual(
                theme_by_record[row_by_word[word]["record_id"]],
                expected_theme,
                word,
            )

    def test_no_visible_generic_fallback_theme_remains(self):
        titles = {group.title.split(" · ", 1)[0] for group in self.catalog.groups["scene"]}
        self.assertNotIn("综合概念", titles)
        self.assertNotIn("常用名词", titles)
        self.assertNotIn("人造物", titles)
        self.assertNotIn("语言交流", titles)
        self.assertNotIn("表达交流", titles)
        self.assertNotIn("大小形状", titles)
        self.assertNotIn("年龄新旧", titles)
        self.assertNotIn("思考学习", titles)
        self.assertNotIn("学习活动", titles)

    def test_no_scientific_scene_category_has_only_one_word(self):
        totals = {}
        for group in self.catalog.groups["scene"]:
            title = group.title.split(" · ", 1)[0]
            totals[title] = totals.get(title, 0) + len(group.words)
        self.assertTrue(totals)
        self.assertTrue(all(total >= 2 for total in totals.values()))

    def test_no_words_are_left_in_other(self):
        other_words = {
            str(row["word"]).casefold()
            for group in self.catalog.groups["scene"]
            if group.title.split(" · ", 1)[0] == "其他"
            for row in group.words
        }
        self.assertEqual(other_words, set())


class ScientificMemoryViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.view = ScientificMemoryView(vocabulary_path=VOCABULARY_PATH)

    def tearDown(self):
        self.view.close()

    def test_home_is_default_and_entries_have_compact_text(self):
        self.assertEqual(self.view.current_method, "scene")
        self.assertIs(self.view.stack.currentWidget(), self.view.home_page)
        self.assertEqual(list(self.view.method_buttons), ["scene", "root", "phonics", "relations"])
        self.assertTrue(all("\n\n" not in button.text() for button in self.view.method_buttons.values()))

    def test_search_is_on_left_side_of_second_header_row(self):
        self.view.show_catalog("scene")
        self.assertIs(self.view.header_search.parent(), self.view.header_search_row)
        self.assertEqual(
            self.view.header_search_row.layout().indexOf(self.view.header_search), 0)
        self.assertEqual(self.view.header_search.size().width(), 220)
        self.assertEqual(self.view.header.height(), 116)

    def test_catalog_rebuild_never_creates_temporary_popup_cards(self):
        self.view.show()
        self.app.processEvents()
        for method in ("root", "phonics", "scene", "root", "scene"):
            self.view.show_catalog(method)
            popup_cards = [
                widget
                for widget in self.app.topLevelWidgets()
                if widget.objectName() == "memory_text_section"
            ]
            self.assertEqual(popup_cards, [], method)
        self.app.processEvents()

    def test_trial_preview_opens_representative_samples_only(self):
        trial_main = SimpleNamespace(
            edition=SimpleNamespace(
                edition_id="trial_gaokao",
                vocabulary_path="assets/editions/gaokao/trial_vocabulary.json",
            )
        )
        trial_view = ScientificMemoryView(trial_main)
        try:
            self.assertTrue(trial_view.trial_preview)
            self.assertEqual(len(trial_view.catalog.words), 3800)
            self.assertEqual(
                {method: len(groups) for method, groups in trial_view.catalog.groups.items()},
                {"scene": 6, "root": 3, "phonics": 3, "relations": 6},
            )
            self.assertIs(trial_view.stack.currentWidget(), trial_view.home_page)
            self.assertTrue(trial_view.btn_trial_upgrade.isHidden())
            self.assertIn("3800", trial_view.btn_trial_upgrade.text())
            self.assertEqual(
                trial_view.btn_trial_upgrade.parent().objectName(),
                "memory_header",
            )
            for method in ("scene", "root", "phonics", "relations"):
                trial_view.show_catalog(method)
                self.assertTrue(
                    trial_view.btn_trial_upgrade.isVisibleTo(trial_view), method)
            trial_view.reset_to_home()
            self.assertEqual(trial_view.current_method, "scene")
            self.assertIs(trial_view.stack.currentWidget(), trial_view.home_page)
            self.assertTrue(trial_view.btn_trial_upgrade.isHidden())
        finally:
            trial_view.close()

    def test_junior_trial_preview_uses_six_independent_junior_scenes(self):
        trial_main = SimpleNamespace(
            edition=SimpleNamespace(
                edition_id="trial_zhongkao",
                vocabulary_path="assets/editions/zhongkao/trial_vocabulary.json",
            )
        )
        trial_view = ScientificMemoryView(trial_main)
        try:
            scene_titles = {
                group.title.split(" · ", 1)[0]
                for group in trial_view.catalog.groups["scene"]
            }
            self.assertEqual(len(scene_titles), 6)
            self.assertEqual(
                scene_titles,
                {"身体部位", "一日三餐", "道路交通", "学校学科", "正面情绪", "常见颜色"},
            )
            self.assertEqual(trial_view.formal_id, "zhongkao")
            self.assertEqual(trial_view.formal_count, 1609)
        finally:
            trial_view.close()

    def test_scene_cards_do_not_overlap(self):
        self.view.resize(1280, 820)
        self.view.show()
        self.app.processEvents()
        sections = self.view.catalog_container.findChildren(
            QtWidgets.QWidget, "memory_text_section"
        )
        first_column = sorted(
            (section for section in sections if section.geometry().x() == min(item.geometry().x() for item in sections)),
            key=lambda section: section.geometry().y(),
        )
        for upper, lower in zip(first_column, first_column[1:]):
            self.assertGreaterEqual(
                lower.geometry().top(),
                upper.geometry().bottom() + self.view.catalog_grid.verticalSpacing(),
            )

    def test_group_defaults_to_full_bilingual_display(self):
        group = self.view.catalog.groups["root"][0]
        self.view.show_group(group)
        visible_words = group.words
        self.assertFalse(self.view.validation_active)
        self.assertFalse(self.view.network.hide_english)
        self.assertEqual(len(self.view.network.word_text_items), len(group.words))
        for row, item in zip(visible_words, self.view.network.word_text_items):
            self.assertIn(row["word"], item.toPlainText())
            self.assertIn(row["pronunciation"], item.toPlainText())
        self.assertIn("PORT", self.view.network.word_text_items[0].toPlainText())

    def test_mastery_validation_hides_and_restores_all_english_together(self):
        group = self.view.catalog.groups["root"][0]
        self.view.show_group(group)
        visible_words = group.words

        self.view._toggle_validation()
        self.assertTrue(self.view.validation_active)
        self.assertTrue(self.view.network.hide_english)
        self.assertEqual(self.view.btn_verify.text(), "取消验证")
        for row, item in zip(visible_words, self.view.network.word_text_items):
            self.assertNotIn(row["word"], item.toPlainText())

        self.view._toggle_validation()
        self.assertFalse(self.view.validation_active)
        self.assertFalse(self.view.network.hide_english)
        for row, item in zip(visible_words, self.view.network.word_text_items):
            self.assertIn(row["word"], item.toPlainText())

    def test_opening_another_group_restores_default_display(self):
        first, second = self.view.catalog.groups["scene"][:2]
        self.view.current_method = "scene"
        self.view.show_group(first)
        self.view._toggle_validation()
        self.assertTrue(self.view.network.hide_english)

        self.view.show_group(second)
        self.assertFalse(self.view.validation_active)
        self.assertFalse(self.view.network.hide_english)
        self.assertEqual(
            len(self.view.network.word_text_items), len(second.words)
        )

    def test_group_pages_have_previous_and_next_navigation(self):
        groups = self.view.catalog.groups["scene"]
        self.view.current_method = "scene"
        self.view.show_group(groups[0])
        self.assertFalse(self.view.btn_previous_group.isEnabled())
        self.assertTrue(self.view.btn_next_group.isEnabled())
        self.assertEqual(
            self.view.lbl_group_position.text(), f"第 1 / {len(groups)} 组"
        )

        self.view.btn_next_group.click()
        self.assertEqual(self.view.current_group.group_id, groups[1].group_id)
        self.assertTrue(self.view.btn_previous_group.isEnabled())
        self.assertEqual(
            self.view.lbl_group_position.text(), f"第 2 / {len(groups)} 组"
        )

        self.view.btn_previous_group.click()
        self.assertEqual(self.view.current_group.group_id, groups[0].group_id)

    def test_all_group_detail_methods_share_navigation(self):
        for method in ("scene", "root", "phonics", "relations"):
            groups = self.view.catalog.groups[method]
            self.view.current_method = method
            self.view.show_group(groups[0])
            self.assertFalse(self.view.btn_previous_group.isEnabled(), method)
            self.assertEqual(
                self.view.lbl_group_position.text(),
                f"第 1 / {len(groups)} 组",
                method,
            )

    def test_phonics_page_highlights_an_obvious_chunk(self):
        self.view.current_method = "phonics"
        group = self.view.catalog.groups["phonics"][0]
        self.view.show_group(group)
        self.assertIn("IGHT", group.title)
        self.assertIn("light", self.view.network.word_text_items[0].toPlainText())

    def test_relations_page_displays_relation_and_ipa(self):
        self.view.current_method = "relations"
        group = self.view.catalog.groups["relations"][0]
        self.view.show_group(group)
        for row, item in zip(group.words, self.view.network.word_text_items):
            text = item.toPlainText()
            self.assertIn(row["word"], text)
            self.assertIn(row["pronunciation"], text)

    def test_relations_method_opens_direct_list(self):
        self.view.show_catalog("relations")
        self.assertIs(self.view.stack.currentWidget(), self.view.relations_page)
        self.assertTrue(self.view.header_search.isVisibleTo(self.view))
        self.assertEqual(self.view.relations_tabs.count(), 2)
        self.assertIn("同义词", self.view.relations_tabs.tabText(0))
        self.assertIn("反义词", self.view.relations_tabs.tabText(1))
        self.assertEqual(
            len(self.view.relation_items), len(self.view.catalog.groups["relations"])
        )
        first_item = self.view.relation_items[0][0]
        entries = first_item.data(QtCore.Qt.ItemDataRole.UserRole)
        self.assertIn("/", entries[0]["pronunciation"])
        self.assertTrue(entries[0]["meaning"])
        self.assertEqual(entries[0]["meaning"], entries[1]["meaning"])
        self.assertEqual(self.view.relations_tabs.widget(0).itemDelegate().symbol, "≈")
        self.assertEqual(self.view.relations_tabs.widget(1).itemDelegate().symbol, "↔")
        self.assertEqual(
            self.view.relations_tabs.widget(0).itemDelegate().accent.name(),
            self.view.relations_tabs.widget(1).itemDelegate().accent.name(),
        )

    def test_scene_directory_is_one_page_of_direct_text_links(self):
        self.view.show_catalog("scene")
        self.assertTrue(self.view.header_search.isVisibleTo(self.view))
        links = self.view.catalog_container.findChildren(
            MemoryTextLink, "memory_group_text_link"
        )
        self.assertEqual(len(links), len(self.view.catalog.groups["scene"]))
        link_texts = [link.text() for link in links]
        self.assertTrue(any("住宅建筑" in text for text in link_texts))
        self.assertTrue(any("服装" in text for text in link_texts))
        self.assertTrue(any("学科" in text for text in link_texts))
        self.assertTrue(any("工具与设备" in text for text in link_texts))
        self.assertTrue(all(not link.toolTip() for link in links))
        self.assertTrue(
            all(link.alignment() & QtCore.Qt.AlignmentFlag.AlignLeft for link in links)
        )
        first_row = [
            self.view.catalog_grid.itemAtPosition(0, column)
            for column in range(self.view._rendered_catalog_columns)
        ]
        self.assertTrue(all(item is not None for item in first_row))
        self.assertTrue(
            all(item.widget().objectName() == "memory_text_section" for item in first_row)
        )
        self.assertFalse(
            self.view.catalog_container.findChildren(QtWidgets.QWidget, "scene_text_column_0")
        )
        links[0].click()
        self.assertIs(self.view.stack.currentWidget(), self.view.map_page)
        self.view._go_back()
        self.assertIs(self.view.stack.currentWidget(), self.view.catalog_page)

    def test_root_and_phonics_directories_use_the_same_text_link_style(self):
        for method in ("root", "phonics"):
            self.view.show_catalog(method)
            links = self.view.catalog_container.findChildren(
                MemoryTextLink, "memory_group_text_link"
            )
            self.assertEqual(len(links), len(self.view.catalog.groups[method]))
            self.assertTrue(all(not link.toolTip() for link in links))
            self.assertTrue(
                all(link.alignment() & QtCore.Qt.AlignmentFlag.AlignLeft for link in links)
            )
            self.assertFalse(
                self.view.catalog_container.findChildren(QtWidgets.QPushButton)
            )

    def test_mastery_button_is_inside_content_page_not_header(self):
        group = self.view.catalog.groups["root"][0]
        self.view.show_group(group)
        self.assertEqual(self.view.btn_verify.parent().objectName(), "memory_verify_bar")
        verify_layout = self.view.btn_verify.parent().layout()
        self.assertIs(verify_layout.itemAt(0).widget(), self.view.btn_verify)
        self.assertIs(verify_layout.itemAt(1).widget(), self.view.lbl_verify_explanation)
        self.assertIn("background:transparent", self.view.btn_verify.parent().styleSheet())
        self.assertTrue(self.view.header_search.isHidden())
        self.assertIn("隐藏", self.view.lbl_verify_explanation.text())


if __name__ == "__main__":
    unittest.main()
