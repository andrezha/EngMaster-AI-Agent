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

    def __init__(self, path, rng=None):
        self.path = path
        self.rng = rng or random.Random()
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
        """Hash a complete row when it has no standard identity field."""
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
        self._inventories[mode] = inventory
        state = self.data["modes"].get(mode)
        if not isinstance(state, dict):
            self._start_round(mode, inventory, 1)
        else:
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
                value.get("version") == self.VERSION
                and
                isinstance(value.get("modes", {}), dict)
                and isinstance(value.get("wrong_rounds", {}), dict)
            ),
        )
        self.storage_error = status == "invalid"
        self.recovered_from_backup = status == "recovered"
        if data is not None:
            data.setdefault("modes", {})
            data.setdefault("wrong_rounds", {})
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

    def ensure_round(self, mode, progress):
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
                "active_seconds": 0.0,
                "total": _safe_nonnegative_int(progress.get("total"), 0),
            }
            mode_data["ongoing"] = ongoing
        else:
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
        if not ongoing.get("started_at"):
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
            return "错词轮次：历史错词｜之前轮次未记录"
        count = _safe_nonnegative_int(record.get("count"), 0)
        last_round = max(1, _safe_nonnegative_int(record.get("last_round"), 1))
        if count <= 1:
            return f"错词轮次：首次在第{last_round}轮答错"
        return f"错词轮次：累计{count}轮｜最近第{last_round}轮"

    def snapshot(self):
        data = self._load()
        for mode, started in self._active_since.items():
            ongoing = data.get("modes", {}).get(mode, {}).get("ongoing")
            if isinstance(ongoing, dict):
                ongoing["active_seconds"] = float(
                    ongoing.get("active_seconds", 0.0)) + max(
                        0.0, time.monotonic() - started)
        return data
