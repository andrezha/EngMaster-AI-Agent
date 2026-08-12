# -*- coding: utf-8 -*-
"""Scientific-memory browsing for the formal Gaokao 3800-word edition.

The feature deliberately stays separate from the existing challenge and
mistake-word flows.  It reorganises the fixed vocabulary for visual study and
offers a lightweight mastery check that hides every English headword in the
current continuously scrollable card wall at once.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import json
import math
from pathlib import PurePosixPath
import re
from typing import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from utils import get_resource_path
from ui_styles import SEARCH_INPUT_STYLE


@dataclass(frozen=True)
class MemoryGroup:
    group_id: str
    title: str
    subtitle: str
    words: tuple[dict, ...]
    hints: tuple[str, ...] = ()
    parent: str = ""


METHOD_META = {
    "root": ("词根记忆", "通过构词结构建立单词联系", "本词根掌握验证"),
    "scene": ("主题场景", "只收录主题明确、归类可靠的词汇", "本主题掌握验证"),
    "phonics": ("音形拼读", "通过读音和字母组合记住拼写", "本音形组掌握验证"),
    "relations": ("同义反义", "用明确的同义或反义关系成组记忆", "本词组掌握验证"),
}

HOME_METHOD_SUBTITLES = {
    "scene": "只收录主题明确、\n归类可靠的词汇",
    "root": "通过构词结构\n建立单词联系",
    "phonics": "通过读音和字母组合\n记住拼写",
    "relations": "用明确的同义或反义关系\n成组记忆",
}

TEXT_CATALOG_PARENTS = {
    "root": {
        "port": "传递与移动", "tele": "传递与移动",
        "mov": "传递与移动", "mot": "传递与移动",
        "spect": "观察与记录", "scrib": "观察与记录",
        "script": "观察与记录", "graph": "观察与记录",
        "form": "形态与结构", "struct": "形态与结构",
        "ject": "动作与变化", "press": "动作与变化", "rupt": "动作与变化",
        "vis": "感知与表达", "vid": "感知与表达",
        "dict": "感知与表达", "view": "感知与表达",
        "act": "行为与关系", "tract": "行为与关系",
        "cept": "行为与关系", "ceive": "行为与关系",
        "mit": "行为与关系", "miss": "行为与关系",
        "serv": "行为与关系", "pos": "行为与关系", "pon": "行为与关系",
        "bio": "科学常用词根", "auto": "科学常用词根", "micro": "科学常用词根",
        "cycl": "科学常用词根", "log": "科学常用词根",
        "logy": "科学常用词根", "uni": "科学常用词根",
    },
    "phonics": {
        "-IGHT": "高频音形组合", "-TURE": "高频音形组合", "-WARD": "高频音形组合",
        "-IFY": "高频音形组合",
        "-TION": "名词构词尾音", "-MENT": "名词构词尾音", "-ANCE": "名词构词尾音",
        "-ENCE": "名词构词尾音", "-ITY": "名词构词尾音", "-NESS": "名词构词尾音",
        "-SHIP": "名词构词尾音",
        "-OUS": "形容词构词尾音", "-ABLE": "形容词构词尾音",
        "-ENT": "形容词构词尾音", "-IVE": "形容词构词尾音",
        "-FUL": "形容词构词尾音", "-LESS": "形容词构词尾音",
        "-ICAL": "形容词构词尾音",
        "-ER": "人物与学科词尾", "-OR": "人物与学科词尾",
        "-IST": "人物与学科词尾", "-CIAN": "人物与学科词尾",
        "-OLOGY": "人物与学科词尾",
    },
}


ROOT_SPECS = (
    ("port", "携带、运输", (
        ("transport", "trans- + PORT"), ("import", "im- + PORT"),
        ("export", "ex- + PORT"), ("portable", "PORT + -able"),
        ("report", "re- + PORT"), ("support", "sup- + PORT"),
    )),
    ("spect", "看、观察", (
        ("inspect", "in- + SPECT"), ("respect", "re- + SPECT"),
        ("prospect", "pro- + SPECT"), ("suspect", "sus- + SPECT"),
        ("inspection", "in- + SPECT + -ion"),
    )),
    ("form", "形成、形状", (
        ("inform", "in- + FORM"), ("transform", "trans- + FORM"),
        ("reform", "re- + FORM"), ("uniform", "uni- + FORM"),
        ("perform", "per- + FORM"), ("information", "in- + FORM + -ation"),
    )),
    ("struct", "建造、组成", (
        ("construct", "con- + STRUCT"), ("instruct", "in- + STRUCT"),
        ("structure", "STRUCT + -ure"),
        ("construction", "con- + STRUCT + -ion"),
        ("instruction", "in- + STRUCT + -ion"),
    )),
    ("ject", "投、掷", (
        ("object", "ob- + JECT"), ("project", "pro- + JECT"),
        ("reject", "re- + JECT"), ("subject", "sub- + JECT"),
    )),
    ("press", "压、按", (
        ("express", "ex- + PRESS"), ("impress", "im- + PRESS"),
        ("depress", "de- + PRESS"), ("pressure", "PRESS + -ure"),
        ("expression", "ex- + PRESS + -ion"),
        ("impression", "im- + PRESS + -ion"),
    )),
    ("rupt", "破、断裂", (
        ("interrupt", "inter- + RUPT"), ("erupt", "e- + RUPT"),
        ("corrupt", "cor- + RUPT"), ("abrupt", "ab- + RUPT"),
    )),
    ("scrib", "写", (
        ("describe", "de- + SCRIB"), ("subscribe", "sub- + SCRIB"),
    )),
    ("script", "写", (
        ("description", "de- + SCRIPT + -ion"),
        ("prescription", "pre- + SCRIPT + -ion"),
    )),
    ("graph", "写、记录", (
        ("geography", "geo- + GRAPHY"), ("biography", "bio- + GRAPHY"),
        ("paragraph", "para- + GRAPH"),
        ("calligraphy", "calli- + GRAPHY"),
        ("photographer", "photo- + GRAPH + -er"),
    )),
    ("tele", "远距离", (
        ("telephone", "TELE + phone"), ("television", "TELE + vision"),
        ("telescope", "TELE + scope"),
    )),
    ("mov", "移动", (
        ("remove", "re- + MOV + -e"), ("movement", "MOV(E) + -ment"),
    )),
    ("mot", "移动", (
        ("motion", "MOT + -ion"), ("motivate", "MOT + -ivate"),
        ("promote", "pro- + MOT"), ("emotion", "e- + MOT + -ion"),
    )),
    ("vis", "看、观察", (
        ("vision", "VIS + -ion"), ("visual", "VIS + -ual"),
        ("visible", "VIS + -ible"), ("television", "tele- + VIS + -ion"),
        ("visit", "VIS + -it"),
    )),
    ("vid", "看、观察", (
        ("video", "VID + -eo"), ("evident", "e- + VID + -ent"),
        ("evidence", "e- + VID + -ence"),
    )),
    ("dict", "说、断言", (
        ("dictionary", "DICT + -ionary"), ("predict", "pre- + DICT"),
        ("contradict", "contra- + DICT"),
    )),
    ("act", "做、行动", (
        ("act", "ACT"), ("action", "ACT + -ion"),
        ("active", "ACT + -ive"), ("activity", "ACT + -ivity"),
        ("actor", "ACT + -or"), ("react", "re- + ACT"),
        ("reaction", "re- + ACT + -ion"),
        ("interaction", "inter- + ACT + -ion"),
    )),
    ("tract", "拉、牵引", (
        ("attract", "at- + TRACT"), ("attraction", "at- + TRACT + -ion"),
        ("contract", "con- + TRACT"),
    )),
    ("cept", "拿、接受", (
        ("accept", "ac- + CEPT"), ("except", "ex- + CEPT"),
        ("concept", "con- + CEPT"), ("reception", "re- + CEPT + -ion"),
    )),
    ("ceive", "拿、接受", (
        ("receive", "re- + CEIVE"), ("perceive", "per- + CEIVE"),
    )),
    ("mit", "送、放出", (
        ("admit", "ad- + MIT"), ("permit", "per- + MIT"),
        ("submit", "sub- + MIT"),
    )),
    ("miss", "送、放出", (
        ("dismiss", "dis- + MISS"),
        ("mission", "MISS + -ion"), ("permission", "per- + MISS + -ion"),
    )),
    ("uni", "一、单一", (
        ("uniform", "UNI + form"), ("universe", "UNI + verse"),
        ("university", "UNI + versity"), ("unite", "UNI + -ite"),
        ("union", "UNI + -on"), ("unique", "UNI + -que"),
    )),
    ("serv", "服务、保留", (
        ("serve", "SERV + -e"), ("service", "SERV + -ice"),
        ("servant", "SERV + -ant"), ("reserve", "re- + SERV + -e"),
        ("preserve", "pre- + SERV + -e"),
    )),
    ("cycl", "环、循环", (
        ("cycle", "CYCL + -e"), ("recycle", "re- + CYCL + -e"),
    )),
    ("bio", "生命", (
        ("biology", "BIO + -logy"), ("biography", "BIO + -graphy"),
    )),
    ("auto", "自己、自动", (
        ("automatic", "AUTO + -matic"), ("autonomous", "AUTO + -nomous"),
    )),
    ("micro", "微小", (
        ("microscope", "MICRO + scope"), ("microwave", "MICRO + wave"),
    )),
    ("pos", "放、安置", (
        ("position", "POS + -ition"), ("positive", "POS + -itive"),
        ("opposite", "op- + POS + -ite"),
        ("expose", "ex- + POS + -e"), ("compose", "com- + POS + -e"),
    )),
    ("pon", "放、安置", (
        ("postpone", "post- + PON + -e"),
        ("component", "com- + PON + -ent"),
        ("opponent", "op- + PON + -ent"),
    )),
    ("view", "看", (
        ("view", "VIEW"), ("review", "re- + VIEW"),
        ("preview", "pre- + VIEW"), ("interview", "inter- + VIEW"),
    )),
    ("log", "言语、道理", (
        ("logical", "LOG + -ical"), ("dialogue", "dia- + LOG + -ue"),
        ("apology", "apo- + LOG + -y"),
    )),
    ("logy", "学科、研究", (
        ("biology", "bio- + LOGY"), ("psychology", "psycho- + LOGY"),
        ("technology", "techno- + LOGY"), ("ecology", "eco- + LOGY"),
    )),
)


PHONICS_SPECS = (
    ("ending_ight", "-IGHT", "/aɪt/ · 明显的结尾音形词块", (
        "light", "night", "right", "bright", "fight", "flight", "sight", "tight",
    )),
    ("ending_tion", "-TION", "/ʃən/ · 常见名词结尾", (
        "action", "attention", "education", "information", "invitation",
        "production", "direction", "competition",
    )),
    ("ending_ment", "-MENT", "/mənt/ · 常见名词结尾", (
        "agreement", "development", "movement", "achievement",
        "treatment", "government", "encouragement", "environment",
    )),
    ("ending_ous", "-OUS", "/əs/ · 常见形容词结尾", (
        "famous", "dangerous", "nervous", "serious", "curious",
        "obvious", "generous", "various",
    )),
    ("ending_able", "-ABLE", "/əbl/ · 表示能够或具有某种性质", (
        "available", "comfortable", "enjoyable", "portable",
        "reasonable", "reliable", "suitable", "valuable",
    )),
    ("ending_ture", "-TURE", "/tʃə(r)/ · 明显的结尾音形词块", (
        "future", "picture", "culture", "nature", "feature",
        "mixture", "structure", "adventure",
    )),
    ("ending_ent", "-ENT", "/ənt/ · 常见结尾词块", (
        "absent", "different", "excellent", "intelligent",
        "patient", "recent", "resident", "student",
    )),
    ("ending_ance", "-ANCE", "/əns/ · 常见名词结尾", (
        "appearance", "assistance", "distance", "importance",
        "performance", "resistance", "entrance",
    )),
    ("ending_ence", "-ENCE", "/əns/ · 常见名词结尾", (
        "confidence", "difference", "evidence", "existence",
        "experience", "influence", "patience",
    )),
    ("ending_ity", "-ITY", "/əti/ · 常见抽象名词结尾", (
        "ability", "activity", "electricity", "equality",
        "identity", "possibility", "responsibility", "university",
    )),
    ("ending_ive", "-IVE", "/ɪv/ · 常见形容词结尾", (
        "active", "attractive", "creative", "positive", "relative", "sensitive",
    )),
    ("ending_ful", "-FUL", "/fəl/ · 表示充满或具有", (
        "beautiful", "careful", "helpful", "powerful",
        "peaceful", "successful", "useful", "harmful",
    )),
    ("ending_less", "-LESS", "/ləs/ · 表示缺少或没有", (
        "breathless", "careless", "endless", "harmless",
        "hopeless", "stainless", "useless", "worthless",
    )),
    ("ending_ness", "-NESS", "/nəs/ · 常见性质名词结尾", (
        "darkness", "fairness", "happiness", "illness",
        "kindness", "sadness", "sickness", "weakness",
    )),
    ("ending_ship", "-SHIP", "/ʃɪp/ · 表示关系、身份或状态", (
        "friendship", "hardship", "leadership", "membership",
        "ownership", "relationship", "scholarship",
    )),
    ("ending_ist", "-IST", "/ɪst/ · 人物或专业身份结尾", (
        "artist", "chemist", "cyclist", "dentist",
        "journalist", "physicist", "pianist", "scientist",
    )),
    ("ending_ify", "-IFY", "/ɪfaɪ/ · 常见动词结尾", (
        "clarify", "classify", "identify", "justify",
        "qualify", "simplify", "terrify",
    )),
    ("ending_ical", "-ICAL", "/ɪkəl/ · 常见形容词结尾", (
        "chemical", "classical", "critical", "electrical",
        "logical", "physical", "political", "technical",
    )),
    ("ending_ward", "-WARD", "/wəd/ · 表示方向的结尾", (
        "afterward", "backward", "downward", "forward",
        "outward", "straightforward",
    )),
    ("ending_ology", "-OLOGY", "/ˈɒlədʒi/ · 学科与研究名称结尾", (
        "biology", "psychology", "technology", "ecology",
    )),
    ("ending_er_person", "-ER", "/ə(r)/ · 表示做某事的人", (
        "teacher", "worker", "writer", "driver",
        "player", "speaker", "reporter",
    )),
    ("ending_or_person", "-OR", "/ə(r)/ · 常见人物身份结尾", (
        "actor", "director", "editor", "educator",
        "inventor", "operator", "visitor",
    )),
    ("ending_cian", "-CIAN", "/ʃən/ · 专业人物身份结尾", (
        "musician", "physician", "politician",
    )),
)


SCENE_SPECS = (
    ("airport", "机场出行", "人物、证件、物品、地点和动作", (
        ("airport", "地点"), ("flight", "行程"), ("passenger", "人物"),
        ("pilot", "人物"), ("passport", "证件"), ("ticket", "证件"),
        ("luggage", "物品"), ("suitcase", "物品"), ("board", "动作"),
        ("land", "动作"), ("arrival", "行程"), ("departure", "行程"),
    )),
    ("classroom", "校园课堂", "人物、学习用品和课堂活动", (
        ("school", "地点"), ("classroom", "地点"), ("teacher", "人物"),
        ("student", "人物"), ("lesson", "学习"), ("textbook", "用品"),
        ("blackboard", "用品"), ("desk", "用品"), ("homework", "学习"),
        ("exam", "学习"), ("learn", "动作"), ("study", "动作"),
    )),
    ("hospital", "医院就医", "医护人员、疾病、治疗和康复", (
        ("hospital", "地点"), ("doctor", "人物"), ("nurse", "人物"),
        ("patient", "人物"), ("medicine", "物品"), ("disease", "病症"),
        ("treatment", "治疗"), ("health", "状态"), ("pain", "病症"),
        ("recover", "动作"), ("operation", "治疗"),
    )),
    ("weather", "天气变化", "天气状态、自然现象和气候", (
        ("weather", "主题"), ("sunny", "状态"), ("rainy", "状态"),
        ("cloudy", "状态"), ("windy", "状态"), ("storm", "现象"),
        ("snow", "现象"), ("temperature", "指标"), ("climate", "长期"),
        ("forecast", "信息"),
    )),
    ("kitchen", "厨房用餐", "三餐、餐具和烹饪活动", (
        ("kitchen", "地点"), ("cook", "动作"), ("meal", "饮食"),
        ("breakfast", "三餐"), ("lunch", "三餐"), ("dinner", "三餐"),
        ("plate", "餐具"), ("bowl", "餐具"), ("spoon", "餐具"),
        ("fork", "餐具"), ("knife", "餐具"), ("food", "饮食"),
    )),
    ("family", "家庭成员", "家庭关系中的常见人物", (
        ("family", "整体"), ("father", "长辈"), ("mother", "长辈"),
        ("parent", "长辈"), ("son", "晚辈"), ("daughter", "晚辈"),
        ("brother", "同辈"), ("sister", "同辈"), ("husband", "夫妻"),
        ("wife", "夫妻"), ("child", "晚辈"),
    )),
    ("road", "道路交通", "道路、车辆、人员和交通动作", (
        ("road", "地点"), ("street", "地点"), ("traffic", "状态"),
        ("car", "车辆"), ("bus", "车辆"), ("taxi", "车辆"),
        ("driver", "人物"), ("passenger", "人物"),
        ("motorcycle", "车辆"), ("cross", "动作"), ("turn", "动作"),
    )),
    ("hotel", "酒店住宿", "预订、入住、服务和房间用品", (
        ("hotel", "地点"), ("room", "地点"), ("guest", "人物"),
        ("reception", "服务"), ("book", "动作"), ("reserve", "动作"),
        ("service", "服务"), ("key", "物品"), ("stay", "动作"),
        ("check", "动作"),
    )),
    ("shopping", "商店购物", "商品、价格、顾客和买卖动作", (
        ("shop", "地点"), ("store", "地点"), ("market", "地点"),
        ("customer", "人物"), ("price", "价格"), ("cost", "价格"),
        ("pay", "动作"), ("buy", "动作"), ("sell", "动作"),
        ("cash", "支付"), ("product", "商品"),
    )),
    ("sports", "运动比赛", "运动项目、人员和比赛动作", (
        ("sport", "主题"), ("exercise", "动作"), ("run", "动作"),
        ("jump", "动作"), ("swim", "动作"), ("football", "项目"),
        ("basketball", "项目"), ("tennis", "项目"), ("player", "人物"),
        ("coach", "人物"), ("match", "比赛"), ("team", "团队"),
    )),
)


def _short_meaning(content: object, limit: int = 12) -> str:
    text = str(content or "").strip()
    first = text.split("|")[0].strip()
    first = re.sub(r"^[A-Za-z_ ]+[：:]\s*", "", first)
    first = first.replace("；", "、")
    if len(first) > limit:
        return first[:limit] + "…"
    return first or "查看释义"


class ScientificMemoryCatalog:
    """Build stable study groups from an edition's fixed vocabulary."""

    def __init__(self, vocabulary_path: str, trial_preview: bool = False,
                 memory_data_path: str | None = None):
        with open(get_resource_path(vocabulary_path), "r", encoding="utf-8") as handle:
            rows = json.load(handle)
        self.words = tuple(row for row in rows if isinstance(row, dict) and row.get("word"))
        self.by_word = {str(row["word"]).casefold(): row for row in self.words}
        self.by_record_id = {str(row.get("record_id", "")): row for row in self.words}
        self.memory_data_path = memory_data_path or str(
            PurePosixPath(vocabulary_path).with_name("scientific_memory_data.json"))
        self.memory_data = self._load_memory_data()
        self.groups = {
            "root": self._build_root_groups(),
            "scene": self._build_scene_groups(),
            "phonics": self._build_phonics_groups(),
            "relations": self._build_relation_groups(),
        }
        if trial_preview:
            self._keep_trial_preview()

    def _keep_trial_preview(self):
        """Expose a small but complete sample of every memory method."""
        scene_title_choices = (
            ("身体部位",),
            ("食物饮料", "一日三餐"),
            ("交通工具", "道路交通"),
            ("学科", "学校学科"),
            ("正面情绪",),
            ("颜色", "常见颜色"),
        )
        scenes = []
        for choices in scene_title_choices:
            match = next(
                (
                    group for group in self.groups["scene"]
                    if group.title.split(" · ", 1)[0] in choices
                ),
                None,
            )
            if match is not None:
                scenes.append(match)
        root_ids = {"root:port", "root:spect", "root:struct"}
        phonics_ids = {
            "phonics:ending_ight", "phonics:ending_tion", "phonics:ending_ment",
        }
        synonyms = [
            group for group in self.groups["relations"]
            if "synonym:" in group.group_id
        ][:3]
        antonyms = [
            group for group in self.groups["relations"]
            if "antonym:" in group.group_id
        ][:3]
        root_groups = [
            group for group in self.groups["root"] if group.group_id in root_ids
        ]
        root_groups.extend(
            group for group in self.groups["root"]
            if group not in root_groups and len(root_groups) < 3
        )
        phonics_groups = [
            group for group in self.groups["phonics"]
            if group.group_id in phonics_ids
        ]
        phonics_groups.extend(
            group for group in self.groups["phonics"]
            if group not in phonics_groups and len(phonics_groups) < 3
        )
        self.groups = {
            "scene": tuple(scenes),
            "root": tuple(root_groups[:3]),
            "phonics": tuple(phonics_groups[:3]),
            "relations": tuple(synonyms + antonyms),
        }

    def _load_memory_data(self) -> dict:
        path = get_resource_path(self.memory_data_path)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError, TypeError):
            return {}

    def _groups_from_records(
        self, key: str, prefix: str, minimum_words: int = 2
    ) -> tuple[MemoryGroup, ...]:
        groups = []
        for raw in self.memory_data.get(key, []):
            records = raw.get("records", [])
            words = tuple(
                self.by_record_id[record_id]
                for record_id in records
                if record_id in self.by_record_id
            )
            hints = tuple(str(value) for value in raw.get("hints", []))
            if len(words) >= minimum_words:
                groups.append(MemoryGroup(
                    f"{prefix}:{raw.get('id', len(groups) + 1)}",
                    str(raw.get("title", "")),
                    str(raw.get("subtitle", "")),
                    words,
                    hints[:len(words)],
                    str(raw.get("parent", "")),
                ))
        return tuple(groups)

    def _existing(self, names: Iterable[str]) -> tuple[dict, ...]:
        return tuple(
            self.by_word[name.casefold()]
            for name in names
            if name.casefold() in self.by_word
        )

    def _existing_with_hints(
        self, entries: Iterable[tuple[str, str]]
    ) -> tuple[tuple[dict, ...], tuple[str, ...]]:
        words = []
        hints = []
        for name, hint in entries:
            row = self.by_word.get(name.casefold())
            if row is not None:
                words.append(row)
                hints.append(hint)
        return tuple(words), tuple(hints)

    def _build_root_groups(self) -> tuple[MemoryGroup, ...]:
        groups = []
        for root, meaning, entries in ROOT_SPECS:
            words, hints = self._existing_with_hints(entries)
            if len(words) >= 2:
                groups.append(MemoryGroup(f"root:{root}", root, meaning, words, hints))
        return tuple(groups)

    def _build_scene_groups(self) -> tuple[MemoryGroup, ...]:
        generated = self._groups_from_records("scene_groups", "scene", minimum_words=1)
        if generated:
            return generated
        groups = []
        for group_id, title, subtitle, entries in SCENE_SPECS:
            words, hints = self._existing_with_hints(entries)
            if len(words) >= 3:
                groups.append(
                    MemoryGroup(f"scene:{group_id}", title, subtitle, words, hints)
                )
        return tuple(groups)

    def _build_relation_groups(self) -> tuple[MemoryGroup, ...]:
        return self._groups_from_records("relation_groups", "relations")

    def _build_phonics_groups(self) -> tuple[MemoryGroup, ...]:
        groups = []
        for group_id, title, subtitle, members in PHONICS_SPECS:
            words = self._existing(members)
            if len(words) >= 3:
                groups.append(MemoryGroup(f"phonics:{group_id}", title, subtitle, words))
        return tuple(groups)

    def scene_word_count(self) -> int:
        return sum(len(group.words) for group in self.groups["scene"])


