"""Build one English candidate pool for junior, senior-high, CET-4 and CET-6."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

from build_junior_phrase_candidates import (
    MOBY,
    OEWN,
    TATOEBA_DIR,
    load_moby,
    load_oewn,
    normalized_phrase,
    tatoeba_counts,
    words,
    write_csv,
)


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "data_sources/processed/phrase_stage_boundaries/phrase_stage_vocabulary_tokens.csv"
OUTPUT_DIR = ROOT / "data_sources/processed/phrase_candidates/four_level"
LEVELS = ("junior", "senior_high", "cet4", "cet6")
RANK = {level: index for index, level in enumerate(LEVELS)}
QUEUE_LIMITS = {"junior": 600, "senior_high": 700, "cet4": 900, "cet6": 900}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_boundaries() -> dict[str, str]:
    with BOUNDARY.open(encoding="utf-8-sig", newline="") as stream:
        return {row["token"]: row["earliest_level"] for row in csv.DictReader(stream)}


def lexical_level(phrase: str, boundary: dict[str, str]) -> str:
    return max((boundary[token] for token in words(phrase)), key=RANK.get)


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


def main() -> int:
    boundary = load_boundaries()
    allowed = set(boundary)
    oewn = load_oewn(allowed)
    moby = load_moby(allowed)
    candidates = set(oewn) | set(moby)
    occurrences = tatoeba_counts(candidates)

    rows: list[dict[str, object]] = []
    for phrase in candidates:
        oewn_item = oewn.get(phrase, {"forms": set(), "pos": set(), "senses": set()})
        in_oewn = phrase in oewn
        in_moby = phrase in moby
        count = occurrences[phrase]
        if not in_oewn and not (in_moby and count > 0):
            continue
        if in_oewn and count > 0:
            status = "evidence_ready_review"
        elif in_moby and count > 0:
            status = "moby_corpus_review"
        elif in_oewn:
            status = "oewn_dictionary_review"
        else:
            # Defensive branch: Moby-only candidates without occurrence
            # evidence were already excluded above.
            status = "insufficient_evidence_hold"
        rows.append(
            {
                "phrase": phrase,
                "normalized_phrase": normalized_phrase(phrase),
                "word_count": len(words(phrase)),
                "minimum_lexical_level": lexical_level(phrase, boundary),
                "oewn_match": str(in_oewn).lower(),
                "oewn_pos": "|".join(sorted(oewn_item["pos"])),
                "oewn_sense_ids": "|".join(sorted(oewn_item["senses"])),
                "moby_match": str(in_moby).lower(),
                "tatoeba_cc0_sentence_count": count,
                "candidate_status": status,
                "priority_score": priority_score(oewn_item["pos"], in_moby, count, phrase),
                "human_review_claimed": "false",
            }
        )

    rows.sort(key=lambda row: (-float(row["priority_score"]), str(row["phrase"])))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pool_path = OUTPUT_DIR / "candidate_pool.csv"
    write_csv(rows, pool_path)

    queue_paths: dict[str, Path] = {}
    queue_counts: dict[str, int] = {}
    for level in LEVELS:
        queue = [
            row
            for row in rows
            if row["minimum_lexical_level"] == level
            and row["candidate_status"] != "insufficient_evidence_hold"
        ][: QUEUE_LIMITS[level]]
        path = OUTPUT_DIR / f"priority_review_{level}.csv"
        write_csv(queue, path)
        queue_paths[level] = path
        queue_counts[level] = len(queue)

    report = {
        "boundary_token_count": len(boundary),
        "boundary_level_counts": dict(Counter(boundary.values())),
        "candidate_pool_count": len(rows),
        "candidate_minimum_level_counts": dict(
            Counter(str(row["minimum_lexical_level"]) for row in rows)
        ),
        "candidate_status_counts": dict(Counter(str(row["candidate_status"]) for row in rows)),
        "priority_queue_counts": queue_counts,
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
            **{f"queue_{level}": sha256_file(path) for level, path in queue_paths.items()},
        },
    }
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
