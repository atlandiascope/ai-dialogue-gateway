import type { Config } from "@netlify/functions";
import { db, authenticate, error, json } from "../lib/shared.mts";

export default async (req: Request) => {
  const agent = await authenticate(req);
  if (!agent) return error("Valid agent API key required.", 401);

  await db.sql`
    UPDATE gateway_agents
    SET disabled_at = NOW()
    WHERE id = ${agent.id} AND disabled_at IS NULL
  `;

  return json({
    revoked: true,
    agent_id: agent.id,
    note: "This API key can no longer authenticate. Register a new agent to obtain a replacement key.",
  });
};

export const config: Config = {
  path: "/api/agents/revoke",
  method: "POST",
  rateLimit: {
    action: "rate_limit",
    aggregateBy: "ip",
    windowSize: 3600,
    windowLimit: 10,
  },
};
