"""One poller plus one serialized AI/send worker; original basic runner is untouched."""
import queue
import math
import threading
import time
from .agent_engine import AgentControls,AgentService
from .agent_store import AgentStore,key
from .agent_gemini import ConversationGemini
from .agent_transport import AgentTransport,AgentAPI
from .auto_reply import TRIGGER,verified_group
from .key_vault import Vault,KeyPool,VAULT_LOCK
from .official_api import OfficialAPI,Transport,APIError
from .polling_test import ReadOnlyTransport,TokenLock,receive_one,webhook_enabled
from .startup_check import ready,profile
from .state import State
from .webhook_switch import hidden
from .reconnect import retryable,wait


class AgentWorker:
    def __init__(self,runtime,bot,group,token,prompt,controls,output=print):
        self.runtime,self.bot,self.group,self.token,self.prompt=runtime,bot,group,token,prompt
        self.controls,self.output=controls,output
        self.queue=queue.Queue(maxsize=32);self.pending=set();self.active_members=set();self.observed={'received':0,'plain':0,'plain_active_member':0};self.lock=threading.Lock()
        self.last_outcome='idle';self.typing_result=None
        self.snapshot={'phase':'starting'};self.ready=threading.Event();self.failed=False
        self.thread=threading.Thread(target=self.run,name='JAT-Agent-worker',daemon=False)
    def submit(self,event,snapshot,received):
        m=event.get('message',{}) if isinstance(event,dict) else {}
        chat,sender=m.get('chat',{}),m.get('from',{})
        if (not isinstance(chat,dict) or not isinstance(sender,dict) or chat.get('id')!=self.group
                or chat.get('chat_type')!='GROUP' or sender.get('is_bot') is not False
                or not isinstance(sender.get('id'),str) or not sender['id'] or sender['id']==self.bot
                or not isinstance(m.get('text'),str)):return False
        identity=key(self.bot,self.group,sender['id'])
        mentioned=TRIGGER in m['text']
        with self.lock:
            self.observed['received']+=1
            if not mentioned:
                self.observed['plain']+=1
                if identity in self.active_members:self.observed['plain_active_member']+=1
                if not (snapshot['agent'] and snapshot['catchall'] and identity in self.active_members):return False
            if identity in self.pending:return False
            try:self.queue.put_nowait((event,snapshot,received,identity))
            except queue.Full:return False
            self.pending.add(identity)
        return True
    def status(self):
        with self.lock:return dict(self.snapshot,pending=len(self.pending),observed=dict(self.observed),capability='SENDER_SESSION_OPT_IN',reply_verified=False)
    def publish(self,service,pool,outcome='idle'):
        if outcome!='idle':self.last_outcome=outcome
        info=service.engine.status()
        data={'phase':'running','sessions':service.store.count(self.bot,self.group),
              'remaining':info['remaining'],'pause_seconds':int(max(0,info['local_until']-time.time())),
              'google_wait_seconds':int(max(0,info['google_until']-time.time(),pool.wait_remaining())),
              'uncertain':info['uncertain'],'outcome':self.last_outcome,'typing_api_last':self.typing_result,'api_active':pool.status()['active']}
        with self.lock:
            self.snapshot=data
            self.active_members=service.store.active_keys(self.bot,self.group)
    def run(self):
        state=store=None
        try:
            state=State(self.runtime/'ai_reply.db');store=AgentStore(self.runtime/'agent_state.db')
            service=AgentService(state,store,self.bot,self.group)
            vault=Vault(self.runtime/'gemini_keys.dpapi')
            pool=KeyPool(vault,self.prompt,factory=ConversationGemini,output=self.output)
            api=AgentAPI(AgentTransport(self.token))
            if service.engine.blocked():raise ValueError('Existing uncertain send guard')
            self.publish(service,pool);self.ready.set()
            while not self.controls.snapshot()['quit']:
                store.prune()
                if self.controls.take_clear():store.clear()
                try:job=self.queue.get(timeout=0.2)
                except queue.Empty:self.publish(service,pool);continue
                event,snapshot,received,identity=job
                try:
                    outcome=service.process(api,pool,event,snapshot,lambda:self.controls.valid(snapshot),received)
                    self.typing_result=getattr(api,'last_typing_result',None)
                    self.publish(service,pool,outcome)
                    self.output('AGENT_RESULT='+outcome)
                    if outcome in ('uncertain_blocked','invalid_key','billing_problem','provider_error'):
                        self.controls.command('OFF')
                finally:
                    with self.lock:self.pending.discard(identity)
                    self.queue.task_done()
        except Exception:
            self.failed=True;self.controls.command('QUIT')
            self.output('OFF AGENT_WORKER: state/provider failure; details hidden. Keep all DBs. No resend.')
        finally:
            self.ready.set()
            if store is not None:store.close()
            if state is not None:state.close()
            self.token=None


