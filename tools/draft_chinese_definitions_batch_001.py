"""Write the reviewed AI draft for Chinese-definition batch 001."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BATCH_DIR = ROOT / "data_sources/enrichment/chinese_definition_batches"
BATCH_PATH = BATCH_DIR / "batch_001.json"


# word: (selected OEWN sense IDs, [(display POS, original Chinese definition)], notes)
DRAFTS: dict[str, tuple[list[str], list[tuple[str, str]], list[str]]] = {
    "a": ([], [("article", "一（个、件等）；任一；每一")], ["按课标中的冠词用法补充；OEWN 候选仅有字母 A 的名词义，未采用。"]),
    "abandon": (["abandon%2:40:00::", "abandon%2:40:01::", "abandon%1:07:00::"], [("verb", "放弃；抛弃；遗弃"), ("noun", "放任；放纵")], []),
    "ability": (["ability%1:07:00::", "ability%1:09:00::"], [("noun", "能力；才能")], []),
    "able": (["able%3:00:00::", "able%5:00:00:competent:00"], [("adjective", "能够；有能力的；能干的")], []),
    "abnormal": (["abnormal%3:00:00::"], [("adjective", "不正常的；反常的")], []),
    "aboard": (["aboard%4:02:01::"], [("adverb", "在船、飞机、火车等交通工具上；上交通工具")], []),
    "about": (["about%4:02:00::", "about%4:02:06::", "about%4:02:01::"], [("preposition", "关于；围绕；在……附近"), ("adverb", "大约；到处；在附近")], ["补充中学阶段常用介词用法；OEWN 候选以副词义为主。"]),
    "above": (["above%5:00:00:preceding:00", "above%1:10:00::", "above%4:02:01::"], [("preposition", "在……上方；高于；超过"), ("adjective", "上面的；上述的"), ("adverb", "在上面；以上")], ["补充常用介词用法。"]),
    "abroad": (["abroad%5:00:00:foreign:02", "abroad%4:02:00::"], [("adverb", "在国外；到国外")], []),
    "absence": (["absence%1:26:00::", "absence%1:04:00::", "absence%1:28:00::"], [("noun", "缺席；不在；缺乏")], []),
    "absent": (["absent%3:00:00::", "absent%2:30:00::"], [("adjective", "缺席的；不在的；不存在的"), ("verb", "缺席；不参加")], []),
    "absolutely": (["absolutely%4:02:00::", "absolutely%4:02:01::"], [("adverb", "绝对地；完全地；当然")], []),
    "absorb": (["absorb%2:43:00::", "absorb%2:31:00::", "absorb%2:35:00::"], [("verb", "吸收；吸取；理解；使全神贯注")], []),
    "abstract": (["abstract%3:00:00::", "abstract%1:10:00::", "abstract%1:09:00::"], [("adjective", "抽象的；理论上的"), ("noun", "摘要；抽象概念")], []),
    "abuse": (["abuse%1:04:02::", "abuse%1:04:01::", "abuse%2:41:00::", "abuse%2:30:02::"], [("noun", "虐待；滥用；辱骂"), ("verb", "虐待；滥用；辱骂")], []),
    "academic": (["academic%3:01:00::", "academic%5:00:00:theoretical:01", "academic%1:18:00::"], [("adjective", "学术的；学校教育的；理论性的"), ("noun", "高校教师；学者")], []),
    "accent": (["accent%1:10:01::", "accent%1:10:00::", "accent%2:32:01::"], [("noun", "口音；重音；强调"), ("verb", "重读；强调")], []),
    "accept": (["accept%2:40:00::", "accept%2:32:00::", "accept%2:31:00::", "accept%2:40:03::"], [("verb", "接受；同意；承认；接纳")], []),
    "access": (["access%1:07:00::", "access%1:07:01::", "access%1:06:00::", "access%2:40:00::", "access%2:38:00::"], [("noun", "进入或使用的权利；通道；访问"), ("verb", "访问；获取；进入")], []),
    "accident": (["accident%1:11:01::", "accident%1:11:00::"], [("noun", "事故；意外事件；偶然")], []),
    "accommodation": (["accommodation%1:06:00::", "accommodation%1:11:00::", "accommodation%1:04:00::"], [("noun", "住处；住宿；适应；调节")], []),
    "accompany": (["accompany%2:38:00::", "accompany%2:42:00::", "accompany%2:36:00::"], [("verb", "陪同；伴随；为……伴奏")], []),
    "according to": ([], [("preposition", "根据；按照；据……所说")], ["课标原有多词表达；依据其通行语法功能编写，OEWN 无对应义项。"]),
    "account": (["account%1:26:00::", "account%1:10:00::", "account%1:10:04::"], [("noun", "账户；账目；叙述；解释"), ("verb", "认为；说明；占（一定比例）")], []),
    "accurate": (["accurate%3:00:00::", "accurate%5:00:00:correct:00"], [("adjective", "准确的；精确的")], []),
    "accuse": (["accuse%2:32:00::", "accuse%2:32:01::"], [("verb", "指控；控告；谴责")], []),
    "ache": (["ache%1:26:00::", "ache%2:39:00::", "ache%2:29:07::"], [("noun", "持续的隐痛"), ("verb", "疼痛；渴望")], []),
    "achieve": (["achieve%2:41:00::"], [("verb", "实现；达到；取得")], []),
    "achievement": (["achievement%1:04:00::"], [("noun", "成就；成绩；完成")], []),
    "acid": (["acid%5:00:00:acidic:00", "acid%1:27:00::"], [("noun", "酸"), ("adjective", "酸性的；尖刻的")], []),
    "acknowledge": (["acknowledge%2:32:00::", "acknowledge%2:32:01::", "acknowledge%2:32:04::"], [("verb", "承认；确认；答谢")], []),
    "acquire": (["acquire%2:40:00::", "acquire%2:31:00::", "acquire%2:30:05::"], [("verb", "获得；取得；学到")], []),
    "across": (["across%4:02:01::", "across%4:02:00::"], [("preposition", "横过；在……对面；遍及"), ("adverb", "从一边到另一边；在对面")], ["补充中学阶段常用介词用法。"]),
    "act": (["act%1:03:00::", "act%1:10:00::", "act%2:41:00::", "act%2:29:00::", "act%2:36:00::"], [("noun", "行为；行动；法案；（戏剧的）一幕"), ("verb", "行动；表现；扮演")], []),
    "action": (["action%1:04:02::", "action%1:26:00::", "action%1:10:00::"], [("noun", "行动；行为；作用；情节")], []),
    "active": (["active%3:00:03::", "active%5:00:00:involved:00", "active%3:00:01::", "active%5:00:00:existent:00"], [("adjective", "积极的；活跃的；主动的；在运行的")], []),
    "activity": (["activity%1:04:00::", "activity%1:26:00::"], [("noun", "活动；活跃状态")], []),
    "actor": (["actor%1:18:00::"], [("noun", "演员；行动者")], []),
    "actress": (["actress%1:18:00::"], [("noun", "女演员")], []),
    "actually": (["actually%4:02:01::", "actually%4:02:00::"], [("adverb", "实际上；事实上；的确")], []),
    "AD": (["ad%4:02:00::"], [("adverb", "公元（用于公元纪年）")], []),
    "adapt": (["adapt%2:30:01::", "adapt%2:30:02::"], [("verb", "使适应；适应；改编")], []),
    "adaptation": (["adaptation%1:10:00::", "adaptation%1:22:00::"], [("noun", "适应；改编；改编作品")], []),
    "add": (["add%2:30:00::", "add%2:32:01::", "add%2:31:00::"], [("verb", "添加；增加；补充说；相加")], []),
    "addict": (["addict%1:18:00::", "addict%1:18:01::", "addict%2:34:00::"], [("noun", "成瘾者；入迷的人"), ("verb", "使上瘾；使沉迷")], []),
    "addition": (["addition%1:04:02::", "addition%1:21:00::", "addition%1:04:01::"], [("noun", "增加；添加物；加法")], []),
    "address": (["address%1:15:00::", "address%1:10:00::", "address%1:10:02::"], [("noun", "地址；演说；称呼"), ("verb", "写地址；向……讲话；处理（问题）")], []),
    "adjust": (["adjust%2:30:00::", "adjust%2:30:01::"], [("verb", "调整；调节；适应")], []),
    "administration": (["administration%1:04:00::", "administration%1:14:00::", "administration%1:04:04::"], [("noun", "管理；行政；管理部门；政府")], []),
    "admire": (["admire%2:37:00::", "admire%2:39:00::"], [("verb", "钦佩；赞赏；欣赏")], []),
    "admit": (["admit%2:32:00::", "admit%2:41:01::", "admit%2:41:00::"], [("verb", "承认；准许进入；接纳")], []),
    "adopt": (["adopt%2:40:02::", "adopt%2:40:00::", "adopt%2:30:00::"], [("verb", "采用；采纳；收养")], []),
    "adorable": (["adorable%5:00:00:lovable:00"], [("adjective", "可爱的；讨人喜爱的")], []),
    "adult": (["adult%5:00:00:mature:01", "adult%1:18:00::"], [("noun", "成年人；成年动物"), ("adjective", "成年的；成人的")], []),
    "advance": (["advance%1:11:00::", "advance%1:11:01::", "advance%1:21:00::"], [("noun", "前进；进步；预付款"), ("verb", "前进；推进；促进"), ("adjective", "预先的；先行的")], []),
    "advantage": (["advantage%1:07:00::", "advantage%1:07:01::", "advantage%2:41:00::"], [("noun", "优势；有利条件；好处"), ("verb", "使处于有利地位")], []),
    "adventure": (["adventure%1:04:00::", "adventure%2:41:01::"], [("noun", "冒险；奇遇"), ("verb", "冒险")], []),
    "advertise": (["advertise%2:32:01::", "advertise%2:32:00::"], [("verb", "做广告；宣传；公布")], []),
    "advertisement": (["advertisement%1:10:00::"], [("noun", "广告；启事")], []),
    "advice": (["advice%1:10:00::"], [("noun", "建议；忠告")], []),
    "advise": (["advise%2:32:00::", "advise%2:32:01::", "advise%2:32:02::"], [("verb", "建议；劝告；通知")], []),
    "advocate": (["advocate%1:18:00::", "advocate%2:32:00::", "advocate%2:32:01::"], [("noun", "拥护者；倡导者"), ("verb", "提倡；主张；拥护")], []),
    "affair": (["affair%1:09:00::", "affair%1:11:00::"], [("noun", "事情；事务；事件；正式活动")], []),
    "affect": (["affect%2:30:00::", "affect%2:37:00::"], [("verb", "影响；使感动")], []),
    "afford": (["afford%2:34:00::", "afford%2:42:00::", "afford%2:40:00::"], [("verb", "买得起；承担得起；提供")], []),
    "afraid": (["afraid%3:00:00::", "afraid%5:00:02:concerned:00", "afraid%5:00:00:disinclined:00"], [("adjective", "害怕的；担心的；不愿意的")], []),
    "Africa": ([], [("proper_noun", "非洲")], ["通用地理专名；OEWN 无对应候选义项，未使用旧词表释义。"]),
    "African": (["african%3:01:00::", "african%1:18:00::"], [("adjective", "非洲的；非洲人的"), ("noun", "非洲人")], []),
    "after": (["after%4:02:01::", "after%4:02:00::"], [("preposition", "在……之后；在……后面"), ("conjunction", "在……以后"), ("adverb", "后来；以后"), ("adjective", "后来的")], ["补充中学阶段常用介词和连词用法。"]),
    "afternoon": (["afternoon%1:28:00::", "afternoon%1:10:00::"], [("noun", "下午；午后")], []),
    "afterward": (["afterward%4:02:00::"], [("adverb", "后来；以后")], []),
    "again": (["again%4:02:00::"], [("adverb", "再一次；又；重新")], []),
    "against": ([], [("preposition", "反对；倚靠；与……竞争；以……为背景；防备")], ["按课标中的常用介词用法补充；OEWN 无对应候选义项。"]),
    "age": (["age%1:07:00::", "age%1:28:00::", "age%1:28:02::", "age%2:30:00::"], [("noun", "年龄；时代；时期"), ("verb", "变老；使老化")], []),
    "agency": (["agency%1:14:00::", "agency%1:14:01::"], [("noun", "机构；代理处；政府部门")], []),
    "agenda": (["agenda%1:09:00::", "agenda%1:10:00::"], [("noun", "议程；待办事项")], []),
    "ago": (["ago%5:00:00:past:00", "ago%4:02:00::"], [("adverb", "以前；……之前")], []),
    "agree": (["agree%2:32:00::", "agree%2:32:01::", "agree%2:42:00::"], [("verb", "同意；赞成；一致；相符")], []),
    "agreement": (["agreement%1:10:01::", "agreement%1:26:01::", "agreement%1:09:00::"], [("noun", "协议；同意；一致")], []),
    "agriculture": (["agriculture%1:04:00::", "agriculture%1:04:01::"], [("noun", "农业；农学")], []),
    "ahead": (["ahead%4:02:00::", "ahead%4:02:06::", "ahead%4:02:02::", "ahead%5:00:00:up:00"], [("adverb", "在前面；向前；提前；领先"), ("adjective", "领先的")], []),
    "aid": (["aid%1:04:00::", "aid%1:21:00::", "aid%2:41:00::"], [("noun", "帮助；援助；辅助物"), ("verb", "帮助；援助")], []),
    "aim": (["aim%1:09:00::", "aim%1:09:01::", "aim%1:04:00::", "aim%2:33:00::", "aim%2:31:01::"], [("noun", "目标；目的；瞄准"), ("verb", "瞄准；旨在；力求")], []),
    "air": (["air%1:27:00::", "air%1:15:00::", "air%1:07:00::", "air%1:10:02::"], [("noun", "空气；空中；神态；广播"), ("verb", "播出；晾晒；表达")], []),
    "airline": (["airline%1:06:00::"], [("noun", "航空公司；航线")], []),
    "airport": (["airport%1:06:00::"], [("noun", "机场；航空站")], []),
    "alarm": (["alarm%1:12:00::", "alarm%1:06:00::", "alarm%1:10:00::", "alarm%2:37:00::", "alarm%2:32:00::"], [("noun", "惊恐；警报；闹钟"), ("verb", "使惊恐；向……报警")], []),
    "alcohol": (["alcohol%1:13:00::", "alcohol%1:27:00::"], [("noun", "酒精；含酒精饮料")], []),
    "alive": (["alive%3:00:01::", "alive%5:00:00:lively:00", "alive%5:00:00:aware:00"], [("adjective", "活着的；有活力的；意识到的")], []),
    "all": (["all%3:00:00::", "all%4:02:00::"], [("determiner", "所有的；全部的"), ("pronoun", "全部；所有人或事物"), ("adverb", "完全；全然")], ["将 OEWN 的量词形容词标签规范为中学语法中的限定词，并补充代词用法。"]),
    "allow": (["allow%2:41:00::", "allow%2:32:00::", "allow%2:42:00::"], [("verb", "允许；准许；使有可能；留出")], []),
    "almost": (["almost%4:02:00::"], [("adverb", "几乎；差不多")], []),
    "alone": (["alone%5:00:00:unaccompanied:00", "alone%5:00:00:exclusive:00", "alone%4:02:00::", "alone%4:02:01::"], [("adjective", "独自的；单独的"), ("adverb", "独自；仅仅")], []),
    "along": (["along%4:02:01::", "along%4:02:00::", "along%4:02:04::"], [("preposition", "沿着；顺着"), ("adverb", "向前；一起；沿着")], ["补充中学阶段常用介词用法。"]),
    "alongside": (["alongside%4:02:00::"], [("preposition", "在……旁边；与……一起"), ("adverb", "在旁边；并排地")], ["补充中学阶段常用介词用法。"]),
    "aloud": (["aloud%4:02:00::", "aloud%4:02:01::"], [("adverb", "出声地；大声地")], []),
    "already": (["already%4:02:00::"], [("adverb", "已经；早已")], []),
    "also": (["also%4:02:00::"], [("adverb", "也；而且；此外")], []),
    "alternative": (["alternative%5:00:00:secondary:01", "alternative%5:00:00:disjunctive:00", "alternative%1:09:00::"], [("noun", "可供选择的事物；替代方案"), ("adjective", "可替代的；供选择的；非传统的")], []),
    "although": ([], [("conjunction", "虽然；尽管；不过")], ["按课标中的连词用法补充；OEWN 无对应候选义项。"]),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    payload = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    records = payload["records"]
    words = [record["word"] for record in records]
    if set(words) != set(DRAFTS) or len(words) != len(DRAFTS):
        missing = sorted(set(words) - set(DRAFTS))
        extra = sorted(set(DRAFTS) - set(words))
        raise ValueError(f"draft key mismatch; missing={missing}, extra={extra}")

    for record in records:
        selected_ids, definitions, notes = DRAFTS[record["word"]]
        source_ids = {
            sense["sense_id"] for sense in record.get("candidate_senses", [])
        }
        unknown = set(selected_ids) - source_ids
        if unknown:
            raise ValueError(f"{record['word']}: unknown sense IDs {sorted(unknown)}")
        record["selected_source_sense_ids"] = selected_ids
        record["definitions_zh"] = [
            {"part_of_speech": pos, "definition": definition}
            for pos, definition in definitions
        ]
        record["display_parts_of_speech"] = list(
            dict.fromkeys(pos for pos, _ in definitions)
        )
        record["definition_status"] = "ai_draft_complete"
        record["qa_status"] = "not_checked"
        record["qa_notes"] = notes

    BATCH_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    manifest_path = BATCH_DIR / "batch_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for batch in manifest["batches"]:
        if batch["file"] == BATCH_PATH.name:
            batch["sha256"] = sha256(BATCH_PATH)
            break
    manifest["pending_ai_draft_count"] = 3700
    manifest["ai_draft_complete_count"] = 100
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    checksum_targets = sorted(BATCH_DIR.glob("batch_*.json")) + [
        BATCH_DIR / "README.md"
    ]
    (BATCH_DIR / "SHA256SUMS.txt").write_text(
        "\n".join(f"{sha256(path)}  {path.name}" for path in checksum_targets)
        + "\n",
        encoding="ascii",
    )
    print("drafted batch 001: 100 records")


if __name__ == "__main__":
    main()
