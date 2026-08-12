from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import panel_update


class PanelUpdateTests(unittest.TestCase):
    def setUp(self):
        panel_update.status = panel_update.UpdateStatus()
        self.write_json = patch.object(panel_update, "write_json").start()
        self.addCleanup(patch.stopall)

    def test_check_only_uses_operation_lock(self):
        with patch.object(panel_update, "operation_lock", return_value=nullcontext()) as operation_lock, patch.object(
            panel_update, "check_update", return_value={"update_available": False}
        ), patch.object(panel_update.status, "set"), patch.object(panel_update, "append_audit"), patch.object(panel_update, "log"):
            panel_update.check_only()
        operation_lock.assert_called_once_with()

    def test_operation_lock_does_not_truncate_metadata_when_busy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock_path = root / ".operation.lock"
            lock_path.write_text("existing owner\n", encoding="utf-8")
            fake_fcntl = SimpleNamespace(
                LOCK_EX=1,
                LOCK_NB=2,
                LOCK_UN=4,
                flock=lambda *_args: (_ for _ in ()).throw(BlockingIOError()),
            )
            with patch.object(panel_update, "SAVE_SLOT_ROOT", root), patch.object(
                panel_update, "SAVE_LOCK_PATH", lock_path
            ), patch.dict(sys.modules, {"fcntl": fake_fcntl}):
                with self.assertRaisesRegex(RuntimeError, "another save/update operation"):
                    with panel_update.operation_lock():
                        pass
            self.assertEqual(lock_path.read_text(encoding="utf-8"), "existing owner\n")

    def test_stopped_server_is_backed_up_without_starting(self):
        with patch.object(panel_update, "operation_lock", return_value=nullcontext()), patch.object(
            panel_update, "check_update", side_effect=[{"update_available": True}, {"update_available": False}]
        ), patch.object(panel_update, "is_service_running", return_value=False), patch.object(
            panel_update, "backup_current_save", return_value="backup"
        ) as backup, patch.object(panel_update, "run_steam_update"), patch.object(panel_update, "fix_ownership"), patch.object(
            panel_update, "systemctl"
        ) as systemctl, patch.object(panel_update, "append_audit"), patch.object(panel_update, "log"):
            panel_update.apply_update()
        backup.assert_called_once_with()
        systemctl.assert_not_called()

    def test_running_server_stops_before_backup_and_restarts_after_failure(self):
        events = []

        def systemctl(action, *_args, **_kwargs):
            events.append(action)
            return "", "", 0

        def backup():
            events.append("backup")
            raise RuntimeError("backup failed")

        with patch.object(panel_update, "operation_lock", return_value=nullcontext()), patch.object(
            panel_update, "check_update", return_value={"update_available": True}
        ), patch.object(panel_update, "is_service_running", return_value=True), patch.object(
            panel_update, "countdown_if_needed"
        ), patch.object(panel_update, "rcon_command", return_value="Complete Save"), patch.object(
            panel_update.time, "sleep"
        ), patch.object(panel_update, "wait_for_service", return_value=True), patch.object(
            panel_update, "backup_current_save", side_effect=backup
        ), patch.object(panel_update, "systemctl", side_effect=systemctl), patch.object(panel_update, "append_audit"), patch.object(
            panel_update, "log"
        ):
            with self.assertRaisesRegex(RuntimeError, "backup failed"):
                panel_update.apply_update()
        self.assertEqual(events, ["stop", "backup", "start"])

    def test_rcon_save_failure_aborts_before_stop_and_backup(self):
        with patch.object(panel_update, "operation_lock", return_value=nullcontext()), patch.object(
            panel_update, "check_update", return_value={"update_available": True}
        ), patch.object(panel_update, "is_service_running", return_value=True), patch.object(
            panel_update, "countdown_if_needed"
        ), patch.object(panel_update, "rcon_command", return_value="[RCON Error] timeout"), patch.object(
            panel_update, "systemctl"
        ) as systemctl, patch.object(panel_update, "backup_current_save") as backup, patch.object(
            panel_update, "append_audit"
        ), patch.object(panel_update, "log"):
            with self.assertRaisesRegex(RuntimeError, "RCON save failed"):
                panel_update.apply_update()
        systemctl.assert_not_called()
        backup.assert_not_called()

    def test_fix_ownership_reports_chown_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(panel_update, "PALWORLD_DIR", path), patch.object(panel_update, "CONFIG_DIR", path), patch.object(
                panel_update, "run_privileged", return_value=("", "denied", 1)
            ):
                with self.assertRaisesRegex(RuntimeError, "denied"):
                    panel_update.fix_ownership()


if __name__ == "__main__":
    unittest.main()
