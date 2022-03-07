import socket

_RECV_BUFFER_SIZE = 1024

def send_command(command: str, ip: str, port: int) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ip, port))
        s.sendall(bytes(command + "\n", "utf-8"))
        rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
        return rec