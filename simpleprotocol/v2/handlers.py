from simpleprotocol.v2.tx import ServerRequest, ServerResponse
import socket


class SimpleProtocolHandler:
    def __init__(self, request: ServerRequest, conn: socket.socket):
        """
        :param request: The request.
        :param conn: The connection For most simple requests, you shouldn't need to communicate with the client, returning a ServerResponse would be sufficient.
        """
        self.request = request
        self.conn = conn

    def handle(self) -> ServerResponse:
        """
        Handle the request.
        """
        raise NotImplementedError


class EchoHandler(SimpleProtocolHandler):
    def handle(self) -> ServerResponse:
        return ServerResponse(0, "Echo", self.request.body, parameters=self.request.parameters)
