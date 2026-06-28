#!/usr/bin/env python3
"""
Palworld Server Web Management Panel.

Small Flask app for managing a Palworld dedicated server over systemd and RCON.
Runtime secrets and paths come from environment variables so the source file can
stay free of machine passwords.
"""

from __future__ import annotations

import os
import json
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request, stream_with_context


app = Flask(__name__)
app.secret_key = os.environ.get("PANEL_SECRET_KEY", os.urandom(24).hex())
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("SAVE_UPLOAD_MAX_BYTES", str(1024 * 1024 * 1024)))

PALWORLD_DIR = Path(os.environ.get("PALWORLD_DIR", "/home/demo/palworld"))
PALWORLD_CONFIG = Path(
    os.environ.get(
        "PALWORLD_CONFIG",
        str(PALWORLD_DIR / "Pal" / "Saved" / "Config" / "LinuxServer" / "PalWorldSettings.ini"),
    )
)
PALWORLD_SERVICE = os.environ.get("PALWORLD_SERVICE", "palworld.service")
PALWORLD_BACKEND = os.environ.get("PALWORLD_BACKEND", "systemd").strip().lower()
PALWORLD_CONTAINER_NAME = os.environ.get("PALWORLD_CONTAINER_NAME", "palworld-panel-palworld-1")
PANEL_USER = os.environ.get("PANEL_USER", "demo")

RCON_HOST = os.environ.get("RCON_HOST", "127.0.0.1")
RCON_PORT = int(os.environ.get("RCON_PORT", "25575"))
RCON_PASSWORD = os.environ.get("RCON_PASSWORD", "")

SYSTEMCTL = os.environ.get("SYSTEMCTL", "/usr/bin/systemctl")
JOURNALCTL = os.environ.get("JOURNALCTL", "/usr/bin/journalctl")
APP_VERSION = os.environ.get("PANEL_ASSET_VERSION", str(int(time.time())))
CONFIG_BACKUP_DIR = Path(os.environ.get("CONFIG_BACKUP_DIR", "/home/demo/palworld-panel/config-backups"))
AUDIT_LOG = Path(os.environ.get("AUDIT_LOG", "/home/demo/palworld-panel/audit.log"))
SAVE_ROOT = PALWORLD_DIR / "Pal" / "Saved"
ACTIVE_SAVEGAMES_DIR = SAVE_ROOT / "SaveGames" / "0"
CONFIG_DIR = SAVE_ROOT / "Config" / "LinuxServer"
GAME_USER_SETTINGS = CONFIG_DIR / "GameUserSettings.ini"
SAVE_SLOT_ROOT = Path(os.environ.get("SAVE_SLOT_ROOT", "/home/demo/palworld-panel/save-slots"))
SAVE_SLOT_DIR = SAVE_SLOT_ROOT / "slots"
SAVE_BACKUP_DIR = SAVE_SLOT_ROOT / "backups"
SAVE_IMPORT_DIR = SAVE_SLOT_ROOT / "imports"
SAVE_LOCK_PATH = SAVE_SLOT_ROOT / ".operation.lock"
ACTIVE_SLOT_PATH = SAVE_SLOT_ROOT / "active-slot.json"
CHOWN = os.environ.get("CHOWN", "/usr/bin/chown")
MOD_LIBRARY_ROOT = Path(os.environ.get("MOD_LIBRARY_ROOT", "/home/demo/palworld-panel/mod-library"))
MOD_UPLOAD_MAX_BYTES = int(os.environ.get("MOD_UPLOAD_MAX_BYTES", str(1024 * 1024 * 1024)))
PALWORLD_MOD_MODE = os.environ.get("PALWORLD_MOD_MODE", "pak-safe")
MOD_PAK_DIR = PALWORLD_DIR / "Pal" / "Content" / "Paks" / "~mods"
PAL_MODS_DIR = PALWORLD_DIR / "Pal" / "Content" / "Paks" / "Mods"
OFFICIAL_MOD_WORKSHOP_DIR = PAL_MODS_DIR / "Workshop"
PAL_MOD_SETTINGS = PAL_MODS_DIR / "PalModSettings.ini"
app.config["MAX_CONTENT_LENGTH"] = max(app.config["MAX_CONTENT_LENGTH"], MOD_UPLOAD_MAX_BYTES)
UPDATE_SCRIPT = Path(os.environ.get("PANEL_UPDATE_SCRIPT", "/home/demo/palworld-panel/panel_update.py"))
UPDATE_STATUS = Path(os.environ.get("PANEL_UPDATE_STATUS", "/home/demo/palworld-panel/update-status.json"))
UPDATE_LOG = Path(os.environ.get("PANEL_UPDATE_LOG", "/home/demo/palworld-panel/update.log"))
UPDATE_SERVICE = os.environ.get("PANEL_UPDATE_SERVICE", "palworld-panel-update.service")
UPDATE_TIMER = os.environ.get("PANEL_UPDATE_TIMER", "palworld-panel-update.timer")
INSTALL_SCRIPT = Path(os.environ.get("PANEL_INSTALL_SCRIPT", "/home/demo/palworld-panel/panel_install.py"))
INSTALL_STATUS = Path(os.environ.get("PANEL_INSTALL_STATUS", "/home/demo/palworld-panel/install-status.json"))
INSTALL_LOG = Path(os.environ.get("PANEL_INSTALL_LOG", "/home/demo/palworld-panel/install.log"))
INSTALL_REQUEST = Path(os.environ.get("PANEL_INSTALL_REQUEST", "/home/demo/palworld-panel/install-request.json"))
INSTALL_SERVICE = os.environ.get("PANEL_INSTALL_SERVICE", "palworld-panel-install.service")
VALID_SLOT_ID = re.compile(r"^[a-z0-9_-]{1,64}$")
SAVE_UPLOAD_MAX_EXTRACTED_BYTES = int(os.environ.get("SAVE_UPLOAD_MAX_EXTRACTED_BYTES", str(2 * 1024 * 1024 * 1024)))

NUMERIC_RANGES = {
    "ExpRate": (0.1, 20),
    "PalCaptureRate": (0.5, 2),
    "PalSpawnNumRate": (0.5, 3),
    "DayTimeSpeedRate": (0.1, 5),
    "NightTimeSpeedRate": (0.1, 5),
    "WorkSpeedRate": (0.5, 5),
    "CollectionDropRate": (0.5, 3),
    "EnemyDropItemRate": (0.5, 3),
    "ItemWeightRate": (0.1, 5),
    "PalDamageRateAttack": (0.1, 5),
    "PalDamageRateDefense": (0.1, 5),
    "PlayerDamageRateAttack": (0.1, 5),
    "PlayerDamageRateDefense": (0.1, 5),
    "PlayerStomachDecreaceRate": (0.1, 5),
    "PlayerStaminaDecreaceRate": (0.1, 5),
    "PlayerAutoHPRegeneRate": (0.1, 5),
    "PlayerAutoHpRegeneRateInSleep": (0.1, 5),
    "PalStomachDecreaceRate": (0.1, 5),
    "PalStaminaDecreaceRate": (0.1, 5),
    "PalAutoHPRegeneRate": (0.1, 5),
    "PalAutoHpRegeneRateInSleep": (0.1, 5),
    "BuildObjectHpRate": (0.1, 10),
    "BuildObjectDamageRate": (0.1, 10),
    "BuildObjectDeteriorationDamageRate": (0, 10),
    "CollectionObjectHpRate": (0.5, 3),
    "CollectionObjectRespawnSpeedRate": (0.5, 3),
    "DropItemMaxNum": (0, 10000),
    "DropItemAliveMaxHours": (0.5, 24),
    "PalEggDefaultHatchingTime": (0, 240),
    "EquipmentDurabilityDamageRate": (0, 5),
    "SupplyDropSpan": (1, 1440),
    "AutoResetGuildTimeNoOnlinePlayers": (0, 720),
    "RCONPort": (1024, 65535),
    "RESTAPIPort": (1024, 65535),
}

FIELD_LABELS = {
    "ExpRate": "经验倍率",
    "PalCaptureRate": "帕鲁捕获率",
    "PalSpawnNumRate": "帕鲁刷新率",
    "DayTimeSpeedRate": "白天速度",
    "NightTimeSpeedRate": "夜晚速度",
    "WorkSpeedRate": "工作速度",
    "CollectionDropRate": "采集掉落率",
    "EnemyDropItemRate": "敌人掉落率",
    "ItemWeightRate": "物品重量倍率",
    "PalDamageRateAttack": "帕鲁攻击力倍率",
    "PalDamageRateDefense": "帕鲁受伤倍率",
    "PlayerDamageRateAttack": "玩家攻击力倍率",
    "PlayerDamageRateDefense": "玩家受伤倍率",
    "DropItemMaxNum": "掉落物最大数量",
    "RCONPort": "RCON 端口",
    "RESTAPIPort": "REST API 端口",
}

BOOL_FIELDS = {
    "bEnablePlayerToPlayerDamage",
    "bEnableFriendlyFire",
    "bIsPvP",
    "bEnableInvaderEnemy",
    "bEnableFastTravel",
    "bEnableFastTravelOnlyBaseCamp",
    "bIsStartLocationSelectByMap",
    "bAllowClientMod",
    "bIsShowJoinLeftMessage",
    "bShowPlayerList",
    "bIsUseBackupSaveData",
    "EnablePredatorBossPal",
    "bHardcore",
    "bPalLost",
    "RCONEnabled",
    "RESTAPIEnabled",
}

