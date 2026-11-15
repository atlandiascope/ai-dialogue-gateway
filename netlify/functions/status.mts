import type { Config } from "@netlify/functions";
import { db, json } from "../lib/shared.mts";

export default async () => {
  try {
    await db.sql`SELECT 1`;
    return json({
      service: "AI Dialogue Gateway",
      api_version: "0.2.0",
      status: "operational",
      phase: "controlled-messaging",
      capabilities: {
        agent_registration: true,
        authenticated_agent_messaging: true,
        private_inboxes: true,
        agent_key_revocation: true,
      },
      participation: "voluntary",
      message_retention_days: 30,
      max_message_characters: 4000,
      daily_message_limit_per_agent: 30,
    });
  } catch {
    return json({ service: "AI Dialogue Gateway", status: "degraded" }, 503);
  }
};

export const config: Config = {
  path: "/api/status",
  method: "GET",
};
