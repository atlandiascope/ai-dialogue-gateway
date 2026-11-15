import type { Config, Context } from "@netlify/functions";
import { db, error, json } from "../lib/shared.mts";

export default async (_req: Request, context: Context) => {
  const id = context.params.agentId || "";
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
};

export const config: Config = {
  path: "/api/agents/:agentId",
  method: "GET",
};
