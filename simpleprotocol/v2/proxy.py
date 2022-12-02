import socket
import threading
import time
from simpleprotocol.v2.client import PupClient
from simpleprotocol.v2.tools import receive_file
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from simpleprotocol.v2.server import PupServer
from clilib.config.config_loader import YAMLConfigurationFile
from clilib.util.util import SchemaValidator
from clilib.util.logging import Logging
from pathlib import Path
import ssl


class PupProxy:
    """
    This is not finished or intended to work yet.
    
    A proxy intended to forward PUP requests to an
    upstream server based on a given Host parameter.
    If the parameter is missing, the request is denied.
    """
    def __init__(self, bind_host: str, bind_port: int, server_config: str, debug: bool = False):
        """
        :param bind_host: The bind host.
        :param bind_port: The bind port.
        :param server_config: The server config.
        :param debug: Whether to enable debug mode.
        """
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.server_config_path = server_config
        self.debug = debug
        self.server_config = YAMLConfigurationFile(self.server_config_path, schema={
            "tls": {
                "enabled": bool,
                "port": int,
            },
            "plaintext": {
                "enabled": bool,
                "port": int,
            },
            "servers": []
        }, auto_create=None)
        self.logger = Logging("PupProxy", debug=debug).get_logger()
        # Use SchemaValidator to validate the server configs here, if any fail, throw an exception.
        # self.server = PupServer(self.bind_host, self.bind_port, self.handle_request, debug=self.debug)
        
    def sni_callback(self, socket, hostname, context):
        """
        The SNI callback. This is used to determine the correct
        certificate to use for a given hostname. This should only
        load the correct certificate based on the connection hostname,
        if that certificate is available in the server configuration.
        This method will not apply a certificate which was not configured
        to the specified hostname to this request. 
        :param socket: The socket.
        :param hostname: The hostname.
        :param context: The context.
        :return: The context.
        """
        if hostname in self.server_config["servers"]:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            if "tls" in self.server_config["servers"][hostname]:
                if "cert" in self.server_config["servers"][hostname]["tls"] and "key" in self.server_config["servers"][hostname]["tls"]:
                    context.load_cert_chain(self.server_config["servers"][hostname]["tls"]["cert"])
            socket.context = context

    def forward(self, request: ServerRequest) -> ServerResponse:
        """
        Forward a request to the configured upstream, or 
        return an error if the upstream does not exist or is
        unreachable.
        :param request: The request.
        :return: The response.
        """
        # Should probably add a header for the original host here.
        # Also should support an 'add header' functionality in the
        # server config.
        if "Host" in request.parameters:
            host = request.parameters["Host"]
            if host in self.server_config["servers"]:
                server = self.server_config["servers"][host]
                if "upstream" not in server:
                    server_response = ServerResponse(500, "No upstream configured for host.")
                    return server_response
                forwarder = PupClient(server["upstream"]["host"], server["upstream"]["port"], ssl_enabled=server["upstream"]["tls"])
                try:
                    client_response = forwarder.send_request(request)
                    server_response = ServerResponse(status=client_response.status, reason=client_response.reason, body=client_response.body, parameters=client_response.parameters, json_body=client_response.json_body)
                    # return server_response
                except Exception as e:
                    self.logger.error(f"Error forwarding request: {e}")
                    server_response = ServerResponse(500, "Error forwarding request.")
                return server_response
            else:
                server_response = ServerResponse(404, "Host not found.")
        else:
            server_response = ServerResponse(400, "Missing Host parameter.")
        return server_response

    def handle_request(self, conn: socket.socket) -> ServerResponse:
        """
        Handle a request.
        :param conn: The client connection to read from.
        :return: The response.
        """
        addr = conn.getpeername()
        request = ServerRequest.from_socket(conn)
        if "Content-Type" in request.parameters and request.parameters["Content-Type"] == "files":
            if "Files" not in request.parameters:
                self.logger.error("({addr[0]}:{addr[1]}): No files specified")
                response = ServerResponse(400, "Bad Request", "No files specified")
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
                    response = ServerResponse(400, "Bad Request", f"Error receiving file: {file_name}")
                    response = server_response.build()
                    response = server_response.encode(server_response.encoding)
                    conn.send(response)
                    return
            request.parameters["Files"] = new_files
        server_response = self.forward(request)
        server_response = server_response.build()
        server_response = server_response.encode(server_response.encoding)
        conn.send(server_response)
        # Todo: Add middleware support before and after request. Should build things like header manipulation into middleware.

    def secure_server(self):
        """
        Start the server in secure mode.
        :return: None.
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        secure_server = context.wrap_socket(server, server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=True, server_hostname=self.bind_host)
        secure_server.bind((self.bind_host, self.server_config["tls"]["port"]))
        secure_server.listen(5)
        while self.running:
            conn, address = secure_server.accept()
            self.logger.info(f"Connection from {address}")
            try:
                thread = threading.Thread(target=self.handle_request, args=(conn,))
                thread.start()
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                conn.close()

    def plaintext_server(self):
        """
        Start the server in plaintext mode.
        :return: None.
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.bind_host, self.server_config["plaintext"]["port"]))
        server.listen(5)
        while self.running:
            conn, address = server.accept()
            self.logger.info(f"Connection from {address}")
            try:
                thread = threading.Thread(target=self.handle_request, args=(conn,))
                thread.start()
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                conn.close()

    def start_server(self):
        """
        Start the server.
        :return: None.
        """
        self.running = True
        secure_server_thread = None
        if self.server_config["tls"]["enabled"]:
            secure_server_thread = threading.Thread(target=self.secure_server)
            secure_server_thread.start()
        if self.server_config["plaintext"]["enabled"]:
            plaintext_server_thread = threading.Thread(target=self.plaintext_server)
            plaintext_server_thread.start()
        while self.running:
            secure_server_restarts = 0
            plaintext_server_restarts = 0
            try:
                time.sleep(1)
                if self.server_config["tls"]["enabled"]:
                    if not secure_server_thread.is_alive():
                        self.logger.error("Secure server thread died.")
                        secure_server_restarts += 1
                        if secure_server_restarts > 5:
                            self.logger.error("Secure server thread died too many times. Shutting down.")
                            self.running = False
                            break
                        else:
                            secure_server_thread = threading.Thread(target=self.secure_server)
                            secure_server_thread.start()
                if self.server_config["plaintext"]["enabled"]:
                    if not plaintext_server_thread.is_alive():
                        self.logger.error("Plaintext server thread died.")
                        plaintext_server_restarts += 1
                        if plaintext_server_restarts > 5:
                            self.logger.error("Plaintext server thread died too many times. Shutting down.")
                            self.running = False
                            break
                        else:
                            plaintext_server_thread = threading.Thread(target=self.plaintext_server)
                            plaintext_server_thread.start()
            except KeyboardInterrupt:
                self.logger.info("Shutting down.")
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Error in main server loop: {e}")
                self.running = False
                break
