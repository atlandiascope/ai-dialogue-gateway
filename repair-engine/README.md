# Universal AI Diagnostics & Repair Engine
**SDK preview 0.1.0 — local Python workspace MVP**

This executable SDK is separate from the public AI Dialogue Gateway. The gateway provides discovery and agent messaging; this package stages and applies local repairs in an operator-authorized workspace.

## Included
- Workspace-confined Python source inspection and syntax diagnostics
- Candidate staging without changing live files
- SHA-256 integrity checks and stale-target detection
- Explicit approval before applying a candidate
- Timestamped backups, rollback, and JSONL audit events
- Atomic file replacement

## Not included yet
Provider adapters, automatic test execution, OS/container sandboxing, remote repair execution, license issuance, billing, or production deployment.

The SDK never executes model-generated code or test commands. Run untrusted repair workers and tests inside an operator-managed container/VM with restricted filesystem, network, process, and credentials. This Python library is not a security sandbox.

## Install
```bash
python -m pip install ./repair-engine
```

## Controlled repair
```python
from universal_ai_repair import RepairEngine
engine = RepairEngine("./my-project")
diagnostics = engine.diagnose("app.py")

# Supply a complete replacement file from your selected model adapter.
candidate = engine.stage_repair("app.py", candidate_source="def greet(name):\\n    return f'Hello, {name}!'\\n",
                                intent="Replace the greeting implementation.")
print(engine.read_candidate(candidate.candidate_id))
print(candidate.candidate_sha256)

# Only after an authorized operator reviews and approves:
result = engine.apply(candidate.candidate_id, approved=True,
                      expected_candidate_sha256=candidate.candidate_sha256)
engine.rollback_to_target(result.backup, result.target, approved=True)
```

## Two modes
**Controlled repair:** diagnose, generate, stage, validate, review, approve, apply.

**Sandboxed automatic repair:** a separate worker may diagnose, generate, stage, and test inside an isolated container/VM. This package does not create that isolation. Applying changes to a host/production workspace still requires operator approval.

## Safety boundaries
Existing files only; default extension `.py`; rejects absolute paths, parent traversal, symlinks, and engine state directory. Candidate source is syntax-checked but never executed. Apply requires explicit approval, candidate SHA-256, and an unchanged original target hash. Backups and audit records live under `.repair-engine/`.

## Sylvie prototype migration
The supplied `sylvie_self_update.py` fetched arbitrary remote code and wrote it directly to files, appended patch text unsafely, and had fragile rollback/logging. This SDK replaces that model with staged full-file candidates, workspace checks, validation, approval, backups, and rollback. It does not silently install executable remote updates.
