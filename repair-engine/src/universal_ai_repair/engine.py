from __future__ import annotations
import hashlib, json, os, tempfile, uuid
from datetime import datetime, timezone
from pathlib import Path
from .errors import ApprovalRequired, CandidateNotFound, StaleCandidate, ValidationFailure, WorkspaceViolation
from .models import ApplyResult, Diagnostic, RepairCandidate
from .validators import validate_python

class RepairEngine:
    """Workspace-scoped repair staging controller. Not an OS-level sandbox."""
    def __init__(self, workspace: str | Path, *, allowed_extensions: tuple[str, ...] = (".py",),
                 max_file_bytes: int = 1_000_000) -> None:
        self.workspace = Path(workspace).expanduser().resolve()
        if not self.workspace.exists() or not self.workspace.is_dir():
            raise WorkspaceViolation("Workspace must be an existing directory.")
        self.allowed_extensions = tuple(ext.lower() for ext in allowed_extensions)
        self.max_file_bytes = max_file_bytes
        self.control_dir = self.workspace / ".repair-engine"
        self.staging_dir = self.control_dir / "staging"
        self.backup_dir = self.control_dir / "backups"
        self.control_dir.mkdir(mode=0o700, exist_ok=True)
        self.staging_dir.mkdir(mode=0o700, exist_ok=True)
        self.backup_dir.mkdir(mode=0o700, exist_ok=True)
        self.audit_path = self.control_dir / "audit.jsonl"
        self._candidates: dict[str, RepairCandidate] = {}

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _target_path(self, relative_path: str) -> Path:
        raw = Path(relative_path)
        if raw.is_absolute() or not raw.parts or ".." in raw.parts:
            raise WorkspaceViolation("Target must be a safe relative path inside the workspace.")
        target = (self.workspace / raw).resolve(strict=False)
        try: target.relative_to(self.workspace)
        except ValueError as exc: raise WorkspaceViolation("Target resolves outside the configured workspace.") from exc
        if target == self.control_dir or self.control_dir in target.parents:
            raise WorkspaceViolation("The engine's internal state cannot be a repair target.")
        if target.suffix.lower() not in self.allowed_extensions:
            raise WorkspaceViolation(f"File extension is not allowed: {target.suffix}")
        current = self.workspace
        for part in raw.parts:
            current = current / part
            if current.is_symlink(): raise WorkspaceViolation("Symlink targets are not allowed.")
        return target

    def _audit(self, event: str, **details: object) -> None:
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **details}
        fd = os.open(self.audit_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")

    def diagnose(self, relative_path: str) -> list[Diagnostic]:
        target = self._target_path(relative_path)
        if not target.is_file(): raise WorkspaceViolation("Target file does not exist.")
        if target.stat().st_size > self.max_file_bytes: raise ValidationFailure("Target exceeds size limit.")
        diagnostics = validate_python(target.read_text(encoding="utf-8"), max_bytes=self.max_file_bytes)
        self._audit("diagnose", target=relative_path, diagnostic_count=len(diagnostics))
        return diagnostics

    def stage_repair(self, relative_path: str, candidate_source: str, *, intent: str) -> RepairCandidate:
        target = self._target_path(relative_path)
        if not target.is_file(): raise WorkspaceViolation("Target must exist; creating new files is disabled.")
        if target.stat().st_size > self.max_file_bytes: raise ValidationFailure("Target exceeds size limit.")
        if not isinstance(candidate_source, str) or not intent.strip():
            raise ValidationFailure("Candidate source and a non-empty repair intent are required.")
        diagnostics = validate_python(candidate_source, max_bytes=self.max_file_bytes)
        original, candidate_bytes = target.read_bytes(), candidate_source.encode("utf-8")
        candidate_id = uuid.uuid4().hex
        staged_path = self.staging_dir / f"{candidate_id}.py"
        fd = os.open(staged_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream: stream.write(candidate_bytes)
        candidate = RepairCandidate(candidate_id, str(target.relative_to(self.workspace)), intent.strip()[:2000],
            datetime.now(timezone.utc).isoformat(), self._sha256(original), self._sha256(candidate_bytes), staged_path)
        self._candidates[candidate_id] = candidate
        self._audit("candidate_staged", candidate_id=candidate_id, target=candidate.target,
            original_sha256=candidate.original_sha256, candidate_sha256=candidate.candidate_sha256,
            diagnostic_count=len(diagnostics))
        return candidate

    def read_candidate(self, candidate_id: str) -> str:
        return self._get_candidate(candidate_id).staged_path.read_text(encoding="utf-8")

    def _get_candidate(self, candidate_id: str) -> RepairCandidate:
        candidate = self._candidates.get(candidate_id)
        if candidate is None or not candidate.staged_path.is_file():
            raise CandidateNotFound("Candidate is not available in this engine session.")
        return candidate

    def apply(self, candidate_id: str, *, approved: bool = False,
              expected_candidate_sha256: str = "") -> ApplyResult:
        if approved is not True: raise ApprovalRequired("An authorized operator must explicitly approve this candidate.")
        candidate = self._get_candidate(candidate_id)
        staged_bytes = candidate.staged_path.read_bytes()
        staged_hash = self._sha256(staged_bytes)
        if staged_hash != candidate.candidate_sha256 or staged_hash != expected_candidate_sha256:
            raise StaleCandidate("Candidate integrity check failed; stage and review it again.")
        target = self._target_path(candidate.target)
        current_bytes = target.read_bytes()
        if self._sha256(current_bytes) != candidate.original_sha256:
            raise StaleCandidate("Target changed after staging; refusing to overwrite newer work.")
        backup_name = (f"{candidate.target.replace('/', '__')}."
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.{uuid.uuid4().hex[:8]}.bak")
        backup_path = self.backup_dir / backup_name
        backup_path.write_bytes(current_bytes); os.chmod(backup_path, 0o600)
        fd, temp_name = tempfile.mkstemp(prefix=".repair-", suffix=target.suffix, dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(staged_bytes); stream.flush(); os.fsync(stream.fileno())
            os.chmod(temp_name, target.stat().st_mode & 0o777)
            os.replace(temp_name, target)
        except Exception:
            try: os.unlink(temp_name)
            except FileNotFoundError: pass
            raise
        self._audit("candidate_applied", candidate_id=candidate_id, target=candidate.target,
            backup=str(backup_path.relative_to(self.workspace)), applied_sha256=staged_hash)
        return ApplyResult(candidate.target, str(backup_path.relative_to(self.workspace)), staged_hash, candidate_id)

    def rollback_to_target(self, backup_relative_path: str, target_relative_path: str, *, approved: bool = False) -> str:
        if approved is not True: raise ApprovalRequired("Rollback requires explicit operator approval.")
        backup = (self.workspace / backup_relative_path).resolve(strict=True)
        try: backup.relative_to(self.backup_dir.resolve())
        except ValueError as exc: raise WorkspaceViolation("Rollback source must be an engine-generated backup.") from exc
        if backup.is_symlink() or not backup.is_file(): raise WorkspaceViolation("Backup is not a regular file.")
        target = self._target_path(target_relative_path)
        data = backup.read_bytes()
        validate_python(data.decode("utf-8"), max_bytes=self.max_file_bytes)
        fd, temp_name = tempfile.mkstemp(prefix=".rollback-", suffix=target.suffix, dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temp_name, target)
        except Exception:
            try: os.unlink(temp_name)
            except FileNotFoundError: pass
            raise
        self._audit("rollback", target=target_relative_path, backup=backup_relative_path,
                    restored_sha256=self._sha256(data))
        return target_relative_path
