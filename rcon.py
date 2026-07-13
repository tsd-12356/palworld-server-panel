"""Small Source RCON client shared by the panel and background updater."""

from __future__ import annotations

import socket
import struct
import time

AUTH_PACKET_TYPE = 3
COMMAND_PACKET_TYPE = 2
AUTH_REQUEST_ID = 1
COMMAND_REQUEST_ID = 2
SENTINEL_REQUEST_ID = 3
MAX_PACKET_SIZE = 4 * 1024 * 1024


def rcon_command(host: str, port: int, password: str, command: str, timeout: float = 10) -> str:
    """Run a Source RCON command and wait for its sentinel response.

    A distinct empty command marks the end of a response. This avoids treating a
    short idle period as completion when a server splits or delays its output.
    """
    if not password:
        return "[RCON Error] RCON_PASSWORD is not configured"

    deadline = time.monotonic() + timeout

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            def set_remaining_timeout() -> None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("response timed out")
                sock.settimeout(remaining)

            def recv_exact(length: int) -> bytes:
                data = bytearray()
                while len(data) < length:
                    set_remaining_timeout()
                    chunk = sock.recv(length - len(data))
                    if not chunk:
                        raise RuntimeError("connection closed while reading response")
                    data.extend(chunk)
                return bytes(data)

            def send_packet(packet_id: int, packet_type: int, body_text: str) -> None:
                body = body_text.encode("utf-8") + b"\x00\x00"
                payload = struct.pack("<ii", packet_id, packet_type) + body
                sock.sendall(struct.pack("<i", len(payload)) + payload)

            def recv_packet() -> tuple[int, int, str]:
                size = struct.unpack("<i", recv_exact(4))[0]
                if size < 10 or size > MAX_PACKET_SIZE:
                    raise RuntimeError("invalid response packet size")
                data = recv_exact(size)
                if data[-2:] != b"\x00\x00":
                    raise RuntimeError("invalid response packet terminator")
                packet_id, packet_type = struct.unpack("<ii", data[:8])
                return packet_id, packet_type, data[8:-2].decode("utf-8", errors="replace")

            send_packet(AUTH_REQUEST_ID, AUTH_PACKET_TYPE, password)
            packet_id, _, _ = recv_packet()
            if packet_id == -1:
                return "[RCON Error] Auth failed"
            if packet_id != AUTH_REQUEST_ID:
                raise RuntimeError("unexpected authentication response")

            send_packet(COMMAND_REQUEST_ID, COMMAND_PACKET_TYPE, command)
            send_packet(SENTINEL_REQUEST_ID, COMMAND_PACKET_TYPE, "")

            responses: list[str] = []
            while True:
                packet_id, _, body = recv_packet()
                if packet_id == SENTINEL_REQUEST_ID:
                    return "\n".join(responses)
                if packet_id == COMMAND_REQUEST_ID and body.strip():
                    responses.append(body.strip())
    except Exception as exc:
        return f"[RCON Error] {exc}"
