"""Solys2

Module that encapsulates and abstracts an interface for interacting with the Solys2.

It exports the following classes:
    * Solys2 : Class that encapsulates and abstracts the connection and interaction \
with the Solys2.
    * CommandOutput : Dataclass that stores the output of a Solys2 message somewhat processed.
    * SolysFunction : Enum that stores the functions that the Solys2 can be set to with the \
FU command.
    * SolysException : Exception raised when there was an error with the Solys2.

It exports the following functions:
    * translate_error : Returns the error related to an error code.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
import datetime
from enum import Enum
from typing import Tuple, List
import time

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
try:
    from . import response
    from . import connection
except:
    from solys2 import response
    from solys2 import connection

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/03/09"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

_MAX_RELOGIN_RECURSION = 3

_DEFAULT_VAL_ERR = -999

_NONES_UNTIL_RECONNECT = 100

@dataclass
class CommandOutput:
    """
    Dataclass that stores the output of a Solys2 message somewhat processed.

    Attributes
    ----------
    raw_response : str
        Raw response TCP message received from the Solys2.
    nums : list of float
        Output numbers present in the raw_response, already filtered.
    out : response.OutCode
        Type of message received from the Solys.
    err : str
        Error code received from the Solys2. If none, it will be an empty str.
    """
    raw_response: str
    nums: List[float]
    out: response.OutCode
    err: str

class SolysFunction(Enum):
    """
    Functions that the Solys2 can be set to with the FU command.

    - NO_FUNCTION : The tracker will not move.
    - STANDARD_OPERATION : The tracker moves in response to motion commands. Homes to (90,90).
    - STANDARD_OPERATION_REVERSE : The tracker moves in response to motion commands. \
