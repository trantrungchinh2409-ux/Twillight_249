export interface Event {
  id:string; chatId:string; kind:'group'|'private'; senderId:string;
  senderIsBot:boolean; text:string; mentionedIds:readonly string[];
}
export class MentionUnverified extends Error {}
const object = (v:unknown): v is Record<string,unknown> => !!v && typeof v==='object' && !Array.isArray(v);
export function parseUpdate(body:unknown): Event|null {
  if(!object(body)||body.ok!==true||!object(body.result)) throw new Error('schema');
  const r=body.result;
  const known=['message.text.received','message.image.received','message.sticker.received','message.voice.received','message.unsupported.received'];
  if(!known.includes(String(r.event_name))) throw new Error('schema');
  if(r.event_name!=='message.text.received') return null;
  const m=r.message;
  if(!object(m)||!object(m.chat)||!object(m.from)) throw new Error('schema');
  // Official guide delivers BOTH mentions and quoted replies. No documented discriminator.
  if(m.chat.chat_type==='GROUP') throw new MentionUnverified();
  if(m.chat.chat_type!=='PRIVATE') throw new Error('schema');
  const fields=[m.message_id,m.chat.id,m.from.id,m.text];
  if(!fields.every(x=>typeof x==='string'&&x.length>0)||typeof m.from.is_bot!=='boolean') throw new Error('schema');
  return {id:m.message_id as string,chatId:m.chat.id as string,kind:'private',senderId:m.from.id as string,senderIsBot:m.from.is_bot,text:m.text as string,mentionedIds:[]};
}
export async function sendMessage(token:string,chatId:string, fetcher:typeof fetch=fetch):Promise<void> {
  try {
    const response=await fetcher(`https://bot-api.zaloplatforms.com/bot${encodeURIComponent(token)}/sendMessage`,{
      method:'POST',redirect:'error',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({chat_id:chatId,text:'JAT Design đã online!'}),signal:AbortSignal.timeout(8000)});
    if(!response.ok) throw new Error();
    const raw=await response.text(); if(raw.length>65536) throw new Error();
    const b:unknown=JSON.parse(raw);
    if(!object(b)||b.ok!==true||!object(b.result)||typeof b.result.message_id!=='string'||!b.result.message_id) throw new Error();
  } catch {throw new Error('send_uncertain');} // no URLs, body, description or automatic send retry
}
