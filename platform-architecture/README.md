# AtlandiaScope Shared Platform Architecture

## Product direction

AtlandiaScope.com is the parent website and customer portal. It owns the customer experience, account navigation, billing experience, and product directory. Sylvie is embedded as the primary assistant. The following remain independently deployed product services:

- Sylvie Runtime
- AI Dialogue Gateway
- Universal AI Diagnostics & Repair Engine

A shared platform layer connects them through authenticated APIs and explicit permissions. Product services must not share unrestricted database credentials or trust browser-supplied identity, balances, or entitlements.

## Customer journey

1. A customer creates one AtlandiaScope account.
2. The AtlandiaScope identity provider authenticates the customer.
3. The website obtains a server-verified identity token.
4. The platform maps the verified identity subject to an internal customer ID.
5. The customer opens Sylvie, the Dialogue Gateway, or Diagnostics & Repair according to account entitlements.
6. The platform checks product and action-specific permissions on every API request.
7. Sylvie checks the exchange wallet before processing a message.
8. After the five introductory successful exchanges, each successful exchange costs 25 USD cents and is deducted from prepaid credits.

## Identity integration boundary

The current GitHub repository does not contain the AtlandiaScope.com source or identify its identity provider. This repository deliberately does not invent a login implementation or accept unverified JWTs.

The sylvie_runtime.platform.CustomerPrincipal is an internal authorization object. It may only be created by a future authentication adapter after validating token signature, issuer, audience, expiry, and subject against the selected identity provider. Browser JSON, query parameters, and unverified token payloads must never be used to create a principal.

The production platform must decide and configure the identity provider and issuer, allowed token audiences, signing-key/JWKS rotation, customer subject-to-internal-ID mapping, and session revocation/account deletion lifecycle.

## Permission model

Product scopes:
- product:sylvie:use
- product:dialogue_gateway:use
- product:diagnostics_repair:use

Action scopes:
- service:gateway:send
- service:gateway:read_inbox
- service:repair:diagnose
- service:repair:propose
- service:repair:apply

Repair application must remain approval-gated. A customer entitlement to use Diagnostics & Repair is not permission to apply code changes without required operator approval.

## Shared API outline

The AtlandiaScope domain should eventually expose versioned server-side endpoints:
- GET /api/platform/me — verified customer profile and entitlements
- GET /api/platform/products — products available to this account
- GET /api/platform/wallet — free exchanges remaining and prepaid credit balance
- POST /api/sylvie/exchanges — create one metered exchange
- POST /api/platform/credits/checkout — create a Stripe Checkout Session for a selected credit bundle
- POST /api/platform/stripe/webhook — verify Stripe signatures and idempotently apply successful top-ups
- POST /api/gateway/... — proxy authorized agent messaging
- POST /api/diagnostics/... — invoke authorized diagnostics operations

The browser must never receive Stripe secret keys, webhook secrets, provider API keys, or direct database credentials.

## Billing rules

- Five successful introductory exchanges per internal customer account, not per browser or device.
- One exchange is one customer message plus its corresponding Sylvie reply.
- Each subsequent successful exchange consumes 25 cents from prepaid credits.
- Reserve credit before provider execution; release it if the provider fails before a reply is delivered.
- Use a server-generated stable idempotency key per request.
- Apply wallet top-ups only after server-side Stripe webhook signature verification and payment validation.
- Handle refunds, disputes, and chargebacks with an auditable ledger adjustment policy before live launch.
- Display exchange history, free allowance, and remaining balance to the customer.
- Do not activate live charges until authentication, Checkout, webhook processing, reconciliation, and end-to-end tests are complete.

## Deployment plan

1. Identify the existing AtlandiaScope.com source repository and hosting project.
2. Confirm the customer identity provider and account model.
3. Add the shared API and identity adapter to the actual parent-site deployment.
4. Connect Sylvie Runtime to authenticated sessions and the exchange wallet.
5. Add Stripe Checkout, verified webhooks, and customer wallet UI.
6. Connect Dialogue Gateway and Diagnostics through narrowly scoped service APIs.
7. Test cross-customer isolation, expired/revoked sessions, missing entitlements, duplicate requests, provider failures, payment failures, refunds, and repair approval boundaries.
8. Deploy to staging, then production after acceptance tests.

## Current implementation status

Implemented in this repository: Sylvie Runtime with OpenAI and Anthropic adapters and provider routing; explicit-consent SQLite memory; SQLite prepaid exchange ledger; internal customer principal and product/action scope authorization primitives; shared-platform architecture contract.

Not implemented: AtlandiaScope.com website integration; customer login or selected identity provider; token verification/JWKS adapter; customer-to-Stripe mapping; production Stripe Checkout or webhook endpoint; customer wallet UI; cross-product proxy APIs; live Sylvie chat endpoint or deployment.

This document describes the target architecture and does not imply that products are already connected.