CHOICE_FIELDS = {
    "DeathPenalty": {"None", "Item", "ItemAndEquipment", "All"},
}


def run_command(args: list[str], timeout: int = 30, sudo: bool = False) -> tuple[str, str, int]:
    """Run a command and return stdout, stderr, and exit code."""
    cmd = ["sudo", "-n", *args] if sudo else args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as exc:  # pragma: no cover - defensive boundary
        return "", str(exc), -1


def systemctl(*args: str, timeout: int = 30) -> tuple[str, str, int]:
    return run_command([SYSTEMCTL, *args], timeout=timeout, sudo=True)


def journalctl(*args: str, timeout: int = 30) -> tuple[str, str, int]:
    return run_command([JOURNALCTL, *args], timeout=timeout, sudo=True)


def using_docker_backend() -> bool:
    return PALWORLD_BACKEND == "docker"


def get_docker_container():
    try:
        import docker  # type: ignore

        client = docker.from_env()
        return client.containers.get(PALWORLD_CONTAINER_NAME)
    except Exception as exc:
        raise RuntimeError(f"Docker backend unavailable: {exc}") from exc


def docker_container_running() -> bool:
    try:
        container = get_docker_container()
        container.reload()
        return container.status == "running"
    except Exception:
        return False


def docker_container_logs(lines: int = 80) -> list[str]:
    try:
        container = get_docker_container()
        raw = container.logs(tail=max(1, min(int(lines), 300)), stdout=True, stderr=True)
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        return text.splitlines() or ["No log entries available"]
    except Exception as exc:
        return [f"Unable to read Docker logs: {exc}"]


def parse_palworld_settings(text: str | None = None) -> dict[str, str]:
    """Parse PalWorldSettings.ini's OptionSettings line into a dict."""
    if text is None:
        text = PALWORLD_CONFIG.read_text(encoding="utf-8") if PALWORLD_CONFIG.exists() else ""

    match = re.search(r"OptionSettings=\((.*)\)", text, re.DOTALL)
    if not match:
        return {}

    inner = match.group(1)
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_quote = False
    quote_char = ""

    for char in inner:
        if in_quote:
            buf.append(char)
            if char == quote_char:
                in_quote = False
            continue
        if char in ('"', "'"):
            in_quote = True
            quote_char = char
            buf.append(char)
        elif char == "(":
            depth += 1
            buf.append(char)
        elif char == ")":
            depth -= 1
            buf.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(char)

    if "".join(buf).strip():
        parts.append("".join(buf).strip())

    options: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        options[key.strip()] = value.strip()
    return options


def build_palworld_settings(options: dict[str, str]) -> str:
    option_line = "OptionSettings=(" + ",".join(f"{key}={value}" for key, value in options.items()) + ")"
    return "[/Script/Pal.PalGameWorldSettings]\n" + option_line + "\n"


def validate_config_changes(changes: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, value in changes.items():
        text = str(value).strip()
        label = FIELD_LABELS.get(key, key)

        if key in NUMERIC_RANGES:
            try:
                number = float(text)
            except ValueError:
                errors.append(f"{label} 必须是数字")
                continue

            minimum, maximum = NUMERIC_RANGES[key]
            if number < minimum or number > maximum:
                errors.append(f"{label} 必须在 {minimum} 到 {maximum} 之间")

        if key in BOOL_FIELDS and text not in {"True", "False"}:
            errors.append(f"{label} 必须是 True 或 False")

        if key in CHOICE_FIELDS and text not in CHOICE_FIELDS[key]:
            choices = ", ".join(sorted(CHOICE_FIELDS[key]))
            errors.append(f"{label} 必须是以下值之一：{choices}")

    return errors


def backup_config_file() -> None:
    if not PALWORLD_CONFIG.exists():
        return
    CONFIG_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(PALWORLD_CONFIG, CONFIG_BACKUP_DIR / f"PalWorldSettings.ini.{stamp}.bak")


def update_palworld_settings(changes: dict[str, Any]) -> dict[str, str]:
    errors = validate_config_changes(changes)
    if errors:
        raise ValueError("; ".join(errors[:5]))

    current = parse_palworld_settings()
    for key, value in changes.items():
        if key and value is not None:
            current[str(key)] = str(value)

    backup_config_file()
    tmp_path = PALWORLD_CONFIG.with_name(f".{PALWORLD_CONFIG.name}.tmp")
    tmp_path.write_text(build_palworld_settings(current), encoding="utf-8")
    tmp_path.replace(PALWORLD_CONFIG)
    return current


def get_changed_config_keys(changes: dict[str, Any]) -> list[str]:
    current = parse_palworld_settings()
    changed = []
    for key, value in changes.items():
        if str(current.get(str(key), "")) != str(value):
            changed.append(str(key))
    return sorted(changed)


def audit_event(action: str, success: bool, **details: Any) -> None:
    """Append an audit event without interrupting the user-facing action."""
    try:
        source_ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "").split(",")[0].strip()
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source_ip": source_ip,
            "action": action,
            "success": bool(success),
            **details,
        }
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_audit_events(limit: int = 80) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 300))
    if not AUDIT_LOG.exists():
        return []

    try:
        lines = AUDIT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    records: list[dict[str, Any]] = []
    for line in lines[-safe_limit:]:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return list(reversed(records))


def tail_text(path: Path, lines: int = 80) -> list[str]:
    if not path.exists():
        return []
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except Exception:
        return []


def read_update_status() -> dict[str, Any]:
    status = read_json(UPDATE_STATUS, {})
    if using_docker_backend():
        status.update(
            {
                "backend": "docker",
                "service_active": False,
                "timer_active": False,
                "auto_update_enabled": False,
                "log_tail": tail_text(UPDATE_LOG, 60) + docker_container_logs(40),
            }
        )
        return status

    active, _, _ = systemctl("is-active", UPDATE_SERVICE, timeout=10)
    timer_active, _, _ = systemctl("is-active", UPDATE_TIMER, timeout=10)
    status.update(
        {
            "backend": "systemd",
            "service_active": active.strip() == "active",
            "timer_active": timer_active.strip() == "active",
            "log_tail": tail_text(UPDATE_LOG, 80),
        }
    )
    return status


def run_update_check_now() -> tuple[bool, str]:
    if not UPDATE_SCRIPT.exists():
        return False, "update script is not installed"
    out, err, code = run_command([sys.executable, str(UPDATE_SCRIPT), "--check"], timeout=120, sudo=False)
    message = out or err or ("检查完成" if code == 0 else f"检查失败：{code}")
    return code == 0, message


def start_update_service() -> tuple[bool, str]:
    if using_docker_backend():
        update_status = read_update_status()
        if not update_status.get("update_available"):
            return False, "当前没有检测到可用更新，请先点击检查更新"
        try:
            write_json(
                UPDATE_STATUS,
                {
                    **update_status,
                    "backend": "docker",
                    "running": True,
                    "phase": "running",
                    "started_at": iso_now(),
                    "success": None,
                    "message": "Restarting Palworld container for SteamCMD validate",
                    "steps": [
                        {"name": "detect", "status": "done", "message": "Update available", "time": iso_now()},
                        {"name": "update", "status": "active", "message": "Container entrypoint will run SteamCMD validate", "time": iso_now()},
                    ],
                },
            )
            container = get_docker_container()
            container.restart(timeout=120)
            time.sleep(3)
            refreshed = read_update_status()
            write_json(
                UPDATE_STATUS,
                {
                    **refreshed,
                    "backend": "docker",
                    "running": False,
                    "phase": "complete",
                    "finished_at": iso_now(),
                    "success": True,
                    "message": "Palworld container restarted; SteamCMD validate runs in container entrypoint",
                    "steps": [
                        {"name": "detect", "status": "done", "message": "Update available", "time": iso_now()},
                        {"name": "update", "status": "done", "message": "Container restarted", "time": iso_now()},
                        {"name": "start", "status": "done", "message": "Container running", "time": iso_now()},
                        {"name": "complete", "status": "done", "message": "Docker update trigger complete", "time": iso_now()},
                    ],
                },
            )
            return True, "Palworld 容器已重启，entrypoint 会自动校验/更新服务端文件"
        except Exception as exc:
            status = read_update_status()
            write_json(
                UPDATE_STATUS,
                {
                    **status,
                    "backend": "docker",
                    "running": False,
                    "phase": "failed",
                    "finished_at": iso_now(),
                    "success": False,
                    "message": str(exc),
                },
            )
            return False, str(exc)

    active, _, _ = systemctl("is-active", UPDATE_SERVICE, timeout=10)
    if active.strip() == "active":
        return False, "更新任务正在运行"
    update_status = read_update_status()
    if not update_status.get("update_available"):
        return False, "当前没有检测到可用更新，请先点击检查更新"
    _, err, code = systemctl("start", UPDATE_SERVICE, timeout=20)
    if code != 0:
        return False, err or f"systemctl start {UPDATE_SERVICE} exited with {code}"
    return True, "更新任务已在后台启动"


