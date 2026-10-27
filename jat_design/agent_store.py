"""User-scoped DPAPI identity/session store; never a log of the group."""
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from .webhook_switch import protect

ALIASES = (('Hoàng Giáp','LÊ KHẢI GIÁP'),('Bạn (phó nhóm)','AI JAT'),
           ('Bot JAT Design','BOT JAT DESIGN'),('Bùi Quang Khải(C lò xo)','KHẢI LÒ XO'),
           ('Đăng','ĐĂNG Đ'),('Đức Mười','NGUYỄN VĂN MƯỜI'),('Trịnh Quang Thành','THÀNH BỐC PHÉC'))


def key(*values):
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


class AgentStore:
    def __init__(self,path,clock=time.time):
        self.clock=clock
        self.db=sqlite3.connect(str(path))
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('CREATE TABLE IF NOT EXISTS agent_members(k TEXT PRIMARY KEY,g TEXT NOT NULL,a TEXT NOT NULL,p BLOB NOT NULL,UNIQUE(g,a))')
        self.db.execute('CREATE TABLE IF NOT EXISTS agent_sessions(k TEXT PRIMARY KEY,g TEXT NOT NULL,v TEXT NOT NULL,expires REAL NOT NULL,p BLOB NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS agent_user_limits(k TEXT PRIMARY KEY,next_at REAL NOT NULL)')
        self.db.commit();self.prune()

    def close(self):self.db.close()
    def encode(self,data):
        raw=json.dumps(data,ensure_ascii=False).encode()
        if len(raw)>32768:raise ValueError('Agent data limit')
        encrypted=protect(raw)
        if protect(encrypted,decrypt=True)!=raw:raise ValueError('Agent DPAPI roundtrip failed')
        return encrypted
    def decode(self,blob):
        if len(blob)>65536:raise ValueError('Agent data limit')
        return json.loads(protect(blob,decrypt=True))
    def prune(self):
        with self.db:
            self.db.execute('DELETE FROM agent_sessions WHERE expires<=?',(self.clock(),))
            self.db.execute('DELETE FROM agent_user_limits WHERE next_at<?',(self.clock()-300,))
    def bind(self,bot,group,sender,alias,replace=False):
        if not all(isinstance(v,str) and v.strip() for v in (bot,group,sender,alias)) or len(alias)>64 or any(ord(c)<32 for c in alias):
            raise ValueError('Invalid identity')
        k,g,a=key(bot,group,sender),key(bot,group),key(alias.casefold())
        row=self.db.execute('SELECT k FROM agent_members WHERE g=? AND a=?',(g,a)).fetchone()
        if row and row[0]!=k:raise ValueError('Alias already bound to another account; unbind explicitly')
        previous=self.db.execute('SELECT a FROM agent_members WHERE k=?',(k,)).fetchone()
        if previous and previous[0]!=a and not replace:raise ValueError('Explicit rename confirmation required')
        blob=self.encode({'bot':bot,'group':group,'sender':sender,'alias':alias})
        with self.db:self.db.execute('INSERT OR REPLACE INTO agent_members VALUES (?,?,?,?)',(k,g,a,blob))
    def alias(self,bot,group,sender):
        row=self.db.execute('SELECT p FROM agent_members WHERE k=?',(key(bot,group,sender),)).fetchone()
        if not row:return 'bạn'
        d=self.decode(row[0])
        if (d.get('bot'),d.get('group'),d.get('sender'))!=(bot,group,sender):raise ValueError('Identity binding mismatch')
        return d['alias']
    def unbind(self,bot,group,alias):
        with self.db:self.db.execute('DELETE FROM agent_members WHERE g=? AND a=?',(key(bot,group),key(alias.casefold())))
    def bound(self,bot,group,alias):
        return self.db.execute('SELECT 1 FROM agent_members WHERE g=? AND a=?',(key(bot,group),key(alias.casefold()))).fetchone() is not None
    def session(self,bot,group,sender):
        self.prune()
        row=self.db.execute('SELECT v,expires,p FROM agent_sessions WHERE k=?',(key(bot,group,sender),)).fetchone()
        if not row:return None
        data=self.decode(row[2])
        if (data.get('bot'),data.get('group'),data.get('sender'))!=(bot,group,sender):raise ValueError('Session identity mismatch')
        history=data.get('history')
        if not isinstance(history,list) or len(history)>6 or any(not isinstance(t,list) or len(t)!=2 or not all(isinstance(x,str) for x in t) for t in history):
            raise ValueError('Invalid session history')
        return {'version':row[0],'expires':row[1],'history':history}
    def touch(self,bot,group,sender):
        current=self.session(bot,group,sender)
        version=current['version'] if current else secrets.token_hex(16)
        history=current['history'] if current else []
        if not current and self.count(bot,group)>=32:raise ValueError('Agent session capacity')
        blob=self.encode({'bot':bot,'group':group,'sender':sender,'history':history})
        with self.db:self.db.execute('INSERT OR REPLACE INTO agent_sessions VALUES (?,?,?,?,?)',
                                     (key(bot,group,sender),key(bot,group),version,self.clock()+300,blob))
        return version,history
    def active(self,bot,group,sender,version=None):
        session=self.session(bot,group,sender)
        return bool(session and (version is None or session['version']==version))
    def append(self,bot,group,sender,version,question,answer):
        current=self.session(bot,group,sender)
        if not current or current['version']!=version:return False
        history=(current['history']+[[question[:1200],answer[:2000]]])[-6:]
        blob=self.encode({'bot':bot,'group':group,'sender':sender,'history':history})
        with self.db:self.db.execute('UPDATE agent_sessions SET p=? WHERE k=? AND v=?',
                                     (blob,key(bot,group,sender),version))
        return True
    def end(self,bot,group,sender):
        with self.db:self.db.execute('DELETE FROM agent_sessions WHERE k=?',(key(bot,group,sender),))
    def clear(self):
        with self.db:self.db.execute('DELETE FROM agent_sessions')
    def count(self,bot,group):
        return self.db.execute('SELECT count(*) FROM agent_sessions WHERE g=? AND expires>?',
                               (key(bot,group),self.clock())).fetchone()[0]
    def active_keys(self,bot,group):
        return {r[0] for r in self.db.execute('SELECT k FROM agent_sessions WHERE g=? AND expires>?',
                                             (key(bot,group),self.clock()))}
    def user_wait(self,bot,group,sender):
        row=self.db.execute('SELECT next_at FROM agent_user_limits WHERE k=?',(key(bot,group,sender),)).fetchone()
        return max(0,row[0]-self.clock()) if row else 0
    def user_claim(self,bot,group,sender):
        with self.db:self.db.execute('INSERT OR REPLACE INTO agent_user_limits VALUES (?,?)',
                                     (key(bot,group,sender),self.clock()+10))
