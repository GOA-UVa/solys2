from dataclasses import dataclass
from enum import Enum
from typing import Any, Union, Tuple, List
import time

from . import response
from . import connection

_MAX_RELOGIN_RECURSION = 3

class TrackerMode(Enum):
    SUN = 'SUN'
    REMOTE = 'REMOTE'
    CLOCK = 'CLOCK'

@dataclass
class CommandOutput:
    raw_response: str
    nums: List[float]
    out: response.OutCode
    err: Tuple[str, None]

class Solys2:
    def __init__(self, ip: str, port: int = 15000, password: str = "solys"):
        self.ip = ip
        self.port = port
        self.password = password
        self.closed = True

        self.connect()
        self.send_password()
        self.lift_protection()

        self.adjust()
        self.version()

    def connect(self):
        """
        Creates a new connection with the Solys. If it had another one, it gets closed.
        """
        if not self.closed:
            self.close()
        self.connection = connection.SolysConnection(self.ip, self.port)
        self.closed = False

    def send_command(self, cmd: str, recursion: int = 0) -> CommandOutput:
        """
        Send command to the solys.

        Parameters
        ----------
        cmd : str
            Command that is going to be sent
        recursion : int
            Level of recursion of this call. First time 0, next 1...
            This recursion is due to the need to try to lift the protection
            in case it goes down, which it does. At some point it will stop
            recursing.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        if recursion >= _MAX_RELOGIN_RECURSION:
            return CommandOutput("", [], response.OutCode.ERROR, response.ErrorCode.E10)
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
        if err == None:
            err = ""
        
        return CommandOutput(str_out, nums, out, err)

    def send_password(self, recursion: int = 0) -> CommandOutput:
        """Change password (PW)
        Send the password to the solys, authenticating this connection.
        Most of the set commands desire a password which can be changed here
        
        Parameters
        ----------
        recursion : int
            Level of recursion of this call. First time 0, next 1...
            This recursion is due to the need to try to lift the protection
            in case it goes down, which it does. At some point it will stop
            recursing.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'PW ' +  self.password
        output = self.send_command(cmd, recursion)
        self.lift_protection()
        return output

    def lift_protection(self, recursion: int = 0) -> CommandOutput:
        """Change protection (PR 0)
        Allows or disallows modification to be done by the web interface to the configuration.

        Parameters
        ----------
        recursion : int
            Level of recursion of this call. First time 0, next 1...
            This recursion is due to the need to try to lift the protection
            in case it goes down, which it does. At some point it will stop
            recursing.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'PR 0'
        output = self.send_command(cmd, recursion)
        return output

    def adjust(self) -> Tuple[float, float, CommandOutput]:
        """Adjust (AD)
        Retrieve the tracking adjustment for all motors. Returns AD <adjustment 0> <adjustment 1>.
        Adjustments are reported in degrees.

        Returns
        -------
        adjustment_0 : float
            Degrees of adjustment of the first motor.
        adjustment_1 : float
            Degrees of adjustment of the second motor.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'AD'
        output = self.send_command(cmd)
        self.offset_cp = output.nums
        return output.nums[0], output.nums[1], output

    def adjust_motor_0(self, degrees: float):
        """Adjust motor 0 (AD 0)
        
        Cause the physical <motor> position to be <relative position> further clockwise while the
        logical position remains the same. The sum of all adjustments is called the total
        adjustment. The parameter <relative position> must be within acceptable limits
        (-0.21� and +0.21�) and must not cause the total adjustment to exceed 4�.
        This command is only permitted after protection has been removed with the PWord command.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].
        """
        cmd = 'AD 0 {}'.format(degrees)
        output = self.send_command(cmd)
        self.adjust()
        return output

    def adjust_motor_1(self, degrees: float):
        """Adjust motor 1 (AD 1)
        
        Cause the physical <motor> position to be <relative position> further clockwise while the
        logical position remains the same. The sum of all adjustments is called the total
        adjustment. The parameter <relative position> must be within acceptable limits
        (-0.21� and +0.21�) and must not cause the total adjustment to exceed 4�.
        This command is only permitted after protection has been removed with the PWord command.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].
        """
        cmd = 'AD 1 {}'.format(degrees)
        output = self.send_command(cmd)
        self.adjust()
        return output

    def version(self) -> CommandOutput:
        """Version (VE)
        Obtain the version of the solys.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'VE'
        output = self.send_command(cmd)
        return output
    
    def reset(self) -> CommandOutput:
        """Reset/Home (HO)
        Tells the Solys to go to its home position. (it will stay there for over 1 minute).
        This might block the Solys for a couple of minutes.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'HO'
        output = self.send_command(cmd)
        return output
    
    def close(self):
        """
        Close the connection.
        """
        self.connection.close()
        self.closed = True

    def set_azimuth(self, azimuth: float) -> CommandOutput:
        """Position 0 (PO 0)
        Set the azimuth angle at which the solys is pointing.

        Parameters
        ----------
        azimuth : float
            Float between 0 and 360, representing the azimuth at which we want the solys to
            point to.
        
        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PO 0 {}".format(azimuth%360))
        return output

    def set_zenith(self, zenith: float) -> CommandOutput:
        """Position 1 (PO 1)
        Set the zenith angle at which the solys is pointing.

        Parameters
        ----------
        zenith : float
            Float between 0 and 90, representing the zenith at which we want the solys to
            point to.
        
        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        zenith = abs(zenith)
        if zenith > 90:
            zenith = 90
        output = self.send_command("PO 1 {}".format(zenith))
        return output
    
    def get_planned_position(self) -> Tuple[int, int, CommandOutput]:
        """Position (PO)
        Obtain the positions that the Solys sais it's going to.
        
        Returns
        -------
        azimuth : float
            Azimuth angle at which the Solys is pointing.
        zenith : float
            Zenith angle at which the Solys is pointing.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PO")
        return output.nums[0], output.nums[1], output
    
    def get_location_pressure(self) -> Tuple[float, float, float, CommandOutput]:
        """Location and pressure (LL)
        Obtain the location and pressure for the site.

        Returns
        -------
        latitude : float
            Latitude in decimal degrees
        longitude : float
            Longitude in decimal degrees
        pressure : float
            Nominal atmospheric pressure recorded for the site
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("LL")
        return output.nums[0], output.nums[1], output.nums[2], output

    def set_power_save(self, save: bool) -> CommandOutput:
        """Power Save (PS)

        Parameters
        ----------
        save : bool
            True if power save activated, false if not.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PS "+str(int(save)))
        return output
    
    def get_power_save(self) -> Tuple[bool, CommandOutput]:
        """Power Save (PS)

        Returns
        -------
        power_save_status : int
            1 if its activated, 0 if not, -1 if error.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PS") 
        return bool(output.nums[0]), output
    
    def get_sun_quadrants(self) -> Tuple[Any, CommandOutput]:
        """Sun sensor scaling (SC)
        Retrieve the scaling factor for each sun sensor quadrant along with the nominal
        scaling of the sensor.

        Returns
        -------
        quad_data : Any
            Any
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("SC")
        return None, output

def translate_error(code: str) -> str:
    """
    Returns the error related to the error code

    Parameters
    ----------
    code : str
        Error code.
    
    Returns
    -------
    msg : str
        Retrieved error message.
    """
    str_code = str(code)
    if str_code in response.ERROR_CODES:
        return response.ERROR_CODES[str_code]
    else:
        return ""