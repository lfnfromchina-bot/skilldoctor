"""Shared issue type used by validator and linter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Level(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    level: Level
    rule: str
    message: str
    skill: str = ""  # skill directory name, filled by callers when batch-scanning

    def as_dict(self) -> dict:
        return {
            "level": self.level.value,
            "rule": self.rule,
            "message": self.message,
            "skill": self.skill,
        }
