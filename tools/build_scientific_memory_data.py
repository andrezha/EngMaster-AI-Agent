"""Build compact scientific-memory metadata for the fixed Gaokao 3800 list."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
VOCAB_PATH = ROOT / "assets/editions/gaokao/vocabulary.json"
SEMANTIC_PATH = ROOT / "data_sources/enrichment/oewn_semantic_base/oewn_semantic_base.json"
OUTPUT_PATH = ROOT / "assets/editions/gaokao/scientific_memory_data.json"
GROUP_SIZE = 12
OTHER_THEME = ("other", "其他", "暂不适合单独成类的词汇")


# Strict, manually reviewed pairs based on the visible common meanings in this
# edition.  Automatic thesaurus expansion is intentionally forbidden here.
STRICT_SYNONYM_PAIRS = (
    ("achieve", "attain"), ("almost", "nearly"), ("answer", "reply"),
    ("baggage", "luggage"), ("begin", "start"), ("big", "large"),
    ("choose", "select"), ("close", "shut"), ("error", "mistake"),
    ("help", "assist"), ("ill", "sick"), ("maybe", "perhaps"),
    ("purchase", "buy"), ("quick", "rapid"), ("repair", "mend"),
)

STRICT_ANTONYM_PAIRS = (
    ("alive", "dead"), ("ancient", "modern"), ("big", "small"),
    ("black", "white"), ("cheap", "expensive"), ("clean", "dirty"),
    ("close", "open"), ("cold", "hot"), ("correct", "wrong"),
    ("deep", "shallow"), ("early", "late"), ("empty", "full"),
    ("enter", "exit"), ("fail", "succeed"), ("fast", "slow"),
    ("fat", "thin"), ("few", "many"), ("first", "last"),
    ("forget", "remember"), ("happy", "sad"), ("high", "low"),
    ("inside", "outside"), ("long", "short"), ("love", "hate"),
    ("major", "minor"), ("maximum", "minimum"), ("more", "less"),
    ("near", "far"), ("new", "old"), ("north", "south"),
    ("positive", "negative"), ("private", "public"), ("pull", "push"),
    ("rich", "poor"), ("rise", "fall"), ("safe", "dangerous"),
    ("same", "different"), ("strong", "weak"), ("true", "false"),
    ("up", "down"), ("useful", "useless"), ("wet", "dry"),
    ("young", "old"), ("possible", "impossible"), ("legal", "illegal"),
    ("success", "failure"), ("war", "peace"),
    ("day", "night"),
)


CLASS_THEMES = {
    "noun.animal": ("animals", "动物世界", "动物种类、特征与活动"),
    "noun.body": ("body", "身体部位", "身体部位、器官与生理"),
    "noun.cognition": ("thinking", "思维认知", "知识、思想、判断与学习"),
    "noun.communication": ("communication", "语言交流", "语言、文字、信息与交流"),
    "noun.event": ("events", "事件活动", "事件、活动与发生过程"),
    "noun.feeling": ("feelings", "情绪感受", "情绪、感受与心理体验"),
    "noun.food": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "noun.group": ("groups", "群体组织", "团体、组织与社会群体"),
    "noun.location": ("places", "地点空间", "地点、区域与空间位置"),
    "noun.motive": ("motives", "目的动机", "目标、原因与行为动机"),
    "noun.object": ("objects", "日常物品", "常见物品与实体对象"),
    "noun.person": ("people", "人物身份", "人物、身份与社会角色"),
    "noun.phenomenon": ("phenomena", "自然现象", "自然现象与客观变化"),
    "noun.plant": ("plants", "植物世界", "植物、农作物与生长"),
    "noun.possession": ("possession", "财物所有", "财产、所有与资源"),
    "noun.process": ("processes", "发展过程", "过程、变化与发展"),
    "noun.quantity": ("quantity", "数量计量", "数字、数量、单位与计量"),
    "noun.relation": ("relations", "关系联系", "关系、联系与相互作用"),
    "noun.shape": ("shape", "形状结构", "形状、结构与外观"),
    "noun.state": ("states", "状态处境", "状态、条件与处境"),
    "noun.substance": ("materials", "材料物质", "材料、物质与组成"),
    "noun.time": ("time", "时间日期", "时间、日期、阶段与顺序"),
    "noun.artifact": ("artifacts", "工具器物", "人造物、工具与设备"),
    "noun.attribute": ("attributes", "性质特征", "性质、特征与程度"),
    "noun.act": ("actions", "行为活动", "行为、活动与实际行动"),
    "verb.body": ("body_actions", "身体动作", "身体动作与生理活动"),
    "verb.change": ("change", "变化发展", "改变、形成与发展"),
    "verb.cognition": ("mental_actions", "思考学习", "思考、理解、记忆与学习"),
    "verb.communication": ("communication_actions", "表达交流", "说、写、表达与传递"),
    "verb.competition": ("competition", "竞赛对抗", "比赛、竞争与胜负"),
    "verb.consumption": ("consumption", "饮食消费", "饮食、使用与消耗"),
    "verb.contact": ("contact_actions", "接触操作", "接触、操作与物体动作"),
    "verb.creation": ("creation", "制作创造", "制作、建设与创造"),
    "verb.emotion": ("emotion_actions", "情感态度", "喜欢、担心、希望与感受"),
    "verb.motion": ("motion", "移动出行", "移动、到达与方向变化"),
    "verb.perception": ("perception", "感官观察", "看、听、感知与发现"),
    "verb.possession": ("possession_actions", "获得使用", "拥有、获得、给予与使用"),
    "verb.social": ("social_actions", "社会行为", "合作、管理、帮助与社会活动"),
    "verb.stative": ("stative", "存在状态", "存在、保持与状态关系"),
    "verb.weather": ("weather_actions", "天气变化", "天气现象及其变化"),
    "adj.all": ("descriptions", "性质描述", "性质、状态与评价描述"),
    "adj.pert": ("related_descriptions", "类别属性", "表示所属类别与相关属性"),
    "adj.ppl": ("result_descriptions", "动作状态", "由动作形成的状态描述"),
    "adv.all": ("adverbs", "方式程度", "方式、程度、时间与频率"),
}


SPECIAL_THEMES = (
    ("transport", "交通出行", "交通工具、道路与出行", {
        "airport", "aircraft", "airplane", "bicycle", "bike", "bus", "car", "coach",
        "driver", "flight", "highway", "journey", "motorcycle", "passenger", "railway",
        "road", "route", "ship", "station", "taxi", "traffic", "train", "transport",
        "travel", "vehicle", "voyage",
    }),
    ("occupations", "职业工作", "职业、岗位与工作身份", {
        "actor", "artist", "author", "boss", "career", "clerk", "cook", "dentist",
        "doctor", "driver", "editor", "engineer", "farmer", "journalist", "judge",
        "lawyer", "manager", "nurse", "officer", "pilot", "police", "profession",
        "reporter", "scientist", "secretary", "soldier", "teacher", "worker", "writer",
    }),
    ("science", "科学研究", "科学、实验与研究方法", {
        "atom", "biology", "chemical", "chemistry", "experiment", "laboratory", "method",
        "physics", "research", "science", "scientific", "scientist", "theory",
    }),
    ("technology", "信息科技", "计算机、网络与现代技术", {
        "computer", "digital", "electronic", "email", "internet", "keyboard", "network",
        "online", "program", "robot", "screen", "software", "technology", "website",
    }),
    ("school", "学校教育", "学校、课程、考试与学习", {
        "blackboard", "campus", "class", "classroom", "college", "course", "education",
        "exam", "homework", "lesson", "school", "student", "study", "teacher", "textbook",
        "university",
    }),
    ("medicine", "医疗健康", "疾病、治疗与健康管理", {
        "cancer", "clinic", "disease", "doctor", "health", "healthy", "hospital",
        "medicine", "nurse", "operation", "pain", "patient", "recover", "treatment",
    }),
    ("family", "家庭成员", "家庭关系与亲属称谓", {
        "aunt", "brother", "child", "cousin", "daughter", "family", "father", "grandfather",
        "grandmother", "husband", "mother", "parent", "relative", "sister", "son", "uncle",
        "wife",
    }),
    ("sports", "体育运动", "运动项目、训练与比赛", {
        "athlete", "basketball", "coach", "exercise", "football", "game", "match", "player",
        "race", "sport", "swim", "team", "tennis", "training",
    }),
    ("clothing", "衣服穿戴", "衣物、鞋帽与穿戴", {
        "boot", "cap", "clothes", "clothing", "coat", "dress", "glove", "hat", "jacket",
        "shirt", "shoe", "skirt", "sock", "suit", "sweater", "trousers", "wear",
    }),
    ("shopping", "购物商业", "商品、价格、买卖与市场", {
        "buy", "cash", "cost", "customer", "goods", "market", "pay", "price", "product",
        "sell", "shop", "shopping", "store",
    }),
    ("weather", "天气气候", "天气、气候与气象现象", {
        "climate", "cloud", "cloudy", "forecast", "rain", "rainy", "snow", "storm", "sunny",
        "temperature", "weather", "wind", "windy",
    }),
    ("home", "居家生活", "房屋、房间与家庭用品", {
        "bathroom", "bedroom", "door", "furniture", "home", "house", "kitchen", "room",
        "sofa", "table", "window",
    }),
    ("arts", "文化艺术", "音乐、美术、戏剧与文化", {
        "art", "artist", "culture", "dance", "film", "music", "painting", "poem", "song",
        "theatre",
    }),
    ("government", "国家社会", "国家、政府、法律与公共事务", {
        "citizen", "country", "government", "law", "legal", "nation", "national", "policy",
        "president", "public", "society", "state",
    }),
    ("business", "经济商业", "经济、企业、金融与贸易", {
        "bank", "business", "company", "economic", "economy", "finance", "industry", "money",
        "trade",
    }),
    ("environment", "环境保护", "环境、污染、资源与保护", {
        "environment", "environmental", "pollution", "protect", "recycle", "resource", "waste",
    }),
)


POS_THEMES = (
    (("article",), ("articles", "冠词限定", "冠词及名词限定作用")),
    (("pronoun", "determiner"), ("pronouns", "代词指代", "人称、指示与数量指代")),
    (("numeral", "ordinal"), ("numbers", "数字量词", "基数、序数、数量与次序")),
    (("preposition",), ("prepositions", "方位介词", "时间、空间与关系介词")),
    (("conjunction",), ("conjunctions", "逻辑连接", "并列、转折、因果与条件")),
    (("modal_verb", "auxiliary", "auxiliary_verb"), ("modals", "情态助动", "能力、可能、意愿与语气")),
    (("interjection",), ("interjections", "感叹回应", "感叹、招呼与简短回应")),
    (("title",), ("titles", "称谓头衔", "人物称谓与正式头衔")),
)


ADJECTIVE_CONTENT_THEMES = (
    ("appearance", "外貌颜色", "外貌、颜色与视觉特征", ("颜色", "美丽", "漂亮", "英俊", "丑", "明亮", "黑色", "白色", "红色", "绿色", "蓝色", "黄色")),
    ("size", "大小形状", "大小、长短、高低与形状", ("大的", "小的", "长的", "短的", "高的", "低的", "宽", "窄", "厚", "薄", "圆", "形状")),
    ("emotion_descriptions", "情绪状态", "高兴、悲伤、紧张与心理状态", ("高兴", "快乐", "悲伤", "愤怒", "害怕", "焦虑", "紧张", "兴奋", "满意", "失望", "孤独")),
    ("quality", "质量评价", "好坏、价值与总体评价", ("优秀", "完美", "重要", "有用", "有价值", "合适", "正确", "错误", "糟糕", "普通", "特殊")),
    ("ability", "能力难度", "能力、可能性与难易程度", ("能够", "有能力", "困难", "容易", "聪明", "熟练", "可能的", "不可能")),
    ("age_time", "年龄新旧", "年龄、年代与新旧状态", ("年轻", "年老", "古老", "现代", "新的", "旧的", "最近", "早的", "晚的")),
    ("speed", "速度频率", "快慢、频率与持续程度", ("快速", "缓慢", "频繁", "通常", "突然", "立即")),
    ("health_state", "健康体感", "健康、疲劳、饥饿与身体状态", ("健康", "生病", "疲劳", "疲倦", "饥饿", "口渴", "疼痛")),
    ("safety", "安全危险", "安全、危险、伤害与保护", ("安全", "危险", "有害", "无害", "致命")),
    ("personality", "性格品德", "性格、品德与待人态度", ("诚实", "友好", "礼貌", "勇敢", "耐心", "懒惰", "善良", "自私", "慷慨")),
    ("certainty", "真假确定", "真实、明显、确定与可能性", ("真实", "虚假", "明显", "确定", "清楚", "准确", "肯定")),
    ("degree_quantity", "数量程度", "多少、完整程度与范围", ("许多", "少量", "全部", "足够", "额外", "主要", "完全", "部分")),
)


ARTIFACT_CONTENT_THEMES = (
    ("buildings", "建筑场所", "建筑、房屋与公共场所", ("建筑", "房屋", "房间", "大厅", "场馆", "剧院", "寺庙", "塔", "桥")),
    ("machines", "机器设备", "机器、设备、装置与仪器", ("机器", "设备", "装置", "仪器", "发动机", "电器")),
    ("tools", "工具用品", "工具、器具与操作用品", ("工具", "器具", "刀", "锤", "剪刀", "钥匙")),
    ("containers", "容器包装", "容器、包装与收纳用品", ("容器", "瓶", "杯", "盒", "箱", "袋", "篮")),
    ("documents", "书刊文件", "书籍、报刊、文件与票证", ("书籍", "报纸", "杂志", "文件", "证件", "票据", "卡片", "地图")),
    ("furniture", "家具陈设", "家具与室内陈设", ("家具", "桌子", "椅子", "床", "沙发", "柜")),
    ("weapons", "军事装备", "武器、防御与军事装备", ("武器", "枪", "炮", "炸弹", "导弹")),
    ("media_devices", "媒体设备", "摄影、声音与媒体设备", ("相机", "照相机", "电视", "收音机", "电话", "麦克风")),
)


ACTION_CONTENT_THEMES = (
    ("work_actions", "工作任务", "工作、任务与职业活动", ("工作", "任务", "职责", "职业")),
    ("learning_actions", "学习活动", "学习、教学、考试与训练", ("学习", "教学", "教育", "考试", "训练")),
    ("meeting_actions", "会议交流", "会议、讨论与交流活动", ("会议", "讨论", "交流", "谈话", "演讲")),
    ("travel_actions", "旅行活动", "旅行、参观与出行活动", ("旅行", "旅游", "参观", "航行")),
    ("management_actions", "管理组织", "管理、组织与行政活动", ("管理", "组织", "控制", "领导")),
    ("service_actions", "服务帮助", "服务、帮助与社会支持", ("服务", "帮助", "援助", "照顾")),
    ("law_actions", "法律治安", "法律、犯罪、调查与处罚", ("犯罪", "法律", "调查", "惩罚", "逮捕")),
    ("celebration_actions", "节日庆祝", "庆祝、仪式与纪念活动", ("庆祝", "仪式", "典礼", "节日")),
    ("production_actions", "生产建设", "生产、制造与建设活动", ("生产", "制造", "建设", "创造")),
)


PRECISE_SCENE_GROUPS = (
    ("subjects", "学科课程", "学校中的明确学科与课程名称", {
        "art", "arithmetic", "astronomy", "biology", "chemistry", "chinese", "english",
        "geography", "geometry", "grammar", "history", "language", "literature", "maths",
        "music", "pe", "philosophy", "physics", "politics", "psychology", "science", "statistics",
    }),
    ("religious_places", "宗教场所", "教堂等宗教活动场所", {
        "cathedral", "church",
    }),
    ("dining_places", "餐饮场所", "用餐、餐饮服务与食品销售场所", {
        "bakery", "cafeteria", "canteen", "pub", "restaurant",
    }),
    ("residential_buildings", "住宅建筑", "住宅、房间及其建筑组成", {
        "apartment", "balcony", "basement", "bungalow", "cellar", "chimney",
        "cottage", "courtyard", "fireplace", "garage", "housing", "washroom",
    }),
    ("public_buildings", "公共建筑", "工作、住宿、展览和公共活动场所", {
        "factory", "gym", "hall", "hotel", "inn", "museum", "stadium", "studio",
        "supermarket", "warehouse", "workplace", "zoo",
    }),
    ("clothing_precise", "衣服穿戴", "衣物、鞋帽及服装组成", {
        "blouse", "cloth", "costume", "garment", "jeans", "scarf", "shorts",
        "sleeve", "t-shirt", "underwear", "uniform", "vest",
    }),
    ("personal_accessories", "随身配饰", "随身携带、佩戴与旅行收纳用品", {
        "handbag", "handkerchief", "helmet", "luggage", "necklace", "wallet",
    }),
    ("home_furnishings", "家具家居", "家具、照明、寝具与家居用品", {
        "armchair", "clock", "cushion", "lamp", "lantern", "pillow", "stove",
        "teapot", "towel",
    }),
    ("transport_precise", "交通工具", "车辆、船舶及公共交通工具", {
        "airline", "ambulance", "balloon", "boat", "cab", "helicopter", "jeep",
        "subway", "tractor", "truck",
    }),
    ("sports_equipment", "运动器材", "运动、滑行与水上活动器材", {
        "paddle", "skateboard", "ski",
    }),
    ("medical_supplies", "医疗用品", "治疗、包扎与药物用品", {
        "bandage", "cure", "drug",
    }),
    ("observation_equipment", "实验观测器材", "实验、观察与测量器材", {
        "microscope", "telescope",
    }),
    ("office_devices", "办公通信设备", "办公、计算与信息传递设备", {
        "fax", "laptop", "typewriter",
    }),
    ("spoken_communication", "口语交流", "对话、讨论、问答与礼貌表达", {
        "advice", "congratulation", "conversation", "debate", "dialogue", "discussion",
        "greeting", "interview", "praise", "refusal", "reply", "request", "salute",
    }),
    ("written_information", "写作文本", "通知、说明、信息与实用文本", {
        "advertisement", "announcement", "blog", "brochure", "caption", "catalogue",
        "comment", "directory", "headline", "message", "motto", "paragraph", "postcard",
        "proposal", "questionnaire", "recipe", "statement", "summary", "text", "timetable",
        "warning",
    }),
    ("literary_reading", "文学阅读", "文学体裁、故事与韵文", {
        "anecdote", "biography", "fiction", "poetry", "rhyme", "saying", "tale", "thriller",
    }),
    ("language_skills", "语言技能", "书写、发音、拼写与词典使用", {
        "calligraphy", "dictionary", "pronunciation", "spelling", "underline",
    }),
    ("media_communication", "媒体传播", "广播、影视与大众传播内容", {
        "advertise", "broadcast", "cartoon", "comedy", "movie", "preview",
    }),
    ("school_materials", "学习用品", "课堂、书写与学习所用物品", {
        "blackboard", "desk", "schoolbag", "textbook",
    }),
    ("school_assessment", "课程考试", "课程设置、考试与学习证明", {
        "curriculum", "diploma", "exam", "quiz",
    }),
    ("documents_credentials", "证件文书", "证件、许可与法律文书", {
        "patent", "visa",
    }),
    ("speaking_voice", "说话与声音", "说话、争论及不同音量的表达", {
        "argue", "complain", "discuss", "pronounce", "shout", "talk", "whisper", "yell",
    }),
    ("inform_explain", "告知与说明", "宣布、解释、提及与引用", {
        "announce", "explain", "indicate", "mention", "quote",
    }),
    ("advice_instruction", "劝告与指令", "建议、说服、指导与提醒", {
        "advise", "consult", "convince", "instruct", "urge", "warn",
    }),
    ("polite_response", "礼貌与回应", "道歉、感谢与鼓掌回应", {
        "apologise", "applaud", "thank",
    }),
    ("legal_expression", "法律与规则", "指控、禁止与规则表达", {
        "accuse", "prohibit",
    }),
    ("belief", "精神与信仰", "精神、信仰与宗教概念", {
        "pray",
    }),
    ("research_actions", "调查研究", "调查、研究与查明", {
        "explore", "investigate",
    }),
    ("thinking_understanding", "思考与理解", "相信、理解、误解与记忆", {
        "believe", "forget", "misunderstand", "understand",
    }),
    ("analysis_judgment", "分析与判断", "分析、评价与作出决定", {
        "analyse", "decide", "evaluate",
    }),
    ("emotion_influence", "情绪影响", "使人惊讶或震惊", {
        "amaze", "astonish",
    }),
    ("ideas_concepts", "思想与观念", "思想、观念、传统与偏见", {
        "belief", "concept", "confucianism", "knowledge", "prejudice", "thought", "tradition",
    }),
    ("methods_strategies", "方法与策略", "完成任务所用的方法、技能与策略", {
        "skill", "strategy", "technique",
    }),
    ("choices_dilemmas", "选择与困境", "备选方案与两难处境", {
        "alternative", "dilemma",
    }),
    ("work_routines", "工作事务", "任务和日常文书工作", {
        "paperwork", "task",
    }),
    ("size_scale", "尺寸大小", "物体或范围的大小", {
        "big", "enormous", "huge", "large", "massive", "small", "tiny", "vast",
    }),
    ("length_width", "长短宽窄", "长度和宽度", {
        "broad", "long", "narrow", "short", "wide",
    }),
    ("height_position", "高低位置", "高度及上下位置", {
        "high", "low", "lower", "tall", "upper",
    }),
    ("thickness", "厚薄粗细", "厚度、薄度与粗细", {
        "thick", "thin",
    }),
    ("shape", "形状外观", "明确的几何形状与外形", {
        "oval", "round", "square",
    }),
    ("age_stage", "年龄阶段", "年轻、年长及年龄层次", {
        "elder", "elderly", "junior", "senior", "young",
    }),
    ("new_old", "新旧状态", "事物的新旧程度", {
        "fresh", "new", "old",
    }),
    ("time_order", "时间早晚", "时间的早晚与先后", {
        "early", "last", "late", "recent",
    }),
    ("sports", "体育运动", "运动项目、训练与比赛", {
        "badminton", "bowling", "boxing", "chess", "compete", "gymnastics",
    }),
    ("dishonesty_precise", "欺骗行为", "欺骗、说谎与作弊行为", {
        "cheat", "deceive", "lie",
    }),
)

ADJECTIVE_SCENE_GROUPS = (
    ("colors", "颜色明暗", "颜色及明暗视觉特征", {
        "black", "blue", "bright", "brown", "dark", "golden", "grey", "pale",
        "pink", "purple", "red", "white", "yellow",
    }),
    ("positive_emotions", "积极情绪", "高兴、满意、感激与希望", {
        "cheerful", "delighted", "eager", "excited", "glad", "grateful", "happy",
        "hopeful", "merry", "optimistic", "pleased", "proud", "thankful",
    }),
    ("negative_emotions", "消极情绪", "害怕、焦虑、悲伤与失望", {
        "afraid", "angry", "anxious", "ashamed", "bored", "confused", "desperate",
        "disappointed", "embarrassed", "frightened", "hopeless", "lonely", "pessimistic",
        "puzzled", "sad", "sorry", "tense", "unhappy", "worried",
    }),
    ("positive_character", "积极品格", "勇敢、诚实、友善与负责", {
        "brave", "careful", "cautious", "confident", "creative", "curious", "fair",
        "frank", "friendly", "generous", "gentle", "honest", "humble", "kind",
        "noble", "polite", "responsible", "wise",
    }),
    ("negative_character", "消极品格", "粗鲁、自私、懒惰与残忍", {
        "aggressive", "careless", "corrupt", "cruel", "foolish", "greedy", "lazy",
        "rude", "selfish", "stubborn", "stupid", "vain",
    }),
    ("body_health", "身体健康状态", "生命、健康、疾病与身体感受", {
        "alive", "asleep", "awake", "blind", "breathless", "dead", "deaf", "disabled",
        "dizzy", "drunk", "fit", "hungry", "ill", "lame", "painful", "pregnant",
        "sick", "sleepy", "thirsty", "tired", "unconscious", "unhealthy", "wounded",
    }),
    ("appearance", "外貌美丑", "外貌、仪态与美丑评价", {
        "attractive", "beautiful", "cute", "elegant", "handsome", "lovely", "pretty", "ugly",
    }),
    ("cleanliness", "清洁整齐", "干净、肮脏及整齐程度", {
        "clean", "dirty", "dusty", "messy", "muddy", "neat", "stainless", "tidy",
    }),
    ("taste_food_state", "味道与食物状态", "味道及食物加工、成熟状态", {
        "bitter", "delicious", "fried", "raw", "ripe", "salty", "sour", "sweet", "tasty",
    }),
    ("temperature_weather", "温度与干湿", "冷热、干湿及天气体感", {
        "cold", "cool", "damp", "dry", "foggy", "hot", "mild", "snowy", "warm", "wet",
    }),
    ("ability_difficulty", "能力与难度", "能力、智力、熟练度与难易", {
        "able", "capable", "challenging", "clever", "difficult", "easy", "fluent",
        "gifted", "intelligent", "practical", "skilled", "smart", "unable",
    }),
    ("truth_accuracy", "真假与准确", "真实、正确、确定与准确程度", {
        "accurate", "actual", "apparent", "authentic", "certain", "correct", "evident",
        "exact", "false", "genuine", "incorrect", "obvious", "precise", "real",
        "reliable", "right", "sure", "true", "uncertain", "valid", "wrong",
    }),
    ("quality_evaluation", "质量与评价", "好坏、价值、重要性与总体评价", {
        "admirable", "awful", "bad", "beneficial", "best", "better", "brilliant",
        "crucial", "decent", "excellent", "exceptional", "fantastic", "fine", "good",
        "great", "harmful", "harmless", "horrible", "important", "nice", "outstanding",
        "perfect", "remarkable", "ridiculous", "splendid", "successful", "suitable",
        "superb", "terrible", "troublesome", "useful", "useless", "valuable", "worthless",
        "worthwhile", "worthy", "worse", "worst",
    }),
    ("quantity_scope", "数量与范围", "数量、范围、完整度与限度", {
        "abundant", "adequate", "ample", "complete", "comprehensive", "double", "entire",
        "extra", "extreme", "full", "limited", "maximum", "medium", "minimum", "multiple",
        "overall", "slight", "substantial", "sufficient", "total", "whole", "widespread",
    }),
    ("time_frequency", "时间与频率", "时间阶段、先后、频率与持续性", {
        "annual", "contemporary", "current", "daily", "final", "following", "frequent",
        "historic", "immediate", "initial", "instant", "later", "latter", "monthly",
        "modern", "next", "permanent", "previous", "primary", "prior", "regular",
        "secondary", "subsequent", "sudden", "temporary", "traditional", "usual", "weekly",
    }),
    ("position_direction", "位置与方向", "内外、远近、上下及方位方向", {
        "absent", "apart", "away", "backward", "central", "direct", "distant", "downstairs",
        "downtown", "downward", "eastern", "external", "far", "further", "inland", "inner",
        "internal", "left", "nearby", "northern", "offshore", "outer", "outward", "overhead",
        "overseas", "remote", "sideways", "southern", "surrounding", "underground",
        "upstairs", "upward", "western",
    }),
    ("same_difference", "异同与对应", "相同、不同、相似及对应关系", {
        "alike", "contradictory", "contrary", "different", "distinct", "diverse", "equal",
        "identical", "joint", "parallel", "respective", "separate", "similar", "single", "unique",
    }),
    ("physical_condition", "物体状态与质感", "软硬、完整、表面及物理状态", {
        "bare", "blank", "broken", "concrete", "deep", "delicate", "empty", "firm",
        "flexible", "fragile", "hard", "heavy", "loose", "open", "rigid", "rough", "sharp",
        "shallow", "smooth", "soft", "solid", "stable", "steady", "steep", "straight",
        "tight", "transparent", "wooden",
    }),
    ("speed_strength", "速度与力量", "快慢、强弱、活力与强度", {
        "active", "energetic", "fast", "fierce", "intense", "lively", "powerful", "quick",
        "rapid", "severe", "slow", "strong", "swift", "tough", "weak",
    }),
    ("sound_volume", "声音特征", "声音的响亮、安静与有无", {
        "loud", "noisy", "quiet", "silent",
    }),
    ("possibility_readiness", "可能与准备", "可能性、必要性、可用性与准备状态", {
        "accessible", "appropriate", "available", "convenient", "likely", "necessary",
        "optional", "possible", "potential", "probable", "proper", "ready", "urgent",
        "willing", "unwilling",
    }),
    ("clarity_complexity", "清晰与复杂", "抽象具体、清晰含糊与复杂程度", {
        "abstract", "ambiguous", "basic", "clear", "complex", "complicated", "explicit",
        "fundamental", "logical", "plain", "simple", "straightforward", "theoretical", "vague",
    }),
    ("social_identity", "社会身份与规范", "社会身份、法律规范及公共属性", {
        "catholic", "confidential", "conservative", "controversial", "conventional",
        "compulsory", "foreign", "formal", "illegal", "independent", "innocent",
        "international", "moral", "native", "nationwide", "private", "religious",
        "sacred", "spiritual", "voluntary",
    }),
    ("origin_scope", "来源与覆盖", "自然人造、来源及覆盖范围", {
        "artificial", "automatic", "autonomous", "global", "natural", "organic",
        "original", "universal", "virtual", "worldwide",
    }),
)

ACTION_SCENE_GROUPS = (
    ("sports_activities", "体育项目", "明确的体育与户外运动项目", {
        "golf", "rugby", "sailing", "shooting", "soccer", "swimming",
    }),
    ("crime_justice", "犯罪与处罚", "犯罪、盗窃、谋杀与处罚", {
        "crime", "murder", "punishment", "theft",
    }),
    ("household_activities", "家务生活", "用餐、园艺与日常家务", {
        "dining", "gardening", "housework",
    }),
    ("leisure_travel", "休闲与旅行", "冒险、娱乐、休闲与旅游", {
        "adventure", "entertainment", "recreation", "tourism",
    }),
    ("effort_achievement", "努力与成果", "尝试、努力及取得成果", {
        "achievement", "attempt", "effort",
    }),
    ("social_change", "社会变革", "建立、解放与改革", {
        "founding", "liberation", "reform",
    }),
    ("observation_actions", "观察检查", "查看、扫视与检查", {
        "glance", "inspection",
    }),
    ("colors", "颜色明暗", "颜色及明暗视觉特征", {"colour"}),
    ("ideas_concepts", "思想与观念", "思想、观念、传统与偏见", {"thinking"}),
    ("quantity", "数量计量", "数字、数量、单位与计量", {"statistic"}),
)

SECOND_PASS_SCENE_GROUPS = (
    ("normal_special", "常规与特殊", "正常、普通、典型与特殊", {
        "abnormal", "normal", "ordinary", "special", "typical", "unusual",
    }),
    ("familiarity", "熟悉与陌生", "熟悉、习惯与未知状态", {
        "accustomed", "familiar", "unknown", "used",
    }),
    ("experience_reaction", "体验与感受", "有趣、无聊、愉快与厌恶感受", {
        "amazing", "awesome", "boring", "disgusting", "disturbing", "enjoyable",
        "exciting", "funny", "humorous", "interesting", "pleasant", "wonderful",
    }),
    ("social_character", "性格与交往", "主动、被动及社交表达特点", {
        "ambitious", "enthusiastic", "modest", "outgoing", "outspoken", "passive",
        "sensitive", "shy", "strict",
    }),
    ("historical_period", "历史年代", "古代、现代与当代", {
        "ancient", "contemporary", "historic", "modern", "primitive",
    }),
    ("comfort_state", "舒适程度", "舒适与不舒适状态", {
        "comfortable", "uncomfortable", "unpleasant",
    }),
    ("mental_condition", "精神状态", "清醒、疯狂及心理状态", {
        "crazy", "mad", "aware",
    }),
    ("occupancy", "空间占用", "拥挤、空缺及占用状态", {
        "crowded", "vacant", "missing",
    }),
    ("safety_risk", "安全与风险", "安全、危险及有害风险", {
        "dangerous", "poisonous", "radioactive", "safe", "secure", "unsafe",
    }),
    ("price_value", "价格与价值", "昂贵、便宜及价值高低", {
        "cheap", "expensive", "precious", "worth",
    }),
    ("body_shape", "体型特征", "肥胖、苗条及体重状态", {
        "fat", "overweight", "slim",
    }),
    ("preference", "喜爱与偏好", "喜欢、偏爱与中意", {
        "favourite", "fond",
    }),
    ("sex_marital", "性别与婚姻", "性别及婚姻状态", {
        "female", "male", "unmarried",
    }),
    ("luck", "幸运与不幸", "幸运、走运与不幸", {
        "fortunate", "lucky", "unfortunate",
    }),
    ("reputation_influence", "知名度与影响", "知名、流行、领先与影响力", {
        "famous", "influential", "leading", "popular", "premier",
    }),
    ("importance_rank", "主次与重要性", "主要、次要及重要程度", {
        "main", "major", "minor", "primary", "secondary", "significant", "vital",
    }),
    ("presence_absence", "存在与缺失", "在场、缺席及缺失状态", {
        "absent", "present", "missing",
    }),
    ("mobility", "移动与便携", "可移动、便携与运行状态", {
        "mobile", "portable", "running",
    }),
    ("possibility_extreme", "可能与不可能", "可能性及难以置信程度", {
        "impossible", "incredible", "unbearable", "unbelievable",
    }),
    ("wealth", "贫富状态", "贫穷、富有与财富状态", {
        "poor", "rich", "wealthy",
    }),
    ("frequency_rarity", "常见与稀少", "常见、罕见及出现频率", {
        "common", "rare",
    }),
    ("peace_violence", "和平与暴力", "和平、暴力及凶猛状态", {
        "harmonious", "peaceful", "savage", "violent", "wild",
    }),
    ("success_failure", "成功与失败", "成功及未成功结果", {
        "successful", "unsuccessful",
    }),
    ("language_forms", "语言形式", "口语、书面语及语言表达形式", {
        "spoken", "learned",
    }),
    ("religious_quality", "宗教属性", "神圣及宗教相关属性", {
        "holy", "religious", "sacred", "spiritual",
    }),
    ("geographic_setting", "城乡与地域", "乡村、城市及地域环境", {
        "rural", "urban",
    }),
    ("positive_negative", "正面与负面", "正面、负面及倾向性", {
        "negative", "positive",
    }),
    ("relevance", "相关程度", "相关与不相关程度", {
        "relevant", "irrelevant",
    }),
    ("crime_conflict_actions", "冲突与社会行动", "战斗、抵制及社会冲突", {
        "battle", "boycott",
    }),
    ("family_change", "家庭关系变化", "结婚、离婚等家庭关系变化", {
        "divorce", "marriage",
    }),
    ("service_actions", "服务帮助", "服务、帮助与社会支持", {"rescue"}),
    ("colors", "颜色明暗", "颜色及明暗视觉特征", {"colour"}),
)

THIRD_PASS_SCENE_GROUPS = (
    ("reasonableness", "合理与荒谬", "合理、荒谬及是否合乎逻辑", {
        "absurd", "reasonable",
    }),
    ("randomness", "随机与任意", "随机、任意及缺少固定规则", {
        "arbitrary", "random",
    }),
    ("stability_consistency", "稳定与持续", "稳定、一致及持续状态", {
        "consistent", "constant", "endless",
    }),
    ("freedom_constraint", "自由与约束", "自由、受约束及限制状态", {
        "bound", "free",
    }),
    ("work_condition", "工作状态", "忙碌、效率与做事周全程度", {
        "busy", "efficient", "thorough",
    }),
    ("legal_status", "法律身份", "有罪、无罪及法律身份状态", {
        "guilty", "innocent",
    }),
    ("subjective_objective", "主观与客观", "主观判断与客观事实", {
        "objective", "subjective",
    }),
    ("dependence", "依赖关系", "依靠、依赖及相互支持", {
        "depend", "rely",
    }),
    ("help_support", "帮助与救援", "帮助、支持及救援行动", {
        "aid", "helpful", "rescue", "support",
    }),
    ("visual_quality", "视觉清晰度", "可见性、鲜明及暗淡程度", {
        "dull", "visible", "vivid",
    }),
    ("style_grade", "风格与等级", "经典、华丽及等级评价", {
        "classic", "extraordinary", "fancy", "grand", "super", "superior", "supreme",
    }),
    ("age_stage", "年龄阶段", "年轻、年长及年龄层次", {
        "born", "mature",
    }),
    ("shape", "形状外观", "明确的几何形状与外形", {"flat"}),
    ("positive_emotions", "积极情绪", "高兴、满意、感激与希望", {"calm"}),
    ("appearance", "外貌美丑", "外貌、仪态与美丑评价", {"adorable"}),
    ("body_health", "身体健康状态", "生命、健康、疾病与身体感受", {"alcoholic"}),
    ("ability_difficulty", "能力与难度", "能力、智力、熟练度与难易", {
        "awkward", "clumsy",
    }),
    ("normal_special", "常规与特殊", "正常、普通、典型与特殊", {
        "odd", "strange",
    }),
    ("truth_accuracy", "真假与准确", "真实、正确、确定与准确程度", {"tentative"}),
    ("quality_evaluation", "质量与评价", "好坏、价值、重要性与总体评价", {
        "silly", "unfair",
    }),
    ("cleanliness", "清洁整齐", "干净、肮脏及整齐程度", {"pure"}),
    ("numbers", "数字量词", "基数、序数、数量与次序", {"sixteenth"}),
    ("business_saving", "储蓄节约", "储蓄、节约及经济行为", {
        "save", "saving",
    }),
)

FOURTH_PASS_SCENE_GROUPS = (
    ("severity", "严重程度", "严重、剧烈及紧急程度", {
        "acute", "serious", "severe",
    }),
    ("sudden_change", "突发变化", "突然、急剧及意外变化", {
        "abrupt", "sudden",
    }),
    ("general_specific", "一般与个别", "一般、个别及特定范围", {
        "general", "individual", "particular",
    }),
    ("practicality", "实用便利", "实用、有帮助及使用便利", {
        "handy", "practical", "useful",
    }),
    ("public_facilities", "公共设施", "公共空间中的设施与陈设", {
        "bench", "fountain", "monument", "statue",
    }),
    ("solitude", "独处与孤独", "独自、孤单及缺少陪伴", {
        "alone", "lonely",
    }),
    ("formal_casual", "正式与随意", "正式、非正式及随意风格", {
        "casual", "formal",
    }),
    ("daily_frequency", "日常频率", "每天、日常及经常发生", {
        "daily", "everyday",
    }),
    ("personal_ownership", "个人所有", "个人、私人及自身所有", {
        "own", "personal", "private",
    }),
    ("quantity_scope", "数量与范围", "数量、范围、完整度与限度", {
        "absolute", "less", "only", "spare",
    }),
    ("same_difference", "异同与对应", "相同、不同、相似及对应关系", {"various"}),
)

FINAL_SCENE_GROUPS = (
    ("length_width", "长短宽窄", "长度和宽度", {"brief"}),
    ("time", "时间日期", "时间、日期、阶段与顺序", {"due"}),
    ("shape", "形状外观", "明确的几何形状与外形", {"even"}),
    ("sex_marital", "性别与婚姻", "性别及婚姻状态", {"gay"}),
    ("fairness", "公平正义", "公平、公正及正义原则", {"fair", "just"}),
    ("objects", "物品对象", "具体物品及一般对象", {"item", "object", "thing"}),
    ("relevance", "相关联系", "相关、联系及相互关系", {
        "connection", "relation", "relevant",
    }),
    ("quantity", "数量计量", "数字、数量、单位与计量", {"percent"}),
)

PRECISE_WORD_THEMES = {
    word: (theme_id, title, subtitle)
    for theme_id, title, subtitle, words in (
        PRECISE_SCENE_GROUPS + ADJECTIVE_SCENE_GROUPS + ACTION_SCENE_GROUPS
        + SECOND_PASS_SCENE_GROUPS + THIRD_PASS_SCENE_GROUPS + FOURTH_PASS_SCENE_GROUPS
        + FINAL_SCENE_GROUPS
    )
    for word in words
}


PARENT_THEME_GROUPS = {
    "人体与健康": {"身体部位", "身体动作", "体型特征", "健康体感", "身体健康状态", "舒适程度", "精神状态", "医疗健康"},
    "人物与职业": {"人物身份", "职业工作", "称谓头衔"},
    "家庭与关系": {"家庭成员", "性别与婚姻", "家庭关系变化", "个人所有", "关系联系", "依赖关系", "群体组织"},
    "性格与情绪": {"性格品德", "积极品格", "消极品格", "性格与交往", "情绪感受", "体验与感受", "积极情绪", "消极情绪", "情绪状态", "情感态度", "独处与孤独", "幸运与不幸", "喜爱与偏好"},
    "学校与教育": {"学校教育", "学科课程", "课程考试", "学习用品", "学习活动", "能力难度", "选择判断"},
    "思考与方法": {"思考与理解", "分析与判断", "思想与观念", "方法与策略", "选择与困境"},
    "口语与交流": {"口语交流", "说话与声音", "告知与说明", "劝告与指令", "礼貌与回应", "会议交流"},
    "阅读与写作": {"写作文本", "文学阅读", "语言技能", "语言形式", "书刊文件", "文本标记"},
    "媒体与传播": {"媒体传播", "宣传推广"},
    "饮食与生活": {"食物饮料", "餐饮场所", "饮食消费", "味道与食物状态", "家务生活", "服务帮助"},
    "建筑与场所": {"住宅建筑", "公共建筑", "公共设施", "宗教场所", "居家生活", "建筑场所"},
    "服装与配饰": {"衣服穿戴", "随身配饰"},
    "家具与用品": {"家具陈设", "家具家居", "容器包装", "日常物品"},
    "物品": {"物品对象"},
    "购物与经济": {"购物商业", "经济商业", "价格与价值", "贫富状态", "储蓄节约", "财物所有", "获得使用"},
    "交通与旅行": {"交通工具", "交通出行", "移动出行", "移动与便携", "旅行活动"},
    "体育与娱乐": {"体育运动", "体育项目", "竞赛对抗", "文化艺术", "休闲与旅行", "节日庆祝", "精神与信仰", "宗教属性", "宗教活动"},
    "社会与公共事务": {"国家社会", "社会身份与规范", "正式与随意", "知名度与影响", "社会行为", "社会变革", "冲突与社会行动", "和平与暴力", "帮助与救援", "公平正义", "法律治安", "法律与规则", "法律身份", "犯罪与处罚", "自由与约束", "管理组织", "违规与欺骗", "欺骗行为"},
    "科学与研究": {"科学研究", "调查研究", "观察检查", "实验操作", "实验观测器材", "来源与覆盖"},
    "技术与设备": {"信息科技", "机器设备", "媒体设备", "办公通信设备"},
    "工具与器材": {"工具与设备", "工具用品", "运动器材", "军事装备"},
    "医疗与护理": {"医疗用品"},
    "证件与文书": {"证件文书"},
    "动物与植物": {"动物世界", "植物世界"},
    "天气与环境": {"天气气候", "天气变化", "自然现象", "环境保护"},
    "尺寸与外形": {"尺寸大小", "长短宽窄", "高低位置", "厚薄粗细", "形状外观", "外貌颜色", "形状结构"},
    "地理与空间": {"地点空间", "位置与方向", "方位介词", "城乡与地域", "国家与地区"},
    "时间与数量": {"数字量词", "数量计量", "数量程度", "数量与范围"},
    "时间与顺序": {"时间日期", "时间早晚", "时间与频率", "日常频率", "历史年代", "常见与稀少"},
    "人物年龄": {"年龄阶段"},
    "事件与活动": {"事件活动", "行为活动", "突发变化"},
    "工作与事务": {"工作事务", "工作任务", "工作状态", "努力与成果", "成功与失败", "生产建设", "制作创造"},
    "动作与变化": {"变化发展", "发展过程", "接触操作", "感官观察"},
    "外观与感官": {"颜色明暗", "外貌美丑", "清洁整齐", "视觉清晰度", "温度与干湿", "声音特征"},
    "判断与评价": {"真假与准确", "质量与评价", "风格与等级", "实用便利", "正面与负面", "主次与重要性", "清晰与复杂"},
    "能力与准备": {"能力与难度", "可能与准备", "可能与不可能"},
    "物理特征": {"物体状态与质感", "速度与力量"},
    "逻辑与关系": {"异同与对应", "一般与个别", "相关程度", "相关联系", "合理与荒谬", "主观与客观"},
    "状态与特征": {"状态处境", "存在状态", "存在与缺失", "空间占用", "稳定与持续", "严重程度", "随机与任意", "常规与特殊", "熟悉与陌生", "新旧状态", "性质描述", "性质特征", "类别属性", "动作状态", "质量评价", "速度频率", "安全危险", "安全与风险", "真假确定", "情绪影响"},
    "逻辑与功能词": {"逻辑连接", "冠词限定", "代词指代", "情态助动", "感叹回应", "方式程度", "目的动机"},
    "材料与资源": {"材料物质", "财物所有"},
    "其他": {"其他"},
}


PARENT_BY_THEME = {
    theme: parent
    for parent, themes in PARENT_THEME_GROUPS.items()
    for theme in themes
}

NATURAL_TITLE_RENAMES = {
    # Main headings
    "人物年龄": "年龄",
    "判断与评价": "判断评价",
    "医疗与护理": "医疗健康",
    "口语与交流": "日常交流",
    "外观与感官": "外观感觉",
    "家具与用品": "家居用品",
    "工作与事务": "工作",
    "思考与方法": "思维方法",
    "时间与数量": "时间数量",
    "物理特征": "物品特征",
    "状态与特征": "常见状态",
    "社会与公共事务": "社会生活",
    "能力与准备": "能力条件",
    "证件与文书": "证件文件",
    "逻辑与关系": "比较关系",
    "逻辑与功能词": "常用功能词",
    "语言交流": "语言信息",
    "表达交流": "表达传递",
    "大小形状": "大小",
    "思考学习": "思维活动",
    "学习活动": "学习训练",
    "工具器物": "日常器具",
    # Child headings
    "突发变化": "突然变化",
    "移动与便携": "移动便携",
    "身体健康状态": "身体状态",
    "舒适程度": "舒适感",
    "年龄阶段": "年龄",
    "宗教属性": "宗教",
    "主次与重要性": "重要程度",
    "实用便利": "实用性",
    "清晰与复杂": "简单与复杂",
    "真假与准确": "真假对错",
    "质量与评价": "好坏评价",
    "风格与等级": "风格档次",
    "感官观察": "观察感知",
    "口语交流": "日常对话",
    "劝告与指令": "建议命令",
    "告知与说明": "通知解释",
    "礼貌与回应": "礼貌用语",
    "说话与声音": "说话方式",
    "位置与方向": "方位方向",
    "地点空间": "地点",
    "城乡与地域": "城乡地区",
    "外貌美丑": "外貌",
    "清洁整齐": "清洁",
    "温度与干湿": "冷热干湿",
    "视觉清晰度": "视觉效果",
    "颜色明暗": "颜色",
    "学校教育": "学校",
    "学科课程": "学科",
    "课程考试": "课程考试",
    "选择判断": "选择决定",
    "个人所有": "个人私有",
    "家庭关系变化": "婚姻变化",
    "性别与婚姻": "性别婚姻",
    "群体组织": "团体组织",
    "尺寸大小": "大小",
    "形状外观": "形状",
    "高低位置": "高低",
    "制作创造": "制作",
    "努力与成果": "努力成果",
    "工作事务": "工作任务",
    "分析与判断": "分析判断",
    "思想与观念": "思想观念",
    "思考与理解": "思考理解",
    "方法与策略": "方法策略",
    "选择与困境": "选择困境",
    "体验与感受": "体验感受",
    "喜爱与偏好": "喜好",
    "幸运与不幸": "运气",
    "性格与交往": "社交性格",
    "情感态度": "情感",
    "情绪感受": "情绪",
    "消极品格": "不良性格",
    "消极情绪": "负面情绪",
    "独处与孤独": "孤独",
    "积极品格": "良好品格",
    "积极情绪": "正面情绪",
    "信息科技": "网络科技",
    "办公通信设备": "办公设备",
    "日常频率": "日常频率",
    "时间与频率": "时间频率",
    "时间早晚": "早晚",
    "常见与稀少": "常见少见",
    "衣服穿戴": "服装",
    "随身配饰": "配饰",
    "材料物质": "材料",
    "物体状态与质感": "物品质感",
    "存在与缺失": "有无状态",
    "安全与风险": "安全危险",
    "常规与特殊": "普通特殊",
    "情绪影响": "惊讶",
    "新旧状态": "新旧",
    "稳定与持续": "稳定持续",
    "空间占用": "空间状态",
    "随机与任意": "随机",
    "冲突与社会行动": "冲突行动",
    "国家社会": "国家社会",
    "知名度与影响": "知名影响",
    "社会身份与规范": "社会身份",
    "实验观测器材": "实验器材",
    "来源与覆盖": "来源范围",
    "可能与准备": "条件可能",
    "能力与难度": "能力难度",
    "证件文书": "证件",
    "价格与价值": "价格价值",
    "获得使用": "获取使用",
    "贫富状态": "贫富",
    "购物商业": "购物",
    "异同与对应": "相同不同",
    "物品对象": "常见物品",
    "相关联系": "相关关系",
    "合理与荒谬": "合理荒谬",
    "一般与个别": "一般个别",
    "主观与客观": "主观客观",
    "代词指代": "代词",
    "冠词限定": "冠词",
    "情态助动": "情态动词",
    "感叹回应": "感叹词",
    "目的动机": "目的原因",
    "逻辑连接": "连词",
    "写作文本": "实用写作",
    "味道与食物状态": "味道食物",
    "饮食消费": "饮食行为",
}


WORD_THEME_OVERRIDES = {
    "antique": ("furniture", "家具陈设", "家具与室内陈设"),
    "beard": ("body", "身体部位", "身体部位、器官与生理"),
    "beef": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "come": ("motion", "移动出行", "移动、到达与方向变化"),
    "buffet": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "cock": ("animals", "动物世界", "动物种类、特征与活动"),
    "gallery": ("arts", "文化艺术", "音乐、美术、戏剧与文化"),
    "mankind": ("people", "人物身份", "人物、身份与社会角色"),
    "queen": ("people", "人物身份", "人物、身份与社会角色"),
    "virus": ("medicine", "医疗健康", "疾病、治疗与健康管理"),
    "needle": ("tools", "工具用品", "工具、器具与操作用品"),
    "lid": ("containers", "容器包装", "容器、包装与收纳用品"),
    "socket": ("artifact_equipment", "工具与设备", "用于操作、生产或测量的工具设备"),
    "cassette": ("media_devices", "媒体设备", "摄影、声音与媒体设备"),
    "fridge": ("machines", "机器设备", "机器、设备、装置与仪器"),
    "pocket": ("clothing", "衣服穿戴", "衣物、鞋帽与穿戴"),
    "brick": ("materials", "材料物质", "材料、物质与组成"),
    "plant": ("plants", "植物世界", "植物、农作物与生长"),
    "mount": ("motion", "移动出行", "移动、到达与方向变化"),
    "banana": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "carrot": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "corn": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "fruit": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "garlic": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "mushroom": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "mustard": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "nut": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "onion": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "peach": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "pepper": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "watermelon": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "dragon": ("animals", "动物世界", "动物种类、特征与活动"),
    "tiger": ("animals", "动物世界", "动物种类、特征与活动"),
    "whale": ("animals", "动物世界", "动物种类、特征与活动"),
    "frost": ("weather", "天气气候", "天气、气候与气象现象"),
    "garbage": ("environment", "环境保护", "环境、污染、资源与保护"),
    "junk": ("environment", "环境保护", "环境、污染、资源与保护"),
    "rubbish": ("environment", "环境保护", "环境、污染、资源与保护"),
    "café": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "chopsticks": ("tools", "工具用品", "工具、器具与操作用品"),
    "ice-cream": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "wi-fi": ("technology", "信息科技", "计算机、网络与现代技术"),
    "animal": ("animals", "动物世界", "动物种类、特征与活动"),
    "beast": ("animals", "动物世界", "动物种类、特征与活动"),
    "creature": ("animals", "动物世界", "动物种类、特征与活动"),
    "event": ("events", "事件活动", "事件、活动与发生过程"),
    "feeling": ("feelings", "情绪感受", "情绪、感受与心理体验"),
    "food": ("food", "食物饮料", "食材、饮品、烹饪与用餐"),
    "group": ("groups", "群体组织", "团体、组织与社会群体"),
    "location": ("places", "地点空间", "地点、区域与空间位置"),
    "motivation": ("motives", "目的动机", "目标、原因与行为动机"),
    "motive": ("motives", "目的动机", "目标、原因与行为动机"),
    "person": ("people", "人物身份", "人物、身份与社会角色"),
    "phenomenon": ("phenomena", "自然现象", "自然现象与客观变化"),
    "quantity": ("quantity", "数量计量", "数字、数量、单位与计量"),
    "space": ("places", "地点空间", "地点、区域与空间位置"),
    "substance": ("materials", "材料物质", "材料、物质与组成"),
    "confucius": ("people", "人物身份", "人物、身份与社会角色"),
    "clone": ("science", "科学研究", "科学、实验与研究方法"),
    "monitor": ("technology", "信息科技", "计算机、网络与现代技术"),
    "printer": ("technology", "信息科技", "计算机、网络与现代技术"),
    "carrier": ("transport", "交通出行", "交通工具、道路与出行"),
    "ward": ("medicine", "医疗健康", "疾病、治疗与健康管理"),
    "god": ("belief", "精神与信仰", "精神、信仰与宗教概念"),
    "soul": ("belief", "精神与信仰", "精神、信仰与宗教概念"),
    "spirit": ("belief", "精神与信仰", "精神、信仰与宗教概念"),
    "choice": ("choice", "选择判断", "选择、决定与判断"),
    "choose": ("choice", "选择判断", "选择、决定与判断"),
    "decision": ("choice", "选择判断", "选择、决定与判断"),
    "option": ("choice", "选择判断", "选择、决定与判断"),
    "select": ("choice", "选择判断", "选择、决定与判断"),
    "shine": ("colors_light", "颜色明暗", "颜色、光线与明暗视觉特征"),
    "green": ("colors_light", "颜色明暗", "颜色、光线与明暗视觉特征"),
    "terminal": ("technology", "信息科技", "计算机、网络与现代技术"),
    "civil": ("social_identity", "社会身份与规范", "社会身份、法律规范及公共属性"),
    "graduation": ("school", "学校教育", "学校、课程、考试与学习"),
    "production": ("work_routines", "工作事务", "任务和日常文书工作"),
    "professional": ("occupations", "职业工作", "职业、岗位与工作身份"),
}


def normalized_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.casefold()))


def select_theme(row: dict, semantic: dict) -> tuple[str, str, str] | None:
    word = str(row["word"]).casefold()
    pos = set(str(row.get("parts_of_speech", "")).split("; "))
    if word in WORD_THEME_OVERRIDES:
        return WORD_THEME_OVERRIDES[word]
    if word in PRECISE_WORD_THEMES:
        return PRECISE_WORD_THEMES[word]
    if word == "o’clock":
        return "time", "时间日期", "时间、日期、阶段与顺序"
    if word in {"else", "why"}:
        return "conjunctions", "逻辑连接", "并列、转折、因果与条件"
    for accepted, theme in POS_THEMES:
        if pos & set(accepted):
            return theme

    semantic_words = {word}
    senses = semantic.get("senses", [])
    primary_pos = str(row.get("parts_of_speech", "")).split(";", 1)[0].strip()
    semantic_pos = "noun" if primary_pos == "proper_noun" else primary_pos
    primary_senses = [
        sense for sense in senses if sense.get("part_of_speech") == semantic_pos
    ]
    for sense in primary_senses[:1]:
        semantic_words.update(normalized_words(" ".join(sense.get("definitions_en", []))))
    for theme_id, title, subtitle, keywords in SPECIAL_THEMES:
        if word in keywords:
            return theme_id, title, subtitle

    # WordNet often returns several senses for a common word.  The source is
    # ordered by frequency, so use the first matching sense as the scene anchor
    # instead of dropping every polysemous word from the catalogue.
    primary_class = next(
        (
            str(sense.get("lexicographer_class", ""))
            for sense in primary_senses
            if sense.get("lexicographer_class")
        ),
        "",
    )
    content = str(row.get("content", ""))
    refinements = ()
    if primary_pos == "adjective":
        refinements = ADJECTIVE_CONTENT_THEMES
    elif primary_class == "noun.act":
        refinements = ACTION_CONTENT_THEMES
    if primary_class == "noun.artifact":
        refinements = ARTIFACT_CONTENT_THEMES
    for theme_id, title, subtitle, markers in refinements:
        if any(marker in content for marker in markers):
            return theme_id, title, subtitle
    if primary_class == "noun.artifact":
        equipment_terms = {
            "tool", "instrument", "device", "equipment", "machine", "apparatus",
            "implement", "utensil", "engine", "weapon",
        }
        if semantic_words & equipment_terms:
            return "artifact_equipment", "工具与设备", "用于操作、生产或测量的工具设备"
    if primary_class in CLASS_THEMES:
        return CLASS_THEMES[primary_class]

    # A very small number of entries have no usable semantic record.  Keep
    # them visible in an honest grammatical scene instead of silently omitting
    # them or putting everything into an oversized “其他”.
    return {
        "proper_noun": ("countries_regions", "国家与地区", "国家、地区及地理名称"),
        "noun": ("common_concepts", "常用事物", "日常事物与常用概念"),
        "verb": ("common_actions", "常用动作", "日常行为、动作与变化"),
        "adjective": ("descriptions", "性质描述", "性质、状态与评价描述"),
        "adverb": ("adverbs", "方式程度", "方式、程度、时间与频率"),
    }.get(primary_pos, ("common_expressions", "常用表达", "常用表达与语法功能"))


def pos_hint(row: dict) -> str:
    pos = str(row.get("parts_of_speech", "")).split("; ")[0]
    return {
        "noun": "名词", "proper_noun": "专有名词", "verb": "动词",
        "adjective": "形容词", "adverb": "副词", "pronoun": "代词",
        "determiner": "限定词", "numeral": "数词", "ordinal": "序数词",
        "preposition": "介词", "conjunction": "连词", "article": "冠词",
        "modal_verb": "情态动词", "interjection": "感叹词", "title": "称谓",
    }.get(pos, "常用词")


def chunked(items: list[str], size: int):
    group_count = max(1, (len(items) + size - 1) // size)
    base, extra = divmod(len(items), group_count)
    start = 0
    for index in range(group_count):
        current_size = base + (1 if index < extra else 0)
        yield items[start:start + current_size]
        start += current_size


def build_scene_groups(vocabulary: list[dict], semantics: dict[str, dict]) -> list[dict]:
    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in vocabulary:
        theme = select_theme(row, semantics.get(row["record_id"], {}))
        if theme is None:
            continue
        buckets[theme].append(row)

    # A category with only one word provides no grouping value.  Merge every
    # singleton into one honest catch-all instead of displaying a fake theme.
    singleton_rows = []
    for theme, rows in list(buckets.items()):
        if theme != OTHER_THEME and len(rows) == 1:
            singleton_rows.extend(rows)
            del buckets[theme]
    buckets[OTHER_THEME].extend(singleton_rows)

    groups = []
    for (theme_id, title, subtitle), rows in sorted(buckets.items(), key=lambda item: item[0][1]):
        rows.sort(key=lambda row: str(row["word"]).casefold())
        pieces = list(chunked(rows, GROUP_SIZE))
        display_title = NATURAL_TITLE_RENAMES.get(title, title)
        parent = NATURAL_TITLE_RENAMES.get(PARENT_BY_THEME.get(title, title), PARENT_BY_THEME.get(title, title))
        for index, piece in enumerate(pieces, 1):
            suffix = f" · {index}" if len(pieces) > 1 else ""
            groups.append({
                "id": f"{theme_id}:{index}",
                "parent": parent,
                "title": display_title + suffix,
                "subtitle": subtitle,
                "records": [row["record_id"] for row in piece],
                "hints": [pos_hint(row) for row in piece],
            })
    return groups


def build_relation_groups(vocabulary: list[dict], _semantic_rows: list[dict]) -> list[dict]:
    """Build only the manually reviewed common-meaning relation pairs."""
    by_word = {str(row["word"]).casefold(): row for row in vocabulary}

    def glosses(word: str) -> list[str]:
        content = str(by_word[word].get("content", "")).split("|", 1)[0].strip()
        content = re.sub(r"^[A-Za-z_ ]+[：:]\s*", "", content)
        return [part.strip() for part in content.split("；") if part.strip()]

    groups = []
    for relation, pairs, label, subtitle in (
        ("synonym", STRICT_SYNONYM_PAIRS, "同义", "高中常用义相同或高度接近"),
        ("antonym", STRICT_ANTONYM_PAIRS, "反义", "高中常用义明确相反"),
    ):
        index = 0
        for left, right in pairs:
            if left not in by_word or right not in by_word:
                continue
            left_glosses, right_glosses = glosses(left), glosses(right)
            if relation == "synonym":
                shared = next((value for value in left_glosses if value in right_glosses), "")
                if not shared:
                    continue
                display_meanings = [shared, shared]
            else:
                display_meanings = [
                    "白天" if left == "day" else left_glosses[0],
                    right_glosses[0],
                ]
            index += 1
            groups.append({
                "id": f"{relation}:{index}",
                "title": f"{label}词组 · {index}",
                "subtitle": subtitle,
                "records": [by_word[left]["record_id"], by_word[right]["record_id"]],
                "hints": display_meanings,
            })
    return groups


def main():
    vocabulary = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    semantic_document = json.loads(SEMANTIC_PATH.read_text(encoding="utf-8"))
    semantic_rows = semantic_document.get("records", [])
    semantics = {row["record_id"]: row for row in semantic_rows}
    scene_groups = build_scene_groups(vocabulary, semantics)
    relation_groups = build_relation_groups(vocabulary, semantic_rows)
    scene_records = [record for group in scene_groups for record in group["records"]]
    document = {
        "schema_version": "1.0",
        "source_vocabulary": "gaokao-3800",
        "scene_group_size_limit": GROUP_SIZE,
        "scene_word_count": len(scene_records),
        "scene_unique_word_count": len(set(scene_records)),
        "scene_groups": scene_groups,
        "relation_groups": relation_groups,
    }
    OUTPUT_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"scene groups: {len(scene_groups)}")
    print(f"scene words: {document['scene_unique_word_count']}")
    print(f"relation groups: {len(relation_groups)}")
    print(f"output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
