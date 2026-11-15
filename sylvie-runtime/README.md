# Sylvie Runtime
**Preview 0.1.0 — provider-neutral conversation foundation**

Sylvie Runtime is a distinct component from the AI Dialogue Gateway and the Universal AI Diagnostics & Repair Engine.

## Included
- Provider-neutral chat adapter contract
- OpenAI Chat Completions adapter
- Anthropic Messages API adapter
- Provider router with configurable primary and secondary
- Per-request automatic fallback on provider request failures
- Offline deterministic provider for development and tests
- Conversation creation and ordered message handling
- Bounded, process-local conversation history
- Input size checks and explicit provider status
- Provider adapters return text only; no tool/function execution is enabled

## Install

    python -m pip install -e "./sylvie-runtime[dev]"

## Configure both providers

Set credentials in the runtime environment or load them from a secure secret manager. Never commit API keys or put them in source files.

    export OPENAI_API_KEY="..."
    export ANTHROPIC_API_KEY="..."

Example configuration (choose model names appropriate to your accounts):

    from sylvie_runtime import (
        AnthropicChatProvider, OpenAIChatProvider, ProviderRouter, SylvieRuntime
    )

    openai = OpenAIChatProvider(model="YOUR_OPENAI_MODEL")
    anthropic = AnthropicChatProvider(model="YOUR_ANTHROPIC_MODEL")
    router = ProviderRouter(
        primary=openai,
        secondary=anthropic,
        automatic_fallback=True,
    )
    sylvie = SylvieRuntime(router)

To switch the preferred provider at runtime:

    router.set_primary("anthropic")  # or "openai"

The router tries the configured primary first. If it raises ProviderRequestError, it tries the secondary for that request. Failover does not silently change the configured primary. Invalid input and programming/configuration errors are not treated as provider outages. Check router.status() to inspect primary, secondary, fallback setting, and last provider used.

Offline development:

    from sylvie_runtime import LocalTestProvider, SylvieRuntime
    sylvie = SylvieRuntime(LocalTestProvider())
    session = sylvie.create_conversation()
    reply = sylvie.send(session, "Hello")
    print(reply.content)

The local provider is a test adapter, not an AI model.

## API behavior and boundaries
- OpenAI uses the Chat Completions endpoint.
- Anthropic uses the Messages endpoint and receives system instructions separately.
- Both use HTTPS, bounded request timeouts, and a 2 MB response limit.
- Provider response bodies are not copied into raised HTTP error messages.
- Only system, user, and assistant text messages are accepted.
- No tools, function calls, external actions, or automatic repair authority are enabled.

## Not included yet
- Persistent memory or database storage
- Web/API server, authentication, user accounts, rate limiting, or billing
- Voice, vision, autonomous actions, or tool execution
- Production deployment or multi-process session coordination
- Health-aware routing, quotas, cost controls, or streaming

## Safety and data boundaries
Sessions are held in process memory and disappear when the process exits. Do not put API keys in source code or commit them to the repository. A future API layer must add authentication, authorization, rate limiting, privacy controls, and secure secret management before public deployment. Tool integrations must use explicit per-tool permissions and operator approval for consequential actions.

This is a foundation package, not a live hosted Sylvie assistant.
