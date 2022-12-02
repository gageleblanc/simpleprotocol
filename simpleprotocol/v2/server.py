from pathlib import Path
import time
import traceback
from clilib.util.logging import Logging
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from simpleprotocol.v2.tools import receive_file, socket_message, receive_data
from simpleprotocol.v2.handlers import SimpleProtocolHandler
import threading
import socket
import ssl


class PupServer:
    def __init__(self, bind_address: str, bind_port: int, secure_bind_port: int = None, timeout: int = 30, ssl_enabled: bool = False, ssl_cert: str = None, ssl_key: str = None, plaintext_disabled: bool = False, logger_name: str = None, logger_desc: str = None, debug: bool = False):
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
        self.plaintext_disabled = plaintext_disabled
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.timeout = timeout
        self.debug = debug
        self.running = True
        if logger_name is None:
            logger_name = "PupServer"
        if logger_desc is None:
            logger_desc = "Server"
        self.logger = Logging(logger_name, logger_desc, debug=debug).get_logger()
        self.secure_bind_port = secure_bind_port
        if not self.ssl_enabled and self.plaintext_disabled:
            raise ValueError("Cannot disable plaintext if SSL is disabled")
        self.plaintext_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.secure_socket = None
        if self.ssl_enabled:
            self.logger.info("SSL enabled")
            if secure_bind_port is None:
                self.secure_bind_port = self.bind_port + 1
            elif isinstance(secure_bind_port, (int, str)):
                try:
                    self.secure_bind_port = int(secure_bind_port)
                except ValueError:
                    self.logger.warning("Invalid secure port, using default")
                    self.secure_bind_port = self.bind_port + 1
            else:
                self.logger.warning("Invalid secure port, using default")
                self.secure_bind_port = self.bind_port + 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self._ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            self.secure_socket = self._ctx.wrap_socket(sock, server_side=True)
        # else:
        # if not self.plaintext_disabled:
        #     self.socket = self.plaintext_socket
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.middleware_before_request = []
        self.routes = {}
        self.middleware_after_request = []

    def route(self, path: str):
        """
        Decorator for registering routes.
        :param path: The path.
        """
        def decorator(func):
            self.register_route(path, func)
            return func
        return decorator

    def before_request(self, func):
        """
        Register a function to run before every request.
        :param func: The function.
        """
        self.middleware_before_request.append(func)

    def after_request(self, func):
        """
        Register a function to run after every request.
        :param func: The function.
        """
        self.middleware_after_request.append(func)

    def register_route(self, path: str, handler: callable):
        """
        Register a route.
        :param path: The path.
        :param handler: The handler for this route.
        """
        # if not issubclass(handler, SimpleProtocolHandler):
        #     raise TypeError("handler must be a subclass of SimpleProtocolHandler")
        path_parts = path.split("/")
        for part in path_parts:
            if '<' in part or '>' in part:
                # This is a variable
                pass
        self.routes[path] = handler

    def handle_connection(self, conn: socket.socket, addr: tuple):
        """
        Handle a connection.
        :param conn: The connection.
        :param addr: The address.
        """

        raw_message = receive_data(conn)
        if not raw_message:
            self.logger.error("({addr[0]}:{addr[1]}): No message received")
            return

        request = ServerRequest(raw_message)
        for func in self.middleware_before_request:
            try:
                mdw_result = func(request=request)
                if isinstance(mdw_result, ServerResponse):
                    self.logger.info(f"({addr[0]}:{addr[1]}): ({func.__name__}) Middleware returned response, sending response")
                    conn.send(socket_message(mdw_result.build()))
                    return
                elif mdw_result is None:
                    self.logger.warning(f"({addr[0]}:{addr[1]}): ({func.__name__}) Middleware returned None")
                    response = ServerResponse(2, "Internal Server Error", "Server cancelled request")
                    return
                elif isinstance(mdw_result, ServerRequest):
                    request = mdw_result
                else:
                    self.logger.error(f"({addr[0]}:{addr[1]}): ({func.__name__}) Invalid middleware result: {mdw_result}")
                    response = ServerResponse(2, "Internal Server Error", "Internal Server Error")
                    conn.send(socket_message(response.build()))
                    return
            except Exception as e:
                self.logger.error(f"({addr[0]}:{addr[1]}): Error running middleware ({func.__name__}): {e}")
                response = ServerResponse(2, "Internal Server Error", "Internal Server Error")
                conn.send(socket_message(response.build()))
                return

        if "Content-Type" in request.parameters and request.parameters["Content-Type"] == "files":
            if "Files" not in request.parameters:
                self.logger.error("({addr[0]}:{addr[1]}): No files specified")
                response = ServerResponse(3, "Bad Request", "No files specified")
                return

            files = request.parameters["Files"].split(",")
            new_files = {}
            for f in files:
                conn.sendall(b"0")
                file_name, file_size = f.split(";")
                file_size = int(file_size)
                try:
                    new_files[file_name] = receive_file(conn, size=file_size)
                except Exception as e:
                    self.logger.error(f"({addr[0]}:{addr[1]}): Error receiving file: {e}")
                    response = ServerResponse(3, "Bad Request", f"Error receiving file: {file_name}")
                    return
            request.parameters["Files"] = new_files

        self.logger.debug(f"Received request from {addr[0]}:{addr[1]}: {request.path}")
        if request.path in self.routes:
            handler = self.routes[request.path]
            try:
                response: ServerResponse = handler(request=request, conn=conn)
                if not isinstance(response, ServerResponse):
                    self.logger.error(f"Handler for {request.path} did not return a ServerResponse")
                    response = ServerResponse(2, "Internal Server Error", "An error occurred while handling your request.")
                    self.logger.info(f"({addr[0]}:{addr[1]}) {response.status} - {request.path}")
                    conn.send(socket_message(response.build()))
                    return
                self.logger.info(f"({addr[0]}:{addr[1]}) {response.status} - {request.path}")
                conn.send(socket_message(response.build()))
            except Exception as e:
                tb = traceback.format_exc()
                self.logger.error(f"Error handling request: {e}\r\n{tb}")
                response = ServerResponse(2, "Internal Server Error", "An error occurred while handling your request.")
                self.logger.info(f"({addr[0]}:{addr[1]}) {response.status} - {request.path}")
                conn.send(socket_message(response.build()))
        else:
            response = ServerResponse(1, "Not Found", "No handler was found for the requested path.")
            self.logger.info(f"({addr[0]}:{addr[1]}) {response.status} - {request.path}")
            conn.send(socket_message(response.build()))
        if "Files" in request.parameters:
            for f, path in request.parameters["Files"].items():
                path = Path(path)
                if path.exists():
                    self.logger.debug("Cleaning up file: %s" % path)
                    path.unlink()
        for func in self.middleware_after_request:
            try:
                func(request, response)
            except Exception as e:
                self.logger.error(f"Error running after request middleware ({func.__name__}): {e}")

    def _accept(self, sck):
        """
        Accept a connection.
        """
        while self.running:
            try:
                conn, addr = sck.accept()
                self.logger.info(f"Accepted connection from {addr[0]}:{addr[1]}")
                thread = threading.Thread(target=self.handle_connection, args=(conn, addr))
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Error handling connection: {e}")
                continue

    def _run_secure(self):
        """
        Start the server using SSL.
        """
        if not self.ssl_enabled:
            self.logger.error("SSL is not enabled")
            return
        self.logger.info(f"Starting secure server on port {self.bind_address}:{self.secure_bind_port}")
        self.secure_socket.bind((self.bind_address, self.secure_bind_port))
        self.secure_socket.listen(5)
        self.secure_socket.settimeout(self.timeout)
        self._accept(self.secure_socket)

    def _run(self):
        """
        Start the server.
        """
        self.logger.info(f"Starting server on port {self.bind_address}:{self.bind_port}")
        self.plaintext_socket.bind((self.bind_address, self.bind_port))
        self.plaintext_socket.listen(5)
        self.plaintext_socket.settimeout(self.timeout)
        self._accept(self.plaintext_socket)

    def start(self):
        """
        Start the server.
        """
        secure_thread = threading.Thread(target=self._run_secure)
        plaintext_thread = threading.Thread(target=self._run)
        if self.ssl_enabled:
            secure_thread.start()
        if not self.plaintext_disabled:
            plaintext_thread.start()
        while self.running:
            try:
                time.sleep(1)
                if not self.plaintext_disabled and not plaintext_thread.is_alive():
                    self.logger.error("Plaintext server thread died, restarting...")
                    plaintext_thread = threading.Thread(target=self._run)
                    plaintext_thread.start()
                if self.ssl_enabled and not secure_thread.is_alive():
                    self.logger.error("Secure server thread died, restarting...")
                    secure_thread = threading.Thread(target=self._run_secure)
                    secure_thread.start()
            except KeyboardInterrupt:
                self.logger.info("Shutting down server...")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Uncaught Server Error: {e}")
                continue
        if self.plaintext_socket and not self.plaintext_disabled:
            self.plaintext_socket.shutdown(socket.SHUT_RDWR)
            self.plaintext_socket.close()
        if self.secure_socket and self.ssl_enabled:
            self.secure_socket.shutdown(socket.SHUT_RDWR)
            self.secure_socket.close()


# For compatibility with older versions, but going forward 
# SimpleProtocol is called PUP (Pretty Uncomplicated Protocol)
SimpleProtocolServer = PupServer
