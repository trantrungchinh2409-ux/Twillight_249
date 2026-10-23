import type {Event} from './zalo-adapter.js';
export function eligible(e:Event,botId:string,groups:ReadonlySet<string>):boolean {
  return !!botId && !!e.id && e.kind==='group' && groups.has(e.chatId) &&
    !e.senderIsBot && !!e.senderId && e.senderId!==botId && !!e.text.trim() && e.mentionedIds.includes(botId);
}
