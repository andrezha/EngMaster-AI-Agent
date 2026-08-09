"""Build reproducible vocabulary boundaries for the tiered phrase project.

This development utility reads only archived official documents.  It never
reads the historical product phrase file.  The outputs are scope evidence for
phrase grading, not ready-made phrase lists.

Dependencies:

    python -m pip install pypdf cryptography
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - developer guidance
    raise SystemExit("Missing dependency: install pypdf and cryptography") from exc


ROOT = Path(__file__).resolve().parents[1]
HIGH_DIR = ROOT / "data_sources" / "raw" / "moe_high_2025"
CET_DIR = ROOT / "data_sources" / "raw" / "cet4"
OUTPUT_DIR = ROOT / "data_sources" / "processed" / "phrase_stage_boundaries"

HIGH_SOURCE_ID = "moe-hs-english-2017-2025-appendix-2"
CET_SOURCE_ID = "cet-english-2016-revised-word-list"

# Zero-based PDF indexes.  The bounds were checked against the visible first
# entry and the section following the word list, not inferred from page count.
HIGH_PAGES = range(75, 132)
CET_PAGES = range(20, 149)


def compact(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").replace("\u3000", " ").split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def single_pdf(directory: Path) -> Path:
    files = sorted(directory.glob("*.pdf"))
    if len(files) != 1:
        raise RuntimeError(f"Expected exactly one PDF in {directory}, found {len(files)}")
    return files[0]


def high_marker(raw_entry: str) -> str:
    match = re.search(r"(\*{1,2})\s*$", raw_entry)
    return match.group(1) if match else ""


def extract_high_rows(pdf_path: Path) -> list[dict[str, object]]:
    reader = PdfReader(pdf_path)
    rows: list[dict[str, object]] = []
    collecting = False
    section = ""
    repeated_i_seen = False

    for page_index in HIGH_PAGES:
        for raw in (reader.pages[page_index].extract_text() or "").splitlines():
            line = compact(raw)
            if not collecting:
                if page_index == HIGH_PAGES.start and line == "A":
                    collecting = True
                    section = "A"
                continue

            if (
                not line
                or re.fullmatch(r"\d+", line)
                or "普通高中英语课程标准" in line
                or line.startswith("│ 附录 │")
            ):
                continue

            if re.fullmatch(r"[A-Z]", line):
                # In section I the heading is immediately followed by the
                # pronoun entry I.  Preserve the second occurrence as a word.
                if line == "I" and section == "I" and not repeated_i_seen:
                    repeated_i_seen = True
                else:
                    section = line
                    continue

            if not re.match(r"^[A-Za-z]", line):
                continue

            marker = high_marker(line)
            entry = line[: -len(marker)].rstrip() if marker else line
            level = {
                "": "junior",
                "*": "senior_high_compulsory",
                "**": "senior_high_selective_compulsory",
            }[marker]
            rows.append(
                {
                    "sequence": len(rows) + 1,
                    "raw_entry": line,
                    "entry": entry,
                    "marker": marker,
                    "curriculum_level": level,
                    "alphabetic_section": section,
                    "source_pdf_page": page_index + 1,
                    "source_print_page": page_index - 2,
                    "source_id": HIGH_SOURCE_ID,
                }
            )
            if entry == "zoo":
                return rows

    raise RuntimeError("High-school Appendix 2 did not end at zoo")


def _cet_visual_lines(page: object) -> list[tuple[float, float, str]]:
    """Reconstruct printed rows so superscripts do not become false entries."""
    glyphs: list[tuple[float, float, str]] = []

    def visitor(text: str, cm: list[float], tm: list[float], font: object, size: float) -> None:
        del tm, font, size
        # This PDF normally exposes one glyph per visitor call.  Retaining the
        # fragment order at an identical coordinate also handles the few
        # multi-character fragments deterministically.
        for char in text:
            if not char.isspace():
                glyphs.append((float(cm[5]), float(cm[4]), char))

    page.extract_text(visitor_text=visitor)
    baselines: list[list[object]] = []
    for y, x, char in sorted(glyphs, key=lambda item: -item[0]):
        for group in baselines:
            if abs(float(group[0]) - y) <= 1.2:
                group[1].append((y, x, char))
                break
        else:
            baselines.append([y, [(y, x, char)]])

    lines: list[tuple[float, float, str]] = []
    for baseline, group_object in baselines:
        group = sorted(group_object, key=lambda item: item[1])
        min_x = min(item[1] for item in group)
        output = ""
        previous_x: float | None = None
        for _y, x, char in group:
            if previous_x is not None and x - previous_x > 8.2:
                output += " "
            output += char
            previous_x = x
        lines.append((float(baseline), min_x, compact(output)))
    return lines


def extract_cet_rows(pdf_path: Path) -> list[dict[str, object]]:
    reader = PdfReader(pdf_path)
    rows: list[dict[str, object]] = []

    for page_index in CET_PAGES:
        for baseline, min_x, line in _cet_visual_lines(reader.pages[page_index]):
            # Lexical rows start at x≈69 (starred) or x≈81 (unstarred).
            # The y/x bounds exclude page headers, folios and the side label.
            if not (80 < baseline < 710 and min_x < 90):
                continue
            if not re.search(r"[A-Za-z]", line):
                continue
            if "全 国 大 学 英 语" in line:
                continue

            marker = "★" if line.startswith("★") else ""
            entry = line[1:].strip() if marker else line
            entry = re.sub(r"\s+[词表]$", "", entry).strip()
            # Printed full-width numerals distinguish homographs.  They are
            # evidence annotations, not part of a spelling used by the app.
            entry = re.sub(r"[０-９]", "", entry)
            entry = compact(entry)
            rows.append(
                {
                    "sequence": len(rows) + 1,
                    "raw_entry": line,
                    "entry": entry,
                    "marker": marker,
                    "exam_level": "cet6_excluded" if marker else "cet4",
                    "source_pdf_page": page_index + 1,
                    "source_print_page": page_index - 4,
                    "source_id": CET_SOURCE_ID,
                }
            )

    if not rows or rows[0]["entry"] != "a/an" or rows[-1]["entry"] != "zoom":
        raise RuntimeError("CET word-list extraction boundaries are incorrect")
    return rows


def lexical_tokens(entry: str) -> set[str]:
    """Return conservative atomic forms used only for phrase-level gating."""
    # The embedded font renders compact spelling alternatives such as
    # advisor/-er as ``advisor/Ｇer``.  A suffix fragment is not an independent
    # word, so discard that encoded alternative instead of emitting ``er``.
    cleaned = re.sub(r"/Ｇ[A-Za-z]+", "", entry)
    cleaned = (
        cleaned.replace("Ｇ", "")
        .replace("􀆳", "'")
        .replace("􀪋", "")
        .replace("‐", "-")
        .replace("‑", "-")
        .replace("–", "-")
        .replace("—", "-")
    )
    tokens = {
        token.casefold()
        for token in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", cleaned)
    }
    # Single letters introduced by corrupt variant notation are not useful
    # scope evidence.  The genuine pronouns/articles remain explicit.
    return {token for token in tokens if len(token) > 1 or token in {"a", "i"}}


def build_token_rows(
    high_rows: list[dict[str, object]], cet_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    evidence: dict[str, dict[str, set[str]]] = {}

    def add(token: str, level: str, source_id: str, raw_entry: str) -> None:
        item = evidence.setdefault(
            token, {"levels": set(), "sources": set(), "entries": set()}
        )
        item["levels"].add(level)
        item["sources"].add(source_id)
        item["entries"].add(raw_entry)

    for row in high_rows:
        level = "junior" if row["curriculum_level"] == "junior" else "senior_high"
        for token in lexical_tokens(str(row["entry"])):
            add(token, level, HIGH_SOURCE_ID, str(row["raw_entry"]))

    for row in cet_rows:
        if row["exam_level"] != "cet4":
            continue
        for token in lexical_tokens(str(row["entry"])):
            add(token, "cet4", CET_SOURCE_ID, str(row["raw_entry"]))

    rank = {"junior": 0, "senior_high": 1, "cet4": 2}
    output: list[dict[str, object]] = []
    for token, item in sorted(evidence.items()):
        levels = sorted(item["levels"], key=rank.get)
        output.append(
            {
                "token": token,
                "earliest_level": levels[0],
                "document_levels": "|".join(levels),
                "source_ids": "|".join(sorted(item["sources"])),
                "source_entry_count": len(item["entries"]),
                "source_entries": " || ".join(sorted(item["entries"])),
            }
        )
    return output


def write_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty output: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    high_pdf = single_pdf(HIGH_DIR)
    cet_pdf = single_pdf(CET_DIR)
    high_rows = extract_high_rows(high_pdf)
    cet_rows = extract_cet_rows(cet_pdf)
    token_rows = build_token_rows(high_rows, cet_rows)

    high_counts = Counter(str(row["curriculum_level"]) for row in high_rows)
    cet_counts = Counter(str(row["exam_level"]) for row in cet_rows)
    validation = {
        "high_source_declared_total": 3100,
        "high_printed_entry_total": len(high_rows),
        "high_printed_level_counts": dict(high_counts),
        "high_first_entry": high_rows[0]["entry"],
        "high_last_entry": high_rows[-1]["entry"],
        "high_internal_consistency_note": (
            "The PDF declares 3100 = 1600 + 500 + 1000, while its printed "
            "Appendix 2 contains 3099 rows = 1600 + 502 + 997. Printed "
            "entries and markers are preserved without invented corrections."
        ),
        "cet_source_declared_item_total": 5418,
        "cet_reconstructed_print_line_total": len(cet_rows),
        "cet_print_line_level_counts": dict(cet_counts),
        "cet_counting_note": (
            "The syllabus declares 5418 word items. This extraction groups "
            "the printed word-family lines by visual baseline; the two counts "
            "measure different units and must not be equated."
        ),
        "normalized_token_total": len(token_rows),
        "token_earliest_level_counts": dict(
            Counter(str(row["earliest_level"]) for row in token_rows)
        ),
        "old_phrase_file_read": False,
    }

    if len(high_rows) != 3099 or high_counts.get("junior") != 1600:
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))
    if len(cet_rows) < 5000 or cet_counts.get("cet4", 0) < 3500:
        raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = {
        "high": OUTPUT_DIR / "high_school_2025_entries.csv",
        "cet": OUTPUT_DIR / "cet_2016_word_family_lines.csv",
        "tokens": OUTPUT_DIR / "phrase_stage_vocabulary_tokens.csv",
    }
    write_csv(high_rows, paths["high"])
    write_csv(cet_rows, paths["cet"])
    write_csv(token_rows, paths["tokens"])

    hashes = {name: sha256_file(path) for name, path in paths.items()}
    validation["output_sha256"] = hashes
    (OUTPUT_DIR / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    hashes["validation"] = sha256_file(OUTPUT_DIR / "validation.json")
    (OUTPUT_DIR / "SHA256SUMS.txt").write_text(
        "".join(
            f"{digest}  {paths[name].name if name in paths else 'validation.json'}\n"
            for name, digest in hashes.items()
        ),
        encoding="utf-8",
    )
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
