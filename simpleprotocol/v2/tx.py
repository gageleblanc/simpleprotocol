import re
import json

test_request = "/test/path/foo_bar/baz\r\nContent-Type: application/json\r\nTest-Parameter: 123\r\n\r\n{\"foo\": \"bar\"}"
test_response = "0 OK\r\nContent-Type: application/json\r\nTest-Parameter: 123\r\n\r\n{\"foo\": \"bar\"}"


class ServerRequest:
    def __init__(self, request: str, encoding: str = "utf-8", json_body: bool = False):
        """
        :param request: The request.
        """
        if isinstance(request, bytes):
            request = request.decode(encoding)

        self.raw_request = request
        self.header_raw = None
        self.path = None
        self.body = None
        self.json_body = json_body
        self.parameters = {}
        self.parse()
    
    def __str__(self):
        return f"Path: {self.path}\r\nParameters: {self.parameters}\r\nBody: {self.body}\r\n"

    def parse(self):
        """
        Parse the request.
        """
        if "\r\n\r\n" in self.raw_request:
            header, body = self.raw_request.split("\r\n\r\n", 1)
        else:
            header = self.raw_request
            body = None
        self.header_raw = header
        self.body = body
        path, parameters = header.split("\r\n", 1)
        if not re.fullmatch(r"^[a-zA-Z0-9/_]+", path):
            raise ValueError("Invalid request path.")
        self.path = path
        parameters = parameters.split("\r\n")
        for parameter in parameters:
            if ":" not in parameter:
                continue
            key, value = parameter.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in self.parameters:
                continue
            self.parameters[key] = value
        if "Content-Type" in self.parameters:
            if self.parameters["Content-Type"] == "application/json":
                self.json_body = True
                self.body = json.loads(self.body)


class ServerResponse:
    def __init__(self, status: int, reason: str, body: str, parameters: dict = {}, encoding: str = "utf-8", json_body: bool = False):
        """
        :param status: The status code.
        :param reason: The reason.
        :param body: The body.
        :param parameters: Optional response parameters.
        :param encoding: The encoding.
        :param json_body: Whether the body is JSON.
        """
        self.status = status
        self.reason = reason
        self.encoding = encoding
        self.body = body
        self.json_body = json_body
        self.parameters = parameters
        if "Content-Type" in self.parameters:
            if self.parameters["Content-Type"] == "application/json":
                self.json_body = True
        if self.json_body:
            if self.body is None:
                self.body = {}
            self.body = json.dumps(body)
            self.parameters["Content-Type"] = "application/json"

    def __str__(self):
        return f"Status: {self.status} {self.reason}\r\nParameters: {self.parameters}\r\nBody: {self.body}\r\n"
    
    def build(self):
        """
        Build the response.
        """
        response = f"{self.status} {self.reason}\r\n"
        for key, value in self.parameters.items():
            response += f"{key}: {value}\r\n"
        response += "\r\n"
        if self.body:
            response += self.body
        return response # .encode(self.encoding)


class ClientResponse:
    def __init__(self, response: str, encoding: str = "utf-8"):
        """
        :param response: The response.
        """
        if isinstance(response, bytes):
            response = response.decode(encoding)

        self.raw_response = response
        self.header_raw = None
        self.status = None
        self.reason = None
        self.body = None
        self.json_body = False
        self.parameters = {}
        self.parse()
    
    def __str__(self):
        return f"Status: {self.status} {self.reason}\r\nParameters: {self.parameters}\r\nBody: {self.body}\r\n"

    def parse(self):
        """
        Parse the response.
        """
        if "\r\n\r\n" in self.raw_response:
            header, body = self.raw_response.split("\r\n\r\n", 1)
        else:
            header = self.raw_response
            body = None
        self.header_raw = header
        self.body = body
        status, parameters = header.split("\r\n", 1)
        if " " in status:
            status, reason = status.split(" ", 1)
            self.status = int(status)
            self.reason = reason
        else:
            self.status = int(status)
        
        parameters = parameters.split("\r\n")
        for parameter in parameters:
            if ":" not in parameter:
                continue
            key, value = parameter.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in self.parameters:
                continue
            self.parameters[key] = value
        if "Content-Type" in self.parameters:
            if self.parameters["Content-Type"] == "application/json":
                self.json_body = True
                self.body = json.loads(self.body)

class ClientRequest:
    def __init__(self, path: str, parameters: dict = {}, body: str = None, encoding: str = "utf-8", json_body: bool = False):
        """
        :param path: The path.
        :param parameters: Optional request parameters.
        :param body: The body.
        :param encoding: The encoding.
        :param json_body: Whether the body is JSON.
        """
        self.path = path
        self.encoding = encoding
        self.body = body
        self.json_body = json_body
        self.parameters = parameters
        if "Content-Type" in self.parameters:
            if self.parameters["Content-Type"] == "application/json":
                self.json_body = True
        if self.json_body:
            if self.body is None:
                self.body = {}
            self.body = json.dumps(body)
            self.parameters["Content-Type"] = "application/json"

    def __str__(self):
        return f"Path: {self.path}\r\nParameters: {self.parameters}\r\nBody: {self.body}\r\n"
    
    def build(self):
        """
        Build the request.
        """
        request = f"{self.path}\r\n"
        for key, value in self.parameters.items():
            request += f"{key}: {value}\r\n"
        request += "\r\n"
        if self.body:
            request += self.body
        return request # .encode(self.encoding)