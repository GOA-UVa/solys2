"""Common

Module containing common constants, functions and datatypes.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
import random
import string

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
# import here

SOLYS_APPROX_DELAY = 5
SOLYS_DELAY_MARGIN = 2
ASD_DELAY = 2
MAX_SECS_DIFF_WARN = 2

def gen_random_str(len: int) -> str:
    """
    Return a random str of the specified length.

    Parameters
    ----------
    len : int
        Length of the desired str.

    Returns
    -------
    rand_str : str
        Generated random str of the specified length.
    """
    return ''.join(random.choice(string.ascii_letters) for i in range(len))


@dataclass
class ContainedBool:
    """
    Dataclass that acts as a container of a boolean variable so it gets passed as a
    reference.
    """
    value : bool
