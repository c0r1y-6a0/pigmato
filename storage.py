import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from pathlib import Path
from typing import List

CONFIG_PATH = Path(os.environ.get("APPDATA", ".")) / "Pigmato" / "config.json"
LOG_PATH    = Path(os.environ.get("APPDATA", ".")) / "Pigmato" / "log.json"
MAX_RECENT_TOPICS = 10


@dataclass
class Config:
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    cycles_before_long_break: int = 4
    autostart: bool = False
    recent_topics: List[str] = field(default_factory=list)


@dataclass
class Session:
    topic: str
    start: str   # ISO-8601 datetime string
    end: str     # ISO-8601 datetime string


class Storage:
    def __init__(self):
        self._config = self._load()

    def _load(self) -> Config:
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            if CONFIG_PATH.exists():
                raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                known = {k: v for k, v in raw.items() if k in Config.__dataclass_fields__}
                return Config(**known)
        except Exception:
            pass
        return Config()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self._config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @property
    def config(self) -> Config:
        return self._config

    def add_topic(self, topic: str) -> None:
        topic = topic.strip()
        if not topic:
            return
        topics = self._config.recent_topics
        if topic in topics:
            topics.remove(topic)
        topics.insert(0, topic)
        self._config.recent_topics = topics[:MAX_RECENT_TOPICS]
        self.save()

    # ------------------------------------------------------------------ #
    # Session log
    # ------------------------------------------------------------------ #

    def log_session(self, topic: str, start: datetime, end: datetime) -> None:
        sessions = self._load_log_raw()
        sessions.append({
            "topic": topic,
            "start": start.isoformat(timespec="seconds"),
            "end":   end.isoformat(timespec="seconds"),
        })
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(
            json.dumps(sessions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_sessions(self, start_date: date, end_date: date) -> List[Session]:
        result = []
        for item in self._load_log_raw():
            try:
                s_date = datetime.fromisoformat(item["start"]).date()
                if start_date <= s_date <= end_date:
                    result.append(Session(
                        topic=item["topic"],
                        start=item["start"],
                        end=item["end"],
                    ))
            except Exception:
                continue
        return result

    def _load_log_raw(self) -> list:
        try:
            if LOG_PATH.exists():
                return json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []
