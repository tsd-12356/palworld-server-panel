from __future__ import annotations

import socket
import struct
import threading
import unittest

from rcon import rcon_command


def read_packet(connection: socket.socket) -> tuple[int, int, str]:
    header = connection.recv(4)
    if len(header) != 4:
        raise RuntimeError("missing packet header")
    size = struct.unpack("<i", header)[0]
    payload = bytearray()
    while len(payload) < size:
        chunk = connection.recv(size - len(payload))
        if not chunk:
            raise RuntimeError("missing packet payload")
        payload.extend(chunk)
    packet_id, packet_type = struct.unpack("<ii", payload[:8])
    return packet_id, packet_type, bytes(payload[8:-2]).decode("utf-8")


def send_packet(connection: socket.socket, packet_id: int, packet_type: int, body: str = "") -> None:
    payload = struct.pack("<ii", packet_id, packet_type) + body.encode("utf-8") + b"\x00\x00"
    connection.sendall(struct.pack("<i", len(payload)) + payload)


class RconServer:
    def __init__(self, handler):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._run, args=(handler,), daemon=True)
        self.thread.start()

    def _run(self, handler):
        try:
            connection, _ = self.listener.accept()
            with connection:
                handler(connection)
        finally:
            self.listener.close()

    def join(self):
        self.thread.join(timeout=2)
        self.assert_finished()

    def assert_finished(self):
        if self.thread.is_alive():
            raise AssertionError("fake RCON server did not finish")


class RconCommandTests(unittest.TestCase):
    def test_collects_multiple_packets_until_idle(self):
        def handler(connection):
            self.assertEqual(read_packet(connection), (1, 3, "secret"))
            send_packet(connection, 1, 2)
            self.assertEqual(read_packet(connection), (2, 2, "ShowPlayers"))
            send_packet(connection, 2, 0, "Name,Player UID,Steam ID\n")
            send_packet(connection, 2, 0, "Player One,uid-1,steam-1")

        server = RconServer(handler)
        response = rcon_command("127.0.0.1", server.port, "secret", "ShowPlayers", timeout=2)
        server.join()
        self.assertEqual(response, "Name,Player UID,Steam ID\nPlayer One,uid-1,steam-1")

    def test_reports_authentication_failure(self):
        def handler(connection):
            self.assertEqual(read_packet(connection), (1, 3, "wrong"))
            send_packet(connection, -1, 2)

        server = RconServer(handler)
        response = rcon_command("127.0.0.1", server.port, "wrong", "Info", timeout=2)
        server.join()
        self.assertEqual(response, "[RCON Error] Auth failed")

    def test_rejects_invalid_packet_size(self):
        def handler(connection):
            self.assertEqual(read_packet(connection), (1, 3, "secret"))
            connection.sendall(struct.pack("<i", 9))

        server = RconServer(handler)
        response = rcon_command("127.0.0.1", server.port, "secret", "Info", timeout=2)
        server.join()
        self.assertEqual(response, "[RCON Error] invalid response packet size")


if __name__ == "__main__":
    unittest.main()
