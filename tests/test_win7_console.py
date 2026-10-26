import builtins
import getpass
import io
import sys
import unittest
from unittest.mock import patch
from jat_design.win7_console import AsciiConsole, console_mode, display_text


class StrictLegacyConsole(io.StringIO):
    def write(self, value):
        if not value.isascii():
            raise OSError(22, 'Simulated legacy console write failure')
        return super().write(value)


class Win7ConsoleTests(unittest.TestCase):
    def test_legacy_unicode_failure_is_reproduced_and_adapter_prints_setup_banner(self):
        from jat_design import setup_api
        output = StrictLegacyConsole()
        with patch('sys.stdout', output), patch('sys.stdin.isatty', return_value=False):
            with self.assertRaises(OSError):
                setup_api.main()  # The exact print at the user's traceback line 51.
            with console_mode(enabled=True):
                self.assertEqual(setup_api.main(), 2)
        self.assertIn('SETUP API - luu khoa Gemini bang DPAPI', output.getvalue())
        self.assertTrue(output.getvalue().isascii())

    def test_hidden_prompt_is_ascii_secret_is_unchanged_and_not_echoed(self):
        from jat_design.webhook_switch import hidden
        output = StrictLegacyConsole()
        secret = 'synthetic-\u0111-\u00e9-key'
        with patch('sys.stdout', output), patch('getpass.getpass', return_value=secret) as original:
            with console_mode(enabled=True):
                self.assertEqual(hidden('API Key (\u1ea9n): '), secret)
        self.assertEqual(original.call_count, 1)
        self.assertTrue(original.call_args[0][0].isascii())
        self.assertNotIn(secret, output.getvalue())

    def test_no_echo_fallback_stays_forbidden(self):
        from jat_design.webhook_switch import hidden
        with patch('getpass.getpass', side_effect=getpass.GetPassWarning('no secure console')):
            with console_mode(enabled=True):
                with self.assertRaises(getpass.GetPassWarning):
                    hidden('API Key (\u1ea9n): ')

    def test_console_only_unicode_content_is_not_mutated(self):
        content = 'C\u00e2u h\u1ecfi Ti\u1ebfng Vi\u1ec7t \u0111\u1ea7y \u0111\u1ee7'
        output = StrictLegacyConsole()
        stream = AsciiConsole(output)
        self.assertEqual(stream.write(content), len(content))
        self.assertEqual(content, 'C\u00e2u h\u1ecfi Ti\u1ebfng Vi\u1ec7t \u0111\u1ea7y \u0111\u1ee7')
        self.assertTrue(output.getvalue().isascii())
        self.assertEqual(display_text('\u0110\u00e3 d\u1eebng \u2014 gi\u1eef d\u1eef li\u1ec7u'), 'Da dung - giu du lieu')

    def test_context_restores_streams_and_getpass_even_on_failure(self):
        before = sys.stdout, sys.stderr, getpass.getpass, builtins.input
        with self.assertRaises(ValueError):
            with console_mode(enabled=True):
                raise ValueError('test')
        self.assertEqual((sys.stdout, sys.stderr, getpass.getpass, builtins.input), before)

    def test_builtin_input_prompt_ascii_but_response_exact(self):
        response = 'C:\\Thư mục\\profile.zip'
        with patch('builtins.input', return_value=response) as original:
            with console_mode(enabled=True):
                self.assertEqual(input('Số thứ tự khóa: '), response)
        self.assertEqual(original.call_args[0][0], 'So thu tu khoa: ')
