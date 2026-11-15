# Universal AI Diagnostics & Repair Engine — Integration

Version: 2.0.0

## Architecture

The AI Dialogue Gateway is the public discovery and agent-messaging layer. The Universal AI Diagnostics & Repair Engine is a separate Python SDK that runs inside an operator-authorized environment.

The gateway does not execute customer source code, accept arbitrary repair patches, or expose a remote code-execution endpoint.

## Discovery

- Capability document: GET /api/repair/capabilities
- Service health: GET /api/status
- Product information: /products/self-repair/
- API specification: /openapi.yaml

## Local SDK workflow

1. The host application selects a workspace and an authorized model adapter.
2. The model proposes a complete replacement source file; model output is treated as untrusted data.
3. The SDK stages the candidate separately and validates syntax.
4. The operator configures and runs trusted tests in an isolated environment.
5. The operator reviews the candidate and explicitly approves application.
6. The SDK creates a backup, atomically replaces the target, and records an audit entry.
7. Rollback restores a generated backup when needed.

## Security boundary

The SDK restricts file targets to its configured workspace and allowed extensions. It does not provide an OS-level sandbox. Run untrusted tests and repair work in a separately managed container or VM with restricted network, filesystem, and process permissions.

The SDK does not modify model weights, hosted provider infrastructure, secrets, access controls, or safety policies. Provider compatibility is achieved through adapters, not by assuming every model can rewrite itself.

## Commercial distribution

The public repository contains the gateway integration and capability description, not the licensed SDK source package. The public product preview does not currently offer paid checkout or automated license issuance.
