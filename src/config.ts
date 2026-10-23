export interface Env {
  DB: D1Database;
  ZALO_BOT_TOKEN?: string;
  ZALO_WEBHOOK_SECRET?: string;
  BOT_ID: string;
  BOT_ENABLED: string;
  ALLOWED_GROUP_IDS: string;
}
export function config(env: Env) {
  const groups: unknown = JSON.parse(env.ALLOWED_GROUP_IDS);
  if (!Array.isArray(groups) || !groups.every(x => typeof x === 'string' && x.length > 0)) throw new Error('config');
  return {enabled: env.BOT_ENABLED === 'true', botId: env.BOT_ID, groups: new Set<string>(groups)};
}
