import socket
from threading import Thread
from typing import Union
from clilib.util.logging import Logging
from simpleprotocol.errors import DataLengthMismatchException
from simpleprotocol.tx import GenericRequestParser, GenericTxBuilder


class SimpleProtocolServer:
    _headers = [
        "LEN",
        "METHOD",
        "PATH",
        "VALUE",
        "TYPE"
    ]
    def __init__(self, host: str = "127.0.0.1", port: int = 3893, logging_level: str = None, server_name: str = "DefaultServerName"):
        self.bind_host = host
        self.bind_port = port
        self.running = False
        self.server_name = server_name
        self._methods = dict()
        self._middleware = list()
        self._methods = {}
        if logging_level is None:
            logging_level = "server"
        Logging.add_logging_level("SERVER", 19)
        Logging.add_logging_level("ACCESS", 18)
        self.logger = Logging(server_name, "SimpleProtocolServer", logging_level=logging_level).get_logger()

    def register_header(self, header: Union[str, list]):
        if type(header) == list:
            self._headers.extend(header)
        else:
            if header not in self._headers:
                self._headers.append(header)

    # Accept single registration or dictionary of methods to register
    def register_handler(self, method: str = None, handler = None):
        if callable(handler):
            self._methods[method] = handler
        elif type(handler) == dict:
            self._methods.update(**handler)
        else:
            raise TypeError("Handler supplied is not callable or dict of callables.")
        self.logger.server("Registered handlers: %s" % ", ".join(self._methods.keys()))

    # Accept single registration or dictionary of middleware to register
    def register_middleware(self, middleware):
        if callable(middleware):
            self._middleware.append(middleware)
        elif type(middleware) == dict:
            self._methods.update(**middleware)
        else:
            raise TypeError("Middleware supplied is not callable or dict of callables.")

    def run_server(self):
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.bind_host, self.bind_port))
            s.listen()
            s.settimeout(15)
            self.logger.info("%s Server Listening on %s:%d" % (self.server_name, self.bind_host, self.bind_port))
            while self.running:
                try:
                    conn, addr = s.accept()
                    Thread(target=self.accept_client, args=(conn, addr)).start()
                except socket.timeout:
                    pass
            self.logger.info("Closing server.")
            s.close()

    def accept_client(self, conn, addr):
        with conn:
            self.logger.access("Connected by %s" % ":".join(str(i) for i in addr))
            rec = conn.recv(8)
            data = rec
            while self.running:
                rec = conn.recv(8)
                data += rec
                if data.decode("utf-8").endswith("\n\n"):
                    break
                if not rec:
                    break
            try:
                req = GenericRequestParser(data.decode("utf-8"), {"addr": addr[0], "port": addr[1]})
                self.logger.debug("Request: \n%s" % str(req).encode("utf-8"))
                res = self._parse_req(req)
                conn.sendall(str(res).encode("utf-8"))
                conn.close()
            except DataLengthMismatchException as ex:
                m = GenericTxBuilder(status=400, response="Invalid data length! Length received: %s, Length expected: %s" % (ex.given_length, ex.expected_length))
                conn.sendall(str(m).encode("utf-8"))
                conn.close()

    def _parse_req(self, request: GenericRequestParser):
        if not hasattr(request, "method"):
            self.logger.warn("Request does not have a method.")
            return GenericTxBuilder(status=400, response="Request does not have a method.")
        if request.method.lower() not in self._methods.keys():
            return GenericTxBuilder(status=500, response="Invalid method: %s" % request.method)
        for m in self._middleware:
            processed = m(request)
            if processed is not None and type(processed) == GenericRequestParser:
                request = processed
            else:
                self.logger.access("%s middleware canceled request" % m.__name__)
                return GenericTxBuilder(status=500, response="%s canceled middleware request" % m.__name__)
        res = self._methods[request.method.lower()](request)
        # Handler needs to return an instance of GenericTxBuilder
        if not isinstance(res, GenericTxBuilder):
            res = GenericTxBuilder(status=400, response="Handler did not return response object.")
        self.logger.access("Status %d for request with method [%s] (Response: %s)" % (res.status, request.method, res.response))
        return res
