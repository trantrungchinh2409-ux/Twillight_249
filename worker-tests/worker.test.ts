import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker from '../src/index.js';
import {Store} from '../src/storage.js';
import {processEvent} from '../src/dedupe.js';
import {parseUpdate,MentionUnverified,sendMessage,type Event} from '../src/zalo-adapter.js';
import {authenticated} from '../src/security.js';
import type {Env} from '../src/config.js';

// INTERNAL normalized model. NOT an actual Zalo group response fixture.
const event:Event={id:'event-1',chatId:'group-1',kind:'group',senderId:'member',senderIsBot:false,text:'ping',mentionedIds:['bot']};
const privatePayload={ok:true,result:{event_name:'message.text.received',message:{from:{id:'member',is_bot:false},chat:{id:'member',chat_type:'PRIVATE'},message_id:'m',text:'hi'}}};
function database() {
  const db=new DatabaseSync(':memory:');db.exec(readFileSync('migrations/0001_state.sql','utf8'));
  const prepare=(sql:string)=>{
    let args:(string|number)[]=[];
    const statement={bind(...values:(string|number)[]){args=values;return statement;},async run(){return statement.runSync();},runSync(){const result=db.prepare(sql).run(...args);return {meta:{changes:Number(result.changes)}};}};
    return statement;
  };
  const binding={prepare,async batch(stmts:ReturnType<typeof prepare>[]){db.exec('BEGIN');try{const results=stmts.map(s=>s.runSync());db.exec('COMMIT');return results;}catch(e){db.exec('ROLLBACK');throw e;}}};
  return {db,store:new Store(binding as unknown as D1Database),binding:binding as unknown as D1Database};
}
function env():Env {return {DB:{} as D1Database,ZALO_WEBHOOK_SECRET:'test-secret-only',ZALO_BOT_TOKEN:'dummy',BOT_ID:'bot',BOT_ENABLED:'true',ALLOWED_GROUP_IDS:'["group-1"]'};}
function req(body:unknown=privatePayload,headers:Record<string,string>={}) {return new Request('https://example.test/webhook',{method:'POST',headers:{'Content-Type':'application/json','X-Bot-Api-Secret-Token':'test-secret-only',...headers},body:JSON.stringify(body)});}

