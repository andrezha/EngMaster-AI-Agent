import hashlib
import glob
import json
import os
import random
import shutil
import time
from datetime import datetime


def backup_existing_file_once(path, tag="round_upgrade"):
    """Create a one-time, non-destructive backup before the round upgrade is used."""
    try:
        if not path or not os.path.isfile(path):
            return ""
        safe_tag = "".join(
            character for character in str(tag) if character.isalnum() or character == "_"
        ) or "upgrade"
        existing = sorted(glob.glob(f"{path}.before_{safe_tag}_*.bak"))
        if existing:
            return existing[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}.before_{safe_tag}_{timestamp}.bak"
        shutil.copy2(path, backup_path)
        return backup_path
    except OSError:
        return ""


def backup_learning_upgrade_once(data_dir, filenames):
    """Snapshot all existing study files once before learning-records are enabled."""
    try:
        existing = sorted(glob.glob(os.path.join(
            data_dir, "backup_before_learning_records_*")))
        if existing:
            return existing[0]
        source_paths = [os.path.join(data_dir, name) for name in filenames]
        source_paths = [path for path in source_paths if os.path.isfile(path)]
        if not source_paths:
            return ""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(
            data_dir, f"backup_before_learning_records_{timestamp}")
        os.makedirs(backup_dir, exist_ok=False)
        for source_path in source_paths:
            shutil.copy2(source_path, os.path.join(
                backup_dir, os.path.basename(source_path)))
        return backup_dir
    except OSError:
        return ""


def atomic_write_json(path, data, indent=2):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=indent)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp_path, path)
    try:
        shutil.copy2(path, f"{path}.last_good.bak")
    except OSError:
        pass


def _load_json_dict_with_recovery(path, validator):
    """Read the primary JSON, falling back to the most recent valid snapshot."""
    found_candidate = False
    for candidate, recovered in ((path, False), (f"{path}.last_good.bak", True)):
        try:
            with open(candidate, "r", encoding="utf-8") as file:
                data = json.load(file)
            found_candidate = True
            if isinstance(data, dict) and validator(data):
                return data, ("recovered" if recovered else "ok")
        except FileNotFoundError:
            continue
        except (json.JSONDecodeError, OSError, UnicodeError):
            found_candidate = True
    return None, ("invalid" if found_candidate else "missing")


def _safe_nonnegative_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


