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
STEAMCMD_NETWORK_MODE="${STEAMCMD_NETWORK_MODE:-auto}"
STEAMCMD_LOG_FILE="${STEAMCMD_UPDATE_LOG:-${PALWORLD_DIR}/.panel-steamcmd-update.log}"
PALWORLD_START_ON_STEAMCMD_FAILURE="${PALWORLD_START_ON_STEAMCMD_FAILURE:-true}"
PALWORLD_UPDATE_REQUEST_FILE="${PALWORLD_UPDATE_REQUEST_FILE:-${PALWORLD_DIR}/.panel-update-request}"
PALWORLD_USER="${PALWORLD_USER:-palworld}"
PALWORLD_UID="${PALWORLD_UID:-1000}"
PALWORLD_GID="${PALWORLD_GID:-1000}"

write_status() {
  local phase="$1"
  local message="$2"
  local success="${3:-true}"
  local update_success="${4:-}"
  local fallback_used="${5:-false}"
  local steamcmd_exit_code="${6:-}"
  local steamcmd_detail="${7:-}"
  local status_file="${PALWORLD_INSTALL_STATUS_FILE:-${PALWORLD_DIR}/.panel-install-status.json}"

  mkdir -p "$(dirname "${status_file}")"
  python3 - "${status_file}" "${phase}" "${message}" "${success}" "${update_success}" "${fallback_used}" "${steamcmd_exit_code}" "${steamcmd_detail}" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, phase, message, success, update_success, fallback_used, steamcmd_exit_code, steamcmd_detail = sys.argv[1:9]
payload = {
    "phase": phase,
    "message": message,
    "success": success.lower() == "true",
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
if update_success:
    payload["update_success"] = update_success.lower() == "true"
if fallback_used.lower() == "true":
    payload["fallback_used"] = True
if steamcmd_exit_code:
    payload["steamcmd_exit_code"] = int(steamcmd_exit_code)
if steamcmd_detail:
    payload["steamcmd_detail"] = steamcmd_detail
with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, ensure_ascii=False, indent=2)
PY
}

if [[ -z "${RCON_PASSWORD}" ]]; then
  echo "RCON_PASSWORD is required. Copy .env.example to .env and set a strong password." >&2
  exit 1
fi

mkdir -p "${STEAMCMD_DIR}" "${PALWORLD_DIR}"

if ! getent group "${PALWORLD_USER}" >/dev/null 2>&1; then
  groupadd --gid "${PALWORLD_GID}" "${PALWORLD_USER}"
fi

if ! id -u "${PALWORLD_USER}" >/dev/null 2>&1; then
  useradd --uid "${PALWORLD_UID}" --gid "${PALWORLD_USER}" --create-home --shell /bin/bash "${PALWORLD_USER}"
fi

chown -R "${PALWORLD_USER}:${PALWORLD_USER}" "${STEAMCMD_DIR}" "${PALWORLD_DIR}"

has_existing_installation() {
  [[ -x "${PALWORLD_DIR}/PalServer.sh" ]]
}

has_proxy_environment() {
  [[ -n "${HTTP_PROXY:-}${HTTPS_PROXY:-}${ALL_PROXY:-}${http_proxy:-}${https_proxy:-}${all_proxy:-}" ]]
}

steamcmd_network_for_attempt() {
  local attempt="$1"
  case "${STEAMCMD_NETWORK_MODE}" in
    direct)
      printf 'direct\n'
      ;;
    proxy)
      printf 'proxy\n'
      ;;
    auto)
      if has_proxy_environment && (( attempt % 2 == 0 )); then
        printf 'proxy\n'
      else
        printf 'direct\n'
      fi
      ;;
  esac
}

