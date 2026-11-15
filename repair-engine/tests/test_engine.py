import pytest
from universal_ai_repair import ApprovalRequired, RepairEngine, StaleCandidate, ValidationFailure, WorkspaceViolation

def test_stage_apply_and_rollback(tmp_path):
    target = tmp_path / "app.py"
    target.write_text("def value():\n    return 1\n", encoding="utf-8")
    engine = RepairEngine(tmp_path)
    candidate = engine.stage_repair("app.py", "def value():\n    return 2\n", intent="Fix value")
    assert "return 2" in engine.read_candidate(candidate.candidate_id)
    with pytest.raises(ApprovalRequired):
        engine.apply(candidate.candidate_id, expected_candidate_sha256=candidate.candidate_sha256)
    result = engine.apply(candidate.candidate_id, approved=True, expected_candidate_sha256=candidate.candidate_sha256)
    assert "return 2" in target.read_text(encoding="utf-8")
    engine.rollback_to_target(result.backup, result.target, approved=True)
    assert "return 1" in target.read_text(encoding="utf-8")

def test_rejects_stale_target(tmp_path):
    target = tmp_path / "app.py"; target.write_text("x = 1\n", encoding="utf-8")
    engine = RepairEngine(tmp_path)
    candidate = engine.stage_repair("app.py", "x = 2\n", intent="Update")
    target.write_text("x = 3\n", encoding="utf-8")
    with pytest.raises(StaleCandidate):
        engine.apply(candidate.candidate_id, approved=True, expected_candidate_sha256=candidate.candidate_sha256)

def test_rejects_invalid_python(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    engine = RepairEngine(tmp_path)
    with pytest.raises(ValidationFailure):
        engine.stage_repair("app.py", "def broken(:\n", intent="Invalid")

def test_rejects_path_escape(tmp_path):
    engine = RepairEngine(tmp_path)
    with pytest.raises(WorkspaceViolation):
        engine.diagnose("../outside.py")
