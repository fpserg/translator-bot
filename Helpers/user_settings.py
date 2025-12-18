from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class UserSettings:
    target_language: str = "en"


class SettingsStore:
    """Very small JSON-backed per-user settings store.

    - Keys: Telegram user_id (int)
    - Values: UserSettings

    Note: For production / multi-replica you should move this to Redis/DB.
    """

    def __init__(self, path: str | os.PathLike = "user_settings.json"):
        self.path = Path(path)
        self._cache: Dict[int, UserSettings] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            self._cache = {}
            return
        data = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        self._cache = {int(k): UserSettings(**v) for k, v in data.items()}

    def _save(self) -> None:
        data = {str(k): vars(v) for k, v in self._cache.items()}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def get(self, user_id: int) -> UserSettings:
        self._load()
        return self._cache.get(user_id, UserSettings())

    def set_target_language(self, user_id: int, lang: str) -> None:
        self._load()
        s = self._cache.get(user_id, UserSettings())
        s.target_language = lang
        self._cache[user_id] = s
        self._save()


class PendingActions:
    """In-memory pending action flags, keyed by user_id."""

    def __init__(self):
        self._pending_detect: set[int] = set()

    def set_detect(self, user_id: int) -> None:
        self._pending_detect.add(user_id)

    def pop_detect(self, user_id: int) -> bool:
        if user_id in self._pending_detect:
            self._pending_detect.remove(user_id)
            return True
        return False

    def clear(self, user_id: int) -> None:
        self._pending_detect.discard(user_id)

    def is_detect(self, user_id: int) -> bool:
        return user_id in self._pending_detect
