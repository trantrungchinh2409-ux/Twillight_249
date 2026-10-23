import {config,type Env} from './config.js';
import {authenticated,boundedJSON} from './security.js';
import {MentionUnverified,parseUpdate,sendMessage} from './zalo-adapter.js';
import {processEvent} from './dedupe.js';
import {Store} from './storage.js';
import {log} from './logger.js';
const answer=(status:number,result:string)=>Response.json({result},{status});
export default {
  async fetch(request:Request,env:Env):Promise<Response> {
    const path=new URL(request.url).pathname;
    if(path==='/health') return request.method==='GET'?answer(200,'ok'):answer(405,'method');
    if(path!=='/webhook') return answer(404,'not_found');
    if(request.method!=='POST') return answer(405,'method');
    if(!env.ZALO_WEBHOOK_SECRET || env.ZALO_WEBHOOK_SECRET.length<8 || env.ZALO_WEBHOOK_SECRET.length>256) return answer(503,'configuration');
    if(!await authenticated(request.headers.get('X-Bot-Api-Secret-Token'),env.ZALO_WEBHOOK_SECRET)) return answer(401,'unauthorized');
    if(request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()!=='application/json') return answer(415,'content_type');
    let body:unknown;
    try {body=await boundedJSON(request);} catch(e){return answer(e instanceof Error&&e.message==='large'?413:400,'invalid_body');}
    const id=crypto.randomUUID();
    try {
      const cfg=config(env);
      if(!cfg.enabled) return answer(200,'disabled');
      if(!cfg.botId||!env.ZALO_BOT_TOKEN||!env.DB) return answer(503,'configuration');
      let event;
      try {event=parseUpdate(body);} catch(e){
        if(e instanceof MentionUnverified){log(id,'mention_unverified');return answer(200,'mention_unverified');}
        return answer(400,'invalid_schema');
      }
      if(!event) return answer(200,'ignored');
      // Await bounded fixed reply. Do not acknowledge before durable reservation.
      const result=await processEvent(event,cfg.botId,cfg.groups,new Store(env.DB),chat=>sendMessage(env.ZALO_BOT_TOKEN!,chat));
      log(id,result);return answer(200,result);
    } catch {log(id,'storage_or_configuration');return answer(503,'unavailable');}
  }
};