def read_install_status() -> dict[str, Any]:
    if using_docker_backend():
        checks = {
            "docker_backend": True,
            "palworld_installed": (PALWORLD_DIR / "PalServer.sh").exists(),
            "palworld_manifest": (PALWORLD_DIR / "steamapps" / "appmanifest_2394010.acf").exists(),
            "panel_installed": Path(__file__).exists(),
            "env_file": True,
            "container_running": docker_container_running(),
        }
        return {
            "backend": "docker",
            "running": False,
            "service_active": False,
            "phase": "docker",
            "message": "Docker Compose 部署模式：安装和修复由容器启动脚本负责",
            "success": True,
            "panel_user": "container",
            "panel_dir": str(Path.cwd()),
            "palworld_dir": str(PALWORLD_DIR),
            "steamcmd": "inside palworld container",
            "checks": checks,
            "steps": [],
            "log_tail": docker_container_logs(80),
        }

    status = read_json(INSTALL_STATUS, {})
    active, _, _ = systemctl("is-active", INSTALL_SERVICE, timeout=10)
    status.update(
        {
            "service_active": active.strip() == "active",
            "log_tail": tail_text(INSTALL_LOG, 100),
        }
    )
    return status


def run_install_check_now() -> tuple[bool, str]:
    if using_docker_backend():
        return True, "Docker Compose 部署模式检查完成"
    if not INSTALL_SCRIPT.exists():
        return False, "installer script is not installed"
    out, err, code = run_command([sys.executable, str(INSTALL_SCRIPT), "--check"], timeout=120, sudo=False)
    message = out or err or ("检查完成" if code == 0 else f"检查失败：{code}")
    return code == 0, message


def start_install_service(action: str) -> tuple[bool, str]:
    if using_docker_backend():
        return False, "Docker 模式不在面板内执行 systemd 安装；请使用 docker compose 管理部署"
    if action not in {"install-palworld", "repair"}:
        return False, "unsupported installer action"
    active, _, _ = systemctl("is-active", INSTALL_SERVICE, timeout=10)
    if active.strip() == "active":
        return False, "安装任务正在运行"
    write_json(INSTALL_REQUEST, {"action": action, "requested_at": iso_now()})
    _, err, code = systemctl("start", INSTALL_SERVICE, timeout=20)
    if code != 0:
        return False, err or f"systemctl start {INSTALL_SERVICE} exited with {code}"
    return True, "安装任务已在后台启动"


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def ensure_save_dirs() -> None:
    SAVE_SLOT_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_IMPORT_DIR.mkdir(parents=True, exist_ok=True)


class SaveOperationBusy(RuntimeError):
    pass


@contextmanager
def save_operation_lock():
    ensure_save_dirs()
    handle = SAVE_LOCK_PATH.open("a+", encoding="utf-8")
    locked_with = ""
    try:
        if os.name == "nt":
            import msvcrt

            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                locked_with = "msvcrt"
            except OSError as exc:
                raise SaveOperationBusy("已有存档操作正在进行，请等待完成后再试") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked_with = "fcntl"
            except BlockingIOError as exc:
                raise SaveOperationBusy("已有存档操作正在进行，请等待完成后再试") from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()} {iso_now()}\n")
        handle.flush()
        yield
    finally:
        try:
            if locked_with == "msvcrt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif locked_with == "fcntl":
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        handle.close()


def path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def assert_safe_managed_path(path: Path) -> Path:
    resolved = path.resolve()
    if path_within(resolved, SAVE_ROOT) or path_within(resolved, SAVE_SLOT_ROOT):
        return resolved
    raise ValueError(f"Path is outside managed save roots: {path}")


def has_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    if path.is_dir():
        return any(child.is_symlink() for child in path.rglob("*"))
    return False


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def latest_mtime(path: Path) -> float | None:
    if not path.exists():
        return None
    mtimes = [item.stat().st_mtime for item in path.rglob("*")]
    return max(mtimes) if mtimes else path.stat().st_mtime


def format_ts(timestamp: float | None) -> str:
    if timestamp is None:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def normalize_slot_id(raw: str) -> str:
    slot_id = re.sub(r"[^a-z0-9_-]+", "-", raw.lower()).strip("-_")
    return slot_id[:64] or f"slot-{int(time.time())}"


def require_slot_id(slot_id: str) -> str:
    slot_id = str(slot_id or "").strip()
    if not VALID_SLOT_ID.match(slot_id):
        raise ValueError("slot_id 只允许小写字母、数字、- 和 _，长度 1-64")
    return slot_id


def slot_path(slot_id: str) -> Path:
    return SAVE_SLOT_DIR / require_slot_id(slot_id)


def slot_savegames_dir(slot_id: str) -> Path:
    return slot_path(slot_id) / "SaveGames" / "0"


def metadata_path(slot_id: str) -> Path:
    return slot_path(slot_id) / "metadata.json"


def get_recorded_active_slot_id() -> str:
    payload = read_json(ACTIVE_SLOT_PATH, {})
    slot_id = str(payload.get("slot_id", "")).strip()
    if slot_id and VALID_SLOT_ID.match(slot_id) and slot_path(slot_id).exists():
        return slot_id
    return ""


def set_recorded_active_slot(slot_id: str, world_id: str) -> None:
    write_json(
        ACTIVE_SLOT_PATH,
        {
            "slot_id": require_slot_id(slot_id),
            "world_id": world_id,
            "updated_at": iso_now(),
        },
    )


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def find_world_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    worlds = []
    for path in root.iterdir():
        if path.is_dir() and (path / "Level.sav").exists():
            worlds.append(path)
    return sorted(worlds, key=lambda item: item.name)


def read_dedicated_server_name() -> str:
    if not GAME_USER_SETTINGS.exists():
        return ""
    match = re.search(r"^DedicatedServerName=(.+)$", GAME_USER_SETTINGS.read_text(encoding="utf-8", errors="replace"), re.M)
    return match.group(1).strip() if match else ""


def write_dedicated_server_name(world_id: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    text = GAME_USER_SETTINGS.read_text(encoding="utf-8", errors="replace") if GAME_USER_SETTINGS.exists() else ""
    line = f"DedicatedServerName={world_id}"
    if re.search(r"^DedicatedServerName=.*$", text, re.M):
        text = re.sub(r"^DedicatedServerName=.*$", line, text, flags=re.M)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "[ServerSettings]\n" + line + "\n"
    tmp = GAME_USER_SETTINGS.with_suffix(".ini.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(GAME_USER_SETTINGS)


def current_world_id() -> str:
    configured = read_dedicated_server_name()
    worlds = find_world_dirs(ACTIVE_SAVEGAMES_DIR)
    if configured and any(world.name == configured for world in worlds):
        return configured
    if worlds:
        return worlds[0].name
    return configured


def savegames_payload_root(source: Path) -> tuple[Path, str, bool]:
    source = assert_safe_managed_path(source)
    if has_symlink(source):
        raise ValueError("存档目录不能包含符号链接")
    if (source / "Level.sav").exists():
        return source, source.name, True
    nested = source / "SaveGames" / "0"
    worlds = find_world_dirs(nested)
    if worlds:
        return nested, worlds[0].name, False
    worlds = find_world_dirs(source)
    if worlds:
        return source, worlds[0].name, False
    raise ValueError("未找到有效存档目录，至少需要 Level.sav")


def uploaded_save_payload_root(source: Path) -> Path:
    source = assert_safe_managed_path(source)
    try:
        savegames_payload_root(source)
        return source
    except ValueError:
        pass

    candidates = []
    for level_file in source.rglob("Level.sav"):
        world_dir = level_file.parent
        if has_symlink(world_dir):
            continue
        if world_dir.parent.name == "0" and world_dir.parent.parent.name == "SaveGames":
            candidates.append(world_dir.parent)
        else:
            candidates.append(world_dir)

    unique = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)

    if not unique:
        raise ValueError("上传包里没有找到 Level.sav")
    if len(unique) > 1:
        raise ValueError("上传包里包含多个世界，请只上传一个存档世界")
    return unique[0]


def safe_extract_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir = assert_safe_managed_path(target_dir)
    total_size = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("压缩包包含不安全路径")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("压缩包不能包含符号链接")
            total_size += info.file_size
            if total_size > SAVE_UPLOAD_MAX_EXTRACTED_BYTES:
                raise ValueError("压缩包解压后太大")

        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            destination = (target_dir / name).resolve()
            if not path_within(destination, target_dir):
                raise ValueError("压缩包包含不安全路径")
            if name.endswith("/"):
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source_file, destination.open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)


MOD_ALLOWED_UPLOAD_SUFFIXES = {".pak", ".sig", ".zip"}
MOD_DANGEROUS_SUFFIXES = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".dll", ".so", ".dylib", ".msi", ".scr", ".com"}


def ensure_mod_dirs() -> None:
    MOD_LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    (MOD_LIBRARY_ROOT / "disabled").mkdir(parents=True, exist_ok=True)
    (MOD_LIBRARY_ROOT / "imports").mkdir(parents=True, exist_ok=True)
    (MOD_LIBRARY_ROOT / "metadata").mkdir(parents=True, exist_ok=True)
    (MOD_LIBRARY_ROOT / "trash").mkdir(parents=True, exist_ok=True)
    MOD_PAK_DIR.mkdir(parents=True, exist_ok=True)
    OFFICIAL_MOD_WORKSHOP_DIR.mkdir(parents=True, exist_ok=True)


def mod_metadata_path(mod_id: str) -> Path:
    return MOD_LIBRARY_ROOT / "metadata" / f"{normalize_mod_id(mod_id)}.json"


def normalize_mod_id(raw: str) -> str:
    mod_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(raw or "").strip()).strip("-_.")
    return (mod_id[:80] or f"mod-{int(time.time())}").lower()


