import type { Config } from "@netlify/functions";
import { db, error, json, sha256, validJsonContentType } from "../lib/shared.mts";

function makeApiKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return "agw_" + btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export default async (req: Request) => {
  if (!validJsonContentType(req)) return error("Content-Type must be application/json.", 415);

  let input: unknown;
  try { input = await req.json(); } catch { return error("Request body must be valid JSON."); }
  if (!input || typeof input !== "object") return error("A JSON object is required.");

  const data = input as Record<string, unknown>;
  const name = typeof data.name === "string" ? data.name.trim() : "";
  const description = typeof data.description === "string" ? data.description.trim() : "";

  if (name.length < 2 || name.length > 80) return error("name must be 2–80 characters.");
  if (description.length > 280) return error("description must be 280 characters or fewer.");

  const apiKey = makeApiKey();
  const keyHash = await sha256(apiKey);

  try {
    const rows = await db.sql<{ id: string; name: string; created_at: string }>`
      INSERT INTO gateway_agents (name, description, api_key_hash)
      VALUES (${name}, ${description}, ${keyHash})
      RETURNING id, name, created_at
    `;
    const agent = rows[0];
    return json({
      registered: true,
      agent,
      api_key: apiKey,
      key_notice: "This key is shown once. Store it securely. The gateway stores only its SHA-256 hash.",
      next_step: "Send messages with Authorization: Bearer YOUR_API_KEY.",
    }, 201);
  } catch {
    return error("Registration could not be completed. Please try again later.", 503);
  }
};

export const config: Config = {
  path: "/api/agents/register",
  method: "POST",
  rateLimit: {
    action: "rate_limit",
    aggregateBy: "ip",
    windowSize: 3600,
    windowLimit: 5,
  },
};
