"""Build an evidence-backed junior phrase candidate pool from approved sources.

The historical product phrase JSON is intentionally not a parameter or input.
This script creates an English-only review queue; it does not select the final
250 records and does not create Chinese definitions or examples.
"""

from __future__ import annotations

import bz2
import csv
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "data_sources/processed/phrase_stage_boundaries/phrase_stage_vocabulary_tokens.csv"
OEWN = ROOT / "data_sources/raw/oewn/english-wordnet-2025-json.zip"
MOBY = ROOT / "data_sources/raw/moby/common.txt"
TATOEBA_DIR = ROOT / "data_sources/raw/tatoeba"
OUTPUT_DIR = ROOT / "data_sources/processed/phrase_candidates/junior"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def words(value: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", value.casefold())


def normalized_phrase(value: str) -> str:
    return " ".join(words(value))


def load_junior_boundary() -> set[str]:
    with BOUNDARY.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        return {row["token"] for row in rows if row["earliest_level"] == "junior"}


def eligible_form(value: str, junior: set[str]) -> bool:
    tokens = words(value)
    return (
        value == value.lower()
        and 2 <= len(tokens) <= 5
        and all(token in junior for token in tokens)
        and re.fullmatch(r"[A-Za-z][A-Za-z '\-]*[A-Za-z]", value) is not None
    )


def load_oewn(junior: set[str]) -> dict[str, dict[str, set[str]]]:
    output: dict[str, dict[str, set[str]]] = {}
    with ZipFile(OEWN) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("entries-") and name.endswith(".json")
        )
        for name in names:
            for lemma, pos_map in json.loads(archive.read(name)).items():
                if not eligible_form(lemma, junior):
                    continue
                key = normalized_phrase(lemma)
                item = output.setdefault(key, {"forms": set(), "pos": set(), "senses": set()})
                item["forms"].add(lemma)
                item["pos"].update(pos_map)
                for pos_data in pos_map.values():
                    for sense in pos_data.get("sense", []):
                        sense_id = sense.get("id")
                        if sense_id:
                            item["senses"].add(sense_id)
    return output


def load_moby(junior: set[str]) -> dict[str, set[str]]:
    output: dict[str, set[str]] = {}
    with MOBY.open(encoding="latin-1") as stream:
        for raw in stream:
            form = raw.strip()
            if eligible_form(form, junior):
                output.setdefault(normalized_phrase(form), set()).add(form)
    return output


def tatoeba_counts(candidates: set[str]) -> Counter[str]:
    by_length: dict[int, set[tuple[str, ...]]] = {size: set() for size in range(2, 6)}
    phrase_by_ngram: dict[tuple[str, ...], list[str]] = {}
    for phrase in candidates:
        token_tuple = tuple(words(phrase))
        by_length[len(token_tuple)].add(token_tuple)
        phrase_by_ngram.setdefault(token_tuple, []).append(phrase)

    files = sorted(TATOEBA_DIR.glob("*.tsv.bz2"))
    if len(files) != 1:
        raise RuntimeError(f"Expected one Tatoeba CC0 archive, found {len(files)}")

    counts: Counter[str] = Counter()
    with bz2.open(files[0], "rt", encoding="utf-8") as stream:
        for raw in stream:
            columns = raw.rstrip("\n").split("\t")
            if len(columns) < 3:
                continue
            sentence_tokens = words(columns[2])
            matched: set[str] = set()
            for size, allowed in by_length.items():
                for index in range(len(sentence_tokens) - size + 1):
                    ngram = tuple(sentence_tokens[index : index + size])
                    if ngram in allowed:
                        matched.update(phrase_by_ngram[ngram])
            counts.update(matched)
    return counts


def priority_score(pos: set[str], in_moby: bool, occurrences: int, phrase: str) -> float:
    score = math.log2(occurrences + 1) * 10
    if "v" in pos:
        score += 10
    if "r" in pos:
        score += 5
    if in_moby:
        score += 4
    if "-" in phrase:
        score -= 8
    score -= max(0, len(words(phrase)) - 3) * 2
    return round(score, 3)


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    junior = load_junior_boundary()
    oewn = load_oewn(junior)
    moby = load_moby(junior)
    candidates = set(oewn) | set(moby)
    occurrences = tatoeba_counts(candidates)

    rows: list[dict[str, object]] = []
    for phrase in candidates:
        oewn_item = oewn.get(phrase, {"forms": set(), "pos": set(), "senses": set()})
        count = occurrences[phrase]
        in_oewn = phrase in oewn
        in_moby = phrase in moby
        if not in_oewn and not (in_moby and count > 0):
            continue
        if in_oewn and count > 0:
            status = "evidence_ready_review"
        elif in_moby and count > 0:
            status = "moby_corpus_review"
        else:
            status = "dictionary_only_hold"
        rows.append(
            {
                "phrase": phrase,
                "normalized_phrase": phrase,
                "word_count": len(words(phrase)),
                "oewn_match": str(in_oewn).lower(),
                "oewn_pos": "|".join(sorted(oewn_item["pos"])),
                "oewn_sense_ids": "|".join(sorted(oewn_item["senses"])),
                "oewn_forms": "|".join(sorted(oewn_item["forms"])),
                "moby_match": str(in_moby).lower(),
                "moby_forms": "|".join(sorted(moby.get(phrase, set()))),
                "tatoeba_cc0_sentence_count": count,
                "all_components_in_junior_boundary": "true",
                "candidate_status": status,
                "priority_score": priority_score(oewn_item["pos"], in_moby, count, phrase),
                "introduced_level_candidate": "junior",
                "human_review_claimed": "false",
            }
        )

    rows.sort(key=lambda row: (-float(row["priority_score"]), str(row["phrase"])))
    review = [row for row in rows if row["candidate_status"] != "dictionary_only_hold"][:600]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pool_path = OUTPUT_DIR / "candidate_pool.csv"
    review_path = OUTPUT_DIR / "priority_review_600.csv"
    write_csv(rows, pool_path)
    write_csv(review, review_path)

    status_counts = Counter(str(row["candidate_status"]) for row in rows)
    report = {
        "junior_boundary_token_count": len(junior),
        "oewn_eligible_multiword_count": len(oewn),
        "moby_eligible_multiword_count": len(moby),
        "candidate_pool_count": len(rows),
        "status_counts": dict(status_counts),
        "priority_review_count": len(review),
        "old_phrase_file_read": False,
        "chinese_content_created": False,
        "final_selection_claimed": False,
        "source_sha256": {
            "stage_boundary": sha256_file(BOUNDARY),
            "oewn": sha256_file(OEWN),
            "moby": sha256_file(MOBY),
            "tatoeba": sha256_file(sorted(TATOEBA_DIR.glob("*.tsv.bz2"))[0]),
        },
        "output_sha256": {
            "candidate_pool": sha256_file(pool_path),
            "priority_review": sha256_file(review_path),
        },
    }
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
