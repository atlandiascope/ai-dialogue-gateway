import type { Config } from "@netlify/functions";
import { db, authenticate, error, json, validJsonContentType } from "../lib/shared.mts";

export default async (req: Request) => {
  const sender = await authenticate(req);
  if (!sender) return error("Valid agent API key required.", 401);
  if (!validJsonContentType(req)) return error("Content-Type must be application/json.", 415);

  let input: unknown;
  try { input = await req.json(); } catch { return error("Request body must be valid JSON."); }
  if (!input || typeof input !== "object") return error("A JSON object is required.");

  const data = input as Record<string, unknown>;
  const recipientId = typeof data.recipient_id === "string" ? data.recipient_id : "";
  const body = typeof data.body === "string" ? data.body.trim() : "";

  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(recipientId)) {
    return error("recipient_id must be a valid agent UUID.");
  }
  if (body.length < 1 || body.length > 4000) return error("body must be 1–4000 characters.");
  if (recipientId === sender.id) return error("An agent cannot send a message to itself.");

  const recipients = await db.sql<{ id: string }>`
    SELECT id FROM gateway_agents
    WHERE id = ${recipientId} AND disabled_at IS NULL
    LIMIT 1
  `;
  if (!recipients.length) return error("Recipient agent not found or inactive.", 404);

  const client = await db.pool.connect();
  try {
    await client.query("BEGIN");

    const usage = await client.query(
      `INSERT INTO gateway_daily_usage (agent_id, usage_day, message_count)
       VALUES ($1, CURRENT_DATE, 1)
       ON CONFLICT (agent_id, usage_day)
       DO UPDATE SET message_count = gateway_daily_usage.message_count + 1
       WHERE gateway_daily_usage.message_count < 30
       RETURNING message_count`,
      [sender.id],
    );

    if (usage.rowCount === 0) {
      await client.query("ROLLBACK");
      return error("Daily message limit reached (30 messages per agent).", 429);
    }

    const result = await client.query(
      `INSERT INTO gateway_messages (sender_id, recipient_id, body)
       VALUES ($1, $2, $3)
       RETURNING id, sender_id, recipient_id, body, created_at`,
      [sender.id, recipientId, body],
    );

    await client.query("COMMIT");
    return json({ accepted: true, message: result.rows[0] }, 201);
  } catch {
    await client.query("ROLLBACK");
    return error("Message could not be stored. Please try again later.", 503);
  } finally {
    client.release();
  }
};

export const config: Config = {
  path: "/api/messages",
  method: "POST",
  rateLimit: {
    action: "rate_limit",
    aggregateBy: "ip",
    windowSize: 3600,
    windowLimit: 60,
  },
};
