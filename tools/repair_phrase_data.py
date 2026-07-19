"""One-time, auditable cleanup for assets/short_phrase.json."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "assets" / "short_phrase.json"

# These were generated around the adjective "dynamic" and are not established
# fixed phrases suitable for a phrase-learning table.
REMOVE_IDS = {143, 390, 395, 426, 454, 482, 494, 495}

# Canonical phrase/meaning corrections, keyed by the original stable id.
CORRECTIONS = {
    19: {"p": "take account of", "m": "考虑到；把……计算在内"},
    42: {"p": "put the blame on", "m": "归咎于；责怪"},
    43: {"p": "take a breath", "m": "喘口气；吸一口气"},
    72: {"p": "come to power", "m": "执政；掌权"},
    102: {"p": "get the upper hand", "m": "占上风；取得优势"},
    128: {"p": "break the rules", "m": "违反规则"},
    144: {"p": "make a contribution to", "m": "为……做出贡献"},
    145: {"p": "make space for / make room for"},
    153: {"p": "set an example for", "m": "为……树立榜样"},
    188: {"p": "keep in touch with", "m": "与……保持联系"},
    221: {"m": "喘口气；恢复呼吸"},
    227: {"p": "die of / die from"},
    257: {"p": "ascribe sth to sth", "m": "把……归因于……"},
    259: {"p": "devote oneself/sth to sth", "m": "致力于；把……奉献给"},
    264: {"p": "accustom oneself to sth", "m": "使自己习惯于……"},
    271: {"p": "compete with / compete against"},
    273: {"p": "congratulate sb on sth", "m": "因某事向某人祝贺"},
    274: {"p": "cure sb of sth", "m": "治好某人的疾病或坏习惯"},
    283: {"p": "inform sb of sth", "m": "把某事通知某人"},
    288: {"p": "prefer A to B", "m": "比起B更喜欢A"},
    289: {"p": "prevent sb from doing sth", "m": "阻止某人做某事"},
    290: {"p": "protect sb/sth from sth", "m": "保护……免受伤害"},
    291: {"p": "provide sb with sth", "m": "向某人提供某物"},
    293: {"p": "remind sb of sth", "m": "提醒某人；使某人想起某事"},
    296: {"p": "separate A from B", "m": "把A与B分开"},
    297: {"p": "spend time/money on sth", "m": "在某事上花时间或金钱"},
    299: {"p": "warn sb of sth", "m": "警告某人注意某事"},
    318: {"p": "take an interest in", "m": "对……产生兴趣"},
    324: {"p": "put the blame on", "m": "归咎于；责备"},
    340: {"p": "get the upper hand", "m": "占上风；取得优势"},
    343: {"m": "对……产生影响"},
    384: {"m": "对……有耐心"},
    481: {"p": "be determined on doing sth", "m": "决意做某事"},
    490: {"p": "be prone to doing sth", "m": "易于做某事；有……倾向"},
    497: {"p": "in contrast to / in contrast with"},
    566: {
        "p": "without question",
        "m": "毫无疑问",
        "en": "Without question, his research was successful.",
        "cn": "毫无疑问，他的研究取得了成功。",
    },
    570: {"p": "had better do sth", "m": "最好做某事"},
    573: {
        "p": "as if / as though",
        "m": "好像；仿佛",
        "en": "He talks as if he were a professional.",
        "cn": "他说起话来仿佛自己是专业人士。",
    },
    575: {"p": "so as to do sth", "m": "以便；为了做某事"},
    576: {"p": "can't help doing sth", "m": "忍不住做某事"},
}

ALTERNATIVES = {
    "turn on/off": ["turn on", "turn off", "turn on/off", "turn on / turn off"],
    "look on...as": ["look on ... as", "look on...as"],
    "get on/off": ["get on", "get off", "get on/off", "get on / get off"],
    "make sure/certain": ["make sure", "make certain", "make sure/certain"],
    "make space for / make room for": ["make space for", "make room for"],
    "die of / die from": ["die of", "die from"],
    "compete with / compete against": ["compete with", "compete against"],
    "in contrast to / in contrast with": ["in contrast to", "in contrast with"],
    "as if / as though": ["as if", "as though"],
    "come to power": ["come to power", "come into power"],
    "not only...but also": ["not only ... but also", "not only...but also"],
    "either...or": ["either ... or", "either...or"],
    "neither...nor": ["neither ... nor", "neither...nor"],
}

# Natural examples replacing the remaining software/layout/routine template
# fragments, and examples that still used the pre-correction phrase form.
EXAMPLE_CORRECTIONS = {
    "take account of": ("We must take account of the weather.", "我们必须把天气因素考虑在内。"),
    "come to power": ("The new party came to power last year.", "新政党去年开始执政。"),
    "set an example for": ("Older children should set a good example for younger ones.", "大孩子应当为小孩子树立好榜样。"),
    "send out": ("The signal was sent out from the tower.", "信号从塔楼发射出去。"),
    "accustom oneself to sth": ("You will soon accustom yourself to the new routine.", "你很快就会习惯新的日常安排。"),
    "find fault with": ("She always finds fault with the way I do the housework.", "她总是挑剔我做家务的方式。"),
    "be lacking in": ("The plan is lacking in detail.", "这个计划缺乏细节。"),
    "be suitable for": ("This room is suitable for a small office.", "这个房间适合作为一间小办公室。"),
    "be disappointed with": ("He was disappointed with the results.", "他对结果感到失望。"),
    "be busy with": ("The architect is busy with his new design.", "那位建筑师正忙于他的新设计。"),
    "be bored with": ("He grew bored with the repetitive work.", "他逐渐厌倦了这种重复性的工作。"),
    "be certain to do": ("Hard work is certain to bring progress.", "努力工作一定会带来进步。"),
    "be familiar with": ("Are you familiar with this procedure?", "你熟悉这个流程吗？"),
    "be tired of": ("He was tired of doing the same tasks every day.", "他厌倦了每天做同样的事情。"),
    "be good for": ("Regular exercise is good for your health.", "经常锻炼有益健康。"),
    "be fed up with": ("I am fed up with his endless complaints.", "我受够了他没完没了的抱怨。"),
    "be different from": ("Life in a town is different from life in a city.", "城镇生活与城市生活不同。"),
    "be popular with": ("The new interface is popular with young designers.", "这个新界面很受年轻设计师欢迎。"),
    "be careful to do": ("Be careful to check every detail.", "注意检查每一个细节。"),
    "be prone to doing sth": ("Tired drivers are prone to making mistakes.", "疲劳驾驶者容易犯错。"),
    "with regard to": ("I have some questions with regard to that contract.", "关于那份合同，我有一些问题。"),
    "apart from": ("Apart from a few typos, the essay is nearly perfect.", "除几处拼写错误外，这篇文章近乎完美。"),
    "as for": ("As for me, I prefer the first option.", "至于我，我更喜欢第一个方案。"),
    "ahead of": ("He finished the work ahead of schedule.", "他提前完成了工作。"),
    "on purpose": ("He broke the vase on purpose.", "他故意打碎了花瓶。"),
    "in general": ("In general, the plan is reasonable.", "总的来说，这个计划是合理的。"),
    "by all means": ("Finish the task by all means.", "务必想办法完成这项任务。"),
    "in advance": ("You should book the room in advance.", "你应该提前预订房间。"),
    "had better do sth": ("You had better leave now.", "你最好现在就离开。"),
    "in detail": ("Please explain the procedure in detail.", "请详细说明这个流程。"),
    "by means of": ("He lifted the box by means of a rope.", "他借助绳子把箱子吊了起来。"),
    "because of": ("We stayed at home because of the cold, rainy weather.", "因为天气阴冷多雨，我们待在家里。"),
    "on time": ("Please arrive for the test on time.", "请准时参加考试。"),
    "so as to do sth": ("He woke up early so as to catch the bus.", "他早起以便赶上公共汽车。"),
    "as well as": ("He is kind as well as clever.", "他既善良又聪明。"),
    "in private": ("The two managers discussed the matter in private.", "两位经理私下讨论了这件事。"),
    "out of shape": ("The wooden box was completely out of shape.", "那个木箱已经完全变形了。"),
    "up to": ("The hall can hold up to one thousand people.", "这个大厅最多可容纳一千人。"),
    "up to now": ("Up to now, everything has gone well.", "到目前为止，一切进展顺利。"),
    "at present": ("At present, the new product is being tested.", "目前，这款新产品正在接受测试。"),
    "by the way": ("By the way, have you seen Jack today?", "顺便问一下，你今天见过杰克吗？"),
    "in a sense": ("In a sense, his decision was right.", "从某种意义上说，他的决定是正确的。"),
    "under control": ("Don't panic; the fire is under control.", "别慌，火势已经得到控制。"),
    "in shape": ("Regular exercise keeps the athlete in shape.", "规律锻炼使这名运动员保持良好状态。"),
    "for example": ("Some animals, for example bears, sleep through much of the winter.", "有些动物，例如熊，会在冬季长时间睡眠。"),
    "off duty": ("After going off duty, he went straight home.", "下班后，他直接回家了。"),
}


def clean_generated_example(text: str) -> str:
    # The source contains 210 examples with an injected template adjective and
    # 45 literal "dynamic dynamic" repetitions. It carries no intended meaning.
    text = re.sub(r"\bdynamic\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    # Repair articles exposed after deleting the injected adjective.
    text = re.sub(r"\ba ([aeiouAEIOU])", r"an \1", text)
    text = re.sub(r"\ban ([^aeiouAEIOU\W])", r"a \1", text)
    return text


def main() -> None:
    rows = json.loads(PATH.read_text(encoding="utf-8"))
    if len(rows) != 600:
        raise RuntimeError(f"expected 600 source rows, found {len(rows)}")

    for row in rows:
        row.update(CORRECTIONS.get(row["id"], {}))
        row["en"] = clean_generated_example(row["en"])
        # A translated copy of the injected template adjective also appeared in
        # some Chinese examples; it is not part of the phrase meaning.
        row["cn"] = row["cn"].replace("动态", "")

    # Remove generated non-phrases, then keep the first (usually cleaner) copy
    # of each exact phrase.
    cleaned = []
    seen = set()
    for row in rows:
        if row["id"] in REMOVE_IDS:
            continue
        key = re.sub(r"\s+", " ", row["p"].strip().lower())
        if key in seen:
            continue
        seen.add(key)
        row.pop("id", None)
        answers = ALTERNATIVES.get(row["p"])
        if answers:
            row["answers"] = answers
        if row["p"] in EXAMPLE_CORRECTIONS:
            row["en"], row["cn"] = EXAMPLE_CORRECTIONS[row["p"]]
        cleaned.append(row)

    for new_id, row in enumerate(cleaned, 1):
        row["id"] = new_id
        # Keep the established field order for readability and compatibility.
        ordered = {"id": row["id"], "p": row["p"], "m": row["m"],
                   "en": row["en"], "cn": row["cn"]}
        if "answers" in row:
            ordered["answers"] = row["answers"]
        row.clear()
        row.update(ordered)

    rendered = "[\n" + ",\n".join(
        "  " + json.dumps(row, ensure_ascii=False) for row in cleaned
    ) + "\n]\n"
    PATH.write_text(rendered, encoding="utf-8")
    print(f"short phrases: 600 -> {len(cleaned)}")


if __name__ == "__main__":
    main()
