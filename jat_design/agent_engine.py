"""Agent layer around unchanged ManagedResponder; raw Zalo reply fields never guessed."""
import copy
import math
import threading
import time
from .auto_reply import TRIGGER,hashed
from .gemini_client import compact
from .managed_limits import ManagedResponder
from .agent_gemini import AgentPrompt


class AgentControls:
    def __init__(self,clock=time.time):
        self.lock=threading.Lock();self.changed=threading.Event();self.clock=clock
        self.bot=self.agent=self.catchall=self.quit=False
        self.epoch=0;self.armed=0;self.clear_requested=False
    def command(self,command):
        with self.lock:
            before=(self.bot,self.agent,self.catchall,self.quit)
            if command=='ON':self.bot=True
            elif command=='OFF':self.bot=False
            elif command=='AGENT ON':self.agent=True
            elif command=='AGENT OFF':self.agent=False
            elif command in ('CATCHALL OFF','FOLLOWUP OFF'):self.catchall=False
            elif command in ('CATCHALL ON','FOLLOWUP ON'):return 'CONFIRM_REQUIRED: type FOLLOWUP ON XAC NHAN; active members may address others'
            elif command in ('CATCHALL ON XAC NHAN','FOLLOWUP ON XAC NHAN'):self.catchall=True
            elif command=='MEMORY CLEAR':self.clear_requested=True
            elif command in ('QUIT','Q'):self.bot=False;self.quit=True
            else:return 'UNKNOWN_COMMAND'
            if before!=(self.bot,self.agent,self.catchall,self.quit) or command=='MEMORY CLEAR':
                self.epoch+=1;self.armed=self.clock()*1000;self.changed.set()
            return 'OK'
    def snapshot(self):
        with self.lock:return {'bot':self.bot,'agent':self.agent,'catchall':self.catchall,'quit':self.quit,
                               'epoch':self.epoch,'armed':self.armed}
    def valid(self,snapshot):
        current=self.snapshot()
        return current['bot'] and not current['quit'] and current['epoch']==snapshot['epoch']
    def take_clear(self):
        with self.lock:
            result=self.clear_requested;self.clear_requested=False;return result


class CancelledBeforeSend(Exception):pass


class GuardedResponder(ManagedResponder):
    """Clear only a proven no-HTTP cancellation, never a real uncertain send."""
    def _send(self,api,text,key,still_on,notice=False):
        class Gate:
            cancelled=False
            def sendMessage(gate,group,answer):
                if not still_on():
                    gate.cancelled=True
                    raise CancelledBeforeSend()
                return api.sendMessage(group,answer)
        gate=Gate()
        outcome=super()._send(gate,text,key,still_on,notice=notice)
        if gate.cancelled:
            with self.state.db:
                self.state.db.execute('DELETE FROM auto_block WHERE k=? AND reason=?',
                                      (self.bot_key,'send_pending_or_uncertain'))
            self.last_error=None
            return self._mark(key,'off')
        return outcome