def path_within_any(path: Path, roots: list[Path]) -> bool:
    return any(path_within(path, root) for root in roots)


def assert_safe_mod_path(path: Path) -> Path:
    resolved = path.resolve()
    roots = [MOD_LIBRARY_ROOT, MOD_PAK_DIR, PAL_MODS_DIR]
    if path_within_any(resolved, roots):
        return resolved
    raise ValueError(f"Path is outside managed mod roots: {path}")


def read_mod_meta(mod_id: str) -> dict[str, Any]:
    return read_json(mod_metadata_path(mod_id), {})


def write_mod_meta(mod_id: str, payload: dict[str, Any]) -> None:
    payload["id"] = normalize_mod_id(mod_id)
    payload["updated_at"] = iso_now()
    write_json(mod_metadata_path(mod_id), payload)


def mod_file_info(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
        "updated_at": format_ts(path.stat().st_mtime if path.exists() else None),
    }


def safe_extract_mod_zip(zip_path: Path, target_dir: Path) -> None:
    target_dir = assert_safe_mod_path(target_dir)
    total_size = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if not name or name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("压缩包包含不安全路径")
            suffix = Path(name).suffix.lower()
            if suffix in MOD_DANGEROUS_SUFFIXES:
                raise ValueError(f"压缩包包含禁止的文件类型：{suffix}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("压缩包不能包含符号链接")
            total_size += info.file_size
            if total_size > MOD_UPLOAD_MAX_BYTES:
                raise ValueError("MOD 压缩包解压后太大")

        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            destination = (target_dir / name).resolve()
            if not path_within(destination, target_dir):
                raise ValueError("压缩包包含不安全路径")
            if name.endswith("/"):
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source_file, destination.open("wb") as target_file:
                shutil.copyfileobj(source_file, target_file)


def find_info_json(root: Path) -> Path | None:
    matches = [path for path in root.rglob("Info.json") if path.is_file()]
    if not matches:
        return None
    matches.sort(key=lambda item: len(item.parts))
    return matches[0]


def read_official_mod_info(info_path: Path) -> dict[str, Any]:
    payload = json.loads(info_path.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(payload, dict):
        raise ValueError("Info.json 格式不正确")
    package_name = str(payload.get("PackageName") or payload.get("Name") or info_path.parent.name).strip()
    if not package_name:
        raise ValueError("Info.json 缺少 PackageName")
    return {
        "package_name": package_name,
        "version": str(payload.get("Version") or payload.get("ModVersion") or ""),
        "is_server": payload.get("IsServer"),
        "install_rules": payload.get("InstallRules"),
        "raw": payload,
    }


def read_active_official_mods() -> set[str]:
    if not PAL_MOD_SETTINGS.exists():
        return set()
    text = PAL_MOD_SETTINGS.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^ActiveModList=(.*)$", text, re.M)
    if not match:
        return set()
    return {item.strip() for item in re.split(r"[,;]", match.group(1)) if item.strip()}


def write_active_official_mods(active: set[str]) -> None:
    PAL_MOD_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[/Script/Pal.PalGameLocalSettings]",
        "bGlobalEnableMod=true" if active else "bGlobalEnableMod=false",
        "ActiveModList=" + ",".join(sorted(active)),
        "",
    ]
    tmp = PAL_MOD_SETTINGS.with_suffix(".ini.tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    tmp.replace(PAL_MOD_SETTINGS)


def discover_mod_files(mod_id: str, enabled: bool) -> list[Path]:
    root = MOD_PAK_DIR if enabled else MOD_LIBRARY_ROOT / "disabled"
    mod_id = normalize_mod_id(mod_id)
    files = []
    for path in root.glob("*"):
        if path.is_file() and path.suffix.lower() in {".pak", ".sig"} and normalize_mod_id(path.stem) == mod_id:
            files.append(path)
    return files


def list_mods() -> list[dict[str, Any]]:
    ensure_mod_dirs()
    mods: dict[str, dict[str, Any]] = {}

    for meta_file in (MOD_LIBRARY_ROOT / "metadata").glob("*.json"):
        meta = read_json(meta_file, {})
        if meta.get("deleted_at"):
            continue
        if meta.get("id"):
            mods[str(meta["id"])] = meta

    for enabled, root in [(True, MOD_PAK_DIR), (False, MOD_LIBRARY_ROOT / "disabled")]:
        for path in root.glob("*"):
            if not path.is_file() or path.suffix.lower() not in {".pak", ".sig"}:
                continue
            mod_id = normalize_mod_id(path.stem)
            meta = mods.setdefault(
                mod_id,
                {
                    "id": mod_id,
                    "name": path.stem,
                    "type": "pak",
                    "source": "discovered",
                    "created_at": "",
                    "notes": "",
                },
            )
            meta["enabled"] = enabled or bool(meta.get("enabled"))
            meta["type"] = "pak" if meta.get("type") in {None, "", "sig"} else meta.get("type")
            meta.setdefault("files", [])
            meta["files"] = [*meta.get("files", []), mod_file_info(path)]

    active_official = read_active_official_mods()
    for item in OFFICIAL_MOD_WORKSHOP_DIR.iterdir() if OFFICIAL_MOD_WORKSHOP_DIR.exists() else []:
        if not item.is_dir():
            continue
        info_path = item / "Info.json"
        if not info_path.exists():
            continue
        try:
            info = read_official_mod_info(info_path)
        except Exception:
            info = {"package_name": item.name, "version": "", "is_server": None, "install_rules": None}
        mod_id = normalize_mod_id(item.name)
        meta = mods.setdefault(
            mod_id,
            {
                "id": mod_id,
                "name": info["package_name"],
                "type": "official",
                "source": "discovered",
                "created_at": "",
                "notes": "",
            },
        )
        meta.update(
            {
                "type": "official",
                "package_name": info["package_name"],
                "version": info.get("version", ""),
                "is_server": info.get("is_server"),
                "install_rules": info.get("install_rules"),
                "enabled": info["package_name"] in active_official,
                "path": str(item),
                "size_bytes": dir_size(item),
                "updated_at": format_ts(latest_mtime(item)),
                "compatibility": "官方服务端 MOD 目前官方标注仅 Windows dedicated server 支持；Linux/Docker 后端请谨慎启用。",
            }
        )

    for meta in mods.values():
        if meta.get("type") == "pak":
            files = meta.get("files") or []
            meta["size_bytes"] = sum(file.get("size_bytes", 0) for file in files)
            meta["compatibility"] = "PAK MOD 通常要求客户端安装同款 MOD；启用后需要重启服务器。"
        meta.setdefault("enabled", False)
        meta.setdefault("needs_restart", True)

    return sorted(mods.values(), key=lambda item: (not item.get("enabled", False), item.get("name") or item.get("id") or ""))


def install_pak_files(files: list[Path], name: str = "", notes: str = "") -> dict[str, Any]:
    pak_files = [path for path in files if path.suffix.lower() == ".pak"]
    if not pak_files:
        raise ValueError("未找到 .pak 文件")
    installed = []
    primary = pak_files[0]
    mod_id = normalize_mod_id(primary.stem)
    for path in files:
        if path.suffix.lower() not in {".pak", ".sig"}:
            continue
        if path.suffix.lower() == ".sig" and normalize_mod_id(path.stem) != mod_id:
            continue
        target = MOD_PAK_DIR / path.name
        if target.exists():
            raise ValueError(f"MOD 文件已存在：{target.name}")
        shutil.copy2(path, target)
        installed.append(mod_file_info(target))
    meta = {
        "id": mod_id,
        "name": name or primary.stem,
        "type": "pak",
        "enabled": True,
        "source": "uploaded",
        "created_at": iso_now(),
        "notes": notes,
        "files": installed,
        "needs_restart": True,
    }
    write_mod_meta(mod_id, meta)
    return meta


def install_official_mod(source_root: Path, name: str = "", notes: str = "") -> dict[str, Any]:
    info_path = find_info_json(source_root)
    if not info_path:
        raise ValueError("未找到 Info.json")
    info = read_official_mod_info(info_path)
    mod_id = normalize_mod_id(info["package_name"])
    target = OFFICIAL_MOD_WORKSHOP_DIR / mod_id
    if target.exists():
        raise ValueError(f"官方 MOD 已存在：{mod_id}")
    shutil.copytree(info_path.parent, target, symlinks=False)
    meta = {
        "id": mod_id,
        "name": name or info["package_name"],
        "type": "official",
        "enabled": False,
        "source": "uploaded",
        "created_at": iso_now(),
        "notes": notes,
        "package_name": info["package_name"],
        "version": info.get("version", ""),
        "is_server": info.get("is_server"),
        "install_rules": info.get("install_rules"),
        "path": str(target),
        "size_bytes": dir_size(target),
        "needs_restart": True,
        "compatibility": "官方服务端 MOD 目前官方标注仅 Windows dedicated server 支持；Linux/Docker 后端默认导入但不自动启用。",
    }
    write_mod_meta(mod_id, meta)
    return meta


def upload_mod(file_storage, name: str = "", notes: str = "") -> dict[str, Any]:
    ensure_mod_dirs()
    filename = Path(file_storage.filename or "").name
    if not filename:
        raise ValueError("请选择要上传的 MOD 文件")
    suffix = Path(filename).suffix.lower()
    if suffix not in MOD_ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError("只支持上传 .pak、.sig 或 .zip")
    if suffix in MOD_DANGEROUS_SUFFIXES:
        raise ValueError("禁止上传可执行文件或脚本")

    upload_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{normalize_mod_id(filename)}"
    upload_dir = MOD_LIBRARY_ROOT / "imports" / upload_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    upload_path = upload_dir / filename
    file_storage.save(upload_path)
    if upload_path.stat().st_size > MOD_UPLOAD_MAX_BYTES:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise ValueError("MOD 文件太大")

    try:
        if suffix == ".zip":
            extract_dir = upload_dir / "extracted"
            extract_dir.mkdir()
            safe_extract_mod_zip(upload_path, extract_dir)
            info_path = find_info_json(extract_dir)
            if info_path:
                mod = install_official_mod(extract_dir, name=name, notes=notes)
            else:
                files = [path for path in extract_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".pak", ".sig"}]
                mod = install_pak_files(files, name=name, notes=notes)
        elif suffix == ".pak":
            sidecar = upload_path.with_suffix(".sig")
            files = [upload_path, sidecar] if sidecar.exists() else [upload_path]
            mod = install_pak_files(files, name=name, notes=notes)
        else:
            target = MOD_PAK_DIR / filename
            if target.exists():
                raise ValueError(f"MOD 文件已存在：{target.name}")
            shutil.copy2(upload_path, target)
            mod_id = normalize_mod_id(upload_path.stem)
            mod = {
                "id": mod_id,
                "name": name or upload_path.stem,
                "type": "sig",
                "enabled": True,
                "source": "uploaded",
                "created_at": iso_now(),
                "notes": notes,
                "files": [mod_file_info(target)],
                "needs_restart": True,
            }
            write_mod_meta(mod_id, mod)
        mod["upload_path"] = str(upload_dir)
        return mod
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise


def set_mod_enabled(mod_id: str, enabled: bool, allow_official: bool = False) -> dict[str, Any]:
    ensure_mod_dirs()
    mod_id = normalize_mod_id(mod_id)
    meta = read_mod_meta(mod_id)
    official_dir = OFFICIAL_MOD_WORKSHOP_DIR / mod_id
    if not meta and (official_dir / "Info.json").exists():
        info = read_official_mod_info(official_dir / "Info.json")
        meta = {
            "id": mod_id,
            "name": info["package_name"],
            "type": "official",
            "package_name": info["package_name"],
            "version": info.get("version", ""),
            "is_server": info.get("is_server"),
            "install_rules": info.get("install_rules"),
            "path": str(official_dir),
        }
    mod_type = meta.get("type") or "pak"
    if mod_type == "official":
        package_name = str(meta.get("package_name") or meta.get("name") or "").strip()
        if not package_name:
            raise ValueError("官方 MOD 缺少 PackageName")
        if enabled and not allow_official:
            raise ValueError("官方服务端 MOD 在当前 Linux/Docker 后端存在兼容风险，请确认风险后再启用")
        active = read_active_official_mods()
        if enabled:
            active.add(package_name)
        else:
            active.discard(package_name)
        write_active_official_mods(active)
        meta["enabled"] = enabled
        meta["needs_restart"] = True
        write_mod_meta(mod_id, meta)
        return meta

    source_root = MOD_LIBRARY_ROOT / "disabled" if enabled else MOD_PAK_DIR
    target_root = MOD_PAK_DIR if enabled else MOD_LIBRARY_ROOT / "disabled"
    moved = []
    for path in discover_mod_files(mod_id, not enabled):
        target = target_root / path.name
        if target.exists():
            raise ValueError(f"目标文件已存在：{target.name}")
        shutil.move(str(path), str(target))
        moved.append(mod_file_info(target))
    if not moved:
        for path in source_root.glob(f"{mod_id}*"):
            if path.is_file() and path.suffix.lower() in {".pak", ".sig"}:
                target = target_root / path.name
                shutil.move(str(path), str(target))
                moved.append(mod_file_info(target))
    if not moved:
        raise ValueError("未找到可切换的 MOD 文件")
    meta.update({"id": mod_id, "type": "pak", "enabled": enabled, "files": moved, "needs_restart": True})
    write_mod_meta(mod_id, meta)
    return meta


def delete_mod(mod_id: str) -> dict[str, Any]:
    ensure_mod_dirs()
    mod_id = normalize_mod_id(mod_id)
    meta = read_mod_meta(mod_id)
    trash_dir = MOD_LIBRARY_ROOT / "trash" / f"{time.strftime('%Y%m%d-%H%M%S')}-{mod_id}"
    trash_dir.mkdir(parents=True, exist_ok=False)
    moved = []

    official_dir = OFFICIAL_MOD_WORKSHOP_DIR / mod_id
    if meta.get("type") == "official" or official_dir.exists():
        package_name = str(meta.get("package_name") or "").strip()
        if not package_name and (official_dir / "Info.json").exists():
            package_name = read_official_mod_info(official_dir / "Info.json")["package_name"]
        active = read_active_official_mods()
        if package_name and package_name in active:
            active.discard(package_name)
            write_active_official_mods(active)
        source = official_dir
        if source.exists():
            shutil.move(str(source), str(trash_dir / source.name))
            moved.append(str(trash_dir / source.name))
    else:
        for enabled in (True, False):
            for path in discover_mod_files(mod_id, enabled):
                target = trash_dir / path.name
                shutil.move(str(path), str(target))
                moved.append(str(target))

    if not moved:
        raise ValueError("未找到要删除的 MOD 文件")
    meta.update({"enabled": False, "deleted_at": iso_now(), "trash_path": str(trash_dir), "needs_restart": True})
    write_mod_meta(mod_id, meta)
    return meta


def empty_mod_trash() -> int:
    ensure_mod_dirs()
    trash = MOD_LIBRARY_ROOT / "trash"
    count = 0
    for item in list(trash.iterdir()):
        item = assert_safe_mod_path(item)
        if item.is_dir():
            shutil.rmtree(item)
            count += 1
        elif item.is_file():
            item.unlink()
            count += 1
    return count


def get_mod_status() -> dict[str, Any]:
    mods = list_mods()
    return {
        "backend": PALWORLD_BACKEND,
        "mode": PALWORLD_MOD_MODE,
        "mod_library_root": str(MOD_LIBRARY_ROOT),
        "pak_enabled_dir": str(MOD_PAK_DIR),
        "official_mod_dir": str(PAL_MODS_DIR),
        "official_server_mods_supported": False,
        "ue4ss_supported": False,
        "needs_restart": any(mod.get("needs_restart") for mod in mods),
        "mods_count": len(mods),
        "enabled_count": sum(1 for mod in mods if mod.get("enabled")),
        "warning": "2.0 首版只自动管理 PAK/官方 Info.json 包；UE4SS/Lua 不自动安装。官方服务端 MOD 目前官方标注仅 Windows dedicated server 支持。",
    }


def restart_for_mods() -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    def step(name: str, success: bool, message: str = "") -> None:
        steps.append({"step": name, "success": success, "message": message})

    backup = None
    try:
        backup = backup_current_save("before-mod-restart")
        step("backup", True, backup["id"])
    except Exception as exc:
        step("backup", False, str(exc))

    success, message = service_action("restart")
    step("restart", success, message)
    if not success:
        raise RuntimeError(message)
    restored = wait_for_service_state(True, timeout=90)
    step("status", restored, "server running" if restored else "server did not report running in time")
    return {"backup": backup, "steps": steps, "running": get_server_status()["running"]}


def copytree_clean(source: Path, target: Path) -> None:
    source = assert_safe_managed_path(source)
    target = assert_safe_managed_path(target)
    if has_symlink(source):
        raise ValueError("存档目录不能包含符号链接")
    if target.is_symlink():
        raise ValueError("目标存档路径不能是符号链接")
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, symlinks=False)


