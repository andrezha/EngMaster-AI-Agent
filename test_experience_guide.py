import os
import sys
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from experience_guide import ExperienceGuideView
from guide_pages import AboutCopyrightView, CommonQuestionsView, InformationTextView, OperationGuideView, QuickOverviewView


class _FakeVocabController:
    def __init__(self):
        self.mode = None

    def switch_challenge_mode(self, mode):
        self.mode = mode


class ExperienceGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    def _window(self):
        window = QtWidgets.QMainWindow()
        window.edition = SimpleNamespace(display_name="高考英语")
        window.stack = QtWidgets.QStackedWidget()
        window.stack.addWidget(QtWidgets.QWidget())
        window.vocab_ctrl = _FakeVocabController()
        window.opened = None
        window._safe_nav_to_word_list = lambda: setattr(window, "opened", "word_list")
        window._safe_nav_to_scientific_memory = lambda: setattr(window, "opened", "memory")
        window.show_phrase_irregular_challenge = lambda: setattr(window, "opened", "phrase")
        window._safe_nav_to_self_register = lambda: setattr(window, "opened", "self_register")
        window.show_learning_guide = lambda: setattr(window, "opened", "learning_guide")
        window.show_operation_guide = lambda: setattr(window, "opened", "operation_guide")
        window.show_common_questions = lambda: setattr(window, "opened", "common_questions")
        return window

    def test_page_explains_resources_verification_and_learning_loop(self):
        window = self._window()
        view = ExperienceGuideView(window)
        buttons = view.findChildren(QtWidgets.QPushButton)
        self.assertEqual(len(buttons), 0)
        page_text = " ".join(
            label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("先用高效方法记忆，再使用词表辅助查看", page_text)
        self.assertIn("3800词提分速记", page_text)
        self.assertIn("不规则动词表", page_text)
        self.assertIn("再验证是否真正掌握", page_text)
        self.assertIn("3800词提分速记应该这样使用", page_text)
        self.assertIn("主题场景为主", page_text)
        self.assertIn("本组掌握验证", page_text)
        self.assertIn("背得快、找得准、补得全", page_text)
        self.assertIn("准高一　提前预习", page_text)
        self.assertIn("高三　高考备考", page_text)
        self.assertIn("学习范围逐轮缩小", page_text)
        self.assertIn("普通闯关识别薄弱词", page_text)
        self.assertIn("自主录入词表", page_text)
        self.assertIn("内置分级词库之外，建立自己的长期个人词库", page_text)
        self.assertIn("自主录入不是体验限制功能", page_text)
        view.close()
        window.close()

    def test_quick_page_has_three_starts_and_two_help_links(self):
        window = self._window()
        view = QuickOverviewView(window)
        self.assertEqual(len(view.findChildren(QtWidgets.QPushButton)), 5)
        page_text = " ".join(
            label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("60秒了解英思成", page_text)
        self.assertIn("单机版 · 免安装", page_text)
        self.assertIn("下载一个程序文件，双击即可运行", page_text)
        self.assertIn("机器码与激活码", page_text)
        self.assertIn("正式版激活和日常学习均无需联网", page_text)
        self.assertIn("学习数据保存在本机", page_text)
        self.assertIsNotNone(view.findChild(
            QtWidgets.QFrame, "standalone_assurance_card"))
        self.assertIn("录入自己的词汇表", page_text)
        self.assertIn("学习过程有记录", page_text)
        self.assertIn("学生可以掌握自己的实际进度", page_text)
        self.assertIn("准高一", page_text)
        self.assertIn("高一", page_text)
        self.assertIn("高二", page_text)
        self.assertIn("高三", page_text)
        self.assertIn("最近50轮记录", page_text)
        self.assertIn("从准高一预习到高三备考", page_text)
        self.assertIn("三个学习目的，一套高中3800词", page_text)
        self.assertIn("提前预习", page_text)
        self.assertIn("课内同步背诵", page_text)
        self.assertIn("高效记忆", page_text)
        self.assertIn("闯关识弱", page_text)
        self.assertIn("自主登记", page_text)
        self.assertIn("推荐学习方法", page_text)
        self.assertIn("先选记忆分类", page_text)
        self.assertIn("每次只学一组", page_text)
        view._open_regular_challenge()
        self.assertEqual(window.vocab_ctrl.mode, "regular")
        self.assertEqual(window.stack.currentIndex(), 0)
        view.close()
        window.close()

    def test_operation_manual_is_separate_and_task_oriented(self):
        window = self._window()
        view = OperationGuideView(window)
        self.assertEqual(view.section_list.count(), 12)
        self.assertIsNotNone(view.findChild(QtWidgets.QFrame, "window_display_notice"))
        all_text = " ".join(
            label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("窗口显示与滚动说明", all_text)
        self.assertIn("常见笔记本窗口和最大化显示", all_text)
        self.assertIn("确认／下一题", all_text)
        view.section_list.setCurrentRow(3)
        labels = view.manual_stack.currentWidget().findChildren(QtWidgets.QLabel)
        memory_text = " ".join(label.text() for label in labels)
        self.assertIn("词汇提分速记", memory_text)
        self.assertIn("主题场景只收录主题明确", memory_text)
        self.assertIn("初中版与高中版使用各自独立的主题目录", memory_text)
        view.section_list.setCurrentRow(7)
        labels = view.manual_stack.currentWidget().findChildren(QtWidgets.QLabel)
        page_text = " ".join(label.text() for label in labels)
        self.assertIn("自主录入与闯关", page_text)
        self.assertIn("英语单词", page_text)
        self.assertIn("中文解释", page_text)
        self.assertIn("重要提示与常见疑问", page_text)
        view.section_list.setCurrentRow(10)
        labels = view.manual_stack.currentWidget().findChildren(QtWidgets.QLabel)
        history_text = " ".join(label.text() for label in labels)
        self.assertIn("轮次学习记录", history_text)
        self.assertIn("有效学习时长", history_text)
        self.assertIn("最近50轮", history_text)
        self.assertIn("免费体验／正式版管理与购买", all_text)
        self.assertIn("下次启动自动进入上次使用的版本", all_text)
        view.close()
        window.close()

    def test_common_questions_is_standalone_and_explains_hidden_language_modes(self):
        window = self._window()
        view = CommonQuestionsView(window)
        page_text = " ".join(
            label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("词表为什么只显示英语或只显示中文", page_text)
        self.assertIn("只看英语", page_text)
        self.assertIn("只看中文", page_text)
        self.assertIn("中英对照", page_text)
        self.assertIn("体验版为什么不能打印", page_text)
        self.assertIn("下拉菜单", page_text)
        self.assertIn("完整资料不开放打印", page_text)
        self.assertIn("怎样购买英语正式版", page_text)
        self.assertIn("前往购买", page_text)
        self.assertIn("粘贴并立即激活", page_text)
        self.assertIn("程序为什么提示已经运行", page_text)
        view.close()
        window.close()

    def test_notice_and_version_documents_can_be_shown_as_in_app_pages(self):
        view = InformationTextView(
            "版本与授权信息",
            "查看当前信息",
            "授权状态：已激活\n本机识别码：TEST",
            "version_info_view",
        )
        self.assertEqual(view.objectName(), "version_info_view")
        self.assertTrue(view.text_view.isReadOnly())
        self.assertIn("授权状态：已激活", view.text_view.toPlainText())
        view.set_text("授权状态：未激活")
        self.assertEqual(view.text_view.toPlainText(), "授权状态：未激活")
        view.close()

    def test_about_page_separates_version_copyright_and_licenses(self):
        view = AboutCopyrightView(
            "授权状态：已激活",
            "Copyright © 2026 英思成（RecallLex）。",
            "Open English WordNet 2025\nipa-dict",
            {"ipa-dict MIT许可证": "MIT License"},
        )
        self.assertEqual(view.objectName(), "about_copyright_view")
        self.assertEqual(view.tabs.count(), 3)
        self.assertEqual(
            [view.tabs.tabText(index) for index in range(view.tabs.count())],
            ["版本与授权", "版权说明", "必要第三方许可"],
        )
        self.assertIn("授权状态：已激活", view.version_text_view.toPlainText())
        self.assertIn("英思成", view.copyright_text_view.toPlainText())
        self.assertNotIn("ECDICT", view.data_notice_text_view.toPlainText())
        self.assertEqual(len(view.findChildren(QtWidgets.QPushButton)), 1)
        view.close()


if __name__ == "__main__":
    unittest.main()
