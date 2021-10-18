import socket
from clilib.util.logging import Logging
from typing import Type
from simpleprotocol.tx import GenericTxBuilder, GenericResponseParser


class SimpleProtocolClient:
    _headers = [
        "STATUS",
        "RESPONSE"
    ]
    client_name = None
    def __init__(self, host: str = "127.0.0.1", port: int = 3893):
        if self.client_name is None:
            self.client_name = "SimpleProtocolClient"
        self.host = host
        self.port = port
        self.logger = Logging(self.client_name).get_logger()

    def _send(self, request: Type[GenericTxBuilder]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((self.host, self.port))
            except ConnectionRefusedError as e:
                self.logger.fatal("Unable to connect to SimpleProtocolServer at %s:%d, %s" % (self.host, self.port, str(e)))
                exit(1)
            self.logger.debug(str(request))
            s.sendall(str(request).encode("utf-8"))
            rec = s.recv(8)
            data = rec
            while True:
                rec = s.recv(8)
                data += rec
                if data.decode("utf-8").endswith("\n\n"):
                    break
                if not rec:
                    break
        return GenericResponseParser(data.decode("utf-8"))