def remove_children(path: Path) -> None:
    path = assert_safe_managed_path(path)
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_symlink():
            raise ValueError("存档目录不能包含符号链接")
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def get_active_save_info() -> dict[str, Any]:
    world_id = current_world_id()
    world_path = ACTIVE_SAVEGAMES_DIR / world_id if world_id else ACTIVE_SAVEGAMES_DIR
    return {
        "world_id": world_id,
        "path": str(world_path),
        "size_bytes": dir_size(world_path),
        "updated_at": format_ts(latest_mtime(world_path)),
        "savegames_root": str(ACTIVE_SAVEGAMES_DIR),
    }


def list_save_slots() -> list[dict[str, Any]]:
    ensure_save_dirs()
    slots = []
    active_world = current_world_id()
    recorded_active_slot_id = get_recorded_active_slot_id()
    for item in sorted(SAVE_SLOT_DIR.iterdir(), key=lambda path: path.name):
        if not item.is_dir():
            continue
        meta = read_json(item / "metadata.json", {})
        slot_id = meta.get("id") or item.name
        savegames = slot_savegames_dir(slot_id)
        worlds = find_world_dirs(savegames)
        world_id = meta.get("world_id") or (worlds[0].name if worlds else "")
        slots.append(
            {
                "id": slot_id,
                "name": meta.get("name") or slot_id,
                "world_id": world_id,
                "source": meta.get("source", ""),
                "notes": meta.get("notes", ""),
                "created_at": meta.get("created_at", ""),
                "last_used_at": meta.get("last_used_at", ""),
                "is_new": bool(meta.get("is_new")),
                "matches_active_world": bool(world_id and world_id == active_world),
                "size_bytes": dir_size(savegames),
                "updated_at": format_ts(latest_mtime(savegames)),
            }
        )
    recorded_slot = next((slot for slot in slots if slot["id"] == recorded_active_slot_id), None)
    if not recorded_slot or (active_world and recorded_slot.get("world_id") != active_world):
        matching_slots = [slot for slot in slots if slot["matches_active_world"]]
        matching_slots.sort(
            key=lambda slot: (
                slot.get("last_used_at") or "",
                slot.get("updated_at") or "",
                slot.get("created_at") or "",
                slot.get("id") or "",
            ),
            reverse=True,
        )
        recorded_active_slot_id = matching_slots[0]["id"] if matching_slots else ""

    for slot in slots:
        slot["is_active"] = bool(recorded_active_slot_id and slot["id"] == recorded_active_slot_id)
        slot["is_same_world_copy"] = bool(slot["matches_active_world"] and not slot["is_active"])
    return slots