class ChallengeRoundStore:
    """Persist independent shuffled-round progress without touching study data."""

    VERSION = 3

    def __init__(self, path, rng=None, key_aliases_by_mode=None):
        self.path = path
        self.rng = rng or random.Random()
        self.key_aliases_by_mode = key_aliases_by_mode or {}
        backup_existing_file_once(path, "stable_identity_upgrade")
        self.storage_error = False
        self.recovered_from_backup = False
        self.data = self._load()
        self._inventories = {}
        self._dirty_modes = set()

    def _load(self):
        data, status = _load_json_dict_with_recovery(
            self.path,
            lambda value: isinstance(value.get("modes"), dict),
        )
        self.storage_error = status == "invalid"
        self.recovered_from_backup = status == "recovered"
        if data is not None:
            return data
        return {"version": self.VERSION, "modes": {}}

    def has_mode(self, mode):
        return isinstance(self.data.get("modes", {}).get(mode), dict)

    @classmethod
    def item_base_key(cls, item):
        return cls._base_key(item)

    def _save(self):
        if not self._dirty_modes:
            return
        if self.storage_error:
            # Never replace an unreadable progress file with a blank first round.
            return
        disk_data = self._load()
        if self.storage_error:
            return
        disk_modes = disk_data.setdefault("modes", {})
        for mode in self._dirty_modes:
            disk_modes[mode] = self.data["modes"][mode]
        disk_data["version"] = self.VERSION
        try:
            atomic_write_json(self.path, disk_data)
        except OSError:
            return
        self.data = disk_data
        self._dirty_modes.clear()

    @staticmethod
    def _base_key(item):
        """Legacy full-row hash retained for migration alias generation."""
        stable_item = {
            key: value for key, value in item.items()
            if key not in {"correct_count"}
        }
        payload = json.dumps(stable_item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _identity_key(cls, item):
        """Hash only an item's identity so wording corrections cannot erase progress."""
        for field, item_type in (
            ("word", "word"),
            ("p", "phrase"),
            ("infinitive", "irregular"),
        ):
            value = str(item.get(field, "")).strip().casefold()
            if value:
                payload = json.dumps(
                    {"type": item_type, "value": value},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return cls._base_key(item)

    def _build_inventory(self, items):
        inventory = {}
        occurrences = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            base = self._identity_key(item)
            occurrence = occurrences.get(base, 0)
            occurrences[base] = occurrence + 1
            key = f"{base}:{occurrence}"
            inventory[key] = item
        return inventory

    def _legacy_key_migrations(self, mode, items):
        """Map version-2 full-row hashes (and known aliases) to stable identities."""
        migrations = {}
        legacy_occurrences = {}
        identity_occurrences = {}
        aliases = self.key_aliases_by_mode.get(mode, {})
        reverse_aliases = {}
        for old_base, current_base in aliases.items():
            reverse_aliases.setdefault(current_base, []).append(old_base)
        for item in items:
            if not isinstance(item, dict):
                continue
            legacy_base = self._base_key(item)
            identity_base = self._identity_key(item)
            legacy_occurrence = legacy_occurrences.get(legacy_base, 0)
            legacy_occurrences[legacy_base] = legacy_occurrence + 1
            identity_occurrence = identity_occurrences.get(identity_base, 0)
            identity_occurrences[identity_base] = identity_occurrence + 1
            stable_key = f"{identity_base}:{identity_occurrence}"
            migrations[f"{legacy_base}:{legacy_occurrence}"] = stable_key
            for old_base in reverse_aliases.get(legacy_base, []):
                migrations[f"{old_base}:{legacy_occurrence}"] = stable_key
        return migrations

    def _migrate_saved_key(self, mode, key, migrations=None):
        """Map a persisted pre-correction item hash to its corrected hash."""
        if not isinstance(key, str):
            return key
        if migrations and key in migrations:
            return migrations[key]
        base, separator, occurrence = key.rpartition(":")
        if not separator or not occurrence.isdigit():
            return key
        aliases = self.key_aliases_by_mode.get(mode, {})
        aliased_key = f"{aliases.get(base, base)}:{occurrence}"
        return migrations.get(aliased_key, aliased_key) if migrations else aliased_key

    def _start_round(self, mode, inventory, round_number):
        order = list(inventory)
        self.rng.shuffle(order)
        self.data["modes"][mode] = {
            "round": max(1, int(round_number)),
            "completed": 0,
            "remaining": order,
            "wrong": [],
            "retry_key": None,
        }
        self._dirty_modes.add(mode)

    def activate(self, mode, items):
        inventory = self._build_inventory(items)
        migrations = self._legacy_key_migrations(mode, items)
        self._inventories[mode] = inventory
        state = self.data["modes"].get(mode)
        if not isinstance(state, dict):
            self._start_round(mode, inventory, 1)
        else:
            state["remaining"] = [
                self._migrate_saved_key(mode, key, migrations)
                for key in state.get("remaining", [])
            ] if isinstance(state.get("remaining"), list) else []
            state["wrong"] = [
                self._migrate_saved_key(mode, key, migrations)
                for key in state.get("wrong", [])
            ] if isinstance(state.get("wrong"), list) else []
            state["retry_key"] = self._migrate_saved_key(
                mode, state.get("retry_key"), migrations
            )
            state["round"] = max(1, _safe_nonnegative_int(state.get("round"), 1))
            state["completed"] = _safe_nonnegative_int(state.get("completed"), 0)
            wrong = state.get("wrong", [])
            if not isinstance(wrong, list):
                wrong = []
            state["wrong"] = list(dict.fromkeys(wrong))
            remaining = state.get("remaining", [])
            if not isinstance(remaining, list):
                remaining = []
            state["remaining"] = [
                key for key in remaining if key in inventory
            ]
            retry_key = state.get("retry_key")
            if retry_key is None and state["remaining"] and state["remaining"][0] in state["wrong"]:
                # Version 1 could be closed during the old auto-advance delay.
                # Treat that current, already-wrong item as awaiting correction.
                retry_key = state["remaining"][0]
            if not state["remaining"] or retry_key != state["remaining"][0]:
                retry_key = None
            state["retry_key"] = retry_key
            if inventory and not state["remaining"]:
                next_round = state["round"] + (1 if state["completed"] else 0)
                self._start_round(mode, inventory, next_round)
            else:
                self._dirty_modes.add(mode)
        self._save()
        return self.current_items(mode)

    def current_items(self, mode):
        state = self.data["modes"].get(mode, {})
        inventory = self._inventories.get(mode, {})
        return [inventory[key] for key in state.get("remaining", []) if key in inventory]

    def wrong_items(self, mode):
        state = self.data["modes"].get(mode, {})
        inventory = self._inventories.get(mode, {})
        return [inventory[key] for key in state.get("wrong", []) if key in inventory]

    def progress(self, mode):
        state = self.data["modes"].get(mode, {})
        remaining = len(state.get("remaining", []))
        completed = _safe_nonnegative_int(state.get("completed"), 0)
        total = completed + remaining
        return {
            "round": max(1, _safe_nonnegative_int(state.get("round"), 1)),
            "current": completed + 1 if remaining else completed,
            "total": total,
            "remaining_after_current": max(0, remaining - 1),
            "wrong": len(state.get("wrong", [])),
        }

    def mark_wrong(self, mode):
        state = self.data["modes"].get(mode)
        if not state or not state.get("remaining"):
            return
        key = state["remaining"][0]
        changed = False
        if key not in state["wrong"]:
            state["wrong"].append(key)
            changed = True
        if state.get("retry_key") != key:
            state["retry_key"] = key
            changed = True
        if changed:
            self._dirty_modes.add(mode)
            self._save()

    def is_retry_required(self, mode):
        state = self.data.get("modes", {}).get(mode, {})
        remaining = state.get("remaining", [])
        return bool(remaining and state.get("retry_key") == remaining[0])

    def advance(self, mode, current_items):
        inventory = self._build_inventory(current_items)
        self._inventories[mode] = inventory
        state = self.data["modes"].get(mode)
        if not state or not state.get("remaining"):
            self.activate(mode, current_items)
            return None, self.current_items(mode)

        completed_key = state["remaining"].pop(0)
        if state.get("retry_key") == completed_key:
            state["retry_key"] = None
        state["completed"] = _safe_nonnegative_int(state.get("completed"), 0) + 1
        state["remaining"] = [key for key in state["remaining"] if key in inventory]
        self._dirty_modes.add(mode)

        summary = None
        if not state["remaining"]:
            summary = {
                "round": state["round"],
                "total": state["completed"],
                "wrong": len(state.get("wrong", [])),
            }
            self._start_round(mode, inventory, state["round"] + 1)
        self._save()
        return summary, self.current_items(mode)


def round_summary_text(summary):
    if not summary:
        return ""
    return (
        f"第{summary['round']}轮完成：共{summary['total']}项，"
        f"本轮错词{summary['wrong']}项；已开始下一轮。"
    )


class ChallengeLearningStore:
    """Store round timing/history and wrong-round metadata separately from study data."""

    VERSION = 2
    HISTORY_LIMIT = 50

    def __init__(self, path):
        self.path = path
        self._active_since = {}
        self.storage_error = False
        self.recovered_from_backup = False

    def _load(self):
        data, status = _load_json_dict_with_recovery(
            self.path,
            lambda value: (
                isinstance(value.get("modes", {}), dict)
                and isinstance(value.get("wrong_rounds", {}), dict)
            ),
        )
        self.storage_error = status == "invalid"
        self.recovered_from_backup = status == "recovered"
        if data is not None:
            data.setdefault("modes", {})
            data.setdefault("wrong_rounds", {})
            if _safe_nonnegative_int(data.get("version"), 0) < 2:
                for mode_data in data["modes"].values():
                    ongoing = mode_data.get("ongoing") if isinstance(mode_data, dict) else None
                    if isinstance(ongoing, dict):
                        ongoing["started_at"] = None
                        ongoing["tracking_started_at"] = None
                        ongoing["active_seconds"] = 0.0
                        ongoing["pending_start_migration"] = True
                data["version"] = self.VERSION
            return data
        return {"version": self.VERSION, "modes": {}, "wrong_rounds": {}}

    def _save(self, data):
        if self.storage_error:
            return
        data["version"] = self.VERSION
        try:
            atomic_write_json(self.path, data)
        except OSError:
            pass

    @staticmethod
    def _now_text():
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def ensure_round(self, mode, progress, started_before_tracking=False):
        data = self._load()
        mode_data = data["modes"].setdefault(mode, {"history": []})
        mode_data.setdefault("history", [])
        ongoing = mode_data.get("ongoing")
        round_number = max(1, _safe_nonnegative_int(progress.get("round"), 1))
        if not isinstance(ongoing, dict) or ongoing.get("round") != round_number:
            ongoing = {
                "round": round_number,
                "started_at": None,
                "tracking_started_at": None,
                "started_before_tracking": bool(started_before_tracking),
                "active_seconds": 0.0,
                "total": _safe_nonnegative_int(progress.get("total"), 0),
            }
            mode_data["ongoing"] = ongoing
        else:
            if ongoing.pop("pending_start_migration", False):
                ongoing["started_before_tracking"] = bool(started_before_tracking)
            ongoing["total"] = _safe_nonnegative_int(
                progress.get("total"), ongoing.get("total", 0))
        self._save(data)

    def begin_round(self, mode):
        data = self._load()
        ongoing = data.get("modes", {}).get(mode, {}).get("ongoing")
        if not isinstance(ongoing, dict):
            return
        now = self._now_text()
        if not ongoing.get("tracking_started_at"):
            ongoing["tracking_started_at"] = now
        if not ongoing.get("started_before_tracking") and not ongoing.get("started_at"):
            ongoing["started_at"] = now
        self._save(data)
        self.resume(mode)

    def resume(self, mode):
        data = self._load()
        ongoing = data.get("modes", {}).get(mode, {}).get("ongoing")
        if (
            isinstance(ongoing, dict)
            and ongoing.get("tracking_started_at")
            and mode not in self._active_since
        ):
            self._active_since[mode] = time.monotonic()

    def pause(self, mode):
        started = self._active_since.pop(mode, None)
        if started is None:
            return
        elapsed = max(0.0, time.monotonic() - started)
        data = self._load()
        ongoing = data.get("modes", {}).get(mode, {}).get("ongoing")
        if isinstance(ongoing, dict):
            ongoing["active_seconds"] = float(
                ongoing.get("active_seconds", 0.0)) + elapsed
            self._save(data)

    def finish_round(self, mode, summary):
        self.pause(mode)
        data = self._load()
        mode_data = data["modes"].setdefault(mode, {"history": []})
        ongoing = mode_data.pop("ongoing", None)
        if not isinstance(ongoing, dict):
            ongoing = {
                "round": summary.get("round", 1),
                "started_at": None,
                "tracking_started_at": self._now_text(),
                "started_before_tracking": True,
                "active_seconds": 0.0,
            }
        ongoing.update({
            "round": summary.get("round", ongoing.get("round", 1)),
            "ended_at": self._now_text(),
            "total": _safe_nonnegative_int(summary.get("total"), 0),
            "wrong": _safe_nonnegative_int(summary.get("wrong"), 0),
            "status": "completed",
        })
        history = mode_data.setdefault("history", [])
        history.append(ongoing)
        mode_data["history"] = history[-self.HISTORY_LIMIT:]
        self._save(data)

    @staticmethod
    def _wrong_item_key(mode, item):
        field = {
            "regular": "word",
            "phrase": "p",
            "irregular": "infinitive",
        }.get(mode)
        if field:
            value = str(item.get(field, "")).strip().casefold()
            if value:
                return f"{field}:{value}"
        return ChallengeRoundStore.item_base_key(item)

    def record_wrong_round(self, mode, item, round_number):
        key = self._wrong_item_key(mode, item)
        data = self._load()
        mode_records = data["wrong_rounds"].setdefault(mode, {})
        record = mode_records.setdefault(key, {"count": 0, "last_round": 0})
        round_number = max(1, _safe_nonnegative_int(round_number, 1))
        if _safe_nonnegative_int(record.get("last_round"), 0) != round_number:
            record["count"] = _safe_nonnegative_int(record.get("count"), 0) + 1
            record["last_round"] = round_number
            self._save(data)

    def wrong_round_record(self, mode, item):
        key = self._wrong_item_key(mode, item)
        data = self._load()
        record = data.get("wrong_rounds", {}).get(mode, {}).get(key)
        return record if isinstance(record, dict) else None

    def wrong_round_text(self, mode, item):
        record = self.wrong_round_record(mode, item)
        if not record:
            return "错题轮次：历史错词｜之前轮次未记录"
        count = _safe_nonnegative_int(record.get("count"), 0)
        last_round = max(1, _safe_nonnegative_int(record.get("last_round"), 1))
        if count <= 1:
            return f"错题轮次：首次在第{last_round}轮答错"
        return f"错题轮次：累计{count}轮｜最近第{last_round}轮"

    def snapshot(self):
        data = self._load()
        for mode, started in self._active_since.items():
            ongoing = data.get("modes", {}).get(mode, {}).get("ongoing")
            if isinstance(ongoing, dict):
                ongoing["active_seconds"] = float(
                    ongoing.get("active_seconds", 0.0)) + max(
                        0.0, time.monotonic() - started)
        return data
