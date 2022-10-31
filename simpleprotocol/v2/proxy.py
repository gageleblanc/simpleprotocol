from simpleprotocol.v2.client import PupClient
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from simpleprotocol.v2.server import PupServer
from clilib.config.config_loader import JSONConfigurationFile
from clilib.util.logging import Logging
from pathlib import Path
import ssl


class PupProxy:
    """
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
        self.server_config = JSONConfigurationFile(self.server_config_path, schema={
            "tls": {
                "enabled": bool
            },
            "servers": {}
        })
        self.logger = Logging("PupProxy", debug=debug).get_logger()
        # self.server = PupServer(self.bind_host, self.bind_port, self.handle_request, debug=self.debug)
        
    def sni_callback(self, socket, hostname, context):
        """
        The SNI callback.
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
        Forward a request.
        :param request: The request.
        :return: The response.
        """
        if "Host" in request.parameters:
            host = request.parameters["Host"]
            if host in self.server_config["servers"]:
                server = self.server_config["servers"][host]
                if "upstream" not in server:
                    return ServerResponse(500, "No upstream configured for host.")
                forwarder = PupClient(server["upstream"]["host"], server["upstream"]["port"], ssl_enabled=server["upstream"]["tls"])
                return forwarder.send_request(request)
            else:
                return ServerResponse(404, "Host not found.")
        else:
            return ServerResponse(400, "Missing Host parameter.")
