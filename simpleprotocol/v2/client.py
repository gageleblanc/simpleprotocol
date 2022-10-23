from clilib.util.logging import Logging
import socket
import ssl
from simpleprotocol.v2.tx import ClientRequest, ClientResponse
from simpleprotocol.v2.tools import socket_message, receive_data


class SimpleProtocolClient:
    def __init__(self, remote_host: str, remote_port: int, ssl_enabled: bool = False, validate_ssl: bool = True, ssl_cert: str = None, ssl_key: str = None, timeout: int = 30):
        """
        :param remote_host: The remote host.
        :param remote_port: The remote port.
        :param ssl_enabled: Whether to enable SSL.
        :param ssl_cert: The path to the SSL certificate.
        :param ssl_key: The path to the SSL key.
        :param timeout: The timeout for the socket.
        """
        self.remote_host = remote_host
        self.remote_port = int(remote_port)
        self.ssl_enabled = ssl_enabled
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.timeout = timeout
        if self.ssl_enabled:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            self._ctx = ssl.create_default_context()
            if not validate_ssl:
                self._ctx.check_hostname = False
                self._ctx.verify_mode = ssl.CERT_NONE
            self._ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            self.socket = self._ctx.wrap_socket(sock, server_hostname=self.remote_host)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = Logging("SimpleProtocol", "Client").get_logger()

    def send_request(self, request: ClientRequest) -> ClientResponse:
        """
        Send a request.
        :param request: The request.
        :return: The response.
        """
        if "Host" not in request.parameters:
            request.parameters["Host"] = self.remote_host
        self.socket.connect((self.remote_host, self.remote_port))
        self.socket.sendall(socket_message(request.build()))
        response = receive_data(self.socket)
        self.logger.info(response)
        if response is not None:
            response = ClientResponse(response)
        return response