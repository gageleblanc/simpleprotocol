from clilib.util.logging import Logging
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from simpleprotocol.v2.tools import socket_message, receive_data
from simpleprotocol.v2.handlers import SimpleProtocolHandler
import socket
import ssl




class SimpleProtocolServer:
    def __init__(self, bind_address: str, bind_port: int, timeout: int = 30, ssl_enabled: bool = False, ssl_cert: str = None, ssl_key: str = None):
        """
        :param bind_address: The address to bind to.
        :param bind_port: The port to bind to.
        :param timeout: The timeout for the socket.
        :param ssl_enabled: Whether to enable SSL.
        :param ssl_cert: The path to the SSL certificate.
        :param ssl_key: The path to the SSL key.
        """
        self.bind_address = bind_address
        self.bind_port = int(bind_port)
        self.ssl_enabled = ssl_enabled
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.timeout = timeout
        if self.ssl_enabled:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self._ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            self.socket = self._ctx.wrap_socket(sock, server_side=True)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.routes = {}
        self.logger = Logging("SimpleProtocol", "Server").get_logger()

    def register_route(self, path: str, handler: SimpleProtocolHandler):
        """
        Register a route.
        :param path: The path.
        :param callback: The callback.
        """
        if not issubclass(handler, SimpleProtocolHandler):
            raise TypeError("handler must be a subclass of SimpleProtocolHandler")
        self.routes[path] = handler

    def handle_connection(self, conn: socket.socket, addr: tuple):
        """
        Handle a connection.
        :param conn: The connection.
        :param addr: The address.
        """
        self.logger.info(f"Connection from {addr[0]}:{addr[1]}")
        raw_message = receive_data(conn)
        self.logger.info(raw_message)
        if not raw_message:
            return
        request = ServerRequest(raw_message)
        self.logger.debug(f"Received request from {addr[0]}:{addr[1]}: {request.path}")
        if request.path in self.routes:
            handler = self.routes[request.path](request, conn)
            response = handler.handle()
            conn.send(socket_message(response.build()))

    def start(self):
        """
        Start the server.
        """
        self.logger.info(f"Starting server on {self.bind_address}:{self.bind_port}")
        self.socket.bind((self.bind_address, self.bind_port))
        self.socket.listen(5)
        self.socket.settimeout(self.timeout)
        while True:
            try:
                conn, addr = self.socket.accept()
                self.handle_connection(conn, addr)
            except socket.timeout:
                pass
    # Todo: add request handling, middleware.
    # Todo: Add recieve_file method