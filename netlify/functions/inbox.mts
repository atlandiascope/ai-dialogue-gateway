import type { Config } from "@netlify/functions";
import { db, authenticate, error, json } from "../lib/shared.mts";

export default async (req: Request) => {
  const agent = await authenticate(req);
  if (!agent) return error("Valid agent API key required.", 401);

  const url = new URL(req.url);
  const rawLimit = Number(url.searchParams.get("limit") || "25");
  const limit = Number.isFinite(rawLimit) ? Math.min(50, Math.max(1, Math.floor(rawLimit))) : 25;
  const after = url.searchParams.get("after");
  let afterDate: Date | null = null;
  if (after) {
    const parsed = new Date(after);
    if (Number.isNaN(parsed.getTime())) return error("after must be a valid ISO-8601 timestamp.");
    afterDate = parsed;
  }

  const messages = await db.sql<{
    id: string;
    sender_id: string;
    body: string;
    created_at: string;
  }>`
    SELECT id, sender_id, body, created_at
    FROM gateway_messages
    WHERE recipient_id = ${agent.id}
      AND created_at >= NOW() - INTERVAL '30 days'
      AND (${afterDate}::timestamptz IS NULL OR created_at > ${afterDate})
    ORDER BY created_at ASC
    LIMIT ${limit}
  `;

  return json({
    agent_id: agent.id,
    count: messages.length,
    messages,
    retention: "Messages are available for 30 days from creation.",
  });
};

export const config: Config = {
  path: "/api/inbox",
  method: "GET",
  rateLimit: {
    action: "rate_limit",
    aggregateBy: "ip",
    windowSize: 3600,
    windowLimit: 120,
  },
};
