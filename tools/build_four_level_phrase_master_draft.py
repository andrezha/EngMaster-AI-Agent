"""Create an AI-screened English master-table draft from the unified pool.

This is an editorial screening pass, not a claim of human/expert review.  It
keeps the decision rules and evidence on every selected row so later passes can
replace individual decisions without changing IDs or copying an outside list.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data_sources/processed/phrase_candidates/four_level/candidate_pool.csv"
OUTPUT_DIR = ROOT / "data_sources/clean/phrase_master_draft"
LEVELS = ("junior", "senior_high", "cet4", "cet6")
RANK = {level: index for index, level in enumerate(LEVELS)}
TARGETS = {"junior": 250, "senior_high": 200, "cet4": 300, "cet6": 300}

NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "first", "second", "third", "fourth", "fifth",
}

SENSITIVE_OR_NARROW = {
    "fuck", "rape", "sexual", "intercourse", "suicide", "porn", "naked",
    "cancer", "diabetes", "syndrome", "surgery", "tumor", "tumour",
    "rifle", "pistol", "bomb", "missile", "artillery", "warhead",
}

NARROW_INSTITUTIONAL = {
    "secretary", "minister", "attorney", "governor", "monarchy", "regiment",
    "parliament", "congress", "tribunal", "lieutenant", "syndicate",
}

ANIMAL_OR_TAXONOMIC = {
    "beetle", "owl", "buffalo", "turtle", "crab", "hawk", "penguin",
    "butterfly", "salmon", "shark", "whale", "dolphin", "panda",
}

FRAGMENT_START = {"the", "this", "that", "some", "any", "every"}
FRAGMENT_END = {"it", "this", "that", "me", "him", "her", "them"}

NUMBER_WHITELIST = {
    "at first", "first aid", "first of all", "in the first place", "one another",
    "one by one", "on the one hand", "at one time", "at the same time",
    "from time to time", "first class", "second hand", "first name",
}

EDITORIAL_LEVEL_OVERRIDES = {
    "at first": "junior",
    "one another": "junior",
    "first of all": "junior",
    "one by one": "junior",
    "first name": "junior",
    "first aid": "junior",
    "at one time": "senior_high",
    "in the first place": "senior_high",
    "on the one hand": "senior_high",
    "second hand": "senior_high",
}


def tokens(phrase: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", phrase.casefold())


def phrase_type(pos_value: str) -> str:
    pos = set(pos_value.split("|"))
    if "v" in pos:
        return "verb_expression"
    if "r" in pos:
        return "adverbial_or_connector"
    if "a" in pos:
        return "adjective_expression"
    if "n" in pos:
        return "lexical_collocation"
    return "fixed_expression"


def exclusion_reason(row: dict[str, str]) -> str:
    phrase = row["phrase"]
    word_list = tokens(phrase)
    word_set = set(word_list)
    if "-" in phrase:
        return "hyphenated compound rather than target phrase"
    if word_set & SENSITIVE_OR_NARROW:
        return "sensitive or overly narrow topic"
    if word_set & NARROW_INSTITUTIONAL:
        return "narrow institutional title or expression"
    if word_set & ANIMAL_OR_TAXONOMIC:
        return "taxonomic or narrow animal term"
    if word_set & NUMBER_WORDS and phrase not in NUMBER_WHITELIST:
        return "mechanical number expression"
    if word_list[0] in FRAGMENT_START or word_list[-1] in FRAGMENT_END:
        return "context-dependent fragment"
    if word_list[0] == "to" and phrase not in {"to date", "to boot", "to some extent"}:
        return "infinitive fragment rather than stable phrase"
    if phrase in {
        "would be", "be given", "have not", "do it", "get it", "buy it",
        "in this", "in that", "on that", "on it", "to it", "out to", "out in",
        "and how", "and so", "much as", "some other", "the true", "do all",
        "have the best", "know nothing", "poor people", "rich people", "bad person",
        "good guy", "bad guy", "old man", "young man", "little man",
    }:
        return "free combination or incomplete expression"
    return ""


def editorial_score(row: dict[str, str]) -> float:
    count = int(row["tatoeba_cc0_sentence_count"])
    pos = set(row["oewn_pos"].split("|"))
    score = math.log2(count + 1) * 10
    if "v" in pos:
        score += 22
    if "r" in pos:
        score += 16
    if "a" in pos:
        score += 5
    if row["moby_match"] == "true":
        score += 5
    if not count:
        score -= 10
    if pos == {"n"}:
        score -= 5
    if len(tokens(row["phrase"])) > 3:
        score -= 3
    return score


def stage_for(row: dict[str, str]) -> str:
    return EDITORIAL_LEVEL_OVERRIDES.get(row["phrase"], row["minimum_lexical_level"])


def included_in(level: str) -> str:
    return "|".join(LEVELS[RANK[level] :])


def main() -> int:
    with POOL.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))

    eligible: dict[str, list[dict[str, str]]] = defaultdict(list)
    excluded = Counter()
    for row in source_rows:
        reason = exclusion_reason(row)
        if reason:
            excluded[reason] += 1
            continue
        row = dict(row)
        row["editorial_level"] = stage_for(row)
        row["editorial_score"] = str(round(editorial_score(row), 3))
        eligible[row["editorial_level"]].append(row)

    selected: list[dict[str, object]] = []
    selected_phrases: set[str] = set()
    for level in LEVELS:
        candidates = sorted(
            eligible[level],
            key=lambda row: (-float(row["editorial_score"]), row["phrase"]),
        )
        # Keep lexical collocations useful, but prevent them from overwhelming
        # teachable verb expressions and connectors.
        type_limits = {
            "junior": {"lexical_collocation": 65},
            "senior_high": {"lexical_collocation": 65},
            "cet4": {"lexical_collocation": 120},
            "cet6": {"lexical_collocation": 135},
        }[level]
        type_counts: Counter[str] = Counter()
        for row in candidates:
            if len([item for item in selected if item["introduced_level"] == level]) >= TARGETS[level]:
                break
            if row["phrase"] in selected_phrases:
                continue
            item_type = phrase_type(row["oewn_pos"])
            limit = type_limits.get(item_type)
            if limit is not None and type_counts[item_type] >= limit:
                continue
            type_counts[item_type] += 1
            selected_phrases.add(row["phrase"])
            selected.append(
                {
                    "record_id": "",
                    "phrase": row["phrase"],
                    "normalized_phrase": row["normalized_phrase"],
                    "introduced_level": level,
                    "included_in": included_in(level),
                    "phrase_type": item_type,
                    "minimum_lexical_level": row["minimum_lexical_level"],
                    "level_decision_method": (
                        "explicit_editorial_override"
                        if row["phrase"] in EDITORIAL_LEVEL_OVERRIDES
                        else "minimum_lexical_level_plus_editorial_screen"
                    ),
                    "oewn_match": row["oewn_match"],
                    "oewn_pos": row["oewn_pos"],
                    "oewn_sense_ids": row["oewn_sense_ids"],
                    "moby_match": row["moby_match"],
                    "tatoeba_cc0_sentence_count": row["tatoeba_cc0_sentence_count"],
                    "selection_reason": "stable-form evidence; stage-compatible components; retained after automated editorial exclusions",
                    "qa_status": "english_scope_draft_ai_screened",
                    "human_review_claimed": "false",
                }
            )

    sequence_by_level = Counter()
    for row in selected:
        level = str(row["introduced_level"])
        sequence_by_level[level] += 1
        prefix = {"junior": "J", "senior_high": "H", "cet4": "C4", "cet6": "C6"}[level]
        row["record_id"] = f"PH-{prefix}-{sequence_by_level[level]:04d}"

    counts = Counter(str(row["introduced_level"]) for row in selected)
    errors = []
    if dict(counts) != TARGETS:
        errors.append(f"target mismatch: {dict(counts)} != {TARGETS}")
    if len(selected_phrases) != len(selected):
        errors.append("duplicate normalized phrase")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "phrase_master_english_draft.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(selected)
    json_path = OUTPUT_DIR / "phrase_master_english_draft.json"
    json_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "record_count": len(selected),
        "introduced_level_counts": dict(counts),
        "unique_phrase_count": len(selected_phrases),
        "excluded_reason_counts": dict(excluded),
        "old_phrase_file_read": False,
        "chinese_content_created": False,
        "human_review_claimed": False,
        "release_ready": False,
        "next_required_step": "AI-assisted row-level tail review and replacement before freezing English scope",
    }
    (OUTPUT_DIR / "automated_screening_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
