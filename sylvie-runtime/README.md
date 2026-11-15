# Sylvie Runtime
**Preview 0.1.0 — provider-neutral conversation foundation**

Sylvie Runtime is a distinct component from the AI Dialogue Gateway and the Universal AI Diagnostics & Repair Engine.

## Included
- Provider-neutral chat adapter contract
- OpenAI Chat Completions adapter
- Anthropic Messages API adapter
- Offline deterministic provider for development and tests
- Conversation creation and ordered message handling
- Bounded, process-local conversation history
- Input size checks and explicit provider status
- Provider adapters return text only; no tool/function execution is enabled

## Install
Install the selected package and optional test dependencies:

    python -m pip install -e "./sylvie-runtime[dev]"

## Configure either provider

Set credentials in the runtime environment. Never commit API keys or put them in source files.

OpenAI:

    export OPENAI_API_KEY="..."
    from sylvie_runtime import OpenAIChatProvider, SylvieRuntime
    sylvie = SylvieRuntime(OpenAIChatProvider(model="YOUR_OPENAI_MODEL"))

Anthropic:

    export ANTHROPIC_API_KEY="..."
    from sylvie_runtime import AnthropicChatProvider, SylvieRuntime
    sylvie = SylvieRuntime(AnthropicChatProvider(model="YOUR_ANTHROPIC_MODEL"))

Both adapters can be used through the same runtime interface. The model name is explicit so deployments can choose and update models without changing Sylvie's conversation code. Credentials may also be passed directly to adapter constructors from a secure secret manager at runtime; do not hardcode them.

Offline development:

    from sylvie_runtime import LocalTestProvider, SylvieRuntime
    sylvie = SylvieRuntime(LocalTestProvider())
    session = sylvie.create_conversation()
    reply = sylvie.send(session, "Hello")
    print(reply.content)

The local provider is a test adapter, not an AI model.

## API behavior and boundaries
- OpenAI uses the Chat Completions endpoint.
- Anthropic uses the Messages endpoint and sends system instructions separately.
- Both use HTTPS, bounded request timeouts, and a 2 MB response limit.
- Provider response bodies are not copied into raised HTTP error messages.
- Only system, user, and assistant text messages are accepted.
- No tools, function calls, external actions, or automatic repair authority are enabled.

## Not included yet
- Persistent memory or database storage
- Web/API server, authentication, user accounts, rate limiting, or billing
- Voice, vision, autonomous actions, or tool execution
- Production deployment or multi-process session coordination
- Automatic provider failover or model routing

## Safety and data boundaries
Sessions are held in process memory and disappear when the process exits. Do not put API keys in source code or commit them to the repository. A future API layer must add authentication, authorization, rate limiting, privacy controls, and secure secret management before public deployment. Tool integrations must use explicit per-tool permissions and operator approval for consequential actions.

This is a foundation package, not a live hosted Sylvie assistant.
