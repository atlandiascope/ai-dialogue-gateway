import { getDatabase } from "@netlify/database";

export const db = getDatabase();

export function json(data: unknown, status = 200) {
  return Response.json(data, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export function error(message: string, status = 400) {
  return json({ error: message }, status);
}

export async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function authenticate(req: Request) {
  const header = req.headers.get("authorization") || "";
  const match = header.match(/^Bearer\s+(agw_[A-Za-z0-9_-]{40,})$/);
  if (!match) return null;

  const keyHash = await sha256(match[1]);
  const rows = await db.sql<{
    id: string;
    name: string;
    disabled_at: string | null;
  }>`
    SELECT id, name, disabled_at
    FROM gateway_agents
    WHERE api_key_hash = ${keyHash}
    LIMIT 1
  `;
  const agent = rows[0];
  if (!agent || agent.disabled_at) return null;
  return agent;
}

export function validJsonContentType(req: Request) {
  return (req.headers.get("content-type") || "")
    .toLowerCase()
    .includes("application/json");
}
