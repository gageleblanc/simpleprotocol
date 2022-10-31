import shutil
from simpleprotocol.v2.server import SimpleProtocolServer
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from pathlib import Path
import os


class TestServer:
    def __init__(self):
        self.server = SimpleProtocolServer("0.0.0.0", 8080, debug=True)
        self.server.register_route("/files", self.files)
        self.server.register_route("/file_count", self.file_count)
        self.server.register_route("/upload", self.upload_file)
        self.server.before_request(self.authenticate)
        self.server.after_request(self.log_request)
        
    def authenticate(self, request: ServerRequest) -> ServerRequest:
        if "Authorization" not in request.parameters:
            return ServerResponse(1, "Unauthorized", "No authorization header")
        if request.parameters["Authorization"] != "Bearer 1234567890":
            return ServerResponse(1, "Unauthorized", "Invalid authorization header")
        return request

    def log_request(self, request: ServerRequest, response: ServerResponse):
        print(f"Request: {request}")
        print(f"Response: {response}")
        
    def files(self, request: ServerRequest, conn) -> ServerResponse:
        current_dir = os.getcwd()
        current_dir = Path(current_dir)
        if "scope" in request.parameters:
            if current_dir.joinpath(request.parameters["scope"]).exists():
                current_dir = current_dir.joinpath(request.parameters["scope"])
            else:
                return ServerResponse(11, "Not found", "Invalid scope")
        files = os.listdir(current_dir)
        return ServerResponse(0, "OK", files, parameters={
            "Content-Type": "application/json",
            "scope": str(current_dir)
        })

    def file_count(self, request: ServerRequest, conn) -> ServerResponse:
        current_dir = os.getcwd()
        current_dir = Path(current_dir)
        if "scope" in request.parameters:
            if current_dir.joinpath(request.parameters["scope"]).exists():
                current_dir = current_dir.joinpath(request.parameters["scope"])
            else:
                return ServerResponse(11, "Not found", "Invalid scope")
        files = os.listdir(current_dir)
        return ServerResponse(0, "OK", len(files), parameters={
            "scope": str(current_dir)
        })

    def upload_file(self, request: ServerRequest, conn) -> ServerResponse:
        upload_dir = Path("/tmp/puploads")
        if not upload_dir.exists():
            upload_dir.mkdir()
        if "Files" not in request.parameters:
            return ServerResponse(1, "Bad request", "No files specified")
        # print(request)
        for fname, path in request.parameters["Files"].items():
            file_path = upload_dir.joinpath(fname)
            shutil.move(path, file_path)
        return ServerResponse(0, "OK", "Files uploaded")

    def run(self):
        self.server.start()

server = TestServer()
server.run()