from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    line: int | None = None

@dataclass(frozen=True)
class RepairCandidate:
    candidate_id: str
    target: str
    intent: str
    created_at: str
    original_sha256: str
    candidate_sha256: str
    staged_path: Path

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["staged_path"] = str(self.staged_path)
        return data

@dataclass(frozen=True)
class ApplyResult:
    target: str
    backup: str
    applied_sha256: str
    candidate_id: str