Homes to (90,0).
    - SUNTRACKING : Following the sun.
    - ACTIVE_TRACKING : Following the sun using the sun sensor for minor adjustment.
    """
    NO_FUNCTION = 0
    STANDARD_OPERATION = 1
    STANDARD_OPERATION_REVERSE = 2
    SUNTRACKING = 4
    ACTIVE_TRACKING = 6

class SolysException(Exception):
    """
    Exception raised when there was an error in the communication with the Solys2, or the message
    was unexpected.
    """
    pass

def _create_solys_exception(error_code: str, raw_response: str = None) -> SolysException:
    """
    Create a SolysException following a standarized format.

    Parameters
    ----------
    error_code : str
        Error code received from the Solys2.
    raw_response : str
        Raw response TCP message received from the Solys2.

    Returns
    -------
    exc : SolysException
        SolysException generated.
    """
    err = error_code
    err_msg = translate_error(err)
    sec_msg = ""
    if raw_response != None:
        sec_msg = "\nRaw response: {}.".format(raw_response)
    return SolysException("ERROR {}: {}.{}".format(err, err_msg, sec_msg))

class Solys2:
    """Solys2
    Class that encapsulates and abstracts the connection and interaction with the Solys2

    Attributes
    ----------
    ip : str
        IP of the Solys2.
    port : int
        Connection port of the Solys2.
    password : str
        User password for the Solys2.
    connection : connection.SolysConnection
        Connection with the Solys2.
    closed : bool
        Boolean value that stores if the connection is closed or not.
    offset_cp : list of float
        Adjustments of the motors. [adjustment_0, adjustment_1].
    """

    def __init__(self, ip: str, port: int = 15000, password: str = "solys"):
        """
        Parameters
        ----------
        ip : str
            IP of the Solys2.
        port : int
            Connection port of the Solys2. Default is 15000.
        password : str
            User password for the Solys2. Default is "solys".

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.
        """
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
        Send command to the solys. If it gets deauthenticated, it authenticates again
        automatically.

        Parameters
        ----------
        cmd : str
            Command that is going to be sent
        recursion : int
            Level of recursion of this call. First time 0, next 1...
            This recursion is due to the need to try to lift the protection
            in case it goes down, which it does. At some point it will stop
            recursing.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = cmd.strip()
        if recursion >= _MAX_RELOGIN_RECURSION:
            err = response.ErrorCode.E10.value
            raise _create_solys_exception(err)
        self.connection.empty_recv()
        try:
            str_out = self.connection.send_cmd(cmd)
        except (ConnectionResetError, BrokenPipeError):
            self.connect()
            str_out = self.connection.send_cmd(cmd)
        nums, out, err = response.process_response(str_out, cmd)
        none_quant = 0
        while out == response.OutCode.NONE:
            # The solys might return empty responses (or older responses) until it answers
            # the command.
            if none_quant > _NONES_UNTIL_RECONNECT:
                # If there are only nones, it's probably disconnected.
                self.connect()
                none_quant = 0
            else:
                none_quant += 1
                time.sleep(0.1)
            str_out = self.connection.recv_msg()
            nums, out, err = response.process_response(str_out, cmd)
        if out == response.OutCode.ERROR:
            if err == 'G':
                if cmd.startswith("PW"):
                    raise _create_solys_exception(err, str_out)
                else:
                    # Password issue, need to relogin
                    recursion += 1
                    self.send_password(recursion)
                    self.lift_protection(recursion)
                    return self.send_command(cmd, recursion)
            else:
                # Any other kind of error
                raise _create_solys_exception(err, str_out)
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

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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

        Also updates the inner variables that store the current adjustments.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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
        req_nums_len = 2
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        self.offset_cp = output.nums
        return output.nums[0], output.nums[1], output

    def _adjust_motor_0(self, degrees: float) -> CommandOutput:
        """Adjust motor 0 (AD 0)
        
        Cause the physical <motor> position to be <relative position> further clockwise while the
        logical position remains the same. The sum of all adjustments is called the total
        adjustment. The parameter <relative position> must be within acceptable limits
        (-0.21º and +0.21º) and must not cause the total adjustment to exceed 4º.
        This command is only permitted after protection has been removed with the PWord command.
        
        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'AD 0 {}'.format(degrees)
        output = self.send_command(cmd)
        if output.out == response.OutCode.ANSWERED or output.out == response.OutCode.ANSWERED_NO_NUMS or \
                output.out == response.OutCode.ANSWERED_VALUE_ERROR:
            self.adjust()
        return output

    def _adjust_motor_1(self, degrees: float) -> CommandOutput:
        """Adjust motor 1 (AD 1)
        
        Cause the physical <motor> position to be <relative position> further clockwise while the
        logical position remains the same. The sum of all adjustments is called the total
        adjustment. The parameter <relative position> must be within acceptable limits
        (-0.21º and +0.21º) and must not cause the total adjustment to exceed 4º.
        This command is only permitted after protection has been removed with the PWord command.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'AD 1 {}'.format(degrees)
        output = self.send_command(cmd)
        if output.out == response.OutCode.ANSWERED or output.out == response.OutCode.ANSWERED_NO_NUMS or \
                output.out == response.OutCode.ANSWERED_VALUE_ERROR:
            self.adjust()
        return output
    
    def adjust_azimuth(self, degrees: float) -> CommandOutput:
        """Adjust the azimuth motor.

        Cause the azimuth motor to be adjusted by the given degrees. The <degrees> parameters
        must be within [-0.2, 0.2] and the total adjustment must not exceed 4.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        degrees = max(-0.2, min(0.2, degrees))
        return self._adjust_motor_0(degrees)
    
    def adjust_zenith(self, degrees: float) -> CommandOutput:
        """Adjust the zenith motor.

        Cause the zenith motor to be adjusted by the given degrees. The <degrees> parameters
        must be within [-0.2, 0.2] and the total adjustment must not exceed 4.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Parameters
        ----------
        degrees : float
            Degrees of adjustment to move (clockwise). Contained in the range [-0.2, 0.2].

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        degrees = max(-0.2, min(0.2, degrees))
        return self._adjust_motor_1(degrees)

    def version(self) -> CommandOutput:
        """Version (VE)
        Obtain the version of the solys.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        cmd = 'VE'
        output = self.send_command(cmd)
        return output
    
    def home(self) -> CommandOutput:
        """Home (HO)
        Tells the Solys to go to its home position. (it will stay there for over 1 minute).
        This might block the Solys for a couple of minutes.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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
    
    def point_down(self) -> CommandOutput:
        """Point down as much as possible
        Set the zenith angle to the maximum possible (94.5)

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.
        
        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PO 1 94.9")
        return output

    def get_planned_position(self) -> Tuple[float, float, CommandOutput]:
        """Position (PO)
        Obtain the positions that the Solys sais it's going to.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.
        
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
        req_nums_len = 2
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        return output.nums[0], output.nums[1], output
    
    def get_current_position(self) -> Tuple[float, float, CommandOutput]:
        """Current Position (CP)
        Obtain the positions where the Solys is at the moment.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.
        
        Returns
        -------
        azimuth : float
            Azimuth angle at which the Solys is pointing.
        zenith : float
            Zenith angle at which the Solys is pointing.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("CP")
        req_nums_len = 2
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        return output.nums[0], output.nums[1], output

    def get_location_pressure(self) -> Tuple[float, float, float, CommandOutput]:
        """Location and pressure (LL)
        Obtain the location and pressure for the site.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

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
        req_nums_len = 3
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        return output.nums[0], output.nums[1], output.nums[2], output

    def set_power_save(self, save: bool) -> CommandOutput:
        """Power Save (PS)

        Parameters
        ----------
        save : bool
            True if power save activated, false if not.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PS "+str(int(save)))
        return output
    
    def get_power_save(self) -> Tuple[bool, CommandOutput]:
        """Power Save (PS)

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        power_save_status : int
            1 if its activated, 0 if not, -1 if error (it should raise an exception).
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("PS")
        req_nums_len = 1
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, output
        return bool(output.nums[0]), output
    
    def get_queue_status(self) -> Tuple[int, int, CommandOutput]:
        """Queue Status (QS)
        Retrieves the current number of path segments in the path for each motor.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.
        
        Returns
        -------
        count_0 : int
            Queue status of the first motor. Azimuth/Horizontal motor.
        count_1 : int
            Queue status of the second motor. Zenith/Vertical motor.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("QS")
        if output.out != response.OutCode.ANSWERED:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        nums, out, err = response.process_response(output.raw_response, "QS", True)
        if err == None:
            err = ""
        output = CommandOutput(output.raw_response, nums, out, err)
        req_nums_len = 2
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return _DEFAULT_VAL_ERR, _DEFAULT_VAL_ERR, output
        return nums[0], nums[1], output

    def get_function(self) -> Tuple[SolysFunction, CommandOutput]:
        """Get Function (FU)
        Retrieve the code indicating the function for which the tracker is being used.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        function : SolysFunction
            Function for which the tracker is being used. NO_FUNCTION in case of error.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("FU")
        req_nums_len = 1
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return SolysFunction.NO_FUNCTION, output
        return SolysFunction(int(output.nums[0])), output

    def set_function(self, func: SolysFunction) -> CommandOutput:
        """Set Function (FU)
        Sets the function of the tracker.
        
        Note: If the instrument was suntracking and is given a non-suntracking function,
        it will continue to follow the sun until it's sent a home (HO) command.

        Parameters
        ----------
        func : SolysFunction
            Function for which the tracker will be used for.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("FU {}".format(func.value))
        return output

    def get_sun_intensity(self) -> Tuple[List[float], float, CommandOutput]:
        """Sun intensity (SI)
        Retrieves the current sun intensity.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        intensities : list of 4 float
            Intensity of each quadrant. [Q1, Q2, Q3, Q4]
        total_intensity : float
            Total intensity.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("SI")
        intensities = []
        total_intensity = 0
        req_nums_len = 5
        if output.out != response.OutCode.ANSWERED or len(output.nums) < req_nums_len:
            return [_DEFAULT_VAL_ERR for _ in range(4)], _DEFAULT_VAL_ERR, output
        intensities = output.nums[:4]
        total_intensity = output.nums[4]
        return intensities, total_intensity, output
    
    def get_raw_status(self) -> Tuple[str, CommandOutput]:
        """Status (IS)
        Get the raw status code returned from the Solys2

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        raw_status : str
            Raw status code received from the Solys2.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        output = self.send_command("IS")
        raw_status = output.raw_response.replace("IS ", "", 1)
        return raw_status, output

    def get_status(self) -> Tuple[str, List[str], List[str], CommandOutput]:
        """
        Gets the status, translated for humans.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        ins_stat : str
            Instrument status.
        flags_true : list of str
            List of all the activated flags.
        flags_false : list of str
            List of all the deactivated flags.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        raw_status, output = self.get_raw_status()
        if output.out == response.OutCode.ERROR or output.out == response.OutCode.NONE:
            return "Error communicating with the Solys2, couldn't retrieve status", [], [], output
        ins_stat, flags_true, flags_false = response.translate_status(raw_status)
        return ins_stat, flags_true, flags_false, output

    def _set_function_with_home(self, func: SolysFunction) -> List[CommandOutput]:
        """
        Set a tracking function, send the home function.

        Parameters
        ----------
        func : SolysFunction
            Function for which the tracker will be used for.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        outputs : list of CommandOutput
            Output of the commands, data received from solys.
        """
        o0 = self.set_function(func)
        o1 = self.home()
        return [o0, o1]

    def set_automatic(self) -> List[CommandOutput]:
        """
        Set the tracker in automatic active tracking following the sun.

        Parameters
        ----------
        func : SolysFunction
            Function for which the tracker will be used for.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        outputs : list of CommandOutput
            Output of the commands, data received from solys.
        """
        return self._set_function_with_home(SolysFunction.ACTIVE_TRACKING)

    def set_manual(self) -> List[CommandOutput]:
        """
        Set the tracker in manual standard operation mode.

        Parameters
        ----------
        func : SolysFunction
            Function for which the tracker will be used for.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        outputs : list of CommandOutput
            Output of the commands, data received from solys.
        """
        return self._set_function_with_home(SolysFunction.STANDARD_OPERATION)
    
    def get_datetime(self) -> Tuple[datetime.datetime, CommandOutput]:
        """Get Time (TI)
        Retrieve the internal time (Universal).

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        dt : datetime.datetime
            Solys2 internal time.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        t0 = time.time()
        output = self.send_command("TI")
        nums = output.nums
        if len(nums) != 5:
            dt = datetime.datetime(1, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
            return dt, output
        tf = time.time()
        t_extra = (tf-t0)/2
        dt = datetime.datetime(int(nums[0]), 1, 1, int(nums[2]), int(nums[3]), int(nums[4]),
            tzinfo=datetime.timezone.utc) + datetime.timedelta(int(nums[1])-1, t_extra)
        return dt, output
    
    def calculate_timedelta(self) -> Tuple[datetime.timedelta, CommandOutput]:
        """
        Calculate the difference between solys internal time (UTC) and the Computer
        time in UTC.

        Raises
        ------
        SolysException
            If an error happens when calling the Solys2.

        Returns
        -------
        tdt : datetime.timedelta
            Difference between solys internal time (UTC) and the Computer time in UTC.
        output : CommandOutput
            Output of the command, data received from solys.
        """
        solys_dt, out = self.get_datetime()
        pc_dt = datetime.datetime.now(datetime.timezone.utc)
        return (solys_dt - pc_dt), out

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
    return ""
