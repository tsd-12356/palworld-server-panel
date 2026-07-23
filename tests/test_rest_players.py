from __future__ import annotations

import importlib.util
import json
import unittest
from unittest.mock import MagicMock, patch


@unittest.skipUnless(importlib.util.find_spec("flask"), "Flask is not installed")
class RestPlayersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global app
        import app

    def setUp(self):
        self.cache_patch = patch.object(app, "_player_response_cache", (0.0, {}))
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)

    def test_rest_players_normalize_documented_response(self):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "players": [
                    {
                        "name": "Player One",
                        "accountName": "steam-player",
                        "playerId": "player-1",
                        "userId": "user-1",
                        "ip": "192.0.2.1",
                        "ping": 42,
                        "level": 30,
                    }
                ]
            }
        ).encode()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch.object(app, "PALWORLD_REST_ENABLED", True), patch.object(app, "PALWORLD_REST_PASSWORD", "secret"), patch.object(
            app, "PALWORLD_REST_HOST", "127.0.0.1"
        ), patch("app.urllib.request.urlopen", return_value=response) as urlopen:
            players, source = app.get_rest_players()

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8212/v1/api/players")
        self.assertTrue(request.get_header("Authorization").startswith("Basic "))
        self.assertEqual(source, "rest")
        self.assertEqual(
            players,
            [{"name": "Player One", "account_name": "steam-player", "player_id": "player-1", "level": "30", "ping": "42"}],
        )

    def test_rest_empty_list_is_successful_without_rcon_fallback(self):
        with patch.object(app, "get_rest_players", return_value=([], "rest")), patch.object(app, "rcon_command") as rcon:
            result = app.get_online_players(player_list_enabled=True)
        self.assertTrue(result["query_ok"])
        self.assertEqual(result["source"], "rest")
        self.assertEqual(result["players"], [])
        rcon.assert_not_called()

    def test_rcon_fallback_is_used_after_rest_failure(self):
        with patch.object(app, "get_rest_players", side_effect=RuntimeError("unreachable")), patch.object(
            app, "rcon_command", return_value="Name,Player UID,Steam ID\nPlayer One,player-1,steam-1"
        ):
            result = app.get_online_players(player_list_enabled=True)
        self.assertTrue(result["query_ok"])
        self.assertEqual(result["source"], "rcon")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["players"][0]["name"], "Player One")

    def test_disabled_rcon_does_not_run_when_rest_fails(self):
        with patch.object(app, "get_rest_players", side_effect=RuntimeError("unreachable")), patch.object(app, "rcon_command") as rcon:
            result = app.get_online_players(player_list_enabled=False)
        self.assertFalse(result["query_ok"])
        self.assertEqual(result["source"], "none")
        rcon.assert_not_called()


if __name__ == "__main__":
    unittest.main()
