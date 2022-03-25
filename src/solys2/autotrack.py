"""AutoTrack

Module that contains the functionalities of performing automatic actions with the Solys2.

It exports the following classes:
    * MoonTracker : Object that contains the thread that controls the Solys2 for tracking
        automatically the Moon.
    * SunTracker : Object that contains the thread that controls the Solys2 for tracking
        automatically the Sun.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple, List
import time
import datetime
import logging
from threading import Thread, Lock
import string
import random

"""___Third-Party Modules___"""
import numpy as np

"""___Solys2 Modules___"""
from . import response
from . import solys2
from . import positioncalc as psc

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón,\
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/03/10"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

_SOLYS_APPROX_DELAY = 5
_SOLYS_DELAY_MARGIN = 2
_ASD_DELAY = 2
_MAX_SECS_DIFF_WARN = 2

class _TrackBody(Enum):
    """
    Enum that represents the celestial body that the Solys will track.
    
    SUN: The sun.
    MOON: The moon.
    """
    SUN = 0
    MOON = 1

@dataclass
class _ContainedBool:
    """
    Dataclass that acts as a container of a boolean variable so it gets passed as a
    reference.
    """
    value : bool

def _get_body_calculator(solys: solys2.Solys2, library: psc._BodyLibrary, logger: logging.Logger,
    altitude: float = 0, kernels_path: str = "./kernels") -> psc.BodyCalculator:
    """
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

def _check_time_solys(solys: solys2.Solys2, logger: logging.Logger):
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
    if abs(secs) <= _MAX_SECS_DIFF_WARN:
        logger.info("Solys clock vs PC clock: {} seconds.".format(secs))
    else:
        logger.warning("Solys clock vs PC clock: {} seconds.".format(secs))

def _wait_position_reached(solys: solys2.Solys2, az: float, ze: float, logger: logging.Logger):
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
        logger.debug("Position difference too large: {}. (Expected vs Actual)".format(pos_dif))
        logger.debug("Azimuth {:0.5f} vs {}. Zenith: {:0.5f} vs {}.".format(az, prev_az,
            ze, prev_ze))
        logger.debug("Sleeping 1 second...")
        time.sleep(1)

