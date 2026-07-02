#!/usr/bin/env bash
set -Eeuo pipefail

STEAMCMD_DIR="${STEAMCMD_DIR:-/steamcmd}"
PALWORLD_DIR="${PALWORLD_DIR:-/palworld}"
PALWORLD_APP_ID="${PALWORLD_APP_ID:-2394010}"
PALWORLD_PORT="${PALWORLD_PORT:-8211}"
PALWORLD_QUERY_PORT="${PALWORLD_QUERY_PORT:-27015}"
RCON_PORT="${RCON_PORT:-25575}"
RCON_PASSWORD="${RCON_PASSWORD:-}"
SERVER_NAME="${SERVER_NAME:-Palworld Docker Server}"
SERVER_DESCRIPTION="${SERVER_DESCRIPTION:-Managed by Palworld Panel}"
SERVER_MAX_PLAYERS="${SERVER_MAX_PLAYERS:-32}"
STEAMCMD_RETRIES="${STEAMCMD_RETRIES:-8}"
STEAMCMD_RETRY_DELAY="${STEAMCMD_RETRY_DELAY:-30}"
PALWORLD_INSTALL_STATUS_FILE="${PALWORLD_INSTALL_STATUS_FILE:-${PALWORLD_DIR}/.panel-install-status.json}"

write_status() {
  local phase="$1"
  local message="$2"
  local success="${3:-true}"
  mkdir -p "$(dirname "${PALWORLD_INSTALL_STATUS_FILE}")"
  python3 - "$PALWORLD_INSTALL_STATUS_FILE" "$phase" "$message" "$success" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, phase, message, success = sys.argv[1:5]
payload = {
    "phase": phase,
    "message": message,
    "success": success.lower() == "true",
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
PY
}

if [[ -z "${RCON_PASSWORD}" ]]; then
  echo "RCON_PASSWORD is required. Copy .env.example to .env and set a strong password." >&2
  exit 1
fi

mkdir -p "${STEAMCMD_DIR}" "${PALWORLD_DIR}"

if [[ ! -x "${STEAMCMD_DIR}/steamcmd.sh" ]]; then
  echo "[entrypoint] Installing SteamCMD"
  write_status "steamcmd" "Installing SteamCMD"
  curl -fsSL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" -o "${STEAMCMD_DIR}/steamcmd_linux.tar.gz"
  tar -xzf "${STEAMCMD_DIR}/steamcmd_linux.tar.gz" -C "${STEAMCMD_DIR}"
fi

echo "[entrypoint] Installing/updating Palworld Dedicated Server"
write_status "installing" "Installing/updating Palworld Dedicated Server"
attempt=1
until "${STEAMCMD_DIR}/steamcmd.sh" \
    +@sSteamCmdForcePlatformType linux \
    +@sSteamCmdForcePlatformBitness 64 \
    +force_install_dir "${PALWORLD_DIR}" \
    +login anonymous \
    +app_update "${PALWORLD_APP_ID}" validate \
    +quit; do
  if [[ "${attempt}" -ge "${STEAMCMD_RETRIES}" ]]; then
    echo "[entrypoint] SteamCMD failed after ${attempt} attempts" >&2
    write_status "failed" "SteamCMD install/update failed after ${attempt} attempts" "false"
    exit 1
  fi

  echo "[entrypoint] SteamCMD failed on attempt ${attempt}/${STEAMCMD_RETRIES}; retrying in ${STEAMCMD_RETRY_DELAY}s" >&2
  write_status "retrying" "SteamCMD failed on attempt ${attempt}/${STEAMCMD_RETRIES}; retrying in ${STEAMCMD_RETRY_DELAY}s" "false"
  attempt=$((attempt + 1))
  sleep "${STEAMCMD_RETRY_DELAY}"
done

if [[ ! -x "${PALWORLD_DIR}/PalServer.sh" ]]; then
  echo "[entrypoint] PalServer.sh was not created by SteamCMD" >&2
  write_status "failed" "SteamCMD finished but PalServer.sh is missing" "false"
  exit 1
fi

CONFIG_DIR="${PALWORLD_DIR}/Pal/Saved/Config/LinuxServer"
SETTINGS_FILE="${CONFIG_DIR}/PalWorldSettings.ini"
GAME_USER_FILE="${CONFIG_DIR}/GameUserSettings.ini"
mkdir -p "${CONFIG_DIR}"

if [[ ! -f "${SETTINGS_FILE}" ]]; then
  if [[ -f "${PALWORLD_DIR}/DefaultPalWorldSettings.ini" ]]; then
    cp "${PALWORLD_DIR}/DefaultPalWorldSettings.ini" "${SETTINGS_FILE}"
  else
    cat >"${SETTINGS_FILE}" <<'EOF'
[/Script/Pal.PalGameWorldSettings]
OptionSettings=()
EOF
  fi
fi

python3 - "$SETTINGS_FILE" <<'PY'
import os
import re
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8", errors="replace").read()
if "OptionSettings=(" not in text:
    text = "[/Script/Pal.PalGameWorldSettings]\nOptionSettings=()\n"

values = {
    "ServerName": '"' + os.environ.get("SERVER_NAME", "Palworld Docker Server").replace('"', '\\"') + '"',
    "ServerDescription": '"' + os.environ.get("SERVER_DESCRIPTION", "Managed by Palworld Panel").replace('"', '\\"') + '"',
    "ServerPlayerMaxNum": os.environ.get("SERVER_MAX_PLAYERS", "32"),
    "PublicPort": os.environ.get("PALWORLD_PORT", "8211"),
    "QueryPort": os.environ.get("PALWORLD_QUERY_PORT", "27015"),
    "RCONEnabled": "True",
    "RCONPort": os.environ.get("RCON_PORT", "25575"),
    "AdminPassword": '"' + os.environ["RCON_PASSWORD"].replace('"', '\\"') + '"',
}

for key, value in values.items():
    if f"{key}=" in text:
        text = re.sub(rf"{re.escape(key)}=([^,\)]+)", f"{key}={value}", text)
    else:
        text = text.replace("OptionSettings=(", f"OptionSettings=({key}={value},", 1)

open(path, "w", encoding="utf-8").write(text)
PY

if [[ ! -f "${GAME_USER_FILE}" ]]; then
  WORLD_ID="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(16).upper())
PY
)"
  cat >"${GAME_USER_FILE}" <<EOF
[/Script/Pal.PalGameInstance]
DedicatedServerName=${WORLD_ID}
EOF
fi

echo "[entrypoint] Starting Palworld"
write_status "starting" "Starting Palworld Dedicated Server"
cd "${PALWORLD_DIR}"
exec "${PALWORLD_DIR}/PalServer.sh"
