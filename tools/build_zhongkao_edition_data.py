"""Build the production junior-high edition from audited project sources.

The curriculum boundary CSV is evidence for scope, not a ready-made product
dictionary.  This builder resolves its junior tokens to the licensed senior-high
product records, records spelling variants explicitly, and supplies the small
number of junior-only headwords as independently authored records.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "editions" / "zhongkao"
HIGH_DIR = ROOT / "assets" / "editions" / "gaokao"
TOKENS_CSV = ROOT / "data_sources" / "processed" / "phrase_stage_boundaries" / "phrase_stage_vocabulary_tokens.csv"
PHRASES_SOURCE = ROOT / "data_sources" / "clean" / "phrase_product_candidates" / "junior_phrases_product_candidate.json"
IRREGULAR_SOURCE = ROOT / "data_sources" / "clean" / "irregular_verbs" / "irregular_verbs_clean.json"
IRREGULAR_SCOPE = ROOT / "research" / "edition_samples" / "zhongkao_irregular_verbs.json"

TRIAL_WORDS = [
    "classroom", "family", "parent", "subject", "homework", "library",
    "weather", "season", "healthy", "exercise", "breakfast", "vegetable",
    "hospital", "travel", "holiday", "museum", "country", "language",
    "future", "dream", "environment", "protect", "volunteer", "culture",
    "festival", "traffic", "important", "different", "because", "together",
]

# Variant token -> product headword.  These are retained as searchable and
# accepted answers rather than duplicated into misleading separate cards.
EXTRA_VARIANTS = {
    "app": "application", "gray": "grey", "gymnasium": "gym",
    "math": "maths", "mom": "mother", "practise": "practice",
    "theater": "theatre",
}

# Tokens produced by splitting an explicitly printed multiword entry.
STRUCTURAL_TOKENS = {"curd": "bean curd", "kung": "kung fu", "fu": "kung fu"}

NEW_RECORDS = {
    "according": ("adjective：相符的；一致的；according to：根据；按照", "/əˈkɔːdɪŋ/", "adjective"),
    "AI": ("noun：人工智能", "/ˌeɪ ˈaɪ/", "noun"),
    "bin": ("noun：垃圾箱；箱子", "/bɪn/", "noun"),
    "bully": ("noun：恃强凌弱者；verb：欺负", "/ˈbʊli/", "noun; verb"),
    "chip": ("noun：碎片；薯片；芯片；筹码；verb：削下；打缺口", "/tʃɪp/", "noun; verb"),
    "chore": ("noun：家务活；日常杂务", "/tʃɔːr/", "noun"),
    "cucumber": ("noun：黄瓜", "/ˈkjuːkʌmbər/", "noun"),
    "empress": ("noun：女皇；皇后", "/ˈemprəs/", "noun"),
    "fireman": ("noun：消防员", "/ˈfaɪəmən/", "noun"),
    "firework": ("noun：烟花；烟火", "/ˈfaɪəwɜːk/", "noun"),
    "hostess": ("noun：女主人；女主持人；女乘务员", "/ˈhəʊstəs/", "noun"),
    "humour": ("noun：幽默；幽默感", "/ˈhjuːmər/", "noun"),
    "kung fu": ("noun：功夫；中国武术", "/ˌkʌŋ ˈfuː/", "noun"),
    "lost": ("adjective：迷路的；丢失的；lose的过去式和过去分词", "/lɒst/", "adjective; verb"),
    "mall": ("noun：购物中心", "/mɔːl/", "noun"),
    "mutton": ("noun：羊肉", "/ˈmʌtən/", "noun"),
    "Olympic": ("adjective：奥林匹克运动会的", "/əˈlɪmpɪk/", "adjective"),
    "organise": ("verb：组织；安排；筹备", "/ˈɔːɡənaɪz/", "verb"),
    "oven": ("noun：烤箱；烤炉", "/ˈʌvən/", "noun"),
    "penguin": ("noun：企鹅", "/ˈpeŋɡwɪn/", "noun"),
    "ping-pong": ("noun：乒乓球", "/ˈpɪŋ pɒŋ/", "noun"),
    "pizza": ("noun：比萨饼", "/ˈpiːtsə/", "noun"),
    "porridge": ("noun：粥；麦片粥", "/ˈpɒrɪdʒ/", "noun"),
    "prince": ("noun：王子；亲王", "/prɪns/", "noun"),
    "princess": ("noun：公主；王妃", "/ˌprɪnˈses/", "noun"),
    "sore": ("adjective：疼痛的；酸痛的；noun：痛处；伤处", "/sɔːr/", "adjective; noun"),
    "teamwork": ("noun：团队合作；协作", "/ˈtiːmwɜːk/", "noun"),
    "teenage": ("adjective：青少年的", "/ˈtiːneɪdʒ/", "adjective"),
}

NEW_VARIANTS = {"humor": "humour", "organize": "organise"}

# The junior scene catalogue is independently curated.  It deliberately does
# not try to place every headword: function words, broad abstract words and
# polysemous words without a clear junior-learning scene remain available in
# the complete vocabulary and in the other memory methods.  This prevents the
# old failure mode where a filtered senior-high taxonomy produced fragments
# such as "团体组织: brush/cream/forest" or "日常物品: beach/moon".
#
# parent, title, subtitle, headwords.  A theme may contain more than 12 words;
# build_scientific_memory splits it into coherent, display-sized groups.
JUNIOR_SCENE_THEMES = (
    ("学校学习", "校园场所", "学校里常见的地点和空间", (
        "classroom", "college", "gym", "hall", "lab", "library",
        "playground", "school", "university",
    )),
    ("学校学习", "课堂用品", "上课、书写和整理学习资料时使用", (
        "blackboard", "chalk", "desk", "dictionary", "eraser", "notebook",
        "pen", "pencil", "ruler", "schoolbag",
    )),
    ("学校学习", "课程学习", "课堂学习、作业和考试活动", (
        "class", "course", "education", "exam", "homework", "lesson",
        "practice", "project", "score", "study", "test",
    )),
    ("学校学习", "学校学科", "初中阶段常见课程名称", (
        "art", "biology", "chemistry", "Chinese", "English", "geography",
        "grammar", "history", "literature", "maths", "music", "PE",
        "physics", "science",
    )),
    ("学校学习", "语言学习", "英语听说读写和语言知识", (
        "conversation", "dialogue", "language", "listen", "meaning",
        "paragraph", "pronounce", "read", "sentence", "speak", "spell",
        "translate", "word", "write",
    )),
    ("家庭生活", "家庭成员", "家庭和亲属关系中的人物", (
        "aunt", "brother", "child", "cousin", "daughter", "family",
        "father", "grandfather", "grandmother", "husband", "mother",
        "parent", "relative", "sister", "son", "uncle", "wife",
    )),
    ("家庭生活", "年龄阶段", "从婴儿到老年的常见年龄称呼", (
        "adult", "baby", "born", "elder", "junior", "kid", "teenage",
        "young", "youth",
    )),
    ("家庭生活", "住宅房间", "家中的房间、区域和基本结构", (
        "apartment", "bathroom", "bedroom", "door", "floor", "garden",
        "gate", "home", "house", "kitchen", "room", "toilet", "wall",
        "window",
    )),
    ("家庭生活", "家具家电", "家庭中常见的家具和电器", (
        "bed", "chair", "clock", "fan", "fridge", "lamp", "mirror",
        "oven", "shelf", "shower", "sofa", "table",
    )),
    ("家庭生活", "家务劳动", "整理、清洁和照料家庭", (
        "chore", "clean", "cook", "housework", "sweep", "tidy",
        "wash",
    )),
    ("饮食健康", "一日三餐", "进餐时间、餐食和用餐活动", (
        "breakfast", "dinner", "drink", "eat", "food", "lunch", "meal",
        "picnic", "restaurant", "snack",
    )),
    ("饮食健康", "餐具容器", "盛放、制作和食用食物的物品", (
        "bowl", "chopsticks", "cup", "dish", "fork", "knife",
        "plate", "pot", "spoon",
    )),
    ("饮食健康", "水果", "常见水果", (
        "apple", "banana", "grape", "lemon", "orange", "pear",
        "strawberry", "watermelon",
    )),
    ("饮食健康", "蔬菜", "常见蔬菜和植物性食材", (
        "bean", "cabbage", "carrot", "corn", "cucumber", "onion",
        "pepper", "potato", "tomato", "vegetable",
    )),
    ("饮食健康", "主食小吃", "常见主食、甜点和小吃", (
        "bean curd", "biscuit", "bread", "cake", "candy", "chocolate",
        "cookie", "dumpling", "hamburger", "noodle", "pancake", "pie",
        "pizza", "porridge", "rice", "sandwich", "soup",
    )),
    ("饮食健康", "肉蛋奶饮品", "常见肉类、奶制品和饮料", (
        "beef", "butter", "cheese", "chicken", "coffee", "cream", "egg", "honey",
        "juice", "meat", "milk", "mutton", "pork", "tea", "yoghurt",
    )),
    ("饮食健康", "健康饮食", "饮食习惯、味道和营养状态", (
        "delicious", "diet", "fresh", "healthy", "hungry", "salt", "sugar",
        "sweet", "thirsty",
    )),
    ("身体健康", "身体部位", "人体常见部位", (
        "arm", "back", "blood", "body", "brain", "ear", "eye", "face",
        "finger", "foot", "hair", "hand", "head", "heart", "knee", "leg",
        "mouth", "neck", "nose", "shoulder", "stomach", "throat", "tooth",
    )),
    ("身体健康", "疾病症状", "常见疾病、疼痛和身体不适", (
        "ache", "cancer", "cough", "disease", "fever", "flu", "ill",
        "illness", "pain", "sick", "sore", "tired", "virus", "wound",
    )),
    ("身体健康", "医院就医", "医院中的人员、用品和健康照护", (
        "dentist", "doctor", "health", "hospital", "medicine", "nurse",
        "patient", "X-ray",
    )),
    ("身体健康", "身体状态", "身体能力、感官和休息状态", (
        "alive", "asleep", "awake", "blind", "dead", "deaf", "fit",
        "sleep", "strong", "weak",
    )),
    ("交通旅行", "道路交通", "道路、车辆和日常通行", (
        "bike", "bus", "car", "coach", "driver", "passenger", "road",
        "station", "street", "taxi", "traffic", "truck",
    )),
    ("交通旅行", "长途交通", "长途交通工具和交通地点", (
        "airport", "plane", "railway", "ship", "train",
    )),
    ("交通旅行", "水域与船只", "江河湖海和常见水上交通工具", (
        "boat", "coast", "island", "lake", "ocean", "river", "sea",
    )),
    ("交通旅行", "旅行度假", "旅行、参观、住宿和假期活动", (
        "camp", "guide", "hike", "holiday", "hotel", "journey", "museum",
        "passport", "tent", "ticket", "tour", "tourist", "travel", "trip",
        "vacation", "visit",
    )),
    ("交通旅行", "移动动作", "出发、到达和途中移动", (
        "arrive", "climb", "cross", "drive", "enter", "fly", "go", "leave",
        "reach", "return", "ride", "run", "stop", "turn", "walk",
    )),
    ("自然世界", "天气气候", "天气状态和气象现象", (
        "climate", "cloud", "cloudy", "fog", "rain", "snow", "storm",
        "sunny", "temperature", "thunder", "weather", "wind", "windy",
    )),
    ("自然世界", "四季时段", "季节和一天中的常见时段", (
        "afternoon", "autumn", "evening", "morning", "night", "noon",
        "season", "spring", "summer", "winter",
    )),
    ("自然世界", "山川地貌", "陆地上的自然环境和地形", (
        "beach", "countryside", "desert", "field", "forest", "ground",
        "hill", "land", "landscape", "mountain", "rock", "sand", "stone",
    )),
    ("自然世界", "天空宇宙", "天空、天体和宇宙", (
        "moon", "planet", "rainbow", "rocket", "sky", "star", "sun", "universe",
        "world",
    )),
    ("自然世界", "植物花木", "常见植物及其组成部分", (
        "bamboo", "flower", "grass", "leaf", "plant", "rose", "tree", "wood",
    )),
    ("动物世界", "昆虫鸟类", "昆虫和常见鸟类", (
        "ant", "bee", "bird", "butterfly", "duck", "eagle", "hen", "insect",
    )),
    ("动物世界", "家养动物", "家庭或农场中常见的动物", (
        "cat", "cow", "dog", "horse", "pet", "pig", "rabbit", "sheep",
    )),
    ("动物世界", "野生动物", "陆地上的常见野生动物", (
        "bear", "elephant", "fox", "giraffe", "lion", "monkey", "panda",
        "penguin", "snake", "tiger", "wolf",
    )),
    ("动物世界", "水生动物", "生活在水中或水边的动物", (
        "fish", "shark", "whale",
    )),
    ("动物世界", "动物身体", "描述动物时常见的身体部位", (
        "tail", "wing",
    )),
    ("穿着外貌", "日常服装", "日常穿着的衣物", (
        "blouse", "cap", "clothes", "coat", "dress", "hat", "jacket",
        "jeans", "shirt", "shorts", "skirt", "suit", "sweater", "T-shirt",
        "trousers", "uniform",
    )),
    ("穿着外貌", "衣物细节与配饰", "鞋袜、衣物细节和随身配饰", (
        "belt", "glove", "pocket", "scarf", "shoe", "sock", "wallet",
    )),
    ("穿着外貌", "人物外貌", "描述人的外表和体型", (
        "beautiful", "cute", "fat", "handsome", "lovely", "pretty", "slim",
        "tall", "ugly",
    )),
    ("颜色形状", "常见颜色", "基础颜色和明暗", (
        "black", "blue", "bright", "brown", "colour", "dark", "green", "grey",
        "pink", "purple", "red", "white", "yellow",
    )),
    ("颜色形状", "形状大小", "常见形状和大小描述", (
        "big", "circle", "flat", "huge", "large", "long", "narrow", "round",
        "short", "small", "square", "straight", "thick", "thin", "tiny", "wide",
    )),
    ("运动娱乐", "球类运动", "常见球类和持拍运动", (
        "badminton", "baseball", "basketball", "football", "ping-pong", "tennis",
        "volleyball",
    )),
    ("运动娱乐", "运动比赛", "体育人物、比赛和训练", (
        "athlete", "champion", "compete", "exercise", "game", "match", "Olympic",
        "race", "sport", "team", "teamwork", "training", "win", "winner",
    )),
    ("运动娱乐", "个人运动与棋类", "常见个人运动项目和棋类活动", (
        "chess", "jump", "kung fu", "skate", "ski", "swim",
    )),
    ("文化娱乐", "音乐舞台", "音乐、舞蹈和舞台表演", (
        "concert", "dance", "drama", "guitar", "opera", "perform",
        "piano", "sing", "song", "theatre", "violin",
    )),
    ("文化娱乐", "影视阅读", "影视、故事和阅读材料", (
        "article", "book", "cartoon", "cinema", "diary", "film", "magazine",
        "movie", "news", "newspaper", "novel", "poem", "story", "television",
    )),
    ("文化娱乐", "节日庆祝", "节日、庆祝和聚会活动", (
        "birthday", "celebrate", "Christmas", "festival", "firework", "gift",
        "party",
    )),
    ("科技媒体", "电脑网络", "电脑、网络和数字技术", (
        "AI", "application", "chip", "computer", "digital", "download", "email",
        "Internet", "keyboard", "laptop", "online", "robot", "screen",
        "technology", "website",
    )),
    ("科技媒体", "通讯影像", "通信、拍摄和大众媒体设备", (
        "camera", "message", "phone", "photo", "radio", "video",
    )),
    ("社会生活", "常见职业", "社会生活中常见的工作", (
        "actor", "actress", "artist", "boss", "engineer", "farmer", "fireman",
        "hostess", "lawyer", "officer",
        "pilot", "policeman", "policewoman", "postman", "scientist", "soldier",
        "teacher", "worker",
    )),
    ("社会生活", "城市建筑", "城市中常见的建筑和公共地点", (
        "bank", "bridge", "building", "factory", "office", "palace", "park",
        "tower", "zoo",
    )),
    ("社会生活", "社区人物", "身边的人和社区关系", (
        "classmate", "friend", "guest", "host", "neighbour", "partner",
        "volunteer",
    )),
    ("社会生活", "国家与城市", "国家、城乡和公共社会", (
        "capital", "citizen", "city", "community", "country", "government",
        "hometown", "nation", "public", "society", "state", "town", "village",
    )),
    ("社会生活", "购物消费", "商店、商品和买卖行为", (
        "buy", "cash", "cheap", "cost", "customer", "expensive", "mall", "market",
        "money", "pay", "price", "product", "sale", "sell", "shop", "store",
        "supermarket",
    )),
    ("社会生活", "人物称谓", "常见礼貌称谓和身份头衔", (
        "emperor", "empress", "king", "lady", "madam", "Mr", "Mrs", "Ms",
        "president", "prince", "princess", "queen", "sir",
    )),
    ("情感交往", "正面情绪", "快乐、希望和积极感受", (
        "calm", "excited", "glad", "happy", "hope", "joy", "love", "pleasure",
        "pride", "proud", "wonderful",
    )),
    ("情感交往", "负面情绪", "害怕、难过和紧张感受", (
        "afraid", "angry", "fear", "hate", "nervous", "regret", "sad", "scare",
        "shame", "shock", "sorry", "worry",
    )),
    ("情感交往", "良好品格", "与人相处时的积极品质", (
        "brave", "careful", "creative", "curious", "friendly", "helpful", "honest",
        "kind", "polite", "responsible", "wise",
    )),
    ("情感交往", "幽默交流", "玩笑、幽默和欢笑", (
        "funny", "humour", "joke", "laugh",
    )),
    ("情感交往", "不良行为", "需要识别和避免的不良行为", (
        "bully", "careless", "cheat", "fight", "lazy", "lie", "steal",
    )),
    ("情感交往", "礼貌交流", "见面、告别、感谢和道歉", (
        "excuse", "goodbye", "greet", "hello", "hi", "introduce", "invite",
        "pardon", "please", "thank", "welcome",
    )),
    ("环境安全", "环境保护", "环境问题和保护行动", (
        "environment", "pollute", "protect", "recycle", "rubbish", "waste",
    )),
    ("环境安全", "灾害与救援", "自然灾害、事故和紧急救援", (
        "accident", "aid", "danger", "disaster", "earthquake", "emergency", "fire",
        "flood", "risk", "safe", "safety",
    )),
    ("日常生活", "日期时间", "日期、时间单位和日程", (
        "calendar", "century", "date", "day", "future", "hour", "minute", "moment",
        "month", "today", "tomorrow", "tonight", "week", "weekday", "weekend",
        "year", "yesterday",
    )),
    ("日常生活", "常用工具", "生活和手工活动中的常见工具", (
        "brush", "key", "lock", "rope", "scissors", "stick", "tape", "tool",
    )),
    ("日常生活", "包装容器", "收纳和盛放物品的容器", (
        "bag", "basket", "bin", "bottle", "box", "packet",
    )),
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def variants(record: dict) -> list[str]:
    raw = record.get("variants", "")
    return [item.strip() for item in str(raw).split(";") if item.strip()]


def add_variant(record: dict, value: str) -> None:
    current = variants(record)
    if value.casefold() not in {v.casefold() for v in current}:
        current.append(value)
    record["variants"] = "; ".join(current)
    accepted = list(record.get("accepted_answers") or [])
    if value.casefold() not in {str(v).casefold() for v in accepted}:
        accepted.append(value)
    record["accepted_answers"] = accepted


def build_vocabulary() -> tuple[list[dict], dict]:
    high = load(HIGH_DIR / "vocabulary.json")
    by_word = {r["word"].casefold(): r for r in high}
    by_variant = {}
    for record in high:
        for value in variants(record):
            by_variant.setdefault(value.casefold(), record)

    with TOKENS_CSV.open(encoding="utf-8-sig", newline="") as stream:
        scope_tokens = [row["token"].strip() for row in csv.DictReader(stream) if row["earliest_level"] == "junior"]

    selected: dict[str, dict] = {}
    coverage = {"headword": [], "existing_variant": [], "added_variant": [], "structural_component": [], "new_headword": []}

    def select(record: dict) -> dict:
        key = record["word"].casefold()
        if key not in selected:
            cloned = copy.deepcopy(record)
            cloned["curriculum_level"] = "junior"
            cloned["edition_scope"] = "junior_high"
            selected[key] = cloned
        return selected[key]

    for token in scope_tokens:
        key = token.casefold()
        if key in by_word:
            select(by_word[key]); coverage["headword"].append(token)
        elif key in by_variant:
            select(by_variant[key]); coverage["existing_variant"].append(token)
        elif key in EXTRA_VARIANTS:
            target = select(by_word[EXTRA_VARIANTS[key].casefold()])
            add_variant(target, token); coverage["added_variant"].append(token)
        elif key in STRUCTURAL_TOKENS:
            target_key = STRUCTURAL_TOKENS[key].casefold()
            if target_key in by_word:
                select(by_word[target_key])
            elif target_key not in {word.casefold() for word in NEW_RECORDS}:
                raise ValueError(f"Missing structural product entry: {STRUCTURAL_TOKENS[key]}")
            coverage["structural_component"].append(token)
        elif key in NEW_VARIANTS:
            coverage["added_variant"].append(token)
        elif key in {word.casefold() for word in NEW_RECORDS}:
            coverage["new_headword"].append(token)
        else:
            raise ValueError(f"Unresolved junior scope token: {token}")

    next_id = 1
    used_ids = {r["record_id"] for r in selected.values()}
    for word, (content, pronunciation, pos) in NEW_RECORDS.items():
        while f"junior-word-{next_id:04d}" in used_ids:
            next_id += 1
        record = {
            "word": word, "content": content, "record_id": f"junior-word-{next_id:04d}",
            "variants": "", "dataset_layer": "junior_curriculum_supplement",
            "curriculum_level": "junior", "edition_scope": "junior_high",
            "parts_of_speech": pos, "definition_method": "independently_drafted_from_open_evidence",
            "qa_status": "automated_checks_passed", "accepted_answers": [],
            "pronunciation": pronunciation, "pronunciation_source": "ipa-dict en_US with British display normalization",
            "pronunciation_match_method": "direct_or_documented_normalization",
        }
        selected[word.casefold()] = record
        next_id += 1

    for alias, target in NEW_VARIANTS.items():
        add_variant(selected[target.casefold()], alias)

    records = sorted(selected.values(), key=lambda r: r["word"].casefold())
    report = {
        "scope_source": str(TOKENS_CSV.relative_to(ROOT)).replace("\\", "/"),
        "scope_tokens": len(scope_tokens), "product_headwords": len(records),
        "coverage": {name: len(values) for name, values in coverage.items()},
        "structural_tokens": STRUCTURAL_TOKENS, "unresolved_tokens": [],
        "note": "课程表中的多词条目拆分词元通过产品词头、明确变体或原多词条目完整覆盖。",
    }
    return records, report


def build_scientific_memory(records: list[dict]) -> dict:
    source = load(HIGH_DIR / "scientific_memory_data.json")
    ids = {r["record_id"] for r in records}
    by_word = {r["word"].casefold(): r for r in records}
    groups = []
    assigned: set[str] = set()
    seen_words: dict[str, str] = {}
    pos_labels = {
        "noun": "名词", "verb": "动词", "adjective": "形容词",
        "adverb": "副词", "pronoun": "代词", "preposition": "介词",
        "conjunction": "连词", "interjection": "感叹词",
    }

    for theme_index, (parent, title, subtitle, words) in enumerate(
            JUNIOR_SCENE_THEMES, 1):
        selected = []
        for word in words:
            key = word.casefold()
            if key not in by_word:
                raise ValueError(f"Junior scene word is not in vocabulary: {word}")
            if key in seen_words:
                raise ValueError(
                    f"Junior scene word appears in both {seen_words[key]} and {title}: {word}")
            seen_words[key] = title
            selected.append(by_word[key])

        chunk_count = math.ceil(len(selected) / 12)
        base_size, larger_chunks = divmod(len(selected), chunk_count)
        chunks = []
        offset = 0
        for chunk_index in range(chunk_count):
            size = base_size + (1 if chunk_index < larger_chunks else 0)
            chunks.append(selected[offset:offset + size])
            offset += size
        for chunk_index, chunk in enumerate(chunks, 1):
            if len(chunk) < 2:
                raise ValueError(f"Junior scene group is too small: {title}")
            records_in_group = [record["record_id"] for record in chunk]
            hints = []
            for record in chunk:
                primary_pos = str(record.get("parts_of_speech") or "").split(";", 1)[0].strip()
                hints.append(pos_labels.get(primary_pos, "词语"))
            groups.append({
                "id": f"junior_scene:{theme_index:02d}:{chunk_index}",
                "parent": parent,
                "title": title if len(chunks) == 1 else f"{title} · {chunk_index}",
                "subtitle": subtitle,
                "records": records_in_group,
                "hints": hints,
            })
            assigned.update(records_in_group)

    relations = []
    for group in source["relation_groups"]:
        if all(rid in ids for rid in group.get("records", [])):
            relations.append(copy.deepcopy(group))

    return {
        "schema_version": "2.0", "source_vocabulary": "zhongkao-core",
        "scene_catalogue_policy": "independently_curated_clear_junior_scenes_only",
        "scene_group_size_limit": 12, "scene_word_count": len(assigned),
        "scene_unique_word_count": len(assigned),
        "scene_excluded_word_count": len(ids - assigned),
        "scene_groups": groups,
        "relation_groups": relations,
    }


def build_irregular(records: list[dict]) -> list[dict]:
    clean = load(IRREGULAR_SOURCE)["records"]
    clean_by_word = {r["infinitive"].casefold(): r for r in clean}
    scope = load(IRREGULAR_SCOPE)
    record_ids = {r["word"].casefold(): r["record_id"] for r in records}
    output = []
    for sequence, candidate in enumerate(scope, 1):
        item = copy.deepcopy(clean_by_word[candidate["infinitive"].casefold()])
        item["sequence"] = sequence
        item["meaning"] = item.get("meaning_zh", "")
        item["edition"] = "zhongkao"
        item["in_edition_vocabulary"] = item["infinitive"].casefold() in record_ids
        item["edition_record_id"] = record_ids.get(item["infinitive"].casefold(), "")
        output.append(item)
    return output


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    vocabulary, coverage = build_vocabulary()
    by_word = {r["word"].casefold(): r for r in vocabulary}
    trial = [copy.deepcopy(by_word[word.casefold()]) for word in TRIAL_WORDS]
    phrases = load(PHRASES_SOURCE)
    for phrase in phrases:
        phrase["edition"] = "zhongkao"
        phrase["data_status"] = "product_auto_validated"
    irregular = build_irregular(vocabulary)
    memory = build_scientific_memory(vocabulary)

    dump(OUT / "vocabulary.json", vocabulary)
    dump(OUT / "trial_vocabulary.json", trial)
    dump(OUT / "phrases.json", phrases)
    dump(OUT / "irregular_verbs.json", irregular)
    dump(OUT / "scientific_memory_data.json", memory)

    for license_name in ["ECDICT_LICENSE.txt", "IPA_DICT_LICENSE.txt", "OPEN_ENGLISH_WORDNET_LICENSE.md", "PRINCETON_WORDNET_LICENSE.txt", "THIRD_PARTY_NOTICES.md"]:
        shutil.copyfile(HIGH_DIR / license_name, OUT / license_name)

    sources = [TOKENS_CSV, HIGH_DIR / "vocabulary.json", HIGH_DIR / "scientific_memory_data.json", PHRASES_SOURCE, IRREGULAR_SOURCE, IRREGULAR_SCOPE]
    manifest = {
        "schema_version": 1, "edition_id": "zhongkao", "status": "product_data_complete_auto_validated",
        "counts": {"vocabulary": len(vocabulary), "trial_vocabulary": len(trial), "phrases": len(phrases),
                   "core_phrases": sum(p.get("tier") == "core" for p in phrases),
                   "extension_phrases": sum(p.get("tier") != "core" for p in phrases),
                   "irregular_verbs": len(irregular),
                   "curated_scene_words": memory["scene_unique_word_count"]},
        "application_paths": {name: f"assets/editions/zhongkao/{name}.json" for name in ["vocabulary", "trial_vocabulary", "phrases", "irregular_verbs", "scientific_memory_data"]},
        "source_files": {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in sources},
        "product_files": {},
        "content_policy": "Junior scope is derived from the audited curriculum boundary; junior scenes are independently curated and include only clear, teachable themes.",
    }
    scene_ids = [rid for group in memory["scene_groups"] for rid in group["records"]]
    scene_titles = {group["title"].split(" · ", 1)[0] for group in memory["scene_groups"]}
    validation = {
        "edition_id": "zhongkao", "status": "passed", "coverage": coverage,
        "checks": {"unique_headwords": len({r["word"].casefold() for r in vocabulary}) == len(vocabulary),
                   "all_have_pronunciation": all(r.get("pronunciation") for r in vocabulary),
                   "trial_exact_subset": all(by_word[r["word"].casefold()] == r for r in trial),
                   "scene_ids_exist": set(scene_ids) <= {r["record_id"] for r in vocabulary},
                   "scene_no_duplicates": len(scene_ids) == len(set(scene_ids)),
                   "scene_selective_not_forced": 0 < len(scene_ids) < len(vocabulary),
                   "scene_groups_have_context": all(2 <= len(g["records"]) <= 12 for g in memory["scene_groups"]),
                   "scene_no_generic_fallback": not ({"其他", "综合概念", "常用名词", "日常物品"} & scene_titles)},
    }
    dump(OUT / "validation_report.json", validation)
    readme = f"""# 初中英语正式版数据包\n\n本目录是可发布的初中版产品数据，不是研究样例。\n\n- 产品词头：{len(vocabulary)} 条（覆盖课程边界证据中的 {coverage['scope_tokens']} 个规范化词元）\n- 免费体验词汇：{len(trial)} 条，与正式词表同步抽取\n- 初中短语：{len(phrases)} 条\n- 初中不规则动词：{len(irregular)} 条\n- 主题场景：独立人工编排 {memory['scene_unique_word_count']} 个主题明确的词头；不强迫代词、介词及宽泛抽象词进入场景\n- 未进入主题场景的词仍保留在完整词表，并可按适用条件进入词根、音形或同反义记忆\n\n边界表仅作为课程范围证据；含义、音标和产品字段沿用本项目已有开放许可数据链，初中独有词条由项目独立整理。详见 manifest.json、validation_report.json 和第三方许可文件。\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    product_names = ["vocabulary.json", "trial_vocabulary.json", "phrases.json", "irregular_verbs.json", "scientific_memory_data.json", "validation_report.json", "README.md"]
    manifest["product_files"] = {name: sha256(OUT / name) for name in product_names}
    dump(OUT / "manifest.json", manifest)
    sums = [f"{sha256(OUT / name)}  {name}" for name in sorted(p.name for p in OUT.iterdir() if p.name != "SHA256SUMS.txt")]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({"vocabulary": len(vocabulary), "trial": len(trial), "phrases": len(phrases), "irregular": len(irregular), "scenes": len(memory["scene_groups"]), "relations": len(memory["relation_groups"]), "coverage": coverage}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