class MemoryNetworkView(QtWidgets.QGraphicsView):
    """One centered topic linked to compact rectangular word cards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("memory_network")
        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing
            | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QtGui.QColor("#f8fafc"))
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.group: MemoryGroup | None = None
        self.method = "root"
        self.words: tuple[dict, ...] = ()
        self.hide_english = False
        self.word_text_items: list[QtWidgets.QGraphicsTextItem] = []

    @staticmethod
    def _rounded_rect_path(rect, radius):
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    @staticmethod
    def _add_html_text(scene, html_text, rect, top_offset=0, margin=12):
        item = QtWidgets.QGraphicsTextItem()
        item.setHtml(html_text)
        item.setTextWidth(rect.width() - margin * 2)
        item.setPos(rect.x() + margin, rect.y() + top_offset)
        item.setZValue(2)
        scene.addItem(item)
        return item

    def set_group(self, group: MemoryGroup, method="root", hide_english=False):
        self.group = group
        self.method = method
        self.words = tuple(group.words)
        self.hide_english = bool(hide_english)
        self._rebuild()

    def set_hide_english(self, hidden: bool):
        self.hide_english = bool(hidden)
        self._rebuild()

    def _method_colors(self):
        return {
            "root": ("#2563eb", "#eaf3ff"),
            "scene": ("#16a34a", "#ecfdf3"),
            "phonics": ("#d97706", "#fff7e6"),
            "relations": ("#7c3aed", "#f3e8ff"),
        }[self.method]

    def _center_html(self):
        label = {
            "root": "词根", "scene": "细分主题", "phonics": "音形词块",
            "relations": "同义反义",
        }[self.method]
        return (
            '<div style="text-align:center;color:#172033;">'
            f'<div style="font-size:13px;color:#64748b;">{label}</div>'
            f'<div style="font-size:25px;font-weight:800;margin-top:3px;">{html.escape(self.group.title)}</div>'
            f'<div style="font-size:13px;color:#475569;margin-top:5px;">{html.escape(self.group.subtitle)}</div>'
            '</div>'
        )

    @staticmethod
    def _ipa(row):
        return html.escape(str(row.get("pronunciation", "")).strip())

    def _root_html(self, word, pronunciation, meaning, hint):
        pieces = []
        for token in hint.split(" + "):
            escaped = html.escape(token)
            if any(char.isupper() for char in token):
                color = "#ea580c"
            elif token.startswith("-"):
                color = "#16a34a"
            else:
                color = "#2563eb"
            pieces.append(f'<span style="color:{color};font-weight:800;">{escaped}</span>')
        return (
            '<div style="text-align:center;color:#172033;">'
            f'<div style="font-size:12px;">{" + ".join(pieces)}</div>'
            f'<div style="font-size:16px;font-weight:800;margin-top:3px;">{html.escape(word)}</div>'
            f'<div style="font-size:10px;color:#64748b;">{pronunciation}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:2px;">{html.escape(meaning)}</div></div>'
        )

    def _scene_html(self, word, pronunciation, meaning, hint):
        return (
            '<div style="text-align:center;color:#172033;">'
            f'<div style="font-size:16px;font-weight:800;">{html.escape(word)}</div>'
            f'<div style="font-size:10px;color:#64748b;">{pronunciation}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:2px;">{html.escape(meaning)}</div>'
            f'<div style="font-size:10px;color:#15803d;margin-top:2px;">{html.escape(hint)}</div></div>'
        )

    def _phonics_html(self, word, pronunciation, meaning):
        chunk = self.group.title.strip("-").casefold()
        lowered = word.casefold()
        start = lowered.rfind(chunk)
        if start >= 0:
            before = html.escape(word[:start])
            marked = html.escape(word[start:start + len(chunk)])
            after = html.escape(word[start + len(chunk):])
            display = f'{before}<span style="color:#ea580c;">{marked}</span>{after}'
        else:
            display = html.escape(word)
        return (
            '<div style="text-align:center;color:#172033;">'
            f'<div style="font-size:17px;font-weight:800;">{display}</div>'
            f'<div style="font-size:10px;color:#b45309;margin-top:2px;">{pronunciation}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:2px;">{html.escape(meaning)}</div></div>'
        )

    def _relations_html(self, word, pronunciation, meaning, hint):
        return (
            '<div style="text-align:center;color:#172033;">'
            f'<div style="font-size:16px;font-weight:800;">{html.escape(word)}</div>'
            f'<div style="font-size:10px;color:#64748b;">{pronunciation}</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:2px;">{html.escape(meaning)}</div>'
            f'<div style="font-size:10px;color:#7c3aed;margin-top:2px;">{html.escape(hint)}</div></div>'
        )

    def _word_html(self, index, row):
        word = str(row.get("word", ""))
        pronunciation = self._ipa(row)
        meaning = _short_meaning(row.get("content"), limit=16)
        hint = self.group.hints[index] if index < len(self.group.hints) else ""
        if self.hide_english:
            hint_color = "#7c3aed" if self.method == "relations" else "#15803d"
            extra = f'<div style="font-size:10px;color:{hint_color};margin-top:3px;">{html.escape(hint)}</div>' if hint else ""
            return (
                '<div style="text-align:center;color:#334155;">'
                f'<div style="font-size:11px;color:#64748b;">{pronunciation}</div>'
                f'<div style="font-size:14px;font-weight:650;margin-top:4px;">{html.escape(meaning)}</div>{extra}</div>'
            )
        if self.method == "root":
            return self._root_html(word, pronunciation, meaning, hint)
        if self.method == "scene":
            return self._scene_html(word, pronunciation, meaning, hint)
        if self.method == "phonics":
            return self._phonics_html(word, pronunciation, meaning)
        return self._relations_html(word, pronunciation, meaning, hint)

    def _rebuild(self):
        scene = QtWidgets.QGraphicsScene(self)
        self.setScene(scene)
        self.word_text_items = []
        if self.group is None:
            return

        accent, center_fill = self._method_colors()
        count = max(1, len(self.words))
        radius_x = 430 if count > 8 else 365
        radius_y = 285 if count > 8 else 255
        card_width, card_height = 190, 96
        center_rect = QtCore.QRectF(-125, -62, 250, 124)

        positions = []
        for index in range(count):
            if count == 1:
                angle = -90
            elif count == 2:
                angle = 180 * index
            else:
                angle = -90 + index * (360 / count)
            radians = angle * 3.141592653589793 / 180
            x = radius_x * math.cos(radians)
            y = radius_y * math.sin(radians)
            positions.append((x, y))
            line = scene.addLine(
                0, 0, x, y, QtGui.QPen(QtGui.QColor(accent), 2.0)
            )
            line.setOpacity(0.5)
            line.setZValue(0)

        center = scene.addPath(
            self._rounded_rect_path(center_rect, 24),
            QtGui.QPen(QtGui.QColor(accent), 2.6),
            QtGui.QBrush(QtGui.QColor(center_fill)),
        )
        center.setZValue(1)
        self._add_html_text(scene, self._center_html(), center_rect, 13, margin=14)

        for index, (row, (x, y)) in enumerate(zip(self.words, positions)):
            word = str(row.get("word", ""))
            rect = QtCore.QRectF(x - card_width / 2, y - card_height / 2, card_width, card_height)
            card = scene.addPath(
                self._rounded_rect_path(rect, 13),
                QtGui.QPen(QtGui.QColor(accent), 1.45),
                QtGui.QBrush(QtGui.QColor("#ffffff")),
            )
            card.setZValue(1)
            top_offset = 15 if self.hide_english else 7
            text_item = self._add_html_text(scene, self._word_html(index, row), rect, top_offset, margin=9)
            text_item.setData(0, word)
            self.word_text_items.append(text_item)

        scene.setSceneRect(-555, -370, 1110, 740)
        self._fit_scene()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_scene()

    def _fit_scene(self):
        if self.scene() is not None and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)


class RelationListWidget(QtWidgets.QListWidget):
    """A compact two-column relation wall that collapses on narrow windows."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = max(320, self.viewport().width() - 18)
        columns = 2 if width >= 860 else 1
        self.setGridSize(QtCore.QSize(width // columns - 4, 86))


class MemoryTextLink(QtWidgets.QLabel):
    """A genuinely left-aligned text link without button chrome."""

    clicked = QtCore.Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def click(self):
        self.clicked.emit()


class RelationComparisonDelegate(QtWidgets.QStyledItemDelegate):
    """Paint a word/IPA/meaning comparison without creating per-row widgets."""

    def __init__(self, accent, symbol, parent=None):
        super().__init__(parent)
        self.accent = QtGui.QColor(accent)
        self.symbol = symbol

    def sizeHint(self, option, index):
        return QtCore.QSize(720, 82)

    def paint(self, painter, option, index):
        entries = index.data(QtCore.Qt.ItemDataRole.UserRole) or []
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(3, 3, -3, -3)
        fill = QtGui.QColor("#eff6ff") if option.state & QtWidgets.QStyle.StateFlag.State_Selected else QtGui.QColor("#ffffff")
        painter.setPen(QtGui.QPen(QtGui.QColor("#dbe4ef"), 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 9, 9)
        if not entries:
            painter.restore()
            return

        entries = entries[:2]
        middle = rect.center().x()
        gap = 42
        cells = (
            QtCore.QRectF(rect.left() + 8, rect.top(), middle - gap - rect.left() - 8, rect.height()),
            QtCore.QRectF(middle + gap, rect.top(), rect.right() - middle - gap - 8, rect.height()),
        )
        for entry, cell in zip(entries, cells):
            painter.setPen(self.accent)
            font = painter.font()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRectF(cell.x(), cell.y() + 5, cell.width(), 22),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                str(entry.get("word", "")),
            )
            painter.setPen(QtGui.QColor("#64748b"))
            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRectF(cell.x(), cell.y() + 27, cell.width(), 17),
                QtCore.Qt.AlignmentFlag.AlignCenter,
                str(entry.get("pronunciation", "")),
            )
            painter.setPen(QtGui.QColor("#334155"))
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRectF(cell.x(), cell.y() + 47, cell.width(), 22),
                QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
                str(entry.get("meaning", "")),
            )
        painter.setPen(self.accent)
        font = painter.font()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRectF(middle - gap, rect.y() + 4, gap * 2, 25),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            self.symbol,
        )
        painter.restore()


