import socket

_RECV_BUFFER_SIZE = 1024
_SECS_TIMEOUT = 10

def _send_command(s: socket.socket, command: str) -> str:
    s.sendall(bytes(command + "\n", "utf-8"))
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

def _recv(s: socket.socket) -> str:
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

class SolysConnection:
    def __init__(self, ip: str, port: int):
        self.connect(ip, port)

    def connect(self, ip: str, port: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(_SECS_TIMEOUT)
        s.setblocking(False)
        s.connect((ip, port))
        self.sock = s

    def send_cmd(self, command: str) -> str:
        return _send_command(self.sock, command)

    def recv_msg(self) -> str:
        return _recv(self.sock)

    def empty_recv(self):
        msg = "a"
        while msg != None and len(msg) > 0:
            msg = self.recv_msg()

    def close(self) -> None:
        self.sock.close()