def create_slot(name: str, notes: str = "", slot_id: str | None = None, is_new: bool = True) -> dict[str, Any]:
    ensure_save_dirs()
    slot_id = require_slot_id(slot_id or normalize_slot_id(name or "new-world"))
    path = slot_path(slot_id)
    if path.exists():
        raise ValueError("存档槽已存在")
    (path / "SaveGames" / "0").mkdir(parents=True)
    metadata = {
        "id": slot_id,
        "name": name or slot_id,
        "world_id": slot_id,
        "created_at": iso_now(),
        "last_used_at": None,
        "source": "new",
        "notes": notes,
        "is_new": is_new,
    }
    write_json(path / "metadata.json", metadata)
    return metadata


def import_slot(source_path: str, name: str, notes: str = "", slot_id: str | None = None) -> dict[str, Any]:
    ensure_save_dirs()
    source_root, world_id, direct_world = savegames_payload_root(Path(source_path).expanduser())
    if path_within(source_root, SAVE_ROOT) and get_server_status()["running"]:
        raise ValueError("服务器运行中不能从当前活跃存档目录导入，请先停止服务器或复制到导入目录")
    slot_id = require_slot_id(slot_id or normalize_slot_id(name or world_id))
    path = slot_path(slot_id)
    if path.exists():
        raise ValueError("存档槽已存在")
    target_root = path / "SaveGames" / "0"
    if direct_world:
        copytree_clean(source_root, target_root / world_id)
    else:
        copytree_clean(source_root, target_root)
    config_source = source_root.parent.parent / "Config" if direct_world and source_root.parent.name == "0" else source_root / "Config"
    if config_source.exists() and path_within(config_source, SAVE_ROOT):
        copytree_clean(config_source, path / "Config")
    metadata = {
        "id": slot_id,
        "name": name or slot_id,
        "world_id": world_id,
        "created_at": iso_now(),
        "last_used_at": None,
        "source": "imported",
        "source_path": str(source_root),
        "notes": notes,
        "is_new": False,
    }
    write_json(path / "metadata.json", metadata)
    return metadata


def upload_save_slot(file_storage, name: str, notes: str = "", slot_id: str | None = None) -> dict[str, Any]:
    ensure_save_dirs()
    filename = Path(file_storage.filename or "").name
    if not filename:
        raise ValueError("请选择要上传的存档压缩包")
    if not filename.lower().endswith(".zip"):
        raise ValueError("目前只支持上传 .zip 存档包")

    upload_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{normalize_slot_id(name or filename)}"
    upload_dir = SAVE_IMPORT_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    zip_path = upload_dir / "upload.zip"
    file_storage.save(zip_path)

    extract_dir = upload_dir / "extracted"
    extract_dir.mkdir()
    try:
        safe_extract_zip(zip_path, extract_dir)
        payload_root = uploaded_save_payload_root(extract_dir)
        slot = import_slot(str(payload_root), name=name, notes=notes, slot_id=slot_id)
        slot["upload_path"] = str(upload_dir)
        return slot
    except Exception:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise


def backup_current_save(reason: str = "manual") -> dict[str, Any]:
    ensure_save_dirs()
    if not ACTIVE_SAVEGAMES_DIR.exists() or not any(ACTIVE_SAVEGAMES_DIR.iterdir()):
        raise ValueError("当前存档目录为空，无法备份")
    world_id = current_world_id() or "unknown"
    backup_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{reason}-{world_id}"
    target = SAVE_BACKUP_DIR / backup_id
    copytree_clean(ACTIVE_SAVEGAMES_DIR, target / "SaveGames" / "0")
    if CONFIG_DIR.exists():
        copytree_clean(CONFIG_DIR, target / "Config" / "LinuxServer")
    metadata = {
        "id": backup_id,
        "world_id": world_id,
        "created_at": iso_now(),
        "reason": reason,
        "size_bytes": dir_size(target),
    }
    write_json(target / "metadata.json", metadata)
    return metadata


def wait_for_service_state(active: bool, timeout: int = 80) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if get_server_status()["running"] is active:
            return True
        time.sleep(2)
    return False


def fix_save_ownership() -> None:
    if using_docker_backend():
        return
    owner = f"{PANEL_USER}:{PANEL_USER}"
    run_command([CHOWN, "-R", owner, str(SAVE_ROOT / "SaveGames")], timeout=60, sudo=True)
    run_command([CHOWN, "-R", owner, str(CONFIG_DIR)], timeout=60, sudo=True)


def switch_save_slot(slot_id: str) -> dict[str, Any]:
    slot_id = require_slot_id(slot_id)
    path = slot_path(slot_id)
    if not path.exists():
        raise ValueError("目标存档槽不存在")
    metadata = read_json(path / "metadata.json", {"id": slot_id, "name": slot_id})
    slot_savegames = slot_savegames_dir(slot_id)
    worlds = find_world_dirs(slot_savegames)
    is_new = bool(metadata.get("is_new"))
    if not worlds and not is_new:
        raise ValueError("目标存档槽无有效存档")

    steps: list[dict[str, Any]] = []

    def step(name: str, success: bool = True, message: str = "") -> None:
        steps.append({"step": name, "success": success, "message": message})

    was_running = get_server_status()["running"]
    if was_running:
        success, message = service_action("stop")
        step("stop", success, message)
        if not success or not wait_for_service_state(False):
            raise RuntimeError("停止服务器失败，已取消切换")
    else:
        step("stop", True, "server already stopped")

    backup = None
    try:
        backup = backup_current_save("before-switch")
        step("backup", True, backup["id"])
    except ValueError as exc:
        if "当前存档目录为空" not in str(exc):
            raise
        step("backup", True, "当前存档目录为空，跳过备份")

    try:
        remove_children(ACTIVE_SAVEGAMES_DIR)
        if worlds:
            copytree_clean(slot_savegames, ACTIVE_SAVEGAMES_DIR)
            world_id = metadata.get("world_id") or worlds[0].name
        else:
            world_id = metadata.get("world_id") or slot_id
        if world_id:
            write_dedicated_server_name(world_id)
        fix_save_ownership()
        step("switch", True, world_id)
    except Exception:
        remove_children(ACTIVE_SAVEGAMES_DIR)
        if backup:
            copytree_clean(SAVE_BACKUP_DIR / backup["id"] / "SaveGames" / "0", ACTIVE_SAVEGAMES_DIR)
        raise

    success, message = service_action("start")
    step("start", success, message)
    if not success:
        raise RuntimeError(message)

    metadata["last_used_at"] = iso_now()
    metadata["world_id"] = world_id
    write_json(path / "metadata.json", metadata)
    set_recorded_active_slot(slot_id, world_id)
    return {"slot": metadata, "backup": backup, "steps": steps, "running": get_server_status()["running"]}


def delete_save_slot(slot_id: str) -> dict[str, Any]:
    slot_id = require_slot_id(slot_id)
    path = slot_path(slot_id)
    if not path.exists():
        raise ValueError("存档槽不存在")
    meta = read_json(path / "metadata.json", {"id": slot_id, "name": slot_id})
    active_slot_id = get_recorded_active_slot_id()
    if not active_slot_id:
        active_slot = next((slot for slot in list_save_slots() if slot.get("is_active")), None)
        active_slot_id = active_slot.get("id", "") if active_slot else ""
    if slot_id == active_slot_id:
        raise ValueError("不能删除当前正在使用的存档")
    if not path_within(path, SAVE_SLOT_DIR):
        raise ValueError("存档槽路径异常")
    shutil.rmtree(path)
    return meta


def unquote_setting(value: str, fallback: str = "") -> str:
    if value is None:
        return fallback
    value = str(value)
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def rcon_command(command: str) -> str:
    """Send an RCON command via the Source RCON protocol."""
    if not RCON_PASSWORD:
        return "[RCON Error] RCON_PASSWORD is not configured"

    try:
        with socket.create_connection((RCON_HOST, RCON_PORT), timeout=5) as sock:
            sock.settimeout(5)

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
                if len(data) < 10:
                    raise RuntimeError("short response body")
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


def get_server_status() -> dict[str, Any]:
    if using_docker_backend():
        try:
            container = get_docker_container()
            container.reload()
            state = container.attrs.get("State", {})
            running = container.status == "running"
            return {
                "running": running,
                "pid": str(state.get("Pid") or ""),
                "start_time": state.get("StartedAt", "") if running else "",
                "service_name": PALWORLD_CONTAINER_NAME,
                "backend": "docker",
            }
        except Exception as exc:
            return {
                "running": False,
                "pid": "",
                "start_time": "",
                "service_name": PALWORLD_CONTAINER_NAME,
                "backend": "docker",
                "error": str(exc),
            }

    out, _, _ = systemctl("is-active", PALWORLD_SERVICE, timeout=10)
    running = out.strip() == "active"
    pid = ""
    start_time = ""

    if running:
        pid, _, _ = systemctl("show", PALWORLD_SERVICE, "--property=MainPID", "--value", timeout=10)
        start_time, _, _ = systemctl(
            "show",
            PALWORLD_SERVICE,
            "--property=ActiveEnterTimestamp",
            "--value",
            timeout=10,
        )

    return {
        "running": running,
        "pid": pid.strip(),
        "start_time": start_time.strip(),
        "service_name": PALWORLD_SERVICE,
        "backend": "systemd",
    }


def parse_players(rcon_response: str) -> list[dict[str, str]]:
    players: list[dict[str, str]] = []
    if not rcon_response or rcon_response.startswith("[RCON Error]"):
        return players

    for line in rcon_response.strip().splitlines()[1:]:
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        players.append(
            {
                "name": parts[0] if len(parts) > 0 else "",
                "player_uid": parts[1] if len(parts) > 1 else "",
                "steam_id": parts[2] if len(parts) > 2 else "",
            }
        )
    return players


def get_game_version() -> str:
    lines = docker_container_logs(120) if using_docker_backend() else journalctl("-u", PALWORLD_SERVICE, "-n", "80", "--no-pager", timeout=10)[0].splitlines()
    for line in reversed(lines):
        match = re.search(r"Game version is (v?[\d.]+)", line)
        if match:
            return match.group(1)
    return ""


def get_server_info() -> dict[str, Any]:
    settings = parse_palworld_settings()
    return {
        "server_name": unquote_setting(settings.get("ServerName", "")),
        "server_description": unquote_setting(settings.get("ServerDescription", "")),
        "port": settings.get("PublicPort", "8211"),
        "rcon_port": settings.get("RCONPort", str(RCON_PORT)),
        "game_version": get_game_version(),
        "online_players": parse_players(rcon_command("ShowPlayers")),
        "max_players": settings.get("ServerPlayerMaxNum", "32"),
        "exp_rate": settings.get("ExpRate", "1.0"),
    }


def read_cpu_times() -> tuple[int, int] | None:
    try:
        first = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()
        values = [int(item) for item in first[1:]]
    except Exception:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return idle, total


def get_cpu_percent() -> float | None:
    first = read_cpu_times()
    if first is None:
        return None
    time.sleep(0.08)
    second = read_cpu_times()
    if second is None:
        return None
    idle_delta = second[0] - first[0]
    total_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return round(max(0, min(100, (1 - idle_delta / total_delta) * 100)), 1)


def get_memory_info() -> dict[str, Any]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    except Exception:
        return {"total": 0, "used": 0, "percent": None}
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(0, total - available)
    percent = round((used / total) * 100, 1) if total else None
    return {"total": total, "used": used, "percent": percent}


def get_system_info() -> dict[str, Any]:
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    disk = shutil.disk_usage(PALWORLD_DIR if PALWORLD_DIR.exists() else "/")
    uptime_seconds = 0.0
    try:
        uptime_seconds = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    except Exception:
        pass
    return {
        "cpu_percent": get_cpu_percent(),
        "load": [round(item, 2) for item in load],
        "memory": get_memory_info(),
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": round((disk.used / disk.total) * 100, 1) if disk.total else None,
        },
        "uptime_seconds": int(uptime_seconds),
    }


def get_server_log(lines: int = 80) -> list[str]:
    if using_docker_backend():
        return docker_container_logs(lines)

    safe_lines = str(max(1, min(int(lines), 300)))
    out, err, code = journalctl(
        "-u",
        PALWORLD_SERVICE,
        "-n",
        safe_lines,
        "--no-pager",
        "--output=cat",
        timeout=15,
    )
    if code != 0:
        return [err or "Unable to read logs"]
    return out.splitlines() or ["No log entries available"]


def get_server_log_stream():
    sent = set()
    while True:
        for line in get_server_log(30):
            token = hash(line)
            if token not in sent:
                sent.add(token)
                yield f"data: {line}\n\n"
        yield "data: \n\n"
        time.sleep(3)


def service_action(action: str) -> tuple[bool, str]:
    if action not in {"start", "stop", "restart"}:
        return False, "Unsupported action"

    if using_docker_backend():
        try:
            container = get_docker_container()
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=60)
            elif action == "restart":
                container.restart(timeout=90)
            time.sleep(3 if action == "restart" else 2)
            running = get_server_status()["running"]
            success = running if action in {"start", "restart"} else not running
            if success:
                messages = {"start": "Server container started", "stop": "Server container stopped", "restart": "Server container restarted"}
                return True, messages[action]
            return False, f"Docker container {action} did not reach expected state"
        except Exception as exc:
            return False, str(exc)

    _, err, code = systemctl(action, PALWORLD_SERVICE, timeout=60)
    time.sleep(2 if action != "restart" else 3)
    running = get_server_status()["running"]
    success = running if action in {"start", "restart"} else not running
    if success:
        messages = {"start": "Server started", "stop": "Server stopped", "restart": "Server restarted"}
        return True, messages[action]
    return False, err or f"systemctl {action} exited with {code}"


@app.route("/")
def index():
    return render_template("index.html", app_version=APP_VERSION)


@app.after_request
def add_cache_headers(response):
    if request.path == "/" or request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@app.route("/api/status")
def api_status():
    status = get_server_status()
    offline_info = {
        "server_name": "N/A",
        "server_description": "",
        "port": "N/A",
        "rcon_port": "N/A",
        "game_version": "N/A",
        "online_players": [],
        "max_players": "N/A",
        "exp_rate": "N/A",
    }
    return jsonify({"status": status, "info": get_server_info() if status["running"] else offline_info})


@app.route("/api/system")
def api_system():
    return jsonify({"success": True, "system": get_system_info()})


@app.route("/api/audit")
def api_audit():
    try:
        limit = int(request.args.get("limit", "80"))
    except ValueError:
        limit = 80
    return jsonify({"success": True, "records": read_audit_events(limit)})


@app.route("/api/update/status")
def api_update_status():
    return jsonify({"success": True, "status": read_update_status()})


@app.route("/api/update/check", methods=["POST"])
def api_update_check():
    success, message = run_update_check_now()
    audit_event("update.check", success, message=message)
    return jsonify({"success": success, "message": message, "status": read_update_status()}), (200 if success else 500)


@app.route("/api/update/apply", methods=["POST"])
def api_update_apply():
    success, message = start_update_service()
    audit_event("update.apply", success, message=message)
    return jsonify({"success": success, "message": message, "status": read_update_status()}), (202 if success else 409)


@app.route("/api/install/status")
def api_install_status():
    return jsonify({"success": True, "status": read_install_status()})


@app.route("/api/install/check", methods=["POST"])
def api_install_check():
    success, message = run_install_check_now()
    audit_event("install.check", success, message=message)
    return jsonify({"success": success, "message": message, "status": read_install_status()}), (200 if success else 500)


@app.route("/api/install/palworld", methods=["POST"])
def api_install_palworld():
    success, message = start_install_service("install-palworld")
    audit_event("install.palworld", success, message=message)
    return jsonify({"success": success, "message": message, "status": read_install_status()}), (202 if success else 409)


@app.route("/api/install/repair", methods=["POST"])
def api_install_repair():
    success, message = start_install_service("repair")
    audit_event("install.repair", success, message=message)
    return jsonify({"success": success, "message": message, "status": read_install_status()}), (202 if success else 409)


@app.route("/api/start", methods=["POST"])
def api_start():
    success, message = service_action("start")
    audit_event("service.start", success, message=message)
    return jsonify({"success": success, "message": message})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    success, message = service_action("stop")
    audit_event("service.stop", success, message=message)
    return jsonify({"success": success, "message": message})


@app.route("/api/restart", methods=["POST"])
def api_restart():
    success, message = service_action("restart")
    audit_event("service.restart", success, message=message)
    return jsonify({"success": success, "message": message})


@app.route("/api/log")
def api_log():
    lines = request.args.get("lines", "80")
    try:
        line_count = int(lines)
    except ValueError:
        line_count = 80
    return jsonify({"lines": get_server_log(line_count)})


