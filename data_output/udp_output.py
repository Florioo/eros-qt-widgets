import datetime
import json
import socket


class UDPOutput:
    ip = None
    port = None
    sock = None
    packets_logged = 0

    def __init__(self) -> None:
        pass

    def open(self, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.packets_logged = 0

    def write(self, data: dict, timestamp=None):
        if self.sock is None:
            return

        data = data.copy()

        # Try to convert all values to floats
        for key, value in data.items():
            try:
                data[key] = float(data[key])
            except Exception:
                pass

        packet = {}
        packet["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f") if timestamp is None else timestamp
        packet["data"] = data

        self.sock.sendto(json.dumps(packet).encode("utf-8"), (self.ip, self.port))
        self.packets_logged += 1

    def close(self):
        if self.sock is None:
            return

        self.sock.close()
        self.sock = None

    def is_open(self) -> bool:
        return self.sock is not None

    def get_logged_packets(self) -> int:
        return self.packets_logged