class ScientificMemoryView(QtWidgets.QWidget):
    """Top-level page for the four agreed scientific-memory methods."""

    def __init__(self, main_window=None, vocabulary_path=None):
        super().__init__()
        self.setObjectName("scientific_memory_view")
        self.main_window = main_window
        edition = getattr(main_window, "edition", None)
        edition_id = str(getattr(edition, "edition_id", ""))
        self.trial_preview = edition_id == "trial" or edition_id.startswith("trial_")
        formal_id = "gaokao" if edition_id == "trial" else edition_id.removeprefix("trial_")
        self.formal_id = formal_id or "gaokao"
        self.formal_count = 1609 if self.formal_id == "zhongkao" else 3800
        if self.trial_preview:
            vocabulary_path = f"assets/editions/{self.formal_id}/vocabulary.json"
        elif vocabulary_path is None:
            vocabulary_path = getattr(
                edition, "vocabulary_path", "assets/editions/gaokao/vocabulary.json"
            )
        memory_path = f"assets/editions/{self.formal_id}/scientific_memory_data.json"
        self.catalog = ScientificMemoryCatalog(
            vocabulary_path, trial_preview=self.trial_preview,
            memory_data_path=memory_path,
        )
        self.current_method = "scene"
        self.current_group: MemoryGroup | None = None
        self.validation_active = False
        self._build_ui()
        self.show_home()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._discard_bin = QtWidgets.QWidget(self)
        self._discard_bin.setObjectName("scientific_memory_discard_bin")
        self._discard_bin.hide()

        self.header = QtWidgets.QFrame()
        self.header.setObjectName("memory_header")
        self.header.setFixedHeight(74)
        self.header.setStyleSheet(
            "QFrame#memory_header{background:#ffffff;border-bottom:1px solid #dbe4ef;}"
        )
        header_outer = QtWidgets.QVBoxLayout(self.header)
        header_outer.setContentsMargins(22, 10, 22, 10)
        header_outer.setSpacing(8)
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(10)
        self.btn_back = QtWidgets.QPushButton("← 返回上一级")
        self.btn_home = QtWidgets.QPushButton("⌂ 提分速记主页")
        for button in (self.btn_back, self.btn_home):
            button.setFixedHeight(38)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton{background:#f8fafc;color:#334155;border:1px solid #cbd5e1;"
                "border-radius:9px;padding:0 14px;font-size:14px;font-weight:600;}"
                "QPushButton:hover{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8;}"
            )
        self.lbl_header_title = QtWidgets.QLabel()
        self.lbl_header_title.setStyleSheet(
            "color:#172033;font-size:21px;font-weight:700;padding-left:8px;"
        )
        self.header_search = QtWidgets.QLineEdit()
        self.header_search.setObjectName("scientific_memory_header_search")
        self.header_search.setClearButtonEnabled(True)
        self.header_search.setFixedSize(220, 36)
        self.header_search.setStyleSheet(SEARCH_INPUT_STYLE)
        self.btn_trial_upgrade = QtWidgets.QPushButton(f"解锁完整{self.formal_count}词")
        self.btn_trial_upgrade.setObjectName("btn_scientific_memory_trial_upgrade")
        self.btn_trial_upgrade.setFixedSize(245, 44)
        self.btn_trial_upgrade.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_trial_upgrade.setStyleSheet(
            "QPushButton{background:#f97316;color:white;border:1px solid #ea580c;"
            "border-radius:11px;padding:0 14px;font-size:15px;font-weight:800;}"
            "QPushButton:hover{background:#ea580c;border-color:#c2410c;}"
        )
        self.btn_trial_upgrade.hide()
        self.btn_trial_upgrade.clicked.connect(self._open_trial_purchase)
        self.btn_verify = QtWidgets.QPushButton()
        self.btn_verify.setObjectName("btn_memory_verify")
        self.btn_verify.setFixedHeight(40)
        self.btn_verify.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(self.btn_back)
        header_layout.addWidget(self.btn_home)
        header_layout.addWidget(self.lbl_header_title)
        header_layout.addWidget(self.btn_trial_upgrade)
        header_layout.addStretch()
        header_outer.addLayout(header_layout)
        self.header_search_row = QtWidgets.QWidget()
        search_layout = QtWidgets.QHBoxLayout(self.header_search_row)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(10)
        search_layout.addWidget(self.header_search)
        search_layout.addStretch()
        header_outer.addWidget(self.header_search_row)
        root.addWidget(self.header)

        self.stack = QtWidgets.QStackedWidget()
        self.home_page = self._build_home_page()
        self.catalog_page = self._build_catalog_page()
        self.relations_page = self._build_relations_page()
        self.map_page = self._build_map_page()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.catalog_page)
        self.stack.addWidget(self.relations_page)
        self.stack.addWidget(self.map_page)
        root.addWidget(self.stack, 1)

        self.btn_back.clicked.connect(self._go_back)
        self.btn_home.clicked.connect(self.show_home)
        self.btn_verify.clicked.connect(self._toggle_validation)
        self.header_search.textChanged.connect(self._on_header_search)

    def _open_trial_purchase(self):
        callback = getattr(self.main_window, "request_trial_activation", None)
        if callable(callback):
            callback()

    def _build_home_page(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("scientific_memory_home_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:#f4f7fb;border:none;}")
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f4f7fb;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(48, 34, 48, 38)
        layout.setSpacing(16)
        memory_name = "初中词汇提分速记" if self.formal_id == "zhongkao" else "高中3800词提分速记"
        title = QtWidgets.QLabel(
            f"{memory_name} · 免费体验" if self.trial_preview else memory_name)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size:30px;font-weight:800;color:#172033;")
        subtitle = QtWidgets.QLabel(
            f"免费体验代表性分类；正式版解锁{self.formal_count}词完整主题与全部分组"
            if self.trial_preview
            else "严格筛选 · 只展示关系明确、适合直接记忆的分组"
        )
        subtitle.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size:16px;color:#64748b;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        self.home_method_container = QtWidgets.QWidget()
        self.home_method_grid = QtWidgets.QGridLayout(self.home_method_container)
        self.home_method_grid.setContentsMargins(0, 0, 0, 0)
        self.home_method_grid.setHorizontalSpacing(20)
        self.home_method_grid.setVerticalSpacing(18)
        self.home_method_grid.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter
            | QtCore.Qt.AlignmentFlag.AlignTop)
        colors = {method: ("#ffffff", "#2563eb") for method in METHOD_META}
        self.method_buttons = {}
        for method in ("scene", "root", "phonics", "relations"):
            title_text, _subtitle_text, _verify = METHOD_META[method]
            subtitle_text = HOME_METHOD_SUBTITLES[method]
            fill, border = colors[method]
            count = len(self.catalog.groups[method])
            button = QtWidgets.QPushButton(
                f"{title_text}\n{subtitle_text}\n{count}个分组"
            )
            button.setObjectName(f"btn_memory_{method}")
            button.setFixedSize(245, 154)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                f"QPushButton{{background:{fill};color:#172033;border:2px solid {border};"
                "border-radius:16px;font-size:15px;font-weight:700;padding:14px 20px;"
                "text-align:left;}"
                f"QPushButton:hover{{background:#ffffff;border-color:{border};}}"
            )
            button.clicked.connect(lambda _checked=False, m=method: self.show_catalog(m))
            self.method_buttons[method] = button
        self._home_method_columns = 0
        self._update_home_method_layout(force=True)
        layout.addWidget(self.home_method_container)
        layout.addStretch()
        note = QtWidgets.QLabel(
            "当前仅开放精选样例；购买正式版后可使用完整提分速记目录"
            if self.trial_preview
            else "完整词表和词汇闯关继续从左侧原有菜单进入"
        )
        note.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet("color:#64748b;font-size:14px;")
        layout.addWidget(note)
        scroll.setWidget(page)
        return scroll

    def _desired_home_method_columns(self):
        available = max(0, self.width() - 96)
        if available >= 4 * 245 + 3 * 20:
            return 4
        if available >= 2 * 245 + 20:
            return 2
        return 1

    def _update_home_method_layout(self, force=False):
        if not hasattr(self, "home_method_grid"):
            return
        columns = self._desired_home_method_columns()
        if not force and columns == self._home_method_columns:
            return
        while self.home_method_grid.count():
            self.home_method_grid.takeAt(0)
        for index, method in enumerate(("scene", "root", "phonics", "relations")):
            self.home_method_grid.addWidget(
                self.method_buttons[method],
                index // columns,
                index % columns,
                QtCore.Qt.AlignmentFlag.AlignTop,
            )
        self._home_method_columns = columns

    def _catalog_columns_for_width(self, method=None):
        method = method or self.current_method
        viewport_width = (
            self.catalog_scroll.viewport().width()
            if hasattr(self, "catalog_scroll") else self.width()
        )
        maximum = 3 if method == "scene" else 4
        return min(maximum, max(1, viewport_width // 260))

    def _refresh_responsive_layout(self):
        self._responsive_update_pending = False
        self._update_home_method_layout()
        if (hasattr(self, "stack")
                and self.stack.currentWidget() is self.catalog_page
                and self.current_method in {"scene", "root", "phonics"}):
            expected = self._catalog_columns_for_width()
            if expected != getattr(self, "_rendered_catalog_columns", None):
                self._render_catalog()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not getattr(self, "_responsive_update_pending", False):
            self._responsive_update_pending = True
            QtCore.QTimer.singleShot(0, self._refresh_responsive_layout)

    def _build_catalog_page(self):
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f8fafc;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(14)
        self.lbl_catalog_intro = QtWidgets.QLabel()
        self.lbl_catalog_intro.setStyleSheet("font-size:15px;color:#64748b;")
        layout.addWidget(self.lbl_catalog_intro)
        self.catalog_scroll = QtWidgets.QScrollArea()
        self.catalog_scroll.setWidgetResizable(True)
        self.catalog_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.catalog_scroll.setStyleSheet("background:transparent;")
        self.catalog_container = QtWidgets.QWidget()
        self.catalog_grid = QtWidgets.QGridLayout(self.catalog_container)
        self.catalog_grid.setContentsMargins(8, 12, 8, 12)
        self.catalog_grid.setHorizontalSpacing(18)
        self.catalog_grid.setVerticalSpacing(18)
        self.catalog_grid.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
        )
        self.catalog_scroll.setWidget(self.catalog_container)
        layout.addWidget(self.catalog_scroll, 1)
        return page

    def _build_relations_page(self):
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f8fafc;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(12)

        self.lbl_relations_intro = QtWidgets.QLabel()
        self.lbl_relations_intro.setStyleSheet("font-size:15px;color:#64748b;")
        layout.addWidget(self.lbl_relations_intro)

        self.relations_tabs = QtWidgets.QTabWidget()
        self.relations_tabs.setObjectName("relations_tabs")
        self.relations_tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #dbe4ef;background:#f8fafc;"
            "border-radius:9px;}QTabBar::tab{background:#eef2f7;color:#475569;"
            "padding:10px 30px;border:1px solid #dbe4ef;border-bottom:none;"
            "font-size:14px;font-weight:700;}QTabBar::tab:selected{background:#eff6ff;"
            "color:#1d4ed8;border-color:#93c5fd;}"
        )
        layout.addWidget(self.relations_tabs, 1)
        self._populate_relations()
        return page

    def _populate_relations(self):
        groups = self.catalog.groups["relations"]
        synonyms = [group for group in groups if "synonym:" in group.group_id]
        antonyms = [group for group in groups if "antonym:" in group.group_id]
        self.relation_items = []
        for title, relation_groups, accent, symbol in (
            (f"同义词（{len(synonyms)}）", synonyms, "#2563eb", "≈"),
            (f"反义词（{len(antonyms)}）", antonyms, "#2563eb", "↔"),
        ):
            tab = self._create_relation_tab(relation_groups, accent, symbol)
            self.relations_tabs.addTab(tab, title)
        self.lbl_relations_intro.setText(
            "严格校对常用义：第一行词对，第二行发音，第三行中文"
        )

    def _create_relation_tab(self, groups, accent, symbol):
        list_widget = RelationListWidget()
        list_widget.setObjectName("relation_comparison_list")
        list_widget.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        list_widget.setSpacing(3)
        list_widget.setUniformItemSizes(True)
        list_widget.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        list_widget.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        list_widget.setWrapping(True)
        list_widget.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        list_widget.setMovement(QtWidgets.QListView.Movement.Static)
        list_widget.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        list_widget.setStyleSheet("QListWidget{background:#f8fafc;border:none;}")
        list_widget.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        list_widget.setItemDelegate(RelationComparisonDelegate(accent, symbol, list_widget))
        for group in groups:
            entries = []
            search_parts = []
            for position, row in enumerate(group.words):
                word = str(row.get("word", ""))
                pronunciation = str(row.get("pronunciation", "")).strip()
                meaning = (
                    group.hints[position]
                    if position < len(group.hints) and group.hints[position]
                    else _short_meaning(row.get("content"), limit=22)
                )
                entries.append({
                    "word": word,
                    "pronunciation": pronunciation,
                    "meaning": meaning,
                })
                search_parts.extend((word, pronunciation, meaning))
            search_text = " ".join(search_parts).casefold()
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.UserRole, entries)
            item.setToolTip(f"  {symbol}  ".join(entry["word"] for entry in entries))
            list_widget.addItem(item)
            self.relation_items.append((item, search_text))
        return list_widget

    def _filter_relations(self, text=""):
        query = str(text).strip().casefold()
        for item, haystack in self.relation_items:
            item.setHidden(bool(query and query not in haystack))

    def _build_map_page(self):
        page = QtWidgets.QWidget()
        page.setStyleSheet("background:#f8fafc;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        verify_bar = QtWidgets.QFrame()
        verify_bar.setObjectName("memory_verify_bar")
        verify_bar.setFixedHeight(48)
        verify_bar.setStyleSheet(
            "QFrame#memory_verify_bar{background:transparent;border:none;}"
        )
        verify_layout = QtWidgets.QHBoxLayout(verify_bar)
        verify_layout.setContentsMargins(4, 4, 4, 4)
        self.lbl_verify_explanation = QtWidgets.QLabel(
            "掌握验证：隐藏当前页面的英文，保留音标和中文进行自查"
        )
        self.lbl_verify_explanation.setStyleSheet(
            "font-size:13px;color:#64748b;border:none;"
        )
        self.btn_previous_group = QtWidgets.QPushButton("← 上一组")
        self.btn_previous_group.setObjectName("btn_memory_previous_group")
        self.lbl_group_position = QtWidgets.QLabel()
        self.lbl_group_position.setObjectName("lbl_memory_group_position")
        self.lbl_group_position.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_group_position.setMinimumWidth(78)
        self.lbl_group_position.setStyleSheet(
            "font-size:13px;color:#64748b;border:none;"
        )
        self.btn_next_group = QtWidgets.QPushButton("下一组 →")
        self.btn_next_group.setObjectName("btn_memory_next_group")
        for button in (self.btn_previous_group, self.btn_next_group):
            button.setFixedHeight(36)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton{background:white;color:#334155;border:1px solid #cbd5e1;"
                "border-radius:8px;padding:0 13px;font-size:13px;font-weight:700;}"
                "QPushButton:hover{background:#eff6ff;border-color:#93c5fd;color:#1d4ed8;}"
                "QPushButton:disabled{background:#f8fafc;color:#cbd5e1;border-color:#e2e8f0;}"
            )
        verify_layout.addWidget(self.btn_verify)
        verify_layout.addWidget(self.lbl_verify_explanation)
        verify_layout.addStretch()
        verify_layout.addWidget(self.btn_previous_group)
        verify_layout.addWidget(self.lbl_group_position)
        verify_layout.addWidget(self.btn_next_group)
        self.btn_previous_group.clicked.connect(
            lambda: self._navigate_group(-1)
        )
        self.btn_next_group.clicked.connect(
            lambda: self._navigate_group(1)
        )
        layout.addWidget(verify_bar)
        self.network = MemoryNetworkView()
        layout.addWidget(self.network, 1)
        return page

    def show_home(self):
        self.validation_active = False
        self.current_group = None
        self.stack.setCurrentWidget(self.home_page)
        self.lbl_header_title.setText(
            "初中词汇提分速记" if self.formal_id == "zhongkao"
            else "3800词提分速记")
        self.btn_back.hide()
        self.btn_home.hide()
        self.btn_verify.hide()
        self.btn_trial_upgrade.hide()
        self.header_search_row.hide()
        self.header_search.hide()
        self.header.setFixedHeight(74)

    def show_catalog(self, method):
        self.current_method = method
        self.validation_active = False
        self.current_group = None
        self.header_search_row.show()
        self.header_search.show()
        self.btn_trial_upgrade.setVisible(self.trial_preview)
        self.header.setFixedHeight(116)
        if method == "relations":
            self.stack.setCurrentWidget(self.relations_page)
            self.lbl_header_title.setText(METHOD_META[method][0])
            self.header_search.setPlaceholderText("搜索同义词或反义词……")
            self.header_search.clear()
            self.btn_back.show()
            self.btn_back.setText("← 提分速记主页")
            self.btn_home.hide()
            self.btn_verify.hide()
            if self.trial_preview:
                self.lbl_relations_intro.setText(
                    "免费体验：精选3组同义词和3组反义词；正式版解锁完整内容"
                )
            return
        self.stack.setCurrentWidget(self.catalog_page)
        title, subtitle, _verify = METHOD_META[method]
        self.lbl_header_title.setText(title)
        self.header_search.setPlaceholderText("搜索主题、分组或单词……")
        self.header_search.clear()
        self.lbl_catalog_intro.setText(
            f"免费体验：每种方法开放少量代表性分组；正式版解锁{self.formal_count}词完整目录。"
            if self.trial_preview
            else "全部分组在同一页以文字目录展示，点击带数量的文字直接进入单词页。"
        )
        self.btn_back.show()
        self.btn_back.setText("← 提分速记主页")
        self.btn_home.hide()
        self.btn_verify.hide()
        self._render_catalog()

    def _clear_grid(self):
        while self.catalog_grid.count():
            item = self.catalog_grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                # Detaching a visible card makes it a temporary top-level
                # window on Windows.  Move it into an always-hidden owned
                # container so it leaves the live catalogue immediately but
                # never becomes a window while deferred deletion is pending.
                widget.hide()
                widget.setParent(self._discard_bin)
                widget.deleteLater()
        self.catalog_container.setMinimumHeight(0)

    def _reserve_catalog_height(self, item_count, columns, item_height):
        rows = max(1, (item_count + columns - 1) // columns)
        self.catalog_container.setMinimumHeight(
            rows * item_height + max(0, rows - 1) * 18 + 28
        )

    def _render_catalog(self, _text=None):
        self._clear_grid()
        query = self.header_search.text().strip().casefold()
        if self.current_method in {"root", "scene", "phonics"}:
            self._render_text_catalog(query)
            return
        groups = []
        for group in self.catalog.groups[self.current_method]:
            haystack = " ".join(
                [group.title, group.subtitle]
                + [str(row.get("word", "")) for row in group.words]
            ).casefold()
            if not query or query in haystack:
                groups.append(group)
        for index, group in enumerate(groups):
            button = QtWidgets.QPushButton(
                f"{group.title}\n{group.subtitle}\n{len(group.words)}个词"
            )
            compact = self.current_method == "scene"
            if compact:
                button.setText(f"{group.title}\n{len(group.words)}个词")
                button.setFixedSize(184, 66)
                button.setToolTip(group.subtitle)
            else:
                button.setFixedSize(220, 112)
            button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton{background:white;color:#172033;border:1.5px solid #93b4df;"
                f"border-radius:{10 if compact else 14}px;font-size:{13 if compact else 14}px;"
                f"font-weight:650;padding:{8 if compact else 14}px;}}"
                "QPushButton:hover{background:#eff6ff;border-color:#2563eb;color:#1d4ed8;}"
            )
            button.clicked.connect(
                lambda _checked=False, selected=group: self.show_group(selected)
            )
            columns = 5 if compact else 4
            self.catalog_grid.addWidget(button, index // columns, index % columns)
        if not groups:
            empty = QtWidgets.QLabel("没有找到相关分组")
            empty.setStyleSheet("font-size:16px;color:#64748b;padding:30px;")
            self.catalog_grid.addWidget(empty, 0, 0)
        else:
            self._reserve_catalog_height(
                len(groups), 5 if self.current_method == "scene" else 4,
                66 if self.current_method == "scene" else 112,
            )

    def _render_text_catalog(self, query=""):
        method = self.current_method
        parents = {}
        for group in self.catalog.groups[method]:
            name = self._scene_category_name(group) if method == "scene" else group.title
            parent = (
                group.parent or name
                if method == "scene"
                else TEXT_CATALOG_PARENTS.get(method, {}).get(name, METHOD_META[method][0])
            )
            haystack = " ".join(
                [parent, name, group.subtitle]
                + [str(row.get("word", "")) for row in group.words]
            ).casefold()
            if query and query not in haystack:
                continue
            parents.setdefault(parent, []).append(group)

        if not parents:
            empty = QtWidgets.QLabel("没有找到相关主题或单词")
            empty.setStyleSheet("font-size:16px;color:#64748b;padding:30px;")
            self.catalog_grid.addWidget(empty, 0, 0)
            return

        column_count = min(
            self._catalog_columns_for_width(method), max(1, len(parents)))
        self._rendered_catalog_columns = column_count
        for column_index in range(column_count):
            self.catalog_grid.setColumnStretch(column_index, 1)

        colors = ("#2563eb",) * 5
        sections = []
        for parent, parent_groups in sorted(parents.items(), key=lambda item: item[0]):
            parent_groups.sort(key=lambda group: group.title)
            for start in range(0, len(parent_groups), 16):
                sections.append((parent, parent_groups[start:start + 16], start > 0, parent_groups))
        sections.sort(
            key=lambda section: (
                -math.ceil(len(section[1]) / (2 if method == "scene" and len(section[1]) >= 4 else 1)),
                section[0],
            )
        )

        rendered_sections = []
        for section_index, (parent, groups, continuation, all_parent_groups) in enumerate(sections):
            row_index, column_index = divmod(section_index, column_count)
            accent = colors[column_index]
            section = QtWidgets.QWidget()
            section.setObjectName("memory_text_section")
            section.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
            section.setStyleSheet(
                "QWidget#memory_text_section{background:#ffffff;border:1px solid #dbe4ef;"
                "border-radius:12px;}"
            )
            section_layout = QtWidgets.QVBoxLayout(section)
            section_layout.setContentsMargins(12, 10, 12, 12)
            section_layout.setSpacing(4)

            word_count = sum(len(group.words) for group in all_parent_groups)
            heading_text = f"{parent}  {word_count}词" if not continuation else f"{parent}（续）"
            heading = QtWidgets.QLabel(heading_text)
            heading.setStyleSheet(
                f"color:{accent};font-size:15px;font-weight:800;padding:2px 2px 7px 2px;"
            )
            section_layout.addWidget(heading)

            links = QtWidgets.QWidget()
            links.setStyleSheet(f"border-left:3px solid {accent};")
            links_layout = QtWidgets.QGridLayout(links)
            links_layout.setContentsMargins(9, 0, 0, 1)
            links_layout.setHorizontalSpacing(8)
            links_layout.setVerticalSpacing(0)
            link_columns = 2 if method == "scene" and len(groups) >= 4 else 1
            for group_index, group in enumerate(groups):
                link = MemoryTextLink()
                link.setObjectName("memory_group_text_link")
                if method == "scene":
                    label = f"{group.title}（{len(group.words)}）"
                else:
                    label = f"{group.title} · {group.subtitle}（{len(group.words)}）"
                link.setText(label)
                link.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                link.setFixedHeight(24)
                link.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.Fixed,
                )
                link.setMinimumWidth(0)
                link.setStyleSheet(
                    "QLabel{background:transparent;border:none;color:#334155;"
                    "font-size:12px;padding:1px 3px;}"
                    f"QLabel:hover{{color:{accent};text-decoration:underline;}}"
                )
                link.clicked.connect(
                    lambda _checked=False, selected=group: self.show_group(selected)
                )
                links_layout.addWidget(
                    link,
                    group_index // link_columns,
                    group_index % link_columns,
                )
            for link_column in range(link_columns):
                links_layout.setColumnStretch(link_column, 1)
            section_layout.addWidget(links)
            section_layout.addStretch()
            self.catalog_grid.addWidget(
                section,
                row_index,
                column_index,
            )
            rendered_sections.append((section, row_index))

        row_weights = [
            max(
                math.ceil(len(groups) / (2 if method == "scene" and len(groups) >= 4 else 1)) + 2
                for _parent, groups, _cont, _all in row
            )
            for start in range(0, len(sections), column_count)
            for row in (sections[start:start + column_count],)
        ]
        for section, row_index in rendered_sections:
            section.setFixedHeight(row_weights[row_index] * 26 + 18)
        estimated_height = (
            sum(weight * 26 + 18 for weight in row_weights)
            + max(0, len(row_weights) - 1) * self.catalog_grid.verticalSpacing()
            + self.catalog_grid.contentsMargins().top()
            + self.catalog_grid.contentsMargins().bottom()
        )
        self.catalog_container.setMinimumHeight(max(580, estimated_height))

    @staticmethod
    def _scene_category_name(group: MemoryGroup) -> str:
        return group.title.split(" · ", 1)[0]

    def show_group(self, group: MemoryGroup):
        self.current_group = group
        self.validation_active = False
        self.stack.setCurrentWidget(self.map_page)
        self.btn_back.show()
        self.btn_back.setText(f"← {METHOD_META[self.current_method][0]}目录")
        self.btn_home.show()
        self.btn_verify.show()
        self.btn_trial_upgrade.hide()
        self.header_search_row.hide()
        self.header_search.hide()
        self.header.setFixedHeight(74)
        self.lbl_header_title.setText(group.title)
        self.lbl_verify_explanation.setText(
            f"掌握验证：隐藏本{METHOD_META[self.current_method][0]}页面的英文，保留音标和中文"
        )
        self._update_verify_button()
        self.network.set_group(
            self.current_group, method=self.current_method, hide_english=False
        )
        self._update_group_navigation()

    def _group_sequence(self) -> tuple[MemoryGroup, ...]:
        return tuple(self.catalog.groups.get(self.current_method, ()))

    def _current_group_index(self) -> int:
        if self.current_group is None:
            return -1
        for index, group in enumerate(self._group_sequence()):
            if group.group_id == self.current_group.group_id:
                return index
        return -1

    def _update_group_navigation(self):
        groups = self._group_sequence()
        index = self._current_group_index()
        valid = index >= 0
        self.lbl_group_position.setText(
            f"第 {index + 1} / {len(groups)} 组" if valid else ""
        )
        self.btn_previous_group.setEnabled(valid and index > 0)
        self.btn_next_group.setEnabled(valid and index < len(groups) - 1)

    def _navigate_group(self, offset: int):
        groups = self._group_sequence()
        index = self._current_group_index()
        target = index + int(offset)
        if index < 0 or target < 0 or target >= len(groups):
            return
        self.show_group(groups[target])

    def _toggle_validation(self):
        if self.current_group is None:
            return
        self.validation_active = not self.validation_active
        self.network.set_hide_english(self.validation_active)
        self._update_verify_button()

    def _update_verify_button(self):
        if self.validation_active:
            self.btn_verify.setText("取消验证")
            self.btn_verify.setStyleSheet(
                "QPushButton{background:#fff7ed;color:#c2410c;border:1px solid #fdba74;"
                "border-radius:9px;padding:0 18px;font-size:14px;font-weight:700;}"
                "QPushButton:hover{background:#ffedd5;}"
            )
        else:
            self.btn_verify.setText(METHOD_META[self.current_method][2])
            self.btn_verify.setStyleSheet(
                "QPushButton{background:#2563eb;color:white;border:none;border-radius:9px;"
                "padding:0 18px;font-size:14px;font-weight:700;}"
                "QPushButton:hover{background:#1d4ed8;}"
            )

    def _go_back(self):
        if self.stack.currentWidget() is self.map_page:
            self.show_catalog(self.current_method)
        else:
            self.show_home()

    def _on_header_search(self, text):
        if self.current_method == "relations":
            self._filter_relations(text)
        elif self.stack.currentWidget() is self.catalog_page:
            self._render_catalog(text)

    def reset_to_home(self):
        self.current_method = "scene"
        self.show_home()
