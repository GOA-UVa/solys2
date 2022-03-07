import socket

_RECV_BUFFER_SIZE = 1024
_SECS_TIMEOUT = 10

sock: socket.socket = None

def _send_command(s: socket.socket, command: str) -> str:
    s.sendall(bytes(command + "\n", "utf-8"))
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

def _recv(s: socket.socket) -> str:
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

def connect(ip: str, port: int):
    global sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    sock = s

def send_command(command: str) -> str:
    return _send_command(sock, command)

def recv_msg() -> str:
    return _recv(sock)

def close_connection() -> None:
    sock.close()