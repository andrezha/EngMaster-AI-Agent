import json
import re
from pathlib import Path


VOCAB_PATH = Path(__file__).parent / "assets" / "vocabulary.json"


def load_vocab():
    return json.loads(VOCAB_PATH.read_text(encoding="utf-8"))


def test_vocabulary_schema_and_pronunciation_fields_are_complete():
    rows = load_vocab()
    assert len(rows) == 3875
    assert all(set(row) == {"word", "content"} for row in rows)
    assert all(row["word"].strip() and row["content"].strip() for row in rows)
    assert all(re.search(r"\[[^\]]+\]", row["content"]) for row in rows)
    assert all(row["content"].count("[") == row["content"].count("]") for row in rows)


def test_headwords_do_not_contain_scraped_pronunciation_or_footnote_fragments():
    rows = load_vocab()
    assert not [
        row["word"]
        for row in rows
        if re.search(r"[/\[*]$", row["word"])
        or re.search(r"\([^)]*,[^)]*\)", row["word"])
        or re.search(r"（.*(?:比较级|最高级|复).*）", row["word"])
    ]


def test_headwords_do_not_contain_double_hyphens():
    rows = load_vocab()
    assert not [row["word"] for row in rows if "--" in row["word"]]

    expected = {
        "best-seller",
        "boat race",
        "bodybuilding",
        "cold-blooded",
        "easy-going",
        "get-together",
        "ice cream",
    }
    words = [row["word"] for row in rows]
    assert all(words.count(word) == 1 for word in expected)


def test_known_high_risk_alignment_repairs_remain_correct():
    by_word = {}
    for row in load_vocab():
        by_word.setdefault(row["word"], []).append(row["content"])

    expected = {
        "cloud": "[klaʊd]",
        "forget": "[fəˈɡet]",
        "performance": "[pəˈfɔːməns]",
        "pig": "[pɪɡ]",
        "power": "[ˈpaʊə(r)]",
        "sight": "[saɪt]",
        "south": "[saʊθ]",
        "with": "[wɪð, wɪθ]",
        "writing": "[ˈraɪtɪŋ]",
        "yourselves": "[jɔːˈselvz; (US) jʊrˈselvz]",
    }
    for word, ipa in expected.items():
        assert any(content.startswith(ipa) for content in by_word[word])

    assert by_word["perform"] == ["[pəˈfɔːm] v. 表演；履行；执行；表现"]
    assert by_word["performance"] == ["[pəˈfɔːməns] n. 表演；演出；表现；性能"]
    assert by_word["performer"] == ["[pəˈfɔːmə(r)] n. 表演者；演奏者"]

    assert by_word["diverse"] == ["[daɪˈvɜːs] a. 不同的；多种多样的；形形色色的"]
    assert by_word["fighter"] == ["[ˈfaɪtə(r)] n. 战士；斗士"]
    assert by_word["vain"] == ["[veɪn] a. 自负的；自视过高的；徒劳的；无效的"]
    assert by_word["statue"] == ["[ˈstætjuː] n. 雕像；塑像"]


def test_heteronyms_include_pronunciations_for_each_listed_part_of_speech():
    rows = load_vocab()
    by_word = {row["word"]: row["content"] for row in rows}
    for word in ("desert", "lead", "live", "present", "row", "subject", "tear", "use"):
        assert ";" in by_word[word], f"{word} lost one of its distinct pronunciations"
