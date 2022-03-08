from enum import Enum
from typing import Union, Tuple, List
import time
from . import response

from . import connection

class TrackerMode(Enum):
    SUN = 'SUN'
    REMOTE = 'REMOTE'
    CLOCK = 'CLOCK'

_MAX_RELOGIN_RECURSION = 3

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

    def send_command(self, cmd: str, recursion: int = 0) -> Tuple[str, List[float], response.OutCode, Union[str, None]]:
        if recursion >= _MAX_RELOGIN_RECURSION:
            return "", [], response.OutCode.ERROR, None
        self.connection.empty_recv()
        str_out = self.connection.send_cmd(cmd)
        nums, out, err = response.process_response(str_out, cmd)
        while out == response.OutCode.NONE:
            time.sleep(0.1)
            resp = self.connection.recv_msg()
            nums, out, err = response.process_response(resp, cmd)
        if out == response.OutCode.ERROR and err == 'G':
            # Password issue, need to relogin
            recursion += 1
            _, _, out_pass, err = self.send_password(recursion)
            if out_pass != response.OutCode.ERROR:
                _, _, out_prot, err = self.lift_protection(recursion)
                if out_prot != response.OutCode.ERROR:
                    self.send_command(cmd, recursion)
        return str_out, nums, out, err

    def send_password(self, recursion: int = 0):
        cmd = 'PW ' +  self.password
        s, nums, out, err = self.send_command(cmd, recursion)
        self.lift_protection()
        return s, nums, out, err

    def lift_protection(self, recursion: int = 0):
        cmd = 'PR 0'
        s, nums, out, err = self.send_command(cmd, recursion)
        return s, nums, out, err

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
    
    def version(self) -> str:
        cmd = 'VE'
        s, nums, out, err  = self.send_command(cmd)
        
        #if False:# any(strfind(INTRA.TRACKER_BRAND,'_AP')):
        #    s = float(s[3:-6])
        #    self.sun_sensor = round(10 * (s - math.floor(s))) == 8
        #else:
        s = s[3:-6]
        self.sun_sensor = True
        return s
    
    def reset(self):
        cmd = 'HO'
        s, nums, out, err = self.send_command(cmd)
        return
    
    def close(self):
        self.connection.close()

    def set_azimuth(self, azimuth: float):
        self.send_command("PO 0 {}".format(azimuth))

    def set_zenith(self, zenith: float):
        self.send_command("PO 1 {}".format(zenith))
    
    def get_planned_position(self) -> Tuple[int, int]:
        s, nums, out, err = self.send_command("PO")
        return nums[0], nums[1]
