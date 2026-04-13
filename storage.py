import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List

CONFIG_PATH = Path(os.environ.get("APPDATA", ".")) / "Pigmato" / "config.json"
MAX_RECENT_TOPICS = 10


@dataclass
class Config:
    work_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    cycles_before_long_break: int = 4
    autostart: bool = False
    recent_topics: List[str] = field(default_factory=list)


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
