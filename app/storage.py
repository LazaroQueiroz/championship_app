from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonRepository:
    """Simple JSON repository for list-based persistence."""

    def __init__(self, file_path: Path, default: Any):
        self.file_path = file_path
        self.default = default
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.save(default)

    def load(self) -> Any:
        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, OSError):
            self.save(self.default)
            return self.default

    def save(self, data: Any) -> None:
        temp_path = self.file_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(self.file_path)
