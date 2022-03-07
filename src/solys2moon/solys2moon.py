from enum import Enum
from typing import Union, Tuple
import time
import re
import math

from . import connection

command = ".PW 65535<LF>;.SE<LF>"

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
    'R': '??????',
    'P': 'Wrong password.'
}

class Solys2:
    def __init__(self, ip: str, port: int = 15000, password: str = "solys"):
        self.ip = ip
        self.port = port
        self.sun_sensor = False
        
        self.change_password(password)
        self.lift_protection()
        
        out, s = self.adjust()
        self.offset_cp = out
        self.version()
    
    def send_command(self, cmd: str) -> Tuple[float, Union[str, None]]:
        str_out = connection.send_command(cmd, self.ip, self.port)
        out = str_out.strip()
        out = re.sub(cmd, '', out)
        unwateted = re.sub({'\d','\.',' '}, '', out)
        out = re.sub(unwateted, '', out)
        out = float(out)
        return out, str_out
    
    def change_password(self, password: str):
        cmd = 'PW ' +  password
        out, s = self.send_command(cmd)
        time.sleep(0.5)
        self.lift_protection()
        return out, s

    def lift_protection(self):
        cmd = 'PR 0'
        out, s = self.send_command(cmd)
        time.sleep(1)
        return out, s
    
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
        out, s = self.send_command(cmd)
        self.offset_cp = out
        return out, s
    
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

def get_pos_raw():
    """Get position raw"""
    pass

def get_pos():
    """Get position"""
    pass

def set_pos(azimuth, elevation):
    """Set position"""
    pass

def get_eye():
    """Get solar measurement of active eye"""
    pass

def get_datetime():
    """Get date and time"""
    pass

def set_time():
    """Set time for PC"""
    pass

def set_date():
    """Set date for PC"""
    pass

def get_mode() -> TrackerMode:
    """Get Tracker mode"""
    pass

def set_mode(mode: TrackerMode):
    """Set Tracker mode"""
    pass
