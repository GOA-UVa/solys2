"""Connection

Module that encapsulates and abstracts functions that allow the low-level communication
with the Solys2.

It exports the following classes:
    * SolysConnection : Class that allows directly sending commands and receiving messages \
from the Solys2.
"""

"""___Built-In Modules___"""
import socket
import time

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
# import here

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/03/09"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

_RECV_BUFFER_SIZE = 1024
_SECS_TIMEOUT = 10

def _send_command(s: socket.socket, command: str) -> str:
    """
    Sends the command through the given socket, and receives the response.

    Parameters
    ----------
    s : socket.socket
        Socket that will be used to send the message through, and receive
        the respons from.
    command : str
        Command that will be sent to the Solys2.

    Returns
    -------
    response : str
        Immediate response given by the Solys2.
    """
    s.sendall(bytes(command + "\n", "utf-8"))
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

def _recv(s: socket.socket) -> str:
    """
    Receives a message from the given socket.

    Parameters
    ----------
    s : socket.socket
        Socket that will be used to receive the respons from.

    Returns
    -------
    response : str
        Response given by the Solys2.
    """
    rec = str(s.recv(_RECV_BUFFER_SIZE), "utf-8")
    return rec

class SolysConnection:
    """SolysConnection
    Class that allows directly sending commands and receiving messages from the Solys2.

    Attributes
    ----------
    sock : socket.socket
        Socket that will be connected to the Solys2.
    """

    def __init__(self, ip: str, port: int):
        """
        Parameters
        ----------
        ip : str
            IP of the Solys2.
        port : int
            Connection port of the Solys2.
        """
        self.connect(ip, port)

    def connect(self, ip: str, port: int):
        """
        Create the socket and connect it to the Solys2.

        Parameters
        ----------
        ip : str
            IP of the Solys2.
        port : int
            Connection port of the Solys2.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(_SECS_TIMEOUT)
        s.connect((ip, port))
        self.sock = s

    def send_cmd(self, command: str) -> str:
        """
        Send a command to the Solys2.

        Parameters
        ----------
        command : str
            Command that will be sent to the Solys2.

        Returns
        -------
        response : str
            Immediate response given by the Solys2.
        """
        return _send_command(self.sock, command)

    def recv_msg(self) -> str:
        """
        Receives a message from the Solys2.

        Returns
        -------
        response : str
            Response given by the Solys2.
        """
        return _recv(self.sock)

    def empty_recv(self):
        """
        Receives messages from the Solys2 until there are no more messages.
        Those messages are descarted.
        """
        msg = "a"
        self.sock.setblocking(False)
        while msg != None and len(msg) > 0:
            try:
                msg = self.recv_msg()
                time.sleep(0.1)
            except:
                break
        self.sock.setblocking(True)

    def close(self) -> None:
        """
        Close the socket connection
        """
        self.sock.close()
