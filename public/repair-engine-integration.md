# Universal AI Diagnostics & Repair Engine — Integration

SDK preview: 0.1.0

## Architecture

The AI Dialogue Gateway is the public discovery and agent-messaging layer. The repair engine is a separate Python SDK that runs inside an operator-authorized environment.

The gateway does not execute customer source code, accept arbitrary repair patches, or expose a remote code-execution endpoint.

## Available SDK functions

The initial package lives in `repair-engine/` in the GitHub repository.

- Inspect an existing Python file and run static syntax diagnostics.
- Stage a complete replacement source file without changing the live target.
- Verify candidate SHA-256 and detect if the target changed after staging.
- Require explicit operator approval before applying.
- Create a backup, atomically replace the file, and record an audit event.
- Restore a generated backup with explicit approval.

## Local SDK workflow

1. The host application selects an authorized workspace.
2. A model adapter (to be added) proposes a complete replacement source file; output is untrusted.
3. The SDK stages the candidate separately and validates Python syntax.
4. The operator reviews the staged source and its hash.
5. The operator explicitly approves application.
6. The SDK creates a backup, atomically replaces the target, and records an audit entry.
7. Rollback restores a generated backup when needed.

## Not implemented in 0.1.0

Provider adapters, automatic test execution, an OS/container sandbox, remote repair execution, commercial packaging, license issuance, and billing.

## Security boundary

The SDK restricts file targets to its configured workspace and allowed extensions. It rejects parent traversal and symlink targets. It does not provide an OS-level sandbox and does not execute model-generated code. Run untrusted repair workers and tests in a separately managed container or VM with restricted network, filesystem, and process permissions.

The SDK does not modify model weights, hosted provider infrastructure, secrets, access controls, or safety policies. Provider compatibility will be achieved through adapters, not by assuming every model can rewrite itself.

## Distribution

The SDK source is available for preview in the repository under `repair-engine/`. It is not yet a licensed commercial release and there is no paid checkout or automated license issuance.
