from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask is not installed")
class ConfigAndStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global app
        import app

    def test_deployment_managed_settings_are_not_returned(self):
        with patch.object(app, "parse_default_palworld_settings", return_value={"AdminPassword": '"secret"', "ServerName": '"Test"'}), patch.object(
            app, "parse_palworld_settings", return_value={"RCONPort": "25575", "ServerName": '"Current"'}
        ):
            self.assertEqual(app.get_panel_settings(), {"ServerName": '"Current"'})

    def test_deployment_managed_settings_cannot_be_saved(self):
        errors = app.validate_config_changes({"AdminPassword": "new-secret"})
        self.assertEqual(errors, ["管理员密码 由部署配置管理，不能在面板中修改"])

    def test_status_skips_rcon_when_player_list_is_disabled(self):
        with patch.object(app, "parse_palworld_settings", return_value={"bShowPlayerList": "False"}), patch.object(
            app, "rcon_command", side_effect=AssertionError("RCON should not be called")
        ), patch.object(app, "get_game_version", return_value="v1"):
            info = app.get_server_info()
        self.assertFalse(info["player_list_enabled"])
        self.assertFalse(info["players_query_ok"])
        self.assertEqual(info["online_players"], [])


if __name__ == "__main__":
    unittest.main()
