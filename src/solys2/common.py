"""Common

Module containing common constants, functions and datatypes.

It exports the following functions:
    * gen_random_str: Generate a random str of the specified length.
    * create_default_logger: Instantiate a simple logger.
    * create_file_logger: Generate a file logger with extra log handlers.

It exports the following classes:
    * ContainedBool: Dataclass that act as a container for bool type.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
import random
import string
import logging
from typing import List

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
# import here

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
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

def create_default_logger(level: int = logging.WARNING) -> logging.Logger:
    """
    Instantiate a simple logger that will be the default one.

    By default it will only log messages if they are level WARNING or higher.

    Parameters
    ----------
    level : int
        Log level that will be logged out.

    Returns
    -------
    logger : logging.Logger
        Generated Logger.
    """
    randstr = gen_random_str(20)
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)
    logger = logging.getLogger('solys2-{}'.format(randstr))
    return logger

def create_file_logger(logfile: str, extra_log_handlers: List[logging.Handler] = [],
    level: int = logging.DEBUG) -> logging.Logger:
    """
    Generate a file logger with extra log handlers.

    Parameters
    ----------
    logfile : str
        Path of the file where the logging will be stored. In case that it's not used, it will be
        printed in stderr.
    extra_log_handlers : list of logging.Handler
        Custom handlers which the log will also log to.
    level : int
        Log level that will be logged out.

    Returns
    -------
    logger : logging.Logger
        Generated Logger.
    """
    randstr = gen_random_str(20)
    logging.basicConfig(level=logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)
    logger = logging.getLogger('solys2-{}'.format(randstr))
    for hand in extra_log_handlers:
        logger.addHandler(hand)
    if logfile != None and logfile != "":
        log_handler = logging.FileHandler(logfile, mode='a')
        log_handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
        logger.addHandler(log_handler)
        logger.setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(level)
    return logger

@dataclass
class ContainedBool:
    """
    Dataclass that acts as a container of a boolean variable so it gets passed as a
    reference.
    """
    value : bool