run_steamcmd() {
  local network_mode="$1"
  local -a env_command=(env)

  if [[ "${network_mode}" == "direct" ]]; then
    env_command=(env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy)
  fi

  runuser -u "${PALWORLD_USER}" -- "${env_command[@]}" "${STEAMCMD_DIR}/steamcmd.sh" \
    +@sSteamCmdForcePlatformType linux \
    +@sSteamCmdForcePlatformBitness 64 \
    +force_install_dir "${PALWORLD_DIR}" \
    +login anonymous \
    "${steamcmd_args[@]}" \
    +quit 2>&1 | tee -a "${STEAMCMD_LOG_FILE}"
  return "${PIPESTATUS[0]}"
}

update_mode="normal"
steamcmd_update_success=""
steamcmd_fallback_used=false
steamcmd_exit_code=""
steamcmd_detail=""
case "${STEAMCMD_NETWORK_MODE}" in
  auto|direct|proxy)
    ;;
  *)
    echo "[entrypoint] Invalid STEAMCMD_NETWORK_MODE=${STEAMCMD_NETWORK_MODE}; using auto" >&2
    STEAMCMD_NETWORK_MODE="auto"
    ;;
esac
if [[ -f "${PALWORLD_UPDATE_REQUEST_FILE}" ]]; then
  requested_mode="$(tr -d '[:space:]' < "${PALWORLD_UPDATE_REQUEST_FILE}")"
  rm -f "${PALWORLD_UPDATE_REQUEST_FILE}"
  case "${requested_mode}" in
    update|validate)
      update_mode="${requested_mode}"
      ;;
    *)
      echo "[entrypoint] Ignoring invalid update request mode: ${requested_mode:-empty}" >&2
      ;;
  esac
fi

if has_existing_installation && [[ "${update_mode}" == "normal" ]]; then
  echo "[entrypoint] Using existing Palworld installation; SteamCMD update is not requested"
  write_status "starting" "Using existing Palworld installation"
else
  if [[ ! -x "${STEAMCMD_DIR}/steamcmd.sh" ]]; then
    echo "[entrypoint] Installing SteamCMD"
    write_status "steamcmd" "Installing SteamCMD"
    curl -fsSL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" -o "${STEAMCMD_DIR}/steamcmd_linux.tar.gz"
    tar -xzf "${STEAMCMD_DIR}/steamcmd_linux.tar.gz" -C "${STEAMCMD_DIR}"
    chown -R "${PALWORLD_USER}:${PALWORLD_USER}" "${STEAMCMD_DIR}"
  fi

  if [[ "${update_mode}" == "validate" ]]; then
    steamcmd_action="Validating Palworld Dedicated Server"
    steamcmd_args=(+app_update "${PALWORLD_APP_ID}" validate)
  elif has_existing_installation; then
    steamcmd_action="Updating Palworld Dedicated Server"
    steamcmd_args=(+app_update "${PALWORLD_APP_ID}")
  else
    steamcmd_action="Installing Palworld Dedicated Server"
    steamcmd_args=(+app_update "${PALWORLD_APP_ID}")
  fi

  echo "[entrypoint] ${steamcmd_action}"
  write_status "installing" "${steamcmd_action}" "true" ""
  : > "${STEAMCMD_LOG_FILE}"
  chown "${PALWORLD_USER}:${PALWORLD_USER}" "${STEAMCMD_LOG_FILE}"
  attempt=1
  steamcmd_succeeded=false
  steamcmd_exit_code=0
  while [[ "${attempt}" -le "${STEAMCMD_RETRIES}" ]]; do
    steamcmd_network_mode="$(steamcmd_network_for_attempt "${attempt}")"
    echo "[entrypoint] SteamCMD attempt ${attempt}/${STEAMCMD_RETRIES} via ${steamcmd_network_mode}" | tee -a "${STEAMCMD_LOG_FILE}"
    if run_steamcmd "${steamcmd_network_mode}"; then
      steamcmd_succeeded=true
      break
    else
      steamcmd_exit_code=$?
    fi

    if [[ "${attempt}" -ge "${STEAMCMD_RETRIES}" ]]; then
      break
    fi

    echo "[entrypoint] SteamCMD failed on attempt ${attempt}/${STEAMCMD_RETRIES} via ${steamcmd_network_mode}; retrying in ${STEAMCMD_RETRY_DELAY}s" >&2
    write_status "retrying" "SteamCMD failed on attempt ${attempt}/${STEAMCMD_RETRIES} via ${steamcmd_network_mode}; retrying in ${STEAMCMD_RETRY_DELAY}s" "false" "false" "false" "${steamcmd_exit_code}"
    attempt=$((attempt + 1))
    sleep "${STEAMCMD_RETRY_DELAY}"
  done

  if [[ "${steamcmd_succeeded}" != "true" ]]; then
    steamcmd_detail="$(tail -n 30 "${STEAMCMD_LOG_FILE}" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g' | tail -c 2000)"
    if has_existing_installation && [[ "${PALWORLD_START_ON_STEAMCMD_FAILURE}" =~ ^([Tt]rue|1|yes|on)$ ]]; then
      echo "[entrypoint] SteamCMD ${update_mode} failed after ${attempt}/${STEAMCMD_RETRIES} attempts; starting existing Palworld installation" >&2
      steamcmd_update_success=false
      steamcmd_fallback_used=true
      write_status "fallback" "SteamCMD ${update_mode} failed after ${attempt} attempts; starting existing Palworld installation" "true" "false" "true" "${steamcmd_exit_code}" "${steamcmd_detail}"
    else
      echo "[entrypoint] SteamCMD failed after ${attempt} attempts" >&2
      write_status "failed" "SteamCMD install/update failed after ${attempt} attempts" "false" "false" "false" "${steamcmd_exit_code}"
      exit 1
    fi
  else
    steamcmd_update_success=true
    write_status "updated" "SteamCMD ${update_mode} completed" "true" "true"
  fi
