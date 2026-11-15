import type { Config } from "@netlify/functions";
import { db } from "../lib/shared.mts";

export default async () => {
  await db.sql`
    DELETE FROM gateway_messages
    WHERE created_at < NOW() - INTERVAL '30 days'
  `;
  return new Response("Expired messages cleaned up.", { status: 200 });
};

export const config: Config = {
  schedule: "0 3 * * *",
};