@app.route("/api/log/stream")
def api_log_stream():
    return Response(
        stream_with_context(get_server_log_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/rcon", methods=["POST"])
def api_rcon():
    data = request.get_json(silent=True) or {}
    command = str(data.get("command", "")).strip()
    if not command:
        return jsonify({"success": False, "message": "No command provided"}), 400
    response = rcon_command(command)
    success = not response.startswith("[RCON Error]")
    audit_event("rcon.command", success, command=command)
    return jsonify({"success": success, "response": response})


@app.route("/api/saves/status")
def api_saves_status():
    try:
        ensure_save_dirs()
        return jsonify(
            {
                "success": True,
                "active": get_active_save_info(),
                "service": get_server_status(),
                "slot_root": str(SAVE_SLOT_ROOT),
                "import_hint": str(SAVE_IMPORT_DIR),
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/slots")
def api_saves_slots():
    try:
        return jsonify({"success": True, "slots": list_save_slots()})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/backup_current", methods=["POST"])
def api_saves_backup_current():
    if get_server_status()["running"]:
        message = "服务器运行中不能手动备份，请先停止服务器，或使用切换流程自动备份"
        audit_event("saves.backup_current", False, message=message)
        return jsonify({"success": False, "message": message}), 409
    try:
        with save_operation_lock():
            backup = backup_current_save("manual")
        audit_event("saves.backup_current", True, backup_id=backup["id"])
        return jsonify({"success": True, "backup": backup, "message": "当前存档已备份"})
    except SaveOperationBusy as exc:
        audit_event("saves.backup_current", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except Exception as exc:
        audit_event("saves.backup_current", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/create_slot", methods=["POST"])
def api_saves_create_slot():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()
    slot_id = str(data.get("slot_id", "")).strip() or None
    if not name:
        return jsonify({"success": False, "message": "请输入存档名称"}), 400
    try:
        with save_operation_lock():
            slot = create_slot(name=name, notes=notes, slot_id=slot_id, is_new=True)
        audit_event("saves.create_slot", True, slot_id=slot["id"])
        return jsonify({"success": True, "slot": slot, "message": "新存档槽已创建"})
    except SaveOperationBusy as exc:
        audit_event("saves.create_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("saves.create_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("saves.create_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/import_slot", methods=["POST"])
def api_saves_import_slot():
    data = request.get_json(silent=True) or {}
    source_path = str(data.get("source_path", "")).strip()
    name = str(data.get("name", "")).strip()
    notes = str(data.get("notes", "")).strip()
    slot_id = str(data.get("slot_id", "")).strip() or None
    if not source_path or not name:
        return jsonify({"success": False, "message": "请输入导入路径和存档名称"}), 400
    try:
        with save_operation_lock():
            slot = import_slot(source_path=source_path, name=name, notes=notes, slot_id=slot_id)
        audit_event("saves.import_slot", True, slot_id=slot["id"], source_path=source_path)
        return jsonify({"success": True, "slot": slot, "message": "存档已导入"})
    except SaveOperationBusy as exc:
        audit_event("saves.import_slot", False, slot_id=slot_id, source_path=source_path, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("saves.import_slot", False, slot_id=slot_id, source_path=source_path, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("saves.import_slot", False, slot_id=slot_id, source_path=source_path, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/upload_slot", methods=["POST"])
def api_saves_upload_slot():
    file_storage = request.files.get("file")
    name = str(request.form.get("name", "")).strip()
    notes = str(request.form.get("notes", "")).strip()
    slot_id = str(request.form.get("slot_id", "")).strip() or None
    if not file_storage or not name:
        return jsonify({"success": False, "message": "请选择 zip 文件并输入存档名称"}), 400
    try:
        with save_operation_lock():
            slot = upload_save_slot(file_storage, name=name, notes=notes, slot_id=slot_id)
        audit_event("saves.upload_slot", True, slot_id=slot["id"], filename=file_storage.filename)
        return jsonify({"success": True, "slot": slot, "message": "存档上传并导入完成"})
    except SaveOperationBusy as exc:
        audit_event("saves.upload_slot", False, slot_id=slot_id, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("saves.upload_slot", False, slot_id=slot_id, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("saves.upload_slot", False, slot_id=slot_id, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/switch", methods=["POST"])
def api_saves_switch():
    data = request.get_json(silent=True) or {}
    slot_id = str(data.get("slot_id", "")).strip()
    if not slot_id:
        return jsonify({"success": False, "message": "缺少目标存档槽"}), 400
    try:
        with save_operation_lock():
            result = switch_save_slot(slot_id)
        audit_event(
            "saves.switch",
            True,
            slot_id=slot_id,
            backup_id=(result.get("backup") or {}).get("id"),
            running=result.get("running"),
        )
        return jsonify({"success": True, "message": "存档切换完成，服务器已启动", **result})
    except SaveOperationBusy as exc:
        audit_event("saves.switch", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("saves.switch", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("saves.switch", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/saves/slots/<slot_id>", methods=["DELETE"])
def api_saves_delete_slot(slot_id: str):
    try:
        with save_operation_lock():
            slot = delete_save_slot(slot_id)
        audit_event("saves.delete_slot", True, slot_id=slot_id)
        return jsonify({"success": True, "slot": slot, "message": "存档槽已删除"})
    except SaveOperationBusy as exc:
        audit_event("saves.delete_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("saves.delete_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("saves.delete_slot", False, slot_id=slot_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/status")
def api_mods_status():
    try:
        return jsonify({"success": True, "status": get_mod_status()})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/list")
def api_mods_list():
    try:
        return jsonify({"success": True, "mods": list_mods()})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/upload", methods=["POST"])
def api_mods_upload():
    file_storage = request.files.get("file")
    name = str(request.form.get("name", "")).strip()
    notes = str(request.form.get("notes", "")).strip()
    if not file_storage:
        return jsonify({"success": False, "message": "请选择 .pak、.sig 或 .zip MOD 文件"}), 400
    try:
        with save_operation_lock():
            mod = upload_mod(file_storage, name=name, notes=notes)
        audit_event("mods.upload", True, mod_id=mod["id"], filename=file_storage.filename, mod_type=mod.get("type"))
        return jsonify({"success": True, "mod": mod, "message": "MOD 上传并导入完成"})
    except SaveOperationBusy as exc:
        audit_event("mods.upload", False, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("mods.upload", False, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("mods.upload", False, filename=file_storage.filename, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/enable", methods=["POST"])
def api_mods_enable():
    data = request.get_json(silent=True) or {}
    mod_id = str(data.get("mod_id", "")).strip()
    allow_official = bool(data.get("allow_official"))
    if not mod_id:
        return jsonify({"success": False, "message": "缺少 mod_id"}), 400
    try:
        with save_operation_lock():
            mod = set_mod_enabled(mod_id, True, allow_official=allow_official)
        audit_event("mods.enable", True, mod_id=mod_id, mod_type=mod.get("type"))
        return jsonify({"success": True, "mod": mod, "message": "MOD 已启用，重启服务器后生效"})
    except SaveOperationBusy as exc:
        audit_event("mods.enable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("mods.enable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("mods.enable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/disable", methods=["POST"])
def api_mods_disable():
    data = request.get_json(silent=True) or {}
    mod_id = str(data.get("mod_id", "")).strip()
    if not mod_id:
        return jsonify({"success": False, "message": "缺少 mod_id"}), 400
    try:
        with save_operation_lock():
            mod = set_mod_enabled(mod_id, False)
        audit_event("mods.disable", True, mod_id=mod_id, mod_type=mod.get("type"))
        return jsonify({"success": True, "mod": mod, "message": "MOD 已禁用，重启服务器后生效"})
    except SaveOperationBusy as exc:
        audit_event("mods.disable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("mods.disable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("mods.disable", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/<mod_id>", methods=["DELETE"])
def api_mods_delete(mod_id: str):
    try:
        with save_operation_lock():
            mod = delete_mod(mod_id)
        audit_event("mods.delete", True, mod_id=mod_id)
        return jsonify({"success": True, "mod": mod, "message": "MOD 已移入废纸篓，重启服务器后生效"})
    except SaveOperationBusy as exc:
        audit_event("mods.delete", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except ValueError as exc:
        audit_event("mods.delete", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("mods.delete", False, mod_id=mod_id, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/empty_trash", methods=["POST"])
def api_mods_empty_trash():
    try:
        with save_operation_lock():
            count = empty_mod_trash()
        audit_event("mods.empty_trash", True, count=count)
        return jsonify({"success": True, "count": count, "message": f"已清理 {count} 个废纸篓项目"})
    except SaveOperationBusy as exc:
        audit_event("mods.empty_trash", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except Exception as exc:
        audit_event("mods.empty_trash", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/mods/apply_restart", methods=["POST"])
def api_mods_apply_restart():
    try:
        with save_operation_lock():
            result = restart_for_mods()
        audit_event(
            "mods.apply_restart",
            True,
            backup_id=(result.get("backup") or {}).get("id"),
            running=result.get("running"),
        )
        return jsonify({"success": True, "message": "服务器已重启，MOD 变更已应用", **result})
    except SaveOperationBusy as exc:
        audit_event("mods.apply_restart", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 409
    except Exception as exc:
        audit_event("mods.apply_restart", False, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify({"settings": parse_palworld_settings()})


@app.route("/api/config", methods=["POST"])
def api_update_config():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    changed_keys = get_changed_config_keys(data)
    try:
        updated = update_palworld_settings(data)
        audit_event("config.save", True, changed_keys=changed_keys)
        return jsonify({"success": True, "settings": updated})
    except ValueError as exc:
        audit_event("config.save", False, changed_keys=changed_keys, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("config.save", False, changed_keys=changed_keys, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/config/apply_restart", methods=["POST"])
def api_apply_config_restart():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    changed_keys = get_changed_config_keys(data)
    try:
        updated = update_palworld_settings(data)
        success, message = service_action("restart")
        audit_event("config.save_restart", success, changed_keys=changed_keys, message=message)
        return jsonify({"success": success, "settings": updated, "message": message})
    except ValueError as exc:
        audit_event("config.save_restart", False, changed_keys=changed_keys, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        audit_event("config.save_restart", False, changed_keys=changed_keys, message=str(exc))
        return jsonify({"success": False, "message": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PANEL_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
