import threading
import zmq as pyzmq

from eros_core import Eros


class ErosZMQBroker:
    def __init__(self, ip, port) -> None:
        self.ip = ip
        self.port = port
        self.eros: Eros|None = None

        self.context = pyzmq.Context()
        self.pub_socket = self.context.socket(pyzmq.PUB)
        self.pub_socket.bind(f"tcp://{self.ip}:{self.port}")

        self.sub_socket = self.context.socket(pyzmq.SUB)
        self.sub_socket.bind(f"tcp://{self.ip}:{self.port+1}")
        self.sub_socket.subscribe("")

        poller = pyzmq.Poller()
        poller.register(self.sub_socket, pyzmq.POLLIN)

        self.transmit_thread = threading.Thread(target=self.transmit_task, daemon=True)
        self.transmit_thread.start()

    def poll_socket(self, socket, timetick=100):
        poller = pyzmq.Poller()
        poller.register(socket, pyzmq.POLLIN)
        # wait up to 100msec
        try:
            while True:
                obj = dict(poller.poll(timetick))
                if socket in obj and obj[socket] == pyzmq.POLLIN:
                    yield socket.recv()
        except KeyboardInterrupt:
            raise

    def transmit_task(self):
        # transmit packets from eros to zmq
        for packet in self.poll_socket(self.sub_socket):
            if self.eros is not None:
                self.eros.transmit_packet(None, packet) #type: ignore

    def attach_eros(self, eros: Eros):
        self.eros = eros

        if eros is not None:
            eros.attach_raw_callback(self.pub_socket.send)
