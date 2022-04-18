"""AutoHelper

Module that contains the functionalities that are used for performing automatic actions
with the Solys2.

It exports the following functions:
    * get_body_calculator : Obtain the BodyCalculator object corresponding to the given \
parameters.
    * check_time_solys : Check the solys internal time against the computer time and log \
an info or warning message if necessary.
    * wait_position_reached : Waits until the solys is approx. pointing at the given position.
    * read_and_move : Reads some information from the solys and writes it down to the logger.
Then it moves it to a position using the given position function and parameters.
    * exception_tracking : When an execution fails and must end a set of actions must be \
taken in order to communicate it and synchronize it.
"""

"""___Built-In Modules___"""
from abc import ABC, abstractmethod
from typing import Dict, Tuple
import time
import datetime
import logging

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
try:
    from .. import response
    from .. import solys2
    from . import positioncalc as psc
    from .. import common as _common
except:
    from solys2 import response
    from solys2.automation import positioncalc as psc
    from solys2 import common as _common
    from solys2 import solys2

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/04/05"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

def get_body_calculator(solys: solys2.Solys2, library: psc._BodyLibrary, logger: logging.Logger,
    altitude: float = 0, kernels_path: str = "./kernels") -> psc.BodyCalculator:
    """
    Obtain the BodyCalculator corresponding to the given parameters.

    Parameters
    ----------
    solys : solys2.Solys2
        Solys2 instance that will be used to send de messages with.
    library : _BodyLibrary
        Body library that will be used to track the body. Moon or Sun.
    logger : logging.Logger
        Logger that will log out the log messages
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.

    Returns
    -------
    calc : BodyCalculator
        Calculator that will be able to calculate the position of the body for a given date.
    """
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            logger.error("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)))
        else:
            logger.error("ERROR obtaining coordinates. Unknown error.")
    logger.debug("Latitude: {:.4f}. Longitude: {:.4f}".format(lat, lon))
    switcher: Dict[int, psc.BodyCalculator] = {
        psc._BodyLibrary.EPHEM_MOON.value: psc.EphemMoonCalc,
        psc._BodyLibrary.SPICEDMOON.value: psc.SpiceMoonCalc,
        psc._BodyLibrary.PYLUNAR.value: psc.PylunarMoonCalc,
        psc._BodyLibrary.PYSOLAR.value: psc.PysolarSunCalc,
        psc._BodyLibrary.EPHEM_SUN.value: psc.EphemSunCalc,
        psc._BodyLibrary.SPICEDSUN.value: psc.SpiceSunCalc
    }
    body_calc_class = switcher[library.value]
    logger.debug("Using {} library.".format(library.name))
    if library.value == psc._BodyLibrary.SPICEDMOON.value or \
        library.value == psc._BodyLibrary.SPICEDSUN.value:
        logger.debug("Using SPICE.")
        return body_calc_class(lat, lon, altitude, kernels_path)
    return body_calc_class(lat, lon)

def check_time_solys(solys: solys2.Solys2, logger: logging.Logger):
    """
    Check the solys internal time against the computer time and log an info or warning
    message if necessary.

    Parameters
    ----------
    solys : solys2.Solys2
        Solys2 which time is wanted to be checked agains computer time.
    logger : logging.Logger
        Logger that will log out the log messages.
    """
    td, _ = solys.calculate_timedelta()
    secs = td.total_seconds()
    if abs(secs) <= _common.MAX_SECS_DIFF_WARN:
        logger.info("Solys clock vs PC clock: {} seconds.".format(secs))
    else:
        logger.warning("Solys clock vs PC clock: {} seconds.".format(secs))

def wait_position_reached(solys: solys2.Solys2, az: float, ze: float, logger: logging.Logger):
    """
    Waits until the solys is approx. pointing at the given position.

    Parameters
    ----------
    solys : solys2.Solys2
        Solys2 that will eventually point to the given position.
    az : float
        Azimuth of the position.
    ze : float
        Zenith of the position.
    logger : logging.Logger
        Logger that will log out the log messages.
    """
    while True:
        # get_queue_status is not that reliable
        prev_az, prev_ze, _ = solys.get_current_position()
        pos_dif = abs(az - prev_az) +  abs(ze - prev_ze)
        if pos_dif <= 0.01:
            break
        logger.debug("Position difference too large: {:.4f}. (Expected vs Actual)".format(pos_dif))
        logger.debug("Azimuth {:.4f} vs {:.4f}. Zenith: {:.4f} vs {:.4f}.".format(az, prev_az,
            ze, prev_ze))
        logger.debug("Sleeping 1 second...")
        time.sleep(1)

def read_and_move(solys: solys2.Solys2, body_calc: psc.BodyCalculator, logger: logging.Logger,
    offset: Tuple[float, float] = (0,0), datetime_offset: float = 0):
    """
    Reads some information from the solys and writes it down to the logger.
    Then it moves it to a position using the given position function and parameters.

    Parameters
    ----------
    solys : solys2.Solys2
        Solys2 in which to perform the read and move actions.
    body_calc : BodyCalculator
        Calculator that will be able to calculate the position of the body for a given date.
    logger : logging.Logger
        Logger that will log out the log messages.
    offset : tuple of 2 floats.
        It will move to the calculated position + some optional offset in degrees.
        (azimuth_offset, zenith_offset). By default (0,0).
    datetime_offset : float
        Offset of seconds that the body positions will be calculated, added to currrent time.
    """
    dt = datetime.datetime.now(datetime.timezone.utc)
    logger.info("UTC Datetime: {}.".format(dt))
    should_check_time_solys = (dt.minute == 0 )
    try:
        prev_az, prev_ze, _ = solys.get_current_position()
        logger.info("Current Position: Azimuth: {:.4f}, Zenith: {:.4f}.".format(prev_az, prev_ze))
        az_adj, ze_adj, _ = solys.adjust()
        logger.debug("Adjustment of {:.4f} and {:.4f}.".format(az_adj, ze_adj))
        dt = datetime.datetime.now(datetime.timezone.utc)
        if should_check_time_solys:
            logger.debug("Checking computer time against Solys internal time.")
            check_time_solys(solys, logger)
        logger.info("Real UTC Datetime: {}".format(dt))
        dt = dt + datetime.timedelta(0, datetime_offset)
        logger.info("Position UTC Datetime: {}".format(dt))
        az, ze = body_calc.get_position(dt)
        new_az = min(360, az + offset[0])
        new_ze = min(90, ze + offset[1])
        solys.set_azimuth(new_az)
        solys.set_zenith(new_ze)
        logger.info("Sent positions:")
        logger.info("Azimuth: {:.4f} + {:.4f} = ({:.4f}).".format(az, offset[0], new_az))
        logger.info("Zenith: {:.4f} + {:.4f} = ({:.4f}).\n".format(ze, offset[1], new_ze))
        wait_position_reached(solys, new_az+az_adj, new_ze+ze_adj, logger)
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.info("Finished moving at UTC datetime: {}.".format(dt))
    except solys2.SolysException as e:
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.error("Error at UTC datetime: {}".format(dt))
        logger.error("Error: {}".format(e))

def exception_tracking(logger: logging.Logger, e: Exception, solys: solys2.Solys2,
    is_finished: _common.ContainedBool):
    """
    When an execution fails and must end a set of actions must be taken in order
    to communicate it and synchronize it.

    Parameters
    ----------
    logger : logging.Logger
        Logger that will log out the log messages
    e : Exception
        Exception that stopped the execution
    solys : Solys2
        Connected Solys2
    is_finished :
        Container for the boolean value that initially was False, but it should be changed
        to True when exiting the function.
    """
    logger.error("Stopped tracking body.")
    logger.error(str(e))
    try:
        solys.close()
    except Exception as eclose:
        logger.error("Error closing connection.")
        logger.error(str(eclose))
    if is_finished:
        is_finished.value = True

class AutomationWorker(ABC):
    @abstractmethod
    def start(self):
        """Start the automatic process in the thread."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the automatic thread, although not immediately."""
        pass

    @abstractmethod
    def is_finished(self) -> bool:
        """Check if the thread has successfully finished executing."""
        pass
