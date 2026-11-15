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
- Opt-in SQLite persistent memory store with per-user isolation, export, deletion, and retention limits
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

## Opt-in persistent memory

`SQLiteMemoryStore` is a separate opt-in memory layer. It stores only records explicitly submitted to `remember()` after that user enables consent with `set_consent(user_id, True)`. Disabling consent deletes that user's stored records. Records are scoped by user ID, can be retrieved/exported/deleted, and are bounded by per-user and per-record limits. No conversation is automatically ingested.

Example:

    from sylvie_runtime import SQLiteMemoryStore
    memory = SQLiteMemoryStore("./data/sylvie-memory.sqlite3")
    memory.set_consent("user-123", True)
    memory.remember("user-123", "Prefers concise responses", category="preferences")
    saved = memory.retrieve("user-123")

The SQLite file is **not encrypted by this library**. Protect it and its backups with deployment-level access controls and encryption. User IDs must come from a trusted authenticated application layer; this package does not provide authentication. The store is local to the deployment and is not yet connected to `SylvieRuntime` automatically.


## Exchange pricing and prepaid credits

The initial pricing policy is **five free successful exchanges per customer account**, followed by **$0.25 USD per successful exchange**. One exchange is one customer message and its corresponding Sylvie reply. A failed provider request must release its reservation and must not consume a free exchange or paid credit.

The `ExchangeWallet` class provides a local SQLite ledger foundation:

    from sylvie_runtime import ExchangeWallet
    wallet = ExchangeWallet("./data/sylvie-wallet.sqlite3")

    # Before calling the AI provider, reserve the exchange:
    reservation = wallet.begin_exchange(authenticated_user_id, request_id)

    try:
        reply = provider.generate(messages)
    except Exception:
        wallet.fail_exchange(authenticated_user_id, reservation.reservation_id)
        raise
    else:
        wallet.complete_exchange(authenticated_user_id, reservation.reservation_id)

Paid exchanges reserve 25 cents before provider processing. Failed provider calls release that reservation. A successful exchange permanently consumes the free allowance or the 25-cent reservation. Requests need stable server-generated idempotency IDs. Do not trust user IDs, request IDs, or balance values supplied by a browser.

Prepaid top-ups are applied using `credit_wallet()` only after a trusted server has verified the Stripe webhook signature and confirmed the payment is successful, in the expected amount and currency, for the correct customer. The Stripe event ID is used for duplicate-event protection. Never expose this method to the browser. The current repository does not yet contain a production Stripe Checkout flow, webhook endpoint, refund/chargeback reconciliation, authentication, or a customer-facing wallet UI. Do not activate live customer charges until those pieces are implemented and tested.

Stripe's integration planner recommended evaluating Metronome for usage-based billing. For this low-value prepaid exchange model, this repository currently implements an internal prepaid ledger foundation; it does not yet connect Metronome or charge a card per message.

## Product architecture

AtlandiaScope.com is intended to become the parent website and customer portal. Sylvie should be embedded as its assistant, while AI Dialogue Gateway and Universal AI Diagnostics & Repair remain separately permissioned services. A shared API layer should handle authenticated customer identity, service-to-service authorization, usage metering, and Stripe billing. The current repository is the Sylvie Runtime and gateway foundation only; the unified AtlandiaScope site and cross-product integration are not yet implemented.

## Not included yet
- Web/API server, authentication, user accounts, rate limiting, or billing
- Web/API server, authentication, user accounts, rate limiting, or billing
- Voice, vision, autonomous actions, or tool execution
- Production deployment or multi-process session coordination
- Health-aware routing, quotas, cost controls, or streaming

## Safety and data boundaries
Sessions are held in process memory and disappear when the process exits. Do not put API keys in source code or commit them to the repository. A future API layer must add authentication, authorization, rate limiting, privacy controls, and secure secret management before public deployment. Tool integrations must use explicit per-tool permissions and operator approval for consequential actions.

This is a foundation package, not a live hosted Sylvie assistant.
