import base64
import socket
import tempfile
from datetime import timedelta


TERMINATOR = b"\0\r\n"

def strfdelta(tdelta, fmt):
    if isinstance(tdelta, (float, int)):
        tdelta = timedelta(seconds=tdelta)
    d = {"days": tdelta.days, "microseconds": tdelta.microseconds, "milliseconds": tdelta.microseconds // 1000}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    # d["milliseconds"] = math.fmod(d["seconds"])[0] * 1000
    # d["microseconds"] = math.fmod(d["seconds"])[1] * 1000000
    return fmt.format(**d)

def print_out(request: str):
    """
    Format request with arrow prefix
    """
    lines = [">> %s" % line for line in request.splitlines()]
    return "\n".join(lines)

def print_in(response: str):
    """
    Format response with arrow prefix
    """
    lines = ["<< %s" % line for line in response.splitlines()]
    return "\n".join(lines)

def route_decorator(path: str):
    """
    Decorator for registering a route. Should add kwargs to the function
    :param path: The path.
    """
    def decorator(func):
        func.path = path
        return func
    return decorator

def socket_message(message: str):
    """
    Format message for socket
    :param message: The message to format.
    """
    return v2_message(message)
    msg = f"{message}{TERMINATOR.decode()}"
    return msg.encode("utf-8")

def v2_message(message: str):
    """
    Version 2 of the message format.
    :param message: The message to send.
    """
    # Encode the message as bytes, then base64.
    message = message.encode("utf-8")
    message = base64.b64encode(message)
    # Create header containing the length of the message.
    header = f"{len(message)}".encode("utf-8")
    header = base64.b64encode(header)
    # Create the payload.
    payload = header + b"." + message
    return payload

def v2_receive_data(conn: socket.socket):
    """
    Receive data from a socket connection.
    :param conn: The socket connection.
    """
    header = b""
    data = b""
    while True:
        _b = conn.recv(1)
        if _b == b".": # End of header
            break
        header += _b
    header_raw = base64.b64decode(header)
    header_decoded = header_raw.decode("utf-8")
    message_size = int(header_decoded)
    while True:
        data += conn.recv(1024)
        if not data:
            return None
        if len(data) >= message_size:
            if len(data) > message_size:
                print(f"[{conn.getsockname()}] - Received more data than expected.")
            break
    data = base64.b64decode(data)
    data = data.strip(TERMINATOR)
    return data.decode("utf-8")

def receive_data(conn: socket.socket):
    """
    Receive data from a socket connection.
    :param conn: The socket connection.
    """
    return v2_receive_data(conn)
    data = b""
    while True:
        data += conn.recv(1024)
        if not data:
            return None
        if data.endswith(TERMINATOR) or data == TERMINATOR:
            break
    return data.strip(TERMINATOR)

def receive_file(conn: socket.socket, size: int, prefix: bytes = None, file_path: str = None):
    """
    Receive a file from a socket connection.
    :param conn: The socket connection.
    :param file_path: The file path to save the file to. If None, the file will be saved to a temporary file.
    """
    if file_path is None:
        file_path = tempfile.mktemp()
    new_prefix = None
    received_bytes = 0
    with open(file_path, "wb") as f:
        while received_bytes < size:
            data = conn.recv(512)
            if not data:
                return None
    
            received_bytes += len(data)
            f.write(data)
#     print(f"Received {received_bytes}/{size} bytes")
    return file_path

def send_file(conn: socket.socket, file_path: str):
    """
    Send a file to a socket connection.
    :param conn: The socket connection.
    :param file_path: The file path to send.
    """
    fullsize = 0
    with open(file_path, "rb") as f:
        while True:
            data = f.read(1024)
            fullsize += len(data)
            if not data:
                break
            conn.sendall(data)


class DelimitedBuffer:
    def __init__(self, conn: socket.socket, delimiter: bytes = b"\r\n", end: bytes = TERMINATOR):
        """
        :param conn: The socket connection.
        :param delimiter: The delimiter.
        """
        self.conn = conn
        self.end = end
        self.delimiter = delimiter
        self.buffer = b""
        self.finished = False
    
    def read(self, size: int = 1024):
        """
        Read data from the socket connection.
        :param size: The size to read.
        """
        while True:
            if self.buffer.endswith(self.delimiter):
                return self.buffer.strip(self.delimiter)
            if self.buffer.endswith(self.end):
                self.finished = True
                return self.buffer.strip(self.end)
            if self.delimiter in self.buffer:
                data, self.buffer = self.buffer.split(self.delimiter, 1)
                return data
            data = self.conn.recv(size)
            if not data:
                self.finished = True
                return None
            self.buffer += data
