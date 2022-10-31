import shutil
from simpleprotocol.v2.server import SimpleProtocolServer
from simpleprotocol.v2.tx import ServerRequest, ServerResponse
from pathlib import Path
import os


server = SimpleProtocolServer("0.0.0.0", 8080, debug=True)

@server.before_request
def authenticate(request: ServerRequest) -> ServerRequest:
    if "Authorization" not in request.parameters:
        return ServerResponse(1, "Unauthorized", "No authorization header")
    if request.parameters["Authorization"] != "Bearer 1234567890":
        return ServerResponse(1, "Unauthorized", "Invalid authorization header")
    return request

@server.after_request
def log_request(request: ServerRequest, response: ServerResponse):
    print(f"Request: {request}")
    print(f"Response: {response}")
    
@server.route("/files")
def files(request: ServerRequest, conn) -> ServerResponse:
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

@server.route("/file_count")
def file_count(request: ServerRequest, conn) -> ServerResponse:
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

@server.route("/upload")
def upload_file(request: ServerRequest, conn) -> ServerResponse:
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

server.start()
