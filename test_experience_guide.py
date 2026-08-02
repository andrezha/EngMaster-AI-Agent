import os
import sys
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from experience_guide import ExperienceGuideView
from guide_pages import CommonQuestionsView, InformationTextView, LearningLoopDiagram, OperationGuideView, QuickOverviewView


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
        self.assertIn("先认识可以用来背诵和查看的词表", page_text)
        self.assertIn("分级词汇表", page_text)
        self.assertIn("不规则动词表", page_text)
        self.assertIn("再验证是否真正掌握", page_text)
        self.assertIn("反复验证，直到完整一轮不再产生新错词", page_text)
        self.assertIn("不知道应该重点背哪些", page_text)
        self.assertIn("单词基础比较薄弱", page_text)
        self.assertIn("单词基础比较好", page_text)
        self.assertIn("学习范围逐轮缩小", page_text)
        self.assertIn("错词闯关", page_text)
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
        self.assertIn("60秒了解 EngMaster", page_text)
        self.assertIn("单机版 · 免安装", page_text)
        self.assertIn("下载一个程序文件，双击即可运行", page_text)
        self.assertIn("机器码与激活码", page_text)
        self.assertIn("正式版激活和日常学习均无需联网", page_text)
        self.assertIn("学习数据保存在本机", page_text)
        self.assertIsNotNone(view.findChild(
            QtWidgets.QFrame, "standalone_assurance_card"))
        self.assertIn("录入自己的词汇表", page_text)
        self.assertIn("学习过程有记录", page_text)
        self.assertIn("初高中生家长", page_text)
        self.assertIn("大学四六级和考研学习者", page_text)
        self.assertIn("最近50轮记录", page_text)
        self.assertIn("不同学习阶段", page_text)
        self.assertIn("初中／高中：学生与家长", page_text)
        self.assertIn("大学四六级／考研：学习者本人", page_text)
        self.assertIn("电脑端的共同价值", page_text)
        self.assertIn("不是年龄定位，而是训练方式的改变", page_text)
        self.assertIn("你获得的不只是一张电子词表", page_text)
        self.assertIn("发现不会、集中错词、反复验证并记录进度", page_text)
        diagram = view.findChild(LearningLoopDiagram, "learning_loop_diagram")
        self.assertIsNotNone(diagram)
        self.assertIn("有新错词则返回错词表继续循环", diagram.accessibleDescription())
        self.assertIn("直到完整一轮没有新错词", page_text)
        view._open_regular_challenge()
        self.assertEqual(window.vocab_ctrl.mode, "regular")
        self.assertEqual(window.stack.currentIndex(), 0)
        view.close()
        window.close()

    def test_operation_manual_is_separate_and_task_oriented(self):
        window = self._window()
        view = OperationGuideView(window)
        self.assertEqual(view.section_list.count(), 11)
        self.assertIsNotNone(view.findChild(QtWidgets.QFrame, "maximize_window_notice"))
        all_text = " ".join(
            label.text() for label in view.findChildren(QtWidgets.QLabel))
        self.assertIn("建议最大化窗口使用", all_text)
        self.assertIn("确认／下一题", all_text)
        view.section_list.setCurrentRow(6)
        labels = view.manual_stack.currentWidget().findChildren(QtWidgets.QLabel)
        page_text = " ".join(label.text() for label in labels)
        self.assertIn("自主录入与闯关", page_text)
        self.assertIn("英语单词", page_text)
        self.assertIn("中文解释", page_text)
        self.assertIn("重要提示与常见疑问", page_text)
        view.section_list.setCurrentRow(9)
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


if __name__ == "__main__":
    unittest.main()
