"""Read-only A/B/C probe BEFORE shared filters; no text, IDs, hashes or tokens in reports."""
import json
import math
from pathlib import Path
import secrets
import sqlite3
import time
from .agent_app import AgentWorker
from .agent_store import key
from .auto_reply import TRIGGER,verified_group
from .key_vault import VAULT_LOCK
from .official_api import APIError,OfficialAPI,Transport
from .polling_test import EVENTS,ReadOnlyTransport,TokenLock,valid_event,webhook_enabled
from .startup_check import profile
from .webhook_switch import hidden


def metadata(result,bot,group,anchor,active_keys,now,phase_started=None):
    obj=result if isinstance(result,dict) else {}
    m=obj.get('message');m=m if isinstance(m,dict) else {}
    chat=m.get('chat');chat=chat if isinstance(chat,dict) else {}
    sender=m.get('from');sender=sender if isinstance(sender,dict) else {}
    text=m.get('text');sid=sender.get('id');name=obj.get('event_name');kind=chat.get('chat_type')
    stamp=m.get('date');numeric=type(stamp) in (int,float)
    try:finite=numeric and math.isfinite(stamp)
    except OverflowError:finite=False
    helper=valid_event(result)
    # Dry-run exact current Worker prefilter, never start a thread/API or persist data.
    worker=AgentWorker(Path('.'),bot,group,'','',None,output=lambda _:None)
    worker.active_members=active_keys
    error=False;queued=False
    try:queued=worker.submit(result,{'bot':True,'agent':True,'catchall':True},0)
    except Exception:error=True
    if not worker.queue.empty():worker.queue.get_nowait()
    return {'event':name if isinstance(name,str) and name in EVENTS else 'OTHER',
            'message_object':isinstance(obj.get('message'),dict),
            'chat':kind if kind in ('GROUP','PRIVATE') else 'OTHER',
            'expected_group':chat.get('id')==group,
            'sender_id_present':isinstance(sid,str) and bool(sid.strip()),
            'sender_non_bot':sender.get('is_bot') is False,'sender_is_self':sid==bot,
            'same_sender_as_A':anchor is not None and sid==anchor,
            'text_string':isinstance(text,str),'text_nonempty':isinstance(text,str) and bool(text.strip()),
            'trigger_in_text':isinstance(text,str) and TRIGGER in text,
            'plain_by_app_rule':isinstance(text,str) and TRIGGER not in text,
            'message_id_present':isinstance(m.get('message_id'),str) and bool(m['message_id']),
            'date_numeric':numeric,'date_finite':finite,'event_time_not_future':finite and stamp<=now*1000+60000,
            'date_after_phase_start':None if phase_started is None else finite and stamp>=phase_started*1000,
            'date_range_hint':'MILLISECONDS_LIKE' if finite and 1e12<=stamp<1e14 else 'SECONDS_LIKE' if finite and 1e9<=stamp<1e11 else 'OTHER',
            'shared_valid_event':helper,'worker_prefilter_pass':worker.observed['received']>0,
            'dry_worker_would_queue':queued,'dry_worker_exception':error,
            'dry_config':'BOT_AGENT_FOLLOWUP_ON','reply_verified':False}


def active_keys_readonly(runtime,bot,group):
    path=Path(runtime)/'agent_state.db'
    if not path.is_file():return set()
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)
    try:return {r[0] for r in db.execute('SELECT k FROM agent_sessions WHERE g=? AND expires>?',(key(bot,group),time.time()))}
    finally:db.close()


def phase(read,label,bot,group,anchor,nonce,active,output=print,clock=time.monotonic,wait=time.sleep,seconds=65):
    report={'label':label,'polls':0,'empty':0,'nonempty':0,'status':'NO_MATCHING_RAW_EVENT','events':[]}
    started_wall=time.time()
    deadline=clock()+seconds
    while clock()<deadline and report['nonempty']<40:
        report['polls']+=1
        try:result=read.post('getUpdates',{'timeout':'30'},timeout=40)
        except APIError as error:
            report.update(status='API_ERROR',api_kind=error.kind,api_code=error.code);break
        if result in ({},None):
            report['empty']+=1;wait(min(1,max(0,deadline-clock())));continue
        report['nonempty']+=1
        technical=metadata(result,bot,group,anchor,active,time.time(),started_wall)
        m=result.get('message',{}) if isinstance(result,dict) else {}
        m=m if isinstance(m,dict) else {}
        sender=m.get('from',{});sender=sender if isinstance(sender,dict) else {}
        text=m.get('text')
        technical['phase_marker_present']=isinstance(text,str) and nonce in text
        report['events']=(report['events']+[technical])[-8:]
        if report['nonempty']<=8:output('PROBE_META='+json.dumps(technical,sort_keys=True))
        if label=='A':
            text=m.get('text')
            match=(technical['expected_group'] and technical['sender_non_bot'] and not technical['sender_is_self']
                   and technical['sender_id_present'] and technical['phase_marker_present'])
        else:match=technical['expected_group'] and technical['same_sender_as_A'] and technical['phase_marker_present']
        if match:
            report['status']='RAW_MATCH_RECEIVED'
            return report,sender.get('id') if label=='A' else anchor
    return report,anchor


def main(base):
    runtime=base/'runtime';report={'version':1,'read_only':True,'messages_sent':0,'phases':[],'labels_operator_assigned':True}
    path=runtime/'agent_followup_probe.json'
    def save():
        temp=path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8');temp.replace(path)
    print('READ-ONLY FOLLOWUP PROBE. Dong Agent va moi poller khac. Khong goi Gemini/typing/sendMessage.')
    with TokenLock(VAULT_LOCK):
        token=hidden('Bot Token hien tai (an, chi RAM; khong doi token): ').strip()
        if not token:return 2
        with TokenLock(token):
            read=ReadOnlyTransport(Transport(token));bot=OfficialAPI(read).getMe()
            if webhook_enabled(read):print('OFF: webhook enabled; no mutation.');return 3
            profile(runtime,bot);group=verified_group(runtime,bot)
            active=active_keys_readonly(runtime,bot,group)
            nonces={label:'JAT-PROBE-'+label+'-'+secrets.token_hex(16).upper() for label in ('A','B','C')};anchor=None
            instructions=[('A','Dung cung mot tai khoan, @bot kem ma: '+nonces['A']),
                          ('B','Cung tai khoan A: gui DUNG MA sau nhu tin THUONG, khong @/Reply: '+nonces['B']),
                          ('C','Cung tai khoan A: Reply vao tin do BOT da gui truoc do, khong @, noi dung la: '+nonces['C'])]
            try:
                for label,instruction in instructions:
                    if input('Enter de mo pha '+label+'; Q de dung: ').strip().upper()=='Q':break
                    print('READY '+label+': '+instruction)
                    print('Cua so khoang65-105 giay do long-poll, Ctrl+C de dung. Chi metadata duoc luu.')
                    data,anchor=phase(read,label,bot,group,anchor,nonces[label],active)
                    report['phases'].append(data);save()
                    print('PROBE_PHASE='+label+' status='+data['status']+' raw='+str(data['nonempty']))
                    if data['status']=='API_ERROR' or (label=='A' and data['status']!='RAW_MATCH_RECEIVED'):break
            finally:
                save()
                print('Saved runtime/agent_followup_probe.json. No sender IDs, text, token or ID hashes. Messages sent=0.')
    return 0
