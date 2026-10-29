"""
Tests for Telegram Bot handlers and application setup.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from telegram_bot import create_telegram_application, get_main_keyboard
from database import init_db

class TestTelegramBot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_application_creation(self):
        fake_token = "123456789:ABCdefGhIJKlmNoPQRstuVWXyz_test"
        app = create_telegram_application(fake_token)
        self.assertIsNotNone(app)
        # Check handlers
        handlers = app.handlers[0]
        self.assertGreater(len(handlers), 3)

    def test_main_keyboard_layout(self):
        markup = get_main_keyboard()
        self.assertIsNotNone(markup.inline_keyboard)
        self.assertGreaterEqual(len(markup.inline_keyboard), 3)

if __name__ == "__main__":
    unittest.main()
