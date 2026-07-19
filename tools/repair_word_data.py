"""Repair confirmed corruption in the bundled vocabulary data.

This is intentionally an explicit, auditable migration.  Every index-based edit
checks the old headword first so the script cannot silently change a different
entry if the source list is reordered later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VOCAB_PATH = ROOT / "assets" / "vocabulary.json"
IRREGULAR_PATH = ROOT / "assets" / "irregular_verbs.json"


def replace_ipa(content: str, ipa: str) -> str:
    """Replace the first bracketed pronunciation and keep the definition."""
    content = content.replace("\u00a0", " ").strip()
    content = re.sub(r"^\s*\[[^\]]*\]\s*", "", content, count=1)
    return f"[{ipa}] {content}".strip()


def update_entry(rows: list[dict[str, str]], number: int, old_word: str, *,
                 word: str | None = None, ipa: str | None = None,
                 content: str | None = None) -> None:
    row = rows[number - 1]
    if row["word"] != old_word:
        raise RuntimeError(
            f"entry {number}: expected {old_word!r}, found {row['word']!r}"
        )
    if word is not None:
        row["word"] = word
    if content is not None:
        row["content"] = content
    if ipa is not None:
        row["content"] = replace_ipa(row["content"], ipa)


def repair_vocabulary() -> list[str]:
    rows = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    if len(rows) != 3875:
        raise RuntimeError(f"expected 3875 vocabulary entries, found {len(rows)}")

    changes: list[str] = []

    # Headwords damaged by OCR/scraping, plus their conventional learner IPA.
    spelling_repairs = {
        94: ("afte", "after", "ˈɑːftə(r)"),
        167: ("acchor", "anchor", "ˈæŋkə(r)"),
        195: ("anywa", "anyway", "ˈenɪweɪ"),
        588: ("cance", "cancer", "ˈkænsə(r)"),
        615: ("cassettle", "cassette", "kəˈset"),
        780: ("commericial", "commercial", "kəˈmɜːʃ(ə)l"),
        1197: ("energ", "energy", "ˈenədʒɪ"),
        1326: ("federa", "federal", "ˈfedərəl"),
        1862: ("kilometr", "kilometre", "ˈkɪləmiːtə(r)"),
        2474: ("pinkpɔɡ", "pink", "pɪŋk"),
        2537: ("possiblyv", "possibly", "ˈpɒsəblɪ"),
        3021: ("shyv", "shy", "ʃaɪ"),
        3025: ("sideroad", "sidewalk", "ˈsaɪdwɔːk"),
        3026: ("sideway", "side road", "ˈsaɪd rəʊd"),
        3155: ("spaghettiv", "spaghetti", "spəˈɡetɪ"),
        3344: ("tabletˈtenɪs", "tablet", "ˈtæblət"),
        3365: ("taxipayer", "taxpayer", "ˈtækspeɪə(r)"),
        3455: ("Tibeta", "Tibetan", "tɪˈbet(ə)n"),
        3470: ("tiresomev", "tiresome", "ˈtaɪəsəm"),
        3540: ("troopv", "troop", "truːp"),
        3638: ("usedv", "used", "juːzd"),
        3718: ("war", "warn", "wɔːn"),
        3817: ("woo", "wool", "wʊl"),
    }
    for number, (old, new, ipa) in spelling_repairs.items():
        update_entry(rows, number, old, word=new, ipa=ipa)
        # Remove isolated letters left behind when the scraper split a word/POS.
        rows[number - 1]["content"] = re.sub(
            r"^\[[^\]]+\]\s*[a-z]\s+(?=(?:n|v|a|ad|prep|conj)\.)",
            lambda m: re.sub(r"\]\s*[a-z]\s+", "] ", m.group(0)),
            rows[number - 1]["content"],
        )
        changes.append(f"#{number} {old} -> {new}")

    # Common words accidentally capitalized in the source. Proper nouns and
    # abbreviations deliberately retain their capitals.
    for number, old, new in [
        (314, "Baby", "baby"), (675, "Cheer", "cheer"),
        (1134, "Dynamic", "dynamic"), (1135, "Dynasty", "dynasty"),
        (1759, "Indicate", "indicate"), (2138, "Mosquito", "mosquito"),
        (2909, "Scratch[", "scratch"),
    ]:
        if number == 2909:
            update_entry(rows, number, old, word=new,
                         content="[skrætʃ] v./n. 划破；划痕；划伤")
        else:
            update_entry(rows, number, old, word=new)
        changes.append(f"#{number} {old} -> {new}")

    # Phrases split between `word` and `content`. Keeping the complete phrase in
    # `word` also makes search and answer checking operate on the real headword.
    phrase_repairs = {
        32: ("according", "according to"),
        185: ("the", "the Antarctic"), 229: ("the", "the Arctic"),
        230: ("the", "the Arctic Ocean"), 278: ("the", "the Atlantic Ocean"),
        342: ("bank", "bank account"), 475: ("telephone", "telephone booth"),
        523: ("the", "the British"), 553: ("bus", "bus stop"),
        601: ("card", "card games"), 650: ("chain", "chain store(s)"),
        675: ("cheer", "cheer up"), 705: ("Christmas", "Christmas card"),
        706: ("Christmas", "Christmas tree"), 707: ("Christmas", "Christmas Eve"),
        806: ("computer", "computer game"), 1372: ("fitting", "fitting room"),
        1467: ("fruit", "fruit juice"), 1661: ("hide", "hide-and-seek"),
        1685: ("Hong", "Hong Kong"), 1698: ("hot", "hot dog"),
        1710: ("human", "human being"), 1764: ("information", "information desk"),
        1847: ("junk", "junk mail"), 1848: ("junk", "junk food"),
        2013: ("table", "table manners"), 2017: ("maple", "maple leaves"),
        2049: ("gold", "gold medal"), 2085: ("Middle", "Middle East"),
        2116: ("mobile", "mobile phone"), 2131: ("moon", "moon cake"),
        2208: ("New", "New York"), 2209: ("New", "New Zealand"),
        2210: ("New", "New Zealander"), 2289: ("Olympic", "Olympic Games"),
        2302: ("opera", "opera house"), 2358: ("the", "the Pacific Ocean"),
        2584: ("primary", "primary school"), 2687: ("raw", "raw material"),
        2713: ("record", "record holder"), 2932: ("melon", "melon seed"),
        2985: ("pencil-", "pencil sharpener"), 3002: ("shop", "shop assistant"),
        3010: ("short", "short wave"), 3100: ("snack", "snack bar"),
        3123: ("soft", "soft drink"), 3198: ("stainless", "stainless steel"),
        3330: ("swimming", "swimming pool"), 3343: ("table", "table tennis"),
        3356: ("tape", "tape recorder"), 3515: ("traffic", "traffic lights"),
    }
    for number, (old, new) in phrase_repairs.items():
        row = rows[number - 1]
        if row["word"] != old:
            raise RuntimeError(f"entry {number}: expected {old!r}, found {row['word']!r}")
        content = row["content"].replace("\u00a0", " ")
        bracket = content.find("[")
        if bracket >= 0:
            content = content[bracket:]
        row["word"] = new
        row["content"] = content.strip()
        changes.append(f"#{number} phrase -> {new}")

    # Confirmed copied/shifted pronunciations. These are deliberately explicit;
    # similar-looking but valid regional variants are not rewritten.
    ipa_repairs = {
        303: "əˈveɪləb(ə)l", 845: "kənˈsjuːm", 1101: "ˈdʌz(ə)n",
        1379: "ˈflæʃlaɪt", 1394: "flaɪ", 1404: "fuːd", 1436: "fɔːθ",
        1684: "ˈhʌnɪ", 1877: "læb", 2065: "ˈmenjuː", 2384: "pɑːk",
        2429: "ˈpɜːfɪkt", 2443: "pəˈsweɪd", 2458: "ˈpɪənɪst",
        2464: "piːs", 2466: "paɪl", 2473: "ˈpɪŋ pɒŋ",
        2496: "ˈpleʒə(r)", 2497: "ˈplentɪ", 2512: "ˈpɒləsɪ",
        2533: "pəˈzes", 2549: "paʊnd", 2573: "prɪˈzɜːv",
        2575: "pres", 2577: "prɪˈtend", 2693: "ˈriːdɪŋ",
        2782: "rɪˈspɒnd", 3012: "ʃʊd", 3014: "ʃaʊt", 3024: "saɪd",
        3034: "sɪɡˈnɪfɪkəns", 3048: "ˈsɪŋə(r)", 3060: "ˌsɪksˈtiːn",
        3062: "saɪz", 3063: "skeɪt", 3066: "skɪl", 3067: "skɪld",
        3080: "ˈsliːpɪ", 3082: "slaɪs", 3087: "sləʊ", 3093: "smɒɡ",
        3094: "sməʊk", 3098: "smuːð", 3102: "snætʃ",
        3103: "ˈsniːkə(r)", 3104: "sniːz", 3112: "sɒb",
        3120: "ˈsəʊfə", 3122: "ˈsɒftweə(r)", 3134: "ˈsʌmweə(r)",
        3136: "sɒŋ", 3137: "suːn", 3160: "spiːk", 3168: "spel",
        3170: "spend", 3332: "swɪs", 3339: "ˈsɪmptəm",
        3367: "tiːtʃ", 3380: "ˈtelɪfəʊn", 3382: "ˈtelɪskəʊp",
        3383: "ˈtelɪvɪʒ(ə)n", 3396: "ˈtentətɪv", 3398: "ˈtɜːmɪn(ə)l",
        3419: "ˈθɪərɪ", 3423: "ðiːz", 3432: "θɜːst", 3458: "ˈtaɪdɪ",
        3472: "ˈtaɪt(ə)l", 3475: "təˈbækəʊ", 3476: "təˈdeɪ",
        3477: "təˈɡeðə(r)", 3484: "tʌn", 3487: "tuː", 3495: "ˈtɔːtəs",
        3499: "tʌf", 3551: "traɪ", 3568: "twɪn", 3581: "ʌnˈeɪb(ə)l",
        3584: "ʌnˈsɜːt(ə)n", 3602: "ʌnˈfɔːtʃənət", 3604: "ʌnˈhæpɪ",
        3615: "ˌʌnˈnəʊn", 3675: "ˈvɪnɪɡə(r)", 3684: "ˈvɪzɪt",
        3692: "ˈvɒlɪbɔːl", 3697: "wæɡ", 3720: "wɒʃ",
        3739: "ˈweðə(r)", 3774: "ˈwɪs(ə)l", 3781: "waɪd",
        3815: "wʊd", 3824: "ˈwɜːkmeɪt", 3831: "wɔːn",
        3839: "ˈwɜːðɪ", 3861: "jɔː(r)", 3873: "zəʊn",
    }
    for number, ipa in ipa_repairs.items():
        replace = rows[number - 1]["word"]
        update_entry(rows, number, replace, ipa=ipa)
        changes.append(f"#{number} {replace}: IPA corrected")

    # Pronunciations accidentally stored in `word` instead of `content`.
    for number, row in enumerate(rows, 1):
        match = re.fullmatch(r"(.+?)\[([^\]]+)\]", row["word"].strip())
        if not match:
            continue
        headword, ipa = match.groups()
        row["word"] = headword.strip()
        if not row["content"].lstrip().startswith("["):
            row["content"] = f"[{ipa.strip()}] {row['content'].strip()}"
        changes.append(f"#{number} {headword}: pronunciation moved to content")

    # A few definition/POS rows were copied from an adjacent entry.
    definition_repairs = {
        8: "[əˈbɔːʃ(ə)n] n. 人工流产；堕胎",
        36: "[ˈækjʊrəsɪ] n. 准确；精确",
        37: "[əˈkjuːz] v. 指控，控告；谴责",
        102: "[ˈeɪdʒənt] n. 代理人；经纪人",
        103: "[əˈɡreʃ(ə)n] n. 侵略；侵犯",
        2698: "[ˈrɪəlɪ] ad. 真正地；到底；确实",
        3455: "[tɪˈbet(ə)n] n. 西藏人；西藏语 a. 西藏的；西藏人的",
        3718: "[wɔːn] vt. 警告；预先通知",
        3817: "[wʊl] n. 羊毛；羊绒",
        3730: "[ˈweɪsaɪd] a. 路边的",
    }
    for number, content in definition_repairs.items():
        rows[number - 1]["content"] = content
        changes.append(f"#{number} definition corrected")

    # Remaining malformed brackets and partial headwords that cannot be handled
    # safely by the general "IPA embedded in word" rule above.
    structural_repairs = {
        1124: ("due", "[djuː; (US) duː] a. 预期的；约定的"),
        1182: ("e-mail", "[ˈiːmeɪl] n. 电子邮件"),
        1281: ("extraordinary", "[ɪkˈstrɔːdɪn(ə)rɪ] a. 离奇的；使人惊奇的"),
        1372: ("fitting room", "[ˈfɪtɪŋ ruːm] 试衣间"),
        2276: ("offence", "[əˈfens] n. 违法行为；犯罪"),
        2277: ("offer", "[ˈɒfə(r)] n.& vt. 提供；建议"),
        2279: ("officer", "[ˈɒfɪsə(r)] n. 军官；公务员；官员；警察，警官"),
        2394: ("party", "[ˈpɑːtɪ] n. 聚会，晚会；党派"),
        2509: ("the North (South) Pole", "[ðə nɔːθ (saʊθ) pəʊl] （地球的）北（南）极，极地"),
        3036: ("silent", "[ˈsaɪlənt] a. 无声的，无对话的"),
        3121: ("soft", "[sɒft] a. 软的，柔和的"),
        3140: ("sort", "[sɔːt] vt. 把…分类，拣选 n. 种类，类别"),
        3147: ("southeast", "[ˌsaʊθˈiːst] n. 东南"),
        3565: ("twenty-first", "[ˌtwentɪ ˈfɜːst] num. 第二十一"),
        3740: ("weatherman", "[ˈweðəmæn] n. 气象员；天气预报员"),
    }
    for number, (word, content) in structural_repairs.items():
        rows[number - 1].update(word=word, content=content)
        changes.append(f"#{number} malformed structure corrected")

    VOCAB_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return changes


def repair_irregular_verbs() -> list[str]:
    rows = json.loads(IRREGULAR_PATH.read_text(encoding="utf-8"))
    repairs = {
        "was,": ("be", "was, were", "been", "是；成为"),
        "burned": ("burn", "burned, burnt", "burned, burnt", "燃烧；烧伤"),
        "dreamed": ("dream", "dreamed, dreamt", "dreamed, dreamt", "做梦；梦想"),
        ",hanged": ("hang", "hung, hanged", "hung, hanged", "悬挂；绞死"),
        "has": ("have", "had", "had", "有"),
        "learned": ("learn", "learned, learnt", "learned, learnt", "学习"),
        "lighted": ("light", "lit, lighted", "lit, lighted", "点燃；照亮"),
        "ridded": ("rid", "rid, ridded", "rid, ridded", "使摆脱"),
        "shined": ("shine", "shone, shined", "shone, shined", "发光；擦亮"),
        "showed": ("show", "showed", "shown, showed", "显示；展示"),
        "sunk": ("sink", "sank, sunk", "sunk", "下沉"),
        "smelled": ("smell", "smelled, smelt", "smelled, smelt", "闻；有气味"),
        "sowed": ("sow", "sowed", "sown, sowed", "播种"),
        "spelled": ("spell", "spelled, spelt", "spelled, spelt", "拼写"),
        "struck": ("strike", "struck", "struck, stricken", "打；撞击"),
    }
    changes: list[str] = []
    for row in rows:
        old = row["infinitive"]
        if old in repairs:
            infinitive, past, participle, meaning = repairs[old]
            row.update(infinitive=infinitive, past_tense=past,
                       past_participle=participle, meaning=meaning)
            changes.append(f"{old} -> {infinitive}")

    meanings = {
        "blow": "吹；刮风；打击",
        "lay": "放置；产卵",
        "lie": "躺；位于",
        "misread": "误读；读错",
        "mistake": "弄错；误解",
    }
    for row in rows:
        if row["infinitive"] in meanings:
            row["meaning"] = meanings[row["infinitive"]]
            changes.append(f"{row['infinitive']}: meaning corrected")

    IRREGULAR_PATH.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return changes


if __name__ == "__main__":
    vocab_changes = repair_vocabulary()
    irregular_changes = repair_irregular_verbs()
    print(f"vocabulary changes: {len(vocab_changes)}")
    print(f"irregular verb changes: {len(irregular_changes)}")
