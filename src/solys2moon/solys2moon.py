from enum import Enum
from typing import Union, Tuple, List
import time
import re
import math

from . import connection

class TrackerMode(Enum):
    SUN = 'SUN'
    REMOTE = 'REMOTE'
    CLOCK = 'CLOCK'

ERROR_CODES = {
    '1': 'framing error.',
    '2': 'reserved for future use.',
    '3': 'unrecognized command.',
    '4': 'message too long.',
    '5': 'unimplemented instruction or non decodable parameters.',
    '6': 'motion queue is full, movement command rejected.',
    '7': 'travel bounds exceeded.',
    '8': 'maximum velocity exceeded.',
    '9': 'maximum acceleration exceeded.',
    'A': 'instrument is operating autonomously, command rejected.',
    'B': 'invalid adjustment size.',
    'C': 'invalid total adjustment.',
    'D': 'duration out of range.',
    'E': 'reserved for future use.',
    'F': 'illegal extent specified.',
    'G': 'attempt to change password protected data.',
    'Y': 'hardware failure detected.',
    'Z': 'illegal internal firmware state.',
    'Q': 'Command is protected  password.',
    'R': 'Unknown command, or unidentified error.',
    'P': 'Wrong password.'
}

class OutCode(Enum):
    NONE = -1
    ERROR = 0
    ANSWERED = 1

def process_response(s: str, cmd: str) -> Tuple[List[float], OutCode, Union[str, None]]:
    """
    Process the response given by the Solys2

    Parameters
    ----------
    s : str
        Response given by the Solys2
    cmd : str
        Command sent to the Solys2

    Returns
    -------
    numbers : list of float
        List of the numbers outputed by the Solys2.
    out_code : OutCode
        OutCode explaining what kind of response was the response given by the Solys2
    err_code : str or None
        Character (len 1 str) containing the error code, in case it's an error, in which case
        the out_code would be equal to ERROR. Otherwise this will be None.
    """
    rstrip = s.strip()
    out_code = OutCode.ANSWERED
    numbers = []
    err_code = None
    if rstrip.startswith(cmd[:2]):
        # If the response starts with the command, it is answering that command
        temp = re.sub(cmd, '', rstrip)
        unwateted = re.sub('(\d|\.|\ )', '', temp)
        only_nums = re.sub(unwateted, '', temp)
        if len(only_nums) > 0:
            numbers = list(map(float, only_nums.split()))
        else:
            numbers = [1]
    elif rstrip.startswith("NO"):
        # If the response starts with "NO", there was an error
        out_code = OutCode.ERROR
        err_code = rstrip.split()[1]
        numbers = [-1]
    else:
        # Otherwise, the answer is not ready yet
        out_code = OutCode.NONE
        numbers = [-1]
    return numbers, out_code, err_code

class Solys2:
    def __init__(self, ip: str, port: int = 15000, password: str = "solys"):
        self.ip = ip
        self.port = port
        self.sun_sensor = False
        self.password = password
        
        self.connect()
        self.send_password()
        self.lift_protection()
        
        self.adjust()
        self.version()
    
    def connect(self):
        self.connection = connection.SolysConnection(self.ip, self.port)

    def send_command(self, cmd: str) -> Tuple[str, List[float], OutCode, Union[str, None]]:
        self.connection.empty_recv()
        str_out = self.connection.send_cmd(cmd, self.ip, self.port)
        nums, out, err = process_response(str_out, cmd)
        while out == OutCode.NONE:
            time.sleep(0.1)
            resp = self.connection.recv_msg()
            nums, out, err = process_response(resp, cmd)
        return str_out, nums, out, err
    
    def send_password(self):
        cmd = 'PW ' +  self.password
        s, nums, out, err = self.send_command(cmd)
        self.lift_protection()
        return

    def lift_protection(self):
        cmd = 'PR 0'
        s, nums, out, err = self.send_command(cmd)
        return
    
    def adjust(self):
        """Adjust (AD)
        Retrieve the tracking adjustment for all motors. Returns AD <adjustment 0> <adjustment 1>.
        Adjustments are reported in degrees.
        Cause the physical <motor> position to be <relative position> further clockwise while the
        logical position remains the same. The sum of all adjustments is called the total
        adjustment. The parameter <relative position> must be within acceptable limits
        (-0.21� and +0.21�) and must not cause the total adjustment to exceed 4�.
        This command is only permitted after protection has been removed with the PWord command.
        """
        cmd = 'AD'
        s, nums, out, err = self.send_command(cmd)
        self.offset_cp = nums
        return
    
    def version(self):
        cmd='VE'
        out, s = self.send_command(cmd)
        while s == None or len(s) == 0:
            out, s = self.send_command(cmd)
            time.sleep(1)
        
        if False:# any(strfind(INTRA.TRACKER_BRAND,'_AP')):
            s = float(s[3:-6])
            self.sun_sensor = round(10 * (s - math.floor(s))) == 8
        else:
            s = s[3:-6]
            self.sun_sensor = True
        return out, s

    def set_azimuth(self, azimuth: float):
        self.send_command("PO 0 {}".format(azimuth))

    def set_zenith(self, zenith: float):
        self.send_command("PO 1 {}".format(zenith))
