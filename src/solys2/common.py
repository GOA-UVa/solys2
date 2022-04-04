"""Common

Module containing common constants, functions and datatypes.

It exports the following functions:
    * gen_random_str: Generate a random str of the specified length.

It exports the following classes:
    * ContainedBool: Dataclass that act as a container for bool type.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
import random
import string

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
# import here

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón,\
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/04/04"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

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