test('health exposes no environment values',async()=>{const r=await worker.fetch(new Request('https://example.test/health'),env());assert.equal(r.status,200);assert.equal(await r.text(),'{"result":"ok"}');});
test('unknown route and wrong method',async()=>{assert.equal((await worker.fetch(new Request('https://example.test/no'),env())).status,404);assert.equal((await worker.fetch(new Request('https://example.test/webhook'),env())).status,405);});
test('missing and wrong authentication rejected',async()=>{assert.equal((await worker.fetch(req({}, {'X-Bot-Api-Secret-Token':'wrong'}),env())).status,401);assert.equal((await worker.fetch(req(),{...env(),ZALO_WEBHOOK_SECRET:undefined})).status,503);});
test('secret comparison',async()=>{assert.equal(await authenticated('test-secret-only','test-secret-only'),true);assert.equal(await authenticated('wrong','test-secret-only'),false);});
test('content type rejected',async()=>{assert.equal((await worker.fetch(req({}, {'Content-Type':'text/plain'}),env())).status,415);});
test('malformed JSON rejected',async()=>{const r=req();assert.equal((await worker.fetch(new Request(r,{body:'{'}),env())).status,400);});
test('oversized actual body rejected even without Content-Length',async()=>{assert.equal((await worker.fetch(req({text:'x'.repeat(65537)}),env())).status,413);});
test('disable switch prevents processing',async()=>{const r=await worker.fetch(req(),{...env(),BOT_ENABLED:'false'});assert.equal((await r.json() as {result:string}).result,'disabled');});
test('private chat ignored without storage use',async()=>{const r=await worker.fetch(req(),env());assert.equal((await r.json() as {result:string}).result,'ignored');});
test('unknown schema rejected',async()=>{assert.equal((await worker.fetch(req({unknown:true}),env())).status,400);});
test('group fails closed even with an invented mentions field',async()=>{const payload=structuredClone(privatePayload);payload.result.message.chat.chat_type='GROUP';assert.throws(()=>parseUpdate(payload),MentionUnverified);const r=await worker.fetch(req({...payload,mentions:['bot']}),env());assert.equal((await r.json() as {result:string}).result,'mention_unverified');});
test('missing bot token and invalid config fail closed',async()=>{assert.equal((await worker.fetch(req(),{...env(),ZALO_BOT_TOKEN:undefined})).status,503);assert.equal((await worker.fetch(req(),{...env(),ALLOWED_GROUP_IDS:'{}'})).status,503);});
test('internal correct mention sends once with persistent SQL reservation',async()=>{const {db,store}=database();try{const sent:string[]=[];const send=async(c:string)=>{sent.push(c);};assert.equal(await processEvent(event,'bot',new Set(['group-1']),store,send,10000),'sent');assert.equal(await processEvent(event,'bot',new Set(['group-1']),store,send,10000),'duplicate_or_cooldown');assert.deepEqual(sent,['group-1']);const row=db.prepare('SELECT * FROM deliveries').get()!;assert.equal(row.status,'sent');assert.equal(JSON.stringify(row).includes('group-1'),false);}finally{db.close();}});
test('internal private/outside group/plain text/wrong mention/self/bot ignored',async()=>{const {db,store}=database();try{for(const change of [{kind:'private'},{chatId:'outside'},{mentionedIds:[],text:'@Bot JAT Design'},{mentionedIds:['other']},{senderId:'bot'},{senderIsBot:true}]){assert.equal(await processEvent({...event,...change} as Event,'bot',new Set(['group-1']),store,async()=>{assert.fail('must not send');}),'ignored');}}finally{db.close();}});
test('SQL cooldown and TTL cleanup',async()=>{const {db,store}=database();try{assert.equal(await store.reserve('1','g',10000),true);assert.equal(await store.reserve('2','g',10001),false);assert.equal(await store.reserve('2','g',15000),true);assert.equal(await store.reserve('3','g',86430000),true);assert.equal(db.prepare('SELECT count(*) AS n FROM deliveries').get()!.n,1);}finally{db.close();}});
test('send timeout is uncertain and never replayed',async()=>{const {db,store}=database();try{let count=0;const send=async()=>{count++;throw new Error('secret');};assert.equal(await processEvent(event,'bot',new Set(['group-1']),store,send,10000),'send_uncertain');await processEvent(event,'bot',new Set(['group-1']),store,send,20000);assert.equal(count,1);assert.equal(db.prepare('SELECT status FROM deliveries').get()!.status,'uncertain');}finally{db.close();}});
test('storage failure prevents sending',async()=>{await assert.rejects(()=>processEvent(event,'bot',new Set(['group-1']),{reserve:async()=>{throw new Error();},finish:async()=>{}},async()=>{assert.fail();}));});
test('official send payload and fixed response',async()=>{let called=0;const mock=(async(url:unknown,init:RequestInit)=>{called++;assert.equal(String(url),'https://bot-api.zaloplatforms.com/botdummy/sendMessage');assert.equal(init.redirect,'error');assert.deepEqual(JSON.parse(init.body as string),{chat_id:'group-1',text:'JAT Design đã online!'});return Response.json({ok:true,result:{message_id:'sent'}});}) as typeof fetch;await sendMessage('dummy','group-1',mock);assert.equal(called,1);});
test('send failures do not expose token or response description',async()=>{await assert.rejects(()=>sendMessage('sensitive','group',(async()=>Response.json({ok:false,description:'sensitive'})) as typeof fetch),/^Error: send_uncertain$/);});
test('logs never include request token, payload or group ID',async()=>{const old=console.log;const logs:string[]=[];console.log=(s:unknown)=>logs.push(String(s));try{await worker.fetch(req(),env());assert.equal(logs.join().includes('test-secret-only'),false);assert.equal(logs.join().includes('member'),false);}finally{console.log=old;}});
