from pathlib import Path
import time
from clilib.util.logging import Logging
import socket
import ssl
from simpleprotocol.v2.tx import ClientRequest, ClientResponse
from simpleprotocol.v2.tools import send_file, socket_message, receive_data


class PupClient:
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
        self.validate_ssl = validate_ssl
        self.ssl_enabled = ssl_enabled
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.timeout = timeout

        self.logger = Logging("PupClient").get_logger()

    def _configure_socket(self):
        if self.ssl_enabled:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            _ctx = ssl.create_default_context()
            if not self.validate_ssl:
                _ctx.check_hostname = False
                _ctx.verify_mode = ssl.CERT_NONE
            if self.ssl_cert is not None and self.ssl_key is not None:
                _ctx.load_cert_chain(self.ssl_cert, self.ssl_key)
            _socket = _ctx.wrap_socket(sock, server_hostname=self.remote_host)
        else:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return _socket

    def send_request(self, request: ClientRequest) -> ClientResponse:
        """
        Send a request.
        :param request: The request.
        :return: The response.
        """
        start_time = time.time()
        if request.path is None or request.path == "":
            request.path = "/"
        if "Host" not in request.parameters:
            request.parameters["Host"] = self.remote_host
        upload_files = []
        if "Files" in request.parameters:
            request.parameters["Content-Type"] = "files"
            upload_files = request.parameters["Files"]
            new_files = []
            for f in request.parameters["Files"]:
                file_path = Path(f)
                file_name = file_path.name
                file_size = file_path.stat().st_size
                if not file_path.exists():
                    raise FileNotFoundError(f"File {f} does not exist")
                new_files.append(f"{file_name};{file_size}")
            request.parameters["Files"] = ",".join(new_files)
        processing_time = time.time() - start_time
        connection_start = time.time()
        _socket = self._configure_socket()
        _socket.connect((self.remote_host, self.remote_port))
        connection_time = time.time() - connection_start
        data_start = time.time()
        _socket.sendall(socket_message(request.build()))
        data_time = time.time() - data_start
        file_upload_start = time.time()
        for f in upload_files:
            status = _socket.recv(1).decode()
            if status == "0":
                send_file(_socket, f)
            else:
                raise Exception("File upload failed")
        file_upload_time = time.time() - file_upload_start

        response = receive_data(_socket)
        # self.logger.info(response)
        overall_time = time.time() - start_time
        if response is not None:
            response = ClientResponse(response, preprocessing_time=processing_time, connection_time=connection_time, data_time=data_time, file_upload_time=file_upload_time, overall_time=overall_time)
        _socket.shutdown(socket.SHUT_RDWR)
        _socket.close()
        return response


# For compatibility with older versions, but going forward 
# SimpleProtocol is called PUP (Pretty Uncomplicated Protocol)
SimpleProtocolClient = PupClient