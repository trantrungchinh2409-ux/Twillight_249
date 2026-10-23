import type {Event} from './zalo-adapter.js';
import {eligible} from './mention-filter.js';
export interface State {
  reserve(key:string,group:string,now:number):Promise<boolean>;
  finish(key:string,status:'sent'|'uncertain'):Promise<void>;
}
async function hash(value:string):Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),x=>x.toString(16).padStart(2,'0')).join('');
}
export async function processEvent(e:Event,botId:string,groups:ReadonlySet<string>,store:State,send:(chatId:string)=>Promise<void>,now=Date.now()):Promise<string> {
  if(!eligible(e,botId,groups)) return 'ignored';
  const group=await hash(JSON.stringify([botId,e.chatId]));
  const key=await hash(JSON.stringify([botId,e.chatId,e.id]));
  if(!await store.reserve(key,group,now)) return 'duplicate_or_cooldown';
  try { await send(e.chatId); }
  catch {await store.finish(key,'uncertain');return 'send_uncertain';}
  await store.finish(key,'sent');return 'sent';
}
