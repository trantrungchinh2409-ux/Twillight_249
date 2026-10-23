export class Store {
  constructor(private db:D1Database) {}
  async reserve(key:string,group:string,now:number):Promise<boolean> {
    // D1 batch is transactional: cleanup + cooldown check + insert serialize in storage.
    const out=await this.db.batch([
      this.db.prepare('DELETE FROM deliveries WHERE expires_at <= ?').bind(now),
      this.db.prepare(`INSERT OR IGNORE INTO deliveries(event_key,group_key,reserved_at,expires_at,status)
        SELECT ?,?,?,?, 'reserved' WHERE NOT EXISTS
        (SELECT 1 FROM deliveries WHERE group_key=? AND reserved_at>?)`).bind(key,group,now,now+86400000,group,now-5000)
    ]);
    return out[1].meta.changes===1;
  }
  async finish(key:string,status:'sent'|'uncertain') {
    await this.db.prepare('UPDATE deliveries SET status=? WHERE event_key=?').bind(status,key).run();
  }
}