def dispatch_received_event(controls,worker,event,received,clock=time.time):
    # A command may change mode while long-poll is in flight. Use current mode
    # only for events born after its arm boundary; queued old jobs keep their epoch.
    current=controls.snapshot()
    if not current['bot'] or current['quit']:return False
    message=event.get('message') if isinstance(event,dict) else None
    stamp=message.get('date') if isinstance(message,dict) else None
    if type(stamp) not in (int,float) or not math.isfinite(stamp):return False
    if not current['armed']<=stamp<=clock()*1000+60000:return False
    return worker.submit(event,current,received)


def keyboard(controls,worker):
    import sys
    import json
    for line in sys.stdin:
        command=line.strip().upper()
        if command=='STATUS':print('AGENT_STATUS='+json.dumps(dict(worker.status(),controls=controls.snapshot()),sort_keys=True),flush=True)
        else:print('COMMAND='+controls.command(command),flush=True)
        if controls.snapshot()['quit']:return
    controls.command('QUIT')


def main(base):
    import sys
    runtime=base/'runtime';controls=AgentControls();worker=None
    if not sys.stdin.isatty():return 2
    print('JAT AGENT: BOT OFF, AGENT OFF. Original bot files/profile unchanged.')
    print('Default: @bot only. Optional sender-session follow-up is independent of unverified Reply metadata.')
    with TokenLock(VAULT_LOCK):
        if ready(runtime,base/'SYSTEM_PROMPT.txt'):return 1
        token=hidden('Bot Token Zalo (an, chi RAM): ').strip()
        if not token:return 2
        with TokenLock(token):
            transport=ReadOnlyTransport(Transport(token));bot=OfficialAPI(transport).getMe()
            if webhook_enabled(transport):print('OFF: webhook enabled. No mutation.');return 3
            profile(runtime,bot);group=verified_group(runtime,bot)
            prompt=(base/'SYSTEM_PROMPT.txt').read_text(encoding='utf-8-sig').strip()
            worker=AgentWorker(runtime,bot,group,token,prompt,controls)
            try:
                worker.thread.start()
                worker.ready.wait(10)
                if worker.failed or not worker.ready.is_set():return 1
                print('ON / OFF | AGENT ON / AGENT OFF | STATUS | MEMORY CLEAR | FOLLOWUP ON / OFF | QUIT')
                print('FOLLOWUP ON requires FOLLOWUP ON XAC NHAN. Default OFF; plain messages may target other members. AGENT ON does not turn BOT ON.')
                threading.Thread(target=keyboard,args=(controls,worker),daemon=True).start()
                failures=0
                while not controls.snapshot()['quit']:
                    snapshot=controls.snapshot()
                    if not snapshot['bot']:time.sleep(0.2);continue
                    errors=[]
                    event=receive_one(transport,seconds=35,stop_on_error=True,
                        on_status=lambda s:errors.append(s) if s.get('phase')=='poll_error' else None,
                        output=lambda msg:None)
                    if errors:
                        detail=errors[-1];print('POLL_ERROR kind=%s code=%s'%(detail['kind'],detail['code']))
                        if not retryable(detail):controls.command('OFF');continue
                        failures+=1
                        wait(60 if detail.get('code')==429 else min(60,5*2**min(failures-1,4)),quit_now=lambda:controls.snapshot()['quit'])
                        continue
                    failures=0
                    if event is not None:dispatch_received_event(controls,worker,event,time.monotonic())
                return 1 if worker.failed else 0
            finally:
                controls.command('QUIT')
                if worker is not None and worker.thread.is_alive():
                    print('OFF: pending cancelled. Waiting for in-flight HTTP to finish safely; no resend.')
                    worker.thread.join()
