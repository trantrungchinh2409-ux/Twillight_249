CREATE TABLE IF NOT EXISTS deliveries (
  event_key TEXT PRIMARY KEY,
  group_key TEXT NOT NULL,
  reserved_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('reserved','sent','uncertain'))
);
CREATE INDEX IF NOT EXISTS deliveries_expiry ON deliveries(expires_at);
CREATE INDEX IF NOT EXISTS deliveries_group_time ON deliveries(group_key,reserved_at);
