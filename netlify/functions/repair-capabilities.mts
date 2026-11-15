import type { Config } from "@netlify/functions";
import { json } from "../lib/shared.mts";

export default async () => json({
  product: {
    id: "universal-ai-diagnostics-repair",
    name: "Universal AI Diagnostics & Repair Engine",
    version: "2.0.0",
    availability: "integration-preview",
    source_distribution: "licensed-package-not-public",
  },
  compatibility: {
    provider_neutral: true,
    integration_modes: ["python-sdk", "rest-adapter", "mcp-adapter-planned"],
    model_providers: ["OpenAI", "Anthropic", "Google", "Meta", "Mistral", "local-models", "custom"],
    note: "Compatibility is through adapters and does not imply access to model weights, vendor internals, or permission to modify a hosted model."
  },
  capabilities: [
    "source-diagnostics",
    "candidate-repair-staging",
    "syntax-validation",
    "operator-configured-tests",
    "sha256-candidate-integrity",
    "operator-approved-atomic-apply",
    "timestamped-backups",
    "rollback",
    "audit-log"
  ],
  safety: {
    workspace_boundary: true,
    explicit_approval_before_live_changes: true,
    remote_code_execution: false,
    automatic_production_deployment: false,
    secrets_or_policy_modification: "not-authorized",
    untrusted_model_output: "treated-as-data-and-validated",
    isolation_note: "Run repair and test workflows inside an operator-managed container or virtual machine. The SDK is not an operating-system sandbox."
  },
  integration: {
    gateway_status: "/api/status",
    capabilities: "/api/repair/capabilities",
    product_page: "/products/self-repair/",
    openapi: "/openapi.yaml"
  }
});

export const config: Config = {
  path: "/api/repair/capabilities",
  method: "GET",
};