fi

if ! has_existing_installation; then
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

python3 - "${SETTINGS_FILE}" <<'PY'
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
    "bShowPlayerList": "True",
    "RCONPort": os.environ.get("RCON_PORT", "25575"),
    "AdminPassword": '"' + os.environ["RCON_PASSWORD"].replace('"', '\\"') + '"',
}

if os.environ.get("PALWORLD_REST_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
    values["RESTAPIEnabled"] = "True"
    values["RESTAPIPort"] = os.environ.get("PALWORLD_REST_PORT", "8212")

for key, value in values.items():
    if f"{key}=" in text:
        text = re.sub(rf"{re.escape(key)}=([^,\)]+)", f"{key}={value}", text)
    else:
        text = text.replace("OptionSettings=(", f"OptionSettings=({key}={value},", 1)

open(path, "w", encoding="utf-8").write(text)
PY
chown "${PALWORLD_USER}:${PALWORLD_USER}" "${SETTINGS_FILE}"

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
chown -R "${PALWORLD_USER}:${PALWORLD_USER}" "${CONFIG_DIR}" "${PALWORLD_DIR}/Pal/Saved"

echo "[entrypoint] Starting Palworld"
if [[ "${steamcmd_fallback_used}" == "true" ]]; then
  write_status "starting" "Starting existing Palworld installation after SteamCMD ${update_mode} failure" "true" "false" "true" "${steamcmd_exit_code}" "${steamcmd_detail}"
elif [[ "${steamcmd_update_success}" == "true" ]]; then
  write_status "starting" "Starting Palworld after successful SteamCMD ${update_mode}" "true" "true"
else
  write_status "starting" "Starting Palworld Dedicated Server"
fi
chown -R "${PALWORLD_USER}:${PALWORLD_USER}" "${PALWORLD_DIR}/Pal" "${PALWORLD_DIR}/Engine" 2>/dev/null || true
exec runuser -u "${PALWORLD_USER}" -- bash -lc "cd '${PALWORLD_DIR}' && exec '${PALWORLD_DIR}/PalServer.sh'"
