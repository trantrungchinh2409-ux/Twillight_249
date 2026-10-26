"""ASCII presentation for legacy Win7 consoles; never transforms application data."""
import builtins
from contextlib import contextmanager
import getpass
import os
import sys
import unicodedata


def display_text(text):
    text = text.replace('\u0111', 'd').replace('\u0110', 'D')
    for before, after in (('\u2014', '-'), ('\u2013', '-'), ('\u2018', "'"), ('\u2019', "'"), ('\u201c', '"'), ('\u201d', '"')):
        text = text.replace(before, after)
    plain = ''.join(char for char in unicodedata.normalize('NFKD', text) if not unicodedata.combining(char))
    return plain.encode('ascii', 'replace').decode('ascii')


class AsciiConsole:
    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        # Return the count in the caller's original string, as TextIO expects.
        self.stream.write(display_text(text))
        return len(text)

    def flush(self):
        return self.stream.flush()

    def __getattr__(self, name):
        return getattr(self.stream, name)


def required():
    if os.environ.get('JAT_ASCII_CONSOLE') == '1':
        return True
    return os.name == 'nt' and tuple(sys.getwindowsversion()[:2]) <= (6, 1)


@contextmanager
def console_mode(enabled=None):
    if not (required() if enabled is None else enabled):
        yield
        return
    stdout, stderr, secret_input, command_input = sys.stdout, sys.stderr, getpass.getpass, builtins.input
    sys.stdout, sys.stderr = AsciiConsole(stdout), AsciiConsole(stderr)

    def hidden(prompt='Password: ', stream=None):
        # Keep getpass itself, including no-echo handling and warning behavior.
        # Its result is the exact secret, without normalization or logging.
        return secret_input(display_text(prompt), stream=stream)

    def command(prompt=''):
        # CPython input() can bypass sys.stdout.write for a real console.
        return command_input(display_text(prompt))

    getpass.getpass = hidden
    builtins.input = command
    try:
        yield
    finally:
        getpass.getpass = secret_input
        builtins.input = command_input
        sys.stdout, sys.stderr = stdout, stderr
