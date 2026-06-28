#!/usr/bin/env python3
"""Background updater for the Palworld panel.

This script is intentionally standalone so systemd timers can run update checks
without involving Flask or gunicorn workers.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any


PALWORLD_DIR = Path(os.environ.get("PALWORLD_DIR", "/home/demo/palworld"))
PALWORLD_SERVICE = os.environ.get("PALWORLD_SERVICE", "palworld.service")
PALWORLD_APP_ID = os.environ.get("PALWORLD_APP_ID", "2394010")
PALWORLD_DEPOT_ID = os.environ.get("PALWORLD_DEPOT_ID", "2394012")
STEAMCMD = os.environ.get("STEAMCMD", "/home/demo/steamcmd/steamcmd.sh")
SYSTEMCTL = os.environ.get("SYSTEMCTL", "/usr/bin/systemctl")
CHOWN = os.environ.get("CHOWN", "/usr/bin/chown")
AUTO_UPDATE_ENABLED = os.environ.get("AUTO_UPDATE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
AUTO_UPDATE_WARN_MINUTES = int(os.environ.get("AUTO_UPDATE_WARN_MINUTES", "10") or "10")

RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "")

PANEL_DIR = Path(os.environ.get("PANEL_DIR", "/home/demo/palworld-panel"))
STATUS_PATH = Path(os.environ.get("PANEL_UPDATE_STATUS", str(PANEL_DIR / "update-status.json")))
LOG_PATH = Path(os.environ.get("PANEL_UPDATE_LOG", str(PANEL_DIR / "update.log")))
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG", str(PANEL_DIR / "audit.log")))
SAVE_SLOT_ROOT = Path(os.environ.get("SAVE_SLOT_ROOT", str(PANEL_DIR / "save-slots")))
SAVE_BACKUP_DIR = SAVE_SLOT_ROOT / "backups"
SAVE_LOCK_PATH = SAVE_SLOT_ROOT / ".operation.lock"
ACTIVE_SAVEGAMES_DIR = PALWORLD_DIR / "Pal" / "Saved" / "SaveGames" / "0"
CONFIG_DIR = PALWORLD_DIR / "Pal" / "Saved" / "Config" / "LinuxServer"
GAME_USER_SETTINGS = CONFIG_DIR / "GameUserSettings.ini"
APP_MANIFEST = PALWORLD_DIR / "steamapps" / f"appmanifest_{PALWORLD_APP_ID}.acf"


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"{iso_now()} {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_audit(action: str, success: bool, **details: Any) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "time": iso_now(),
        "source_ip": "systemd",
        "action": action,
        "success": success,
        **details,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


class UpdateStatus:
    def __init__(self) -> None:
        self.payload: dict[str, Any] = {
            "running": False,
            "phase": "idle",
            "message": "",
            "auto_update_enabled": AUTO_UPDATE_ENABLED,
            "warn_minutes": AUTO_UPDATE_WARN_MINUTES,
            "checked_at": "",
            "started_at": "",
            "finished_at": "",
            "local_buildid": "",
            "local_manifest": "",
            "latest_manifest": "",
            "update_available": False,
            "success": None,
            "steps": [],
        }

    def load_existing(self) -> None:
        if not STATUS_PATH.exists():
            return
        try:
            existing = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(existing, dict):
            self.payload.update(existing)

    def set(self, **items: Any) -> None:
        self.payload.update(items)
        write_json(STATUS_PATH, self.payload)

    def step(self, name: str, status: str, message: str = "") -> None:
        steps = [item for item in self.payload.get("steps", []) if item.get("name") != name]
        steps.append({"name": name, "status": status, "message": message, "time": iso_now()})
        self.set(steps=steps)


status = UpdateStatus()


def run(args: list[str], timeout: int = 60) -> tuple[str, str, int]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "command timed out", -1


def run_privileged(args: list[str], timeout: int = 60) -> tuple[str, str, int]:
    if os.geteuid() == 0:
        return run(args, timeout=timeout)
    return run(["sudo", "-n", *args], timeout=timeout)


def systemctl(*args: str, timeout: int = 60) -> tuple[str, str, int]:
    return run_privileged([SYSTEMCTL, *args], timeout=timeout)


def is_service_running() -> bool:
    out, _, _ = systemctl("is-active", PALWORLD_SERVICE, timeout=10)
    return out.strip() == "active"


def wait_for_service(active: bool, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_service_running() is active:
            return True
        time.sleep(2)
    return False


def parse_local_manifest() -> dict[str, str]:
    text = APP_MANIFEST.read_text(encoding="utf-8", errors="replace") if APP_MANIFEST.exists() else ""
    buildid = ""
    build_match = re.search(r'"buildid"\s+"([^"]+)"', text)
    if build_match:
        buildid = build_match.group(1)

    depot_manifest = ""
    depot_match = re.search(
        rf'"{re.escape(PALWORLD_DEPOT_ID)}"\s*\{{(?P<body>.*?)\n\s*\}}',
        text,
        flags=re.S,
    )
    if depot_match:
        manifest_match = re.search(r'"manifest"\s+"([^"]+)"', depot_match.group("body"))
        if manifest_match:
            depot_manifest = manifest_match.group(1)

    return {"buildid": buildid, "manifest": depot_manifest}


def fetch_latest_manifest() -> str:
    url = f"https://api.steamcmd.net/v1/info/{PALWORLD_APP_ID}"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    app_data = data["data"][PALWORLD_APP_ID]
    return str(app_data["depots"][PALWORLD_DEPOT_ID]["manifests"]["public"]["gid"])


def check_update() -> dict[str, Any]:
    status.step("detect", "active", "Checking local and latest manifests")
    local = parse_local_manifest()
    latest_manifest = fetch_latest_manifest()
    update_available = bool(latest_manifest and local.get("manifest") and latest_manifest != local["manifest"])
    status.set(
        phase="checked",
        checked_at=iso_now(),
        auto_update_enabled=AUTO_UPDATE_ENABLED,
        local_buildid=local.get("buildid", ""),
        local_manifest=local.get("manifest", ""),
        latest_manifest=latest_manifest,
        update_available=update_available,
        message="Update available" if update_available else "Already up to date",
        success=True,
    )
    status.step("detect", "done", "Update available" if update_available else "Already up to date")
    return {
        "local_buildid": local.get("buildid", ""),
        "local_manifest": local.get("manifest", ""),
        "latest_manifest": latest_manifest,
        "update_available": update_available,
    }


@contextmanager
def operation_lock():
    SAVE_SLOT_ROOT.mkdir(parents=True, exist_ok=True)
    handle = SAVE_LOCK_PATH.open("w", encoding="utf-8")
    try:
        import fcntl

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another save/update operation is already running") from exc
        handle.write(f"update {os.getpid()} {iso_now()}\n")
        handle.flush()
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        handle.close()


def rcon_command(command: str, timeout: int = 5) -> str:
    if not RCON_PASSWORD:
        return "[RCON Error] RCON_PASSWORD is not configured"
    try:
        with socket.create_connection((RCON_HOST, RCON_PORT), timeout=timeout) as sock:
            sock.settimeout(timeout)

            def send_packet(packet_id: int, packet_type: int, body_text: str) -> None:
                body = body_text.encode("utf-8") + b"\x00\x00"
                payload = struct.pack("<ii", packet_id, packet_type) + body
                sock.sendall(struct.pack("<i", len(payload)) + payload)

            def recv_packet() -> tuple[int, int, str]:
                header = sock.recv(4)
                if len(header) != 4:
                    raise RuntimeError("short response header")
                size = struct.unpack("<i", header)[0]
                data = b""
                while len(data) < size:
                    chunk = sock.recv(size - len(data))
                    if not chunk:
                        break
                    data += chunk
                packet_id, packet_type = struct.unpack("<ii", data[:8])
                body = data[8:-2].decode("utf-8", errors="replace")
                return packet_id, packet_type, body

            send_packet(1, 3, RCON_PASSWORD)
            packet_id, _, _ = recv_packet()
            if packet_id == -1:
                return "[RCON Error] Auth failed"
            send_packet(2, 2, command)
            responses: list[str] = []
            sock.settimeout(1)
            while True:
                try:
                    _, _, body = recv_packet()
                    if body.strip():
                        responses.append(body.strip())
                except socket.timeout:
                    break
            return "\n".join(responses)
    except Exception as exc:
        return f"[RCON Error] {exc}"


def player_count() -> int:
    if not is_service_running():
        return 0
    output = rcon_command("ShowPlayers")
    if output.startswith("[RCON Error]"):
        log(f"Unable to read player count: {output}")
        return 0
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return 0
    if lines[0].lower().startswith("name"):
        lines = lines[1:]
    return len(lines)


def broadcast(message: str) -> None:
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "_", message).strip("_")
    if not safe:
        return
    output = rcon_command(f"Broadcast {safe}")
    log(f"Broadcast: {safe} -> {output or 'OK'}")


def countdown_if_needed(minutes: int) -> None:
    if minutes <= 0 or player_count() == 0:
        status.step("notify", "done", "No online players, skipping countdown")
        return

    status.step("notify", "active", f"Broadcasting {minutes} minute update countdown")
    checkpoints = []
    if minutes >= 10:
        checkpoints.append((minutes * 60, f"Palworld server update in {minutes} minutes"))
        checkpoints.append((5 * 60, "Palworld server update in 5 minutes"))
    elif minutes >= 5:
        checkpoints.append((minutes * 60, f"Palworld server update in {minutes} minutes"))
    checkpoints.extend([(60, "Palworld server update in 1 minute"), (30, "Palworld server update in 30 seconds"), (10, "Palworld server update in 10 seconds")])

    previous = minutes * 60
    for seconds_left, message in checkpoints:
        if seconds_left > previous:
            continue
        sleep_for = previous - seconds_left
        if sleep_for > 0:
            time.sleep(sleep_for)
        broadcast(message)
        previous = seconds_left
    if previous > 0:
        time.sleep(previous)
    status.step("notify", "done", "Countdown finished")


def current_world_id() -> str:
    if GAME_USER_SETTINGS.exists():
        text = GAME_USER_SETTINGS.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^DedicatedServerName=(.+)$", text, flags=re.M)
        if match:
            return match.group(1).strip()
    if ACTIVE_SAVEGAMES_DIR.exists():
        for item in sorted(ACTIVE_SAVEGAMES_DIR.iterdir()):
            if item.is_dir() and (item / "Level.sav").exists():
                return item.name
    return "unknown"


def backup_current_save() -> str:
    if not ACTIVE_SAVEGAMES_DIR.exists() or not any(ACTIVE_SAVEGAMES_DIR.iterdir()):
        return "skipped-empty-save"
    SAVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    world_id = current_world_id()
    backup_id = f"{time.strftime('%Y%m%d-%H%M%S')}-before-update-{world_id}"
    target = SAVE_BACKUP_DIR / backup_id
    shutil.copytree(ACTIVE_SAVEGAMES_DIR, target / "SaveGames" / "0", symlinks=False)
    if CONFIG_DIR.exists():
        shutil.copytree(CONFIG_DIR, target / "Config" / "LinuxServer", symlinks=False)
    write_json(
        target / "metadata.json",
        {
            "id": backup_id,
            "world_id": world_id,
            "created_at": iso_now(),
            "reason": "before-update",
        },
    )
    return backup_id


def fix_ownership() -> None:
    paths = [
        PALWORLD_DIR / "Pal" / "Saved" / "SaveGames",
        CONFIG_DIR,
    ]
    for path in paths:
        if path.exists():
            run_privileged([CHOWN, "-R", "demo:demo", str(path)], timeout=180)


def run_steam_update() -> None:
    command = [
        STEAMCMD,
        "+@sSteamCmdForcePlatformType",
        "linux",
        "+@sSteamCmdForcePlatformBitness",
        "64",
        "+force_install_dir",
        str(PALWORLD_DIR),
        "+login",
        "anonymous",
        "+app_update",
        PALWORLD_APP_ID,
        "validate",
        "+quit",
    ]
    log("Running SteamCMD update")
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
        assert process.stdout is not None
        for line in process.stdout:
            log("steamcmd: " + line.rstrip())
        code = process.wait(timeout=3600)
    if code != 0:
        raise RuntimeError(f"SteamCMD update failed with exit code {code}")


def apply_update(auto: bool = False) -> None:
    status.load_existing()
    status.set(running=True, phase="running", started_at=iso_now(), finished_at="", success=None, steps=[], message="Checking for updates")
    try:
        with operation_lock():
            details = check_update()
            if auto and not AUTO_UPDATE_ENABLED:
                status.set(running=False, phase="disabled", finished_at=iso_now(), success=True, message="Auto update disabled")
                log("Auto update disabled")
                return
            if not details["update_available"]:
                status.set(running=False, phase="idle", finished_at=iso_now(), success=True, message="Already up to date")
                append_audit("update.check", True, message="already up to date", **details)
                log("Already up to date")
                return

            append_audit("update.apply", True, message="update started", **details)
            was_running = is_service_running()

            if was_running:
                countdown_if_needed(AUTO_UPDATE_WARN_MINUTES)
                status.step("save", "active", "Saving current world")
                save_output = rcon_command("Save", timeout=10)
                log(f"RCON Save: {save_output or 'OK'}")
                time.sleep(5)
                status.step("save", "done", "Save command sent")
            else:
                status.step("notify", "done", "Server was stopped")
                status.step("save", "done", "Server was stopped")

            status.step("backup", "active", "Backing up current save")
            backup_id = backup_current_save()
            status.step("backup", "done", backup_id)

            if was_running:
                status.step("stop", "active", "Stopping Palworld service")
                _, err, code = systemctl("stop", PALWORLD_SERVICE, timeout=90)
                if code != 0 or not wait_for_service(False, 120):
                    raise RuntimeError(err or "failed to stop Palworld service")
                status.step("stop", "done", "Server stopped")
            else:
                status.step("stop", "done", "Server already stopped")

            status.step("update", "active", "Updating with SteamCMD")
            run_steam_update()
            status.step("update", "done", "SteamCMD update finished")

            status.step("permissions", "active", "Fixing ownership")
            fix_ownership()
            status.step("permissions", "done", "Ownership fixed")

            status.step("start", "active", "Starting Palworld service")
            _, err, code = systemctl("start", PALWORLD_SERVICE, timeout=90)
            if code != 0 or not wait_for_service(True, 150):
                raise RuntimeError(err or "failed to start Palworld service")
            status.step("start", "done", "Server started")

            final = check_update()
            status.step("complete", "done", "Update complete")
            status.set(running=False, phase="complete", finished_at=iso_now(), success=True, message="Update complete")
            append_audit("update.apply", True, message="update complete", backup_id=backup_id, **final)
            log("Update complete")
    except Exception as exc:
        message = str(exc)
        status.step("failed", "error", message)
        status.set(running=False, phase="failed", finished_at=iso_now(), success=False, message=message)
        append_audit("update.failed", False, message=message)
        log(f"Update failed: {message}")
        raise


def check_only() -> None:
    status.load_existing()
    status.set(running=True, phase="checking", started_at=iso_now(), success=None, message="Checking for updates", steps=[])
    try:
        details = check_update()
        status.set(running=False, finished_at=iso_now(), success=True)
        append_audit("update.check", True, **details)
        log(status.payload.get("message", "Check complete"))
    except Exception as exc:
        status.step("detect", "error", str(exc))
        status.set(running=False, phase="failed", finished_at=iso_now(), success=False, message=str(exc))
        append_audit("update.check", False, message=str(exc))
        log(f"Check failed: {exc}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="check only; do not update")
    parser.add_argument("--apply", action="store_true", help="check and apply update if needed")
    parser.add_argument("--auto", action="store_true", help="timer mode; obey AUTO_UPDATE_ENABLED")
    args = parser.parse_args()

    try:
        if args.check:
            check_only()
        else:
            apply_update(auto=args.auto)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
