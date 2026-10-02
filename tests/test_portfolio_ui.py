"""Exercise the actual Streamlit page without paid network requests."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "m13_streamlit" / "s05_portfolio.py"


class PortfolioUITests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ENTRYPOINT.is_file(), "portfolio page is not implemented")
        self.env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": ""})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.dotenv_patch = patch("dotenv.load_dotenv", return_value=False)
        self.dotenv_patch.start()
        self.addCleanup(self.dotenv_patch.stop)

    def app(self, with_key=True):
        app = AppTest.from_file(str(ENTRYPOINT), default_timeout=15)
        if with_key:
            app.secrets["OPENAI_API_KEY"] = "fixture-key"
        app.run()
        if "portfolio" in app.session_state:
            self.addCleanup(app.session_state["portfolio"].close)
        return app

    def test_missing_key_shows_configuration_message_without_chat(self):
        app = self.app(with_key=False)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.chat_input), 0)
        self.assertTrue(app.warning)

    def test_exhausted_quota_disables_chat_and_clear_keeps_it_exhausted(self):
        app = self.app()
        app.session_state["portfolio"].used_turns = 5
        app.run()
        self.assertTrue(app.chat_input[0].disabled)
        app.button[0].click().run()
        self.assertEqual(app.session_state["portfolio"].used_turns, 5)
        self.assertTrue(app.chat_input[0].disabled)
        self.assertEqual(len(app.exception), 0)

    def test_new_visitors_have_different_session_ids(self):
        first, second = self.app(), self.app()
        self.assertNotEqual(first.session_state["portfolio"].session_id,
                            second.session_state["portfolio"].session_id)


if __name__ == "__main__":
    unittest.main()
