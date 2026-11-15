# Sylvie Runtime
**Preview 0.1.0 — conversation foundation**

Sylvie Runtime is a distinct component from the AI Dialogue Gateway and the Universal AI Diagnostics & Repair Engine.

## Included
- Provider-neutral chat adapter contract
- Offline deterministic provider for development and tests
- Conversation creation and ordered message handling
- Bounded, process-local conversation history
- Input size checks and explicit provider status

## Not included yet
- Live model-provider adapters or credentials
- Persistent memory or database storage
- Web/API server, authentication, user accounts, rate limiting, or billing
- Voice, vision, autonomous actions, or tool execution
- Production deployment or multi-process session coordination

## Quick start
Install the package in editable mode, then:

    from sylvie_runtime import LocalTestProvider, SylvieRuntime

    sylvie = SylvieRuntime(LocalTestProvider())
    session = sylvie.create_conversation()
    reply = sylvie.send(session, "Hello")
    print(reply.content)

The local provider is a test adapter, not an AI model. Implement ChatProvider to connect a selected model provider. Provider adapters return text only; they do not receive implicit tool execution authority.

## Safety and data boundaries
Sessions are held in process memory and disappear when the process exits. Do not put API keys in source code or commit them to the repository. A future API layer must add authentication, authorization, rate limiting, privacy controls, and secure secret management before public deployment. Tool integrations must use explicit per-tool permissions and operator approval for consequential actions.

This is a foundation package, not a live hosted Sylvie assistant.