def _read_and_move(solys: solys2.Solys2, body_calc: psc.BodyCalculator, logger: logging.Logger,
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
    check_time_solys = (dt.minute == 0 )
    try:
        prev_az, prev_ze, _ = solys.get_current_position()
        qsi, total_intens, _ = solys.get_sun_intensity()
        logger.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
        logger.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
        dt = datetime.datetime.now(datetime.timezone.utc)
        if check_time_solys:
            logger.debug("Checking computer time against Solys internal time.")
            _check_time_solys(solys, logger)
        logger.info("Real UTC Datetime: {}".format(dt))
        dt = dt + datetime.timedelta(0, datetime_offset)
        logger.info("Position UTC Datetime: {}".format(dt))
        az, ze = body_calc.get_position(dt)
        new_az = min(360, az + offset[0])
        new_ze = min(90, ze + offset[1])
        solys.set_azimuth(new_az)
        solys.set_zenith(new_ze)
        logger.info("Sent positions: Azimuth: {} + {} ({}). Zenith: {} + {} ({}).\n".format(az,
            offset[0], new_az, ze, offset[1], new_ze))
        _wait_position_reached(solys, new_az, new_ze, logger)
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.info("Finished moving at UTC datetime: {}.".format(dt))
    except solys2.SolysException as e:
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.error("Error at UTC datetime: {}".format(dt))
        logger.error("Error: {}".format(e))

def _track_body(ip: str, seconds: float, library: psc._BodyLibrary, mutex_cont: Lock,
    cont_track: _ContainedBool, logger: logging.Logger, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    altitude: float = 0, kernels_path: str = "./kernels"):
    """
    Track a celestial body

    Parameters
    ----------
    ip : str
        IP of the solys.
    seconds : float
        Amount of seconds waited between each message of change of position of zenith and azimuth.
    library : _BodyLibrary
        Body library that will be used to track the body. Moon or Sun.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    logger : logging.Logger
        Logger that will log out the log messages
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    body_calc = _get_body_calculator(solys, library, logger, altitude, kernels_path)
    if library.value in [l.value for l in psc.SunLibrary]:
        logger.info("Tracking sun. Connected with Solys2.")
    else:
        logger.info("Tracking moon. Connected with Solys2.")
    _check_time_solys(solys, logger)
    # Start tracking in a loop
    sleep_time = 0
    time_offset = ((seconds - _SOLYS_APPROX_DELAY) / 2.0) + _SOLYS_APPROX_DELAY
    t0 = time.time()
    mutex_cont.acquire()
    cont_track.value = True
    while cont_track.value:
        mutex_cont.release()
        logger.debug("Waited {} seconds.\n".format(sleep_time))
        _read_and_move(solys, body_calc, logger, datetime_offset = time_offset)
        tf = time.time()
        tdiff = tf - t0
        sleep_time = (seconds - tdiff)
        if sleep_time > 0:
            time.sleep(sleep_time)
        t0 = time.time()
        mutex_cont.acquire()
    mutex_cont.release()
    solys.close()
    if is_finished:
        is_finished.value = True
    logger.info("Tracking stopped and connection closed.")

@dataclass
class CrossParameters:
    """
    Parameters needed when performing a cross over a Body.

    The offset attributes will define the interval that will be per

    Attributes
    ----------
    azimuth_min_offset : float
        Minimum value of azimuth offset in degrees. Included in the interval.
    azimuth_max_offset : float
        Maximum value of azimuth offset in degrees. Included in the interval.
    azimuth_step : float
        Amount of degrees that are between each azimuth cross point.
    zenith_min_offset : float
        Minimum value of zenith offset in degrees. Included in the interval.
    zenith_max_offset : float
        Maximum value of zenith offset in degrees. Included in the interval.
    zenith_step : float
        Amount of degrees that are between each zenith cross point.
    countdown : float
        Amount of seconds that the Solys2 will wait before the ASD is calculated, logging
        a countdown.
    post_wait : float
        Amount of seconds that the Solys2 will wait after the ASD has been calculated.
    """
    azimuth_min_offset: float
    azimuth_max_offset: float
    azimuth_step: float
    zenith_min_offset: float
    zenith_max_offset: float
    zenith_step: float
    countdown: int
    post_wait: int

def _perform_offsets_body(solys: solys2.Solys2, logger: logging.Logger,
    offsets: List[Tuple[float, float]], body_calc: psc.BodyCalculator, cp: CrossParameters,
    mutex_cont: Lock = None, cont_track: _ContainedBool = None):
    """
    Perform a series of solys-synchronized offsets over a body, for the cross and mesh.

    Parameters
    ----------
    solys : Solys2
        Solys2 instance that will be used to send de messages with.
    logger : logging.Logger
        Logger that will log out the log messages.
    offsets : list of tuple of floats
        List of offsets (az, ze) that will be performed.
    body_calc : BodyCalculator
        Calculator that will be able to calculate the position of the body for a given date.
    cp : CrossParameters
        Parameters needed when performing a cross/mesh over a Body.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track.
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    stoppable: bool = False
    if mutex_cont and cont_track:
        stoppable = True
    sleep_time0 = 0
    sleep_time1 = 0
    solys_delay = _SOLYS_APPROX_DELAY + _SOLYS_DELAY_MARGIN
    dt_offset = cp.countdown + _ASD_DELAY/2.0 + solys_delay
    for offset in offsets:
        if stoppable:
            mutex_cont.acquire()
        if stoppable and not cont_track.value:
            logger.info("Operation stopped manually.")
            break
        if stoppable:
            mutex_cont.release()
        t0 = time.time()
        _read_and_move(solys, body_calc, logger, offset, datetime_offset=dt_offset)
        sleep_time0 = cp.countdown
        tf = time.time()
        diff_td = tf - t0
        wait_time = (dt_offset - _ASD_DELAY/2.0) - (diff_td + sleep_time0)
        if wait_time > 0:
            logger.debug("Sleeping {} seconds".format(wait_time))
            time.sleep(wait_time)
        for i in range(sleep_time0):
            logger.warn("COUNTDOWN:{}".format(sleep_time0-i))
            time.sleep(1)
        logger.warn("COUNTDOWN:0")
        sleep_time1 = cp.post_wait
        logger.debug("Waiting {} seconds (post).".format(sleep_time1))
        if sleep_time1 > 0:
            time.sleep(sleep_time1)

def _cross_body(ip: str, library: psc._BodyLibrary, logger: logging.Logger, cross_params: CrossParameters,
    port: int = 15000, password: str = "solys", is_finished: _ContainedBool = None,
    altitude: float = 0, kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a cross over a body

    Parameters
    ----------
    ip : str
        IP of the solys.
    library : _BodyLibrary
        Body library that will be used to track the body. Moon or Sun.
    logger : logging.Logger
        Logger that will log out the log messages
    cross_params : CrossParameters
        Parameters needed when performing a cross over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    body_calc = _get_body_calculator(solys, library, logger, altitude, kernels_path)
    if library in psc.SunLibrary:
        logger.info("Performing a solar cross. Connected with Solys2.")
    else:
        logger.info("Performing a lunar cross. Connected with Solys2.")
    cp = cross_params
    logger.info("Performing cross with azimuth range [{},{}], steps {}, and zenith range [{},{}],\
steps {}. Countdown of {} and post wait of {} seconds".format(cp.azimuth_min_offset,
        cp.azimuth_max_offset, cp.azimuth_step, cp.zenith_min_offset, cp.zenith_max_offset,
        cp.zenith_step, cp.countdown, cp.post_wait))
    _check_time_solys(solys, logger)
    # Generating the offsets
    offsets: List[Tuple[float, float]] = \
        [(i, 0) for i in np.arange(cp.azimuth_min_offset, cp.azimuth_max_offset + cp.azimuth_step,
            cp.azimuth_step)]
    offsets += [(0, i) for i in np.arange(cp.zenith_min_offset, cp.zenith_max_offset + cp.zenith_step,
        cp.zenith_step)]
    logger.debug("Moving next to the body...")
    _read_and_move(solys, body_calc, logger, (0,0))
    logger.debug("Moved next to the body.")
    logger.info("Starting cross")
    _perform_offsets_body(solys, logger, offsets, body_calc, cp, mutex_cont, cont_track)
    solys.close()
    if is_finished:
        is_finished.value = True
    logger.info("Tracking stopped and connection closed.")

def lunar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a cross over the Moon

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    cross_params : CrossParameters
        Parameters needed when performing a cross over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    library : MoonLibrary
        Lunar library that will be used to track the Moon. By default is ephem.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    return _cross_body(ip, library, logger, cross_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track)

def solar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    library: psc.SunLibrary = psc.SunLibrary.PYSOLAR, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a cross over the Sun

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    cross_params : CrossParameters
        Parameters needed when performing a cross over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    library : SunLibrary
        Solar library that will be used to track the Sun. By default is pysolar.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    return _cross_body(ip, library, logger, cross_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track)

def _mesh_body(ip: str, library: psc._BodyLibrary, logger: logging.Logger, mesh_params: CrossParameters,
    port: int = 15000, password: str = "solys", is_finished: _ContainedBool = None,
    altitude: float = 0, kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a mesh over a body

    Parameters
    ----------
    ip : str
        IP of the solys.
    library : _BodyLibrary
        Body library that will be used to track the body. Moon or Sun.
    logger : logging.Logger
        Logger that will log out the log messages
    mesh_params : CrossParameters
        Parameters needed when performing a mesh over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    body_calc = _get_body_calculator(solys, library, logger, altitude, kernels_path)
    if library in psc.SunLibrary:
        logger.info("Performing a solar mesh. Connected with Solys2.")
    else:
        logger.info("Performing a lunar mesh. Connected with Solys2.")
    cp = mesh_params
    logger.info("Performing mesh with azimuth range [{},{}], steps {}, and zenith range [{},{}],\
steps {}. Countdown of {} and post wait of {} seconds".format(cp.azimuth_min_offset,
        cp.azimuth_max_offset, cp.azimuth_step, cp.zenith_min_offset, cp.zenith_max_offset,
        cp.zenith_step, cp.countdown, cp.post_wait))
    _check_time_solys(solys, logger)
    # Generating the offsets
    offsets: List[Tuple[float, float]] = []
    for i in np.arange(cp.azimuth_min_offset, cp.azimuth_max_offset + cp.azimuth_step,
            cp.azimuth_step):
        for j in np.arange(cp.zenith_min_offset, cp.zenith_max_offset + cp.zenith_step,
                cp.zenith_step):
            offsets.append((i,j))
    logger.debug("Moving next to the body...")
    _read_and_move(solys, body_calc, logger, (0,0))
    logger.debug("Moved next to the body.")
    logger.info("Starting mesh")
    _perform_offsets_body(solys, logger, offsets, body_calc, cp, mutex_cont, cont_track)
    solys.close()
    if is_finished:
        is_finished.value = True
    logger.info("Tracking stopped and connection closed.")

def lunar_mesh(ip: str, logger: logging.Logger, mesh_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a mesh over the Moon

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    mesh_params : CrossParameters
        Parameters needed when performing a mesh over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    library : MoonLibrary
        Lunar library that will be used to track the Moon. By default is ephem.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    return _mesh_body(ip, library, logger, mesh_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track)

def solar_mesh(ip: str, logger: logging.Logger, mesh_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    library: psc.SunLibrary = psc.SunLibrary.PYSOLAR, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _ContainedBool = None):
    """
    Perform a mesh over the Sun

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    mesh_params : CrossParameters
        Parameters needed when performing a mesh over a Body.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    library : SunLibrary
        Solar library that will be used to track the Sun. By default is pysolar.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    """
    return _mesh_body(ip, library, logger, mesh_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track)

def black_moon(ip: str, logger: logging.Logger, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None,
    library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON, altitude: float = 0,
    kernels_path: str = "./kernels"):
    """
    Perform a black for the moon. Point to a position where the moon is not present so the noise
    can be calculated. (Opposite azimuth and zenith = 45)

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    library : MoonLibrary
        Lunar library that will be used to track the Moon. By default is ephem.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    """
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    body_calc = _get_body_calculator(solys, library, logger, altitude, kernels_path)
    _check_time_solys(solys, logger)

    dt = datetime.datetime.now(datetime.timezone.utc)
    az, ze = body_calc.get_position(dt)
    prev_az, prev_ze, _ = solys.get_current_position()
    qsi, total_intens, _ = solys.get_sun_intensity()
    az_offset = 180
    if az > 180:
        az_offset *= -1
    ze_offset = 45-ze
    logger.info("Performing a lunar black of ({},{}) degrees. Connected with Solys2.".format(
        az_offset, ze_offset))
    _read_and_move(solys, body_calc, logger, (az_offset, ze_offset))
    dt = datetime.datetime.now(datetime.timezone.utc)
    prev_az, prev_ze, _ = solys.get_current_position()
    qsi, total_intens, _ = solys.get_sun_intensity()
    logger.info("UTC Datetime: {}".format(dt))
    logger.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
    logger.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
    solys.close()
    if is_finished:
        is_finished.value = True
    logger.info("Black finished and connection closed.")

def _gen_random_str(len: int) -> str:
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

class _BodyTracker:
    """_BodyTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the selected body.

    Attributes
    ----------
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    logger : logging.Logger
        Logger that will log out the log messages.
    thread : Thread
        Thread that will execute the tracking function.
    _is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it will be True
        when the thread has successfully ended execution.
    """
    def __init__(self, ip: str, seconds: float, library: psc._BodyLibrary, port: int = 15000,
        password: str = "solys", log: bool = False, logfile: str = "",
        altitude: float = 0, kernels_path: str = "./kernels",
        extra_log_handlers: List[logging.Handler] = []):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each message of change of position of zenith and
            azimuth.
        library : _BodyLibrary
            Body library that will be used to track the body. Moon or Sun.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        extra_log_handlers : list of logging.Handler
            Custom handlers which the log will also log to.
        """
        self.mutex_cont = Lock()
        self.cont_track = _ContainedBool(True)
        self._configure_logger(log, logfile, extra_log_handlers)
        self._is_finished = _ContainedBool(False)
        # Create thread
        self.thread = Thread(target = _track_body, args = (ip, seconds, library, self.mutex_cont,
            self.cont_track, self.logger, port, password, self._is_finished, altitude, kernels_path))
        self.thread.start()
    
    def _configure_logger(self, log: bool, logfile: str, extra_log_handlers: List[logging.Handler]):
        """Configure the logging output
        
        Shell logging at warning level and file logger at debug level if log is True.

        Parameters
        ----------
        log : bool
            True if some logging is required. Otherwise silent except for warnings and errors.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in stderr.
        extra_log_handlers : list of logging.Handler
            Custom handlers which the log will also log to.
        """
        randstr = _gen_random_str(20)
        logging.basicConfig(level=logging.WARNING)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.WARNING)
        self.logger = logging.getLogger('autotrack._BodyTracker-{}'.format(randstr))
        for hand in extra_log_handlers:
            self.logger.addHandler(hand)
        if logfile != "":
            log_handler = logging.FileHandler(logfile, mode='a')
            log_handler.setFormatter(logging.Formatter('%(levelname)s:%(message)s'))
            self.logger.addHandler(log_handler)
            if log:
                self.logger.setLevel(logging.DEBUG)
        elif log:
            logging.getLogger().setLevel(logging.DEBUG)
            for handler in logging.getLogger().handlers:
                handler.setLevel(logging.DEBUG)

    def stop_tracking(self):
        """
        Stop the tracking of the tracked body. The connection with the Solys2 will be closed and
        the thread stopped.

        It won't be stopped immediately, at most there will be a delay of __init__ "seconds"
        parameter.
        """
        self.mutex_cont.acquire()
        self.cont_track.value = False
        self.mutex_cont.release()
        handlers = self.logger.handlers
        for handler in handlers:
            handler.close()
            self.logger.removeHandler(handler)
    
    def is_finished(self) -> bool:
        """
        Check if the thread has successfully finished executing. This requires having had called
        stop_tracking() and waited the needed seconds to be True.

        Returns
        -------
        has_finished : bool
            True if it has finished successfully.
        """
        return self._is_finished.value

class MoonTracker(_BodyTracker):
    """MoonTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the Moon.
    """
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = "", library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON,
        altitude: float = 0, kernels_path: str = "./kernels",
        extra_log_handlers: List[logging.Handler] = []):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each message of change of position of zenith and
            azimuth.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        library : MoonLibrary
            Lunar library that will be used to track the Moon. By default is ephem.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        extra_log_handlers : list of logging.Handler
            Custom handlers which the log will also log to.
        """
        super().__init__(ip, seconds, library, port, password, log, logfile, altitude,
            kernels_path, extra_log_handlers)

class SunTracker(_BodyTracker):
    """SunTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the Sun.
    """
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = "", library: psc.SunLibrary = psc.SunLibrary.PYSOLAR,
        altitude: float = 0, kernels_path: str = "./kernels",
        extra_log_handlers: List[logging.Handler] = []):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each message of change of position of zenith and
            azimuth.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        library : SunLibrary
            Solar library that will be used to track the Sun. By default is pysolar.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        extra_log_handlers : list of logging.Handler
            Custom handlers which the log will also log to.
        """
        super().__init__(ip, seconds, library, port, password, log, logfile, altitude,
            kernels_path, extra_log_handlers)
