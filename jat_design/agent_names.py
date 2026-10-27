"""Explicit manager-confirmed aliases bound to actual API IDs, never display-name matching."""
from pathlib import Path
import secrets
import sys
import time
from .agent_store import AgentStore,ALIASES
from .auto_reply import verified_group
from .local_group_profile import eligible
from .key_vault import VAULT_LOCK
from .official_api import OfficialAPI,Transport,APIError
from .polling_test import ReadOnlyTransport,TokenLock,receive_one,webhook_enabled
from .webhook_switch import RUNTIME,hidden
from .startup_check import ready,profile


def capture_alias(transport,bot,group,alias,store,confirm=input,output=print,receiver=receive_one,clock=time.time):
    started=clock();nonce='JAT-NAME-'+secrets.token_hex(16).upper()
    output('Nguoi quan ly: yeu cau DUNG THANH VIEN muon gan ten gui @bot kem ma moi:')
    output(nonce)
    output('READY NAME: receive-only, 5 phut. Khong in ID/ten hien thi/noi dung.')
    def accept(e):
        return eligible(e,bot,nonce,started,clock()) and e['message']['chat']['id']==group
    e=receiver(ReadOnlyTransport(transport),seconds=300,stop_on_error=True,output=output,accept=accept)
    if e is None or not accept(e):return False
    output('Da nhan ma tu mot tai khoan non-bot trong dung nhom. API ID da lay truc tiep, chua gan ten.')
    if confirm('Nguoi quan ly da xac minh dung nguoi cho ten "'+alias+'"? Go XAC NHAN (cho phep doi ten cu cua tai khoan nay): ').strip()!='XAC NHAN':return False
    store.bind(bot,group,e['message']['from']['id'],alias,replace=True)
    output('PASS: ten da gan voi dung group_id + sender_id; luu DPAPI/SQLite. Khong gui tin.')
    return True


def main(base):
    if not sys.stdin.isatty():return 2
    print('NAME SETUP: dong bot/poller khac. Quan ly phai xac minh danh tinh; khong doan tu anh/thu tu.')
    runtime=Path(base)/'runtime'
    with TokenLock(VAULT_LOCK):
        if ready(runtime,Path(base)/'SYSTEM_PROMPT.txt'):return 1
        token=hidden('Bot Token Zalo (an, chi RAM): ').strip()
        if not token:return 2
        with TokenLock(token):
            transport=ReadOnlyTransport(Transport(token));bot=OfficialAPI(transport).getMe()
            if webhook_enabled(transport):print('OFF: webhook enabled; no mutation.');return 3
            profile(runtime,bot);group=verified_group(runtime,bot)
            store=AgentStore(runtime/'agent_state.db')
            try:
                while True:
                    for index,(label,alias) in enumerate(ALIASES,1):
                        print('%s: %s -> %s [%s]'%(index,label,alias,'BOUND' if store.bound(bot,group,alias) else 'UNBOUND'))
                    command=input('1-7: gan/doi ten | 0: ten khac | X: go lien ket ten | Q: xong: ').strip().upper()
                    if command=='Q':return 0
                    if command=='X':
                        alias=input('Ten goi can go lien ket (khong nhap ID): ').strip()
                        if input('Go GO TEN de xoa lien ket ten nay, khong xoa DB/bo dem: ').strip()=='GO TEN':
                            store.unbind(bot,group,alias);print('Da go lien ket; cac counter/dedup giu nguyen.')
                        continue
                    if command=='0':alias=input('Ten muon duoc goi, toi da64 ky tu: ').strip()
                    elif command in tuple(str(i) for i in range(1,8)):
                        alias=ALIASES[int(command)-1][1]
                    else:continue
                    if command=='3':
                        if input('Gan BOT JAT DESIGN vao bot da getMe xac minh? Go XAC NHAN: ').strip()=='XAC NHAN':
                            store.bind(bot,group,bot,alias,replace=True);print('PASS BOT NAME: getMe ID, khong gan vao thanh vien.')
                        continue
                    try:
                        if not alias or len(alias)>64 or any(ord(c)<32 for c in alias):raise ValueError()
                        if not capture_alias(transport,bot,group,alias,store):print('Chua gan ten: huy/het han/API/filter. Khong tao lien ket gia.')
                    except ValueError:print('Khong gan duoc: ten khong hop le/da gan tai khoan khac; go lien ket dung neu can. Khong in ID.')
            finally:store.close()
