from __future__ import annotations

import importlib.util
from types import SimpleNamespace
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
            app, "get_online_players", return_value={"players": [], "source": "none", "query_ok": False, "error": "disabled", "fallback_used": False}
        ), patch.object(app, "get_game_version", return_value="v1"):
            info = app.get_server_info()
        self.assertFalse(info["player_list_enabled"])
        self.assertFalse(info["players_query_ok"])
        self.assertEqual(info["online_players"], [])

    def test_rcon_api_returns_command_output(self):
        result = SimpleNamespace(success=True, acknowledged=True, response="Welcome to Pal Server", message="")
        with app.app.test_client() as client, patch.object(app, "execute_panel_rcon_command", return_value=result):
            response = client.post("/api/rcon", json={"command": "Info"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["response"], "Welcome to Pal Server")
        self.assertTrue(response.json["acknowledged"])

    def test_showplayers_allows_no_response_but_info_does_not(self):
        with patch.object(app, "execute_rcon_command", return_value=SimpleNamespace()) as execute:
            app.execute_panel_rcon_command("ShowPlayers")
            app.execute_panel_rcon_command("Info")
        self.assertTrue(execute.call_args_list[0].kwargs["allow_no_response"])
        self.assertFalse(execute.call_args_list[1].kwargs["allow_no_response"])

    def test_rcon_api_allows_showplayers_without_response(self):
        result = SimpleNamespace(
            success=True,
            acknowledged=False,
            response="",
            message="Command sent; this Palworld command did not return an RCON response",
        )
        with app.app.test_client() as client, patch.object(app, "execute_panel_rcon_command", return_value=result) as execute:
            response = client.post("/api/rcon", json={"command": "ShowPlayers"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertFalse(response.json["acknowledged"])
        self.assertIn("did not return", response.json["message"])
        execute.assert_called_once_with("ShowPlayers")

    def test_rcon_api_rejects_non_ascii_broadcast(self):
        with app.app.test_client() as client, patch.object(app, "execute_panel_rcon_command") as execute:
            response = client.post("/api/rcon", json={"command": "Broadcast 请问"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json["success"])
        self.assertIn("ASCII", response.json["message"])
        execute.assert_not_called()

    def test_rcon_api_reports_unacknowledged_command(self):
        result = SimpleNamespace(success=False, acknowledged=False, response="", message="The server did not acknowledge the command")
        with app.app.test_client() as client, patch.object(app, "execute_panel_rcon_command", return_value=result):
            response = client.post("/api/rcon", json={"command": "Info"})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json["success"])
        self.assertEqual(response.json["message"], "The server did not acknowledge the command")


if __name__ == "__main__":
    unittest.main()
