from enum import Enum
import re
from typing import Union, Tuple, List

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
    """
    Enum that represents the type of message received from the Solys.

    NONE: Empty message, or a response that is not for the sent command.
    ERROR: An error was encountered-
    ANSWERED: The response was a successfull answer for the command.
    """
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
            only_nums_split = only_nums.split()
            isdecimal = all(s.isdecimal() for s in only_nums_split)
            if isdecimal:
                numbers = list(map(float, only_nums_split))
            else:
                numbers = [1]
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