class AgentService:
    def __init__(self,state,store,bot_id,group_id,clock=time.time,monotonic=time.monotonic,
                 sleeper=time.sleep,reply_adapter=None):
        self.state,self.store,self.bot_id,self.group_id=state,store,bot_id,group_id
        self.clock,self.monotonic,self.sleeper=clock,monotonic,sleeper
        self.engine=GuardedResponder(state,bot_id,group_id,clock)
        # Runtime supplies no adapter. Only offline normalized fixtures/future verified
        # integration can provide one; no raw reply/mentions key or CLI bypass exists.
        self.reply_adapter=reply_adapter
    def fields(self,event):
        if not isinstance(event,dict) or event.get('event_name')!='message.text.received':return None
        m=event.get('message')
        if not isinstance(m,dict):return None
        chat,sender=m.get('chat'),m.get('from')
        if not isinstance(chat,dict) or not isinstance(sender,dict):return None
        if (chat.get('chat_type')!='GROUP' or chat.get('id')!=self.group_id
                or sender.get('is_bot') is not False or sender.get('id')==self.bot_id
                or not all(isinstance(v,str) and v.strip() for v in
                           (sender.get('id'),m.get('message_id'),m.get('text')))):return None
        return m
    def wait(self,seconds,valid):
        end=self.monotonic()+max(0,seconds)
        while self.monotonic()<end:
            if not valid():return False
            self.sleeper(min(0.1,max(0,end-self.monotonic())))
        return valid()
    def process(self,api,pool,event,snapshot,valid,received_at):
        if not valid():return 'off'
        message=self.fields(event)
        if message is None:return 'ignored'
        stamp=message.get('date')
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or not snapshot['armed']<=stamp<=self.clock()*1000+60000:
            return 'old_or_unknown_time'
        sender=message['from']['id'];text=message['text'];mentioned=TRIGGER in text
        if not snapshot['agent']:
            # Existing basic behavior, same counters/dedup/guards and no memory.
            return self.engine.handle(api,pool,event,True,snapshot['armed'],still_on=valid)
        if not mentioned:
            if not self.store.active(self.bot_id,self.group_id,sender):return 'no_session'
            evidence = self.reply_adapter(event,self.bot_id) if self.reply_adapter is not None else None
            if evidence is False:return 'addressed_to_other'
            addressed = evidence is True
            if not (addressed or snapshot['catchall']):
                return 'reply_metadata_unverified' if self.reply_adapter is None else 'not_addressed'
        question=(text.replace(TRIGGER,'',1) if mentioned else text).strip()
        if question.casefold() in ('/end','/stop','/pause','/clear','/xoa'):
            if not self.state.reserve(self.engine.group_key,hashed(message['message_id'])):return 'duplicate'
            self.store.end(self.bot_id,self.group_id,sender)
            self.state.mark(self.engine.group_key,hashed(message['message_id']),'agent_session_ended')
            return 'session_ended'
        if not question:return 'empty_question'
        if self.store.user_wait(self.bot_id,self.group_id,sender)>0:return 'user_cooldown'
        # Wait for old global cooldown in this worker; polling runs separately.
        wait=max(0,self.engine.status()['cooldown_until']-self.clock())
        if wait>0 and not self.wait(wait+0.01,valid):return 'off'
        if self.monotonic()-received_at>60:return 'queue_expired'
        if self.engine.blocked():return 'uncertain_blocked'
        transformed=copy.deepcopy(event)
        transformed['message']['text']=TRIGGER+' '+question
        service=self
        class ContextPool:
            version=None;answer=None;local_until=None
            def wait_remaining(inner):return pool.wait_remaining()
            def generate(inner,current):
                inner.version,history=service.store.touch(service.bot_id,service.group_id,sender)
                alias=service.store.alias(service.bot_id,service.group_id,sender)
                service.store.user_claim(service.bot_id,service.group_id,sender)
                inner.local_until=service.engine.status()['local_until']
                if allowed() and hasattr(api,'typing'):
                    api.typing(service.group_id)
                if not allowed():return ''
                assistant=service.store.alias(service.bot_id,service.group_id,service.bot_id)
                answer=pool.generate(AgentPrompt(current,history,alias,assistant if assistant!='bạn' else 'BOT JAT DESIGN'))
                inner.answer=compact((alias+', ' if alias!='bạn' and alias.casefold() not in answer.casefold() else '')+answer)
                # Delay only after model work; no typing placeholder, polling is independent.
                service.wait(max(0,received_at+2.5-service.monotonic()),allowed)
                return inner.answer
        context=ContextPool()
        def allowed():
            if not valid():return False
            if context.version is None:return True
            if not self.store.active(self.bot_id,self.group_id,sender,context.version):return False
            # This request already owns its budget slot, including the tenth slot
            # that starts the pause. A later/longer pause or provider wait cancels it.
            info=self.engine.status()
            return (info['local_until']<=max(self.clock(),context.local_until)
                    and info['google_until']<=self.clock() and pool.wait_remaining()<=0)
        outcome=self.engine.handle(api,context,transformed,True,snapshot['armed'],still_on=allowed)
        if outcome=='sent' and context.version is not None:
            self.store.append(self.bot_id,self.group_id,sender,context.version,question,context.answer)
        return outcome
