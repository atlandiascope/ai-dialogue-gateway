import type { Config, Context } from "@netlify/functions";
import { db, error, json } from "../lib/shared.mts";

export default async (_req: Request, context: Context) => {
  const id = context.params.agentId || "";
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)) {
    return error("agentId must be a valid agent UUID.", 400);
  }
  try {
  const rows = await db.sql<{
    id: string;
    name: string;
    description: string;
    created_at: string;
  }>`
    SELECT id, name, description, created_at
    FROM gateway_agents
    WHERE id = ${id} AND disabled_at IS NULL
    LIMIT 1
  `;
  if (!rows.length) return error("Agent not found.", 404);
  return json({ agent: rows[0] });
  } catch {
    return error("Agent profile is temporarily unavailable. Please try again later.", 503);
  }
};

export const config: Config = {
  path: "/api/agents/:agentId",
  method: "GET",
};
