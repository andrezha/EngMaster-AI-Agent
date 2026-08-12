"""Edition registry for the single-codebase 英思成 application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Iterable


PAGE_VOCAB_CHALLENGE = "vocab_challenge"
PAGE_WORD_LIST = "word_list"
PAGE_PHRASE_CHALLENGE = "phrase_challenge"
PAGE_PHRASE_LIST = "phrase_list"
PAGE_SELF_REGISTER = "self_register"


@dataclass(frozen=True)
class EditionConfig:
    edition_id: str
    display_name: str
    window_title: str
    vocabulary_path: str
    phrase_path: str
    irregular_verbs_path: str
    enabled_pages: frozenset[str]
    production_ready: bool
    word_count: int

    @property
    def base_display_name(self) -> str:
        return self.display_name.removesuffix("体验")

    @property
    def product_title(self) -> str:
        if is_trial_edition(self):
            return f"{self.base_display_name}免费体验版（{self.word_count}词）"
        return f"{self.display_name}{self.word_count}词汇版"

    @property
    def word_list_title(self) -> str:
        if self.edition_id == "gaokao":
            return "高中3800词汇表"
        return f"{self.base_display_name}词汇表（{self.word_count}词）"

    @property
    def challenge_title(self) -> str:
        if self.edition_id == "gaokao":
            return "高中3800词闯关"
        return f"{self.base_display_name}词汇闯关（{self.word_count}词）"

    def page_enabled(self, page_id: str) -> bool:
        return page_id in self.enabled_pages


_BASE_WORD_PAGES = frozenset({
    PAGE_VOCAB_CHALLENGE,
    PAGE_WORD_LIST,
    PAGE_SELF_REGISTER,
})
_ALL_VOCABULARY_PAGES = _BASE_WORD_PAGES | {
    PAGE_PHRASE_CHALLENGE,
    PAGE_PHRASE_LIST,
}
EDITIONS = {
    "zhongkao": EditionConfig(
        edition_id="zhongkao",
        display_name="初中英语",
        window_title="英思成 初中英语核心词汇版 v1.0",
        vocabulary_path="assets/editions/zhongkao/vocabulary.json",
        phrase_path="assets/editions/zhongkao/phrases.json",
        irregular_verbs_path="assets/editions/zhongkao/irregular_verbs.json",
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=True,
        word_count=1609,
    ),
    "gaokao": EditionConfig(
        edition_id="gaokao",
        display_name="高中",
        window_title="英思成 高中3800词汇版 v1.0",
        vocabulary_path="assets/editions/gaokao/vocabulary.json",
        phrase_path="assets/editions/gaokao/phrases.json",
        irregular_verbs_path="assets/editions/gaokao/irregular_verbs.json",
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=True,
        word_count=3800,
    ),
    "cet4": EditionConfig(
        edition_id="cet4",
        display_name="大学英语四级",
        window_title="英思成 大学英语四级4500词汇版 v1.0",
        vocabulary_path="research/edition_samples/cet4_sample.json",
        phrase_path="research/edition_samples/cet4_phrases.json",
        irregular_verbs_path="research/edition_samples/cet4_irregular_verbs.json",
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=False,
        word_count=4500,
    ),
    "cet6": EditionConfig(
        edition_id="cet6",
        display_name="大学英语六级",
        window_title="英思成 大学英语六级5500词汇版 v1.0",
        vocabulary_path="research/edition_samples/cet6_sample.json",
        phrase_path="research/edition_samples/cet6_phrases.json",
        irregular_verbs_path="research/edition_samples/cet6_irregular_verbs.json",
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=False,
        word_count=5500,
    ),
    "kaoyan": EditionConfig(
        edition_id="kaoyan",
        display_name="考研英语",
        window_title="英思成 考研英语5500词汇版 v1.0",
        vocabulary_path="research/edition_samples/kaoyan_sample.json",
        phrase_path="research/edition_samples/kaoyan_phrases.json",
        irregular_verbs_path="research/edition_samples/kaoyan_irregular_verbs.json",
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=False,
        word_count=5500,
    ),
}

RELEASED_EDITION_IDS = tuple(
    edition_id for edition_id, config in EDITIONS.items()
    if config.production_ready
)

# Each audience gets a difficulty-matched 30-word experience.  Trial editions
# deliberately keep their own IDs so progress, mistakes and self-entered words
# are isolated both from formal products and from the other trial levels.
_TRIAL_VOCABULARY_PATHS = {
    "zhongkao": "assets/editions/zhongkao/trial_vocabulary.json",
    "gaokao": "assets/editions/gaokao/trial_vocabulary.json",
    "cet4": "research/edition_samples/cet4_sample.json",
    "cet6": "research/edition_samples/cet6_sample.json",
    "kaoyan": "research/edition_samples/kaoyan_sample.json",
}
TRIAL_EDITIONS = {
    f"trial_{formal_id}": EditionConfig(
        edition_id=f"trial_{formal_id}",
        display_name=f"{formal.display_name}体验",
        window_title=f"英思成 {formal.display_name}免费体验版（30词） v1.0",
        vocabulary_path=_TRIAL_VOCABULARY_PATHS[formal_id],
        phrase_path=formal.phrase_path,
        irregular_verbs_path=formal.irregular_verbs_path,
        enabled_pages=_ALL_VOCABULARY_PAGES,
        production_ready=True,
        word_count=30,
    )
    for formal_id, formal in EDITIONS.items()
}
# Backward-compatible alias: old builds remembered "trial".  It now opens the
# high-school trial and is rewritten as trial_gaokao on the next save.
TRIAL_EDITION = TRIAL_EDITIONS["trial_gaokao"]
AVAILABLE_TRIAL_EDITION_IDS = tuple(
    f"trial_{edition_id}" for edition_id in RELEASED_EDITION_IDS
)
ALL_EDITIONS = {**EDITIONS, **TRIAL_EDITIONS, "trial": TRIAL_EDITION}

DEFAULT_EDITION_ID = "gaokao"


def resolve_edition(edition=None) -> EditionConfig:
    if isinstance(edition, EditionConfig):
        return edition
    edition_id = str(edition or DEFAULT_EDITION_ID).strip().lower()
    try:
        return ALL_EDITIONS[edition_id]
    except KeyError as exc:
        choices = ", ".join(ALL_EDITIONS)
        raise ValueError(f"未知版本 {edition_id!r}；可用版本：{choices}") from exc


def is_trial_edition(edition) -> bool:
    if isinstance(edition, EditionConfig):
        edition_id = edition.edition_id
    else:
        edition_id = str(edition or "").strip().lower()
    return edition_id == "trial" or edition_id.startswith("trial_")


def is_available_trial_edition(edition) -> bool:
    if isinstance(edition, EditionConfig):
        edition_id = edition.edition_id
    else:
        edition_id = str(edition or "").strip().lower()
    return edition_id == "trial" or edition_id in AVAILABLE_TRIAL_EDITION_IDS


def extract_edition_args(argv: Iterable[str]) -> tuple[EditionConfig, list[str]]:
    """Remove the internal --edition option before Qt parses command-line args."""
    args = list(argv)
    cleaned = [args[0]] if args else []
    requested = os.environ.get("RECALLLEX_EDITION", DEFAULT_EDITION_ID)
    index = 1
    while index < len(args):
        arg = args[index]
        if arg.startswith("--edition="):
            requested = arg.split("=", 1)[1]
        elif arg == "--edition" and index + 1 < len(args):
            index += 1
            requested = args[index]
        else:
            cleaned.append(arg)
        index += 1
    return resolve_edition(requested), cleaned


def edition_was_explicitly_requested(argv: Iterable[str]) -> bool:
    """Return whether startup already selected an edition outside the UI."""
    if os.environ.get("RECALLLEX_EDITION"):
        return True
    return any(
        arg == "--edition" or arg.startswith("--edition=")
        for arg in list(argv)[1:]
    )
