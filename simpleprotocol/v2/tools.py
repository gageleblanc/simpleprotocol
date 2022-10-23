import socket


def socket_message(message: str):
    """
    Format message for socket
    :param message: The message to format.
    """
    msg = f"{message}\0\r\n"
    return msg.encode("utf-8")

def receive_data(conn: socket.socket):
    """
    Receive data from a socket connection.
    :param conn: The socket connection.
    """
    data = b""
    while True:
        data += conn.recv(1024)
        if not data:
            return None
        if data.endswith(b"\0\r\n") or data == b"\0\r\n":
            break
    return data.strip(b"\0\r\n")