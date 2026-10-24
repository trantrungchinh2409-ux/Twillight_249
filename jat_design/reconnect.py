"""Retry only reads/transient provider transport; never replay sendMessage."""
import time
from .official_api import APIError


def retryable(detail):
    return (detail.get('kind') in ('network', 'timeout')
            or (detail.get('kind') == 'http' and detail.get('code') in (429, 500, 502, 503, 504)))


def wait(delay, quit_now=lambda: False, sleep=time.sleep, clock=time.monotonic):
    end = clock()+delay
    while clock() < end:
        if quit_now(): return False
        sleep(min(0.2, max(0, end-clock())))
    return not quit_now()


def read_with_reconnect(call, output=print, pause=wait):
    failures = 0
    while True:
        try: return call()
        except APIError as error:
            detail = {'kind': error.kind, 'code': error.code}
            if not retryable(detail): raise
            failures += 1
            delay = 60 if error.code == 429 else min(60, 5*2**min(failures-1, 4))
            output('Kết nối đọc gián đoạn: loại=%s mã=%s; chờ %ss. Không gọi sendMessage.' %
                   (error.kind, error.code, delay))
            if not pause(delay): raise KeyboardInterrupt()
