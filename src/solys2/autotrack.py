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
from typing import Tuple, List, Callable, Union
import time
import datetime
import logging
from threading import Thread, Lock
import string
import random

"""___Third-Party Modules___"""
import pylunar
from pysolar import solar
import numpy as np

"""___Solys2 Modules___"""
from . import response
from . import solys2

"""___Authorship___"""
__author__ = "Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, and Ramiro González Catón"
__created__ = "2022/03/10"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

def _decdeg2dms(dd: float) -> Tuple[int, int, int]:
    """
    Converts decimal degrees to degree, minute, second

    Parameters
    ----------
    dd : float
        Value to be transformed from decimal degrees.

    Returns
    -------
    deg : int
        Degrees.
    mnt : int
        Minutes.
    sec : int
        Seconds.
    """
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return int(deg), int(mnt), int(sec)

class _TrackBody(Enum):
    """
    Enum that represents the celestial body that the Solys will track.
    
    SUN: The sun.
    MOON: The moon.
    """
    SUN = 0
    MOON = 1

def _get_moon_position(mi: pylunar.MoonInfo, dt: datetime.datetime) -> Tuple[float, float]:
    """
    Obtain lunar azimuth and zenith.

    Parameters
    ----------
    mi : pylunar.MoonInfo
        MoonInfo with the geographical coordinates of the observer already set, that will be used
        to calculate the lunar position.
    dt : datetime.datetime
        Datetime at which the lunar position will be calculated.

    Returns
    -------
    azimuth : float
        Lunar azimuth calculated.
    zenith : float
        Lunar zenith calculated.
    """
    mi.update(dt)
    az = mi.azimuth()
    ze = 90-mi.altitude()
    return az, ze

def _get_sun_position(coords: Tuple[float, float], dt: datetime.datetime) -> Tuple[float, float]:
    """
    Obtain solar azimuth and zenith.

    Parameters
    ----------
    coords : tuple of two floats.
        (latitude, longitude)
        Geographical coordinates of the observer that will be used to calculate
        the solar position.
    dt : datetime.datetime
        Datetime at which the solar position will be calculated.

    Returns
    -------
    azimuth : float
        Solar azimuth calculated.
    zenith : float
        Solar zenith calculated.
    """
    lat = coords[0]
    lon = coords[1]
    az = solar.get_azimuth(lat, lon, dt)
    ze = 90-solar.get_altitude(lat, lon, dt)
    return az, ze

@dataclass
class _ContainedBool:
    """
    Dataclass that acts as a container of a boolean variable so it gets passed as a
    reference.
    """
    value : bool

def _get_position_function(solys: solys2.Solys2, body: _TrackBody, logger: logging.Logger
    ) -> Tuple[Callable[[Union[Tuple[float, float], pylunar.MoonInfo], datetime.datetime],
    Tuple[float, float]], Union[Tuple[float, float], pylunar.MoonInfo]]:
    """
    Parameters
    ----------
    solys : solys2.Solys2
        Solys2 instance that will be used to send de messages with.
    body : _TrackBody
        Body that will be performed the cross on. Moon or Sun.
    logger : logging.Logger
        Logger that will log out the log messages

    Returns
    -------
    get_position : function
        Function that will return the zenith and azimuth of the selected body.
    mi_params : tuple of two floats (lat, lon) or MoonInfo
        The parameter of the returned function get_position.
    """
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            logger.error("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)))
        else:
            logger.error("ERROR obtaining coordinates. Unknown error.")
    if body == _TrackBody.SUN:
        get_position = _get_sun_position
        mi_coords = (lat, lon)
    else:
        get_position = _get_moon_position
        mi_coords = pylunar.MoonInfo(_decdeg2dms(lat), _decdeg2dms(lon))
    return get_position, mi_coords

def _track_body(ip: str, seconds: float, body: _TrackBody, mutex_cont: Lock,
    cont_track: _ContainedBool, logger: logging.Logger, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None):
    """
    Track a celestial body

    Parameters
    ----------
    ip : str
        IP of the solys.
    seconds : float
        Amount of seconds waited between each change of position of zenith and azimuth.
    body : _TrackBody
        Body that will be tracked. Moon or Sun.
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

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    get_position, mi_coords = _get_position_function(solys, body, logger)
    if body == _TrackBody.SUN:
        logger.info("Tracking sun. Connected with Solys2.")
    else:
        logger.info("Tracking moon. Connected with Solys2.")
    # Start tracking in a loop
    sleep_time = 0
    t0 = time.time()
    mutex_cont.acquire()
    cont_track.value = True
    while cont_track.value:
        mutex_cont.release()
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.debug("Waited {} seconds.\n".format(sleep_time))
        az, ze = get_position(mi_coords, dt)
        az = min(360, az)
        ze = min(90, ze)
        try:
            prev_az, prev_ze, _ = solys.get_current_position()
            qsi, total_intens, _ = solys.get_sun_intensity()
            solys.set_azimuth(az)
            solys.set_zenith(ze)
            logger.info("Datetime: {}".format(dt))
            logger.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
            logger.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
            logger.info("Sent positions: Azimuth: {}. Zenith: {}.\n".format(az, ze))
            while True:
                # get_queue_status is not that reliable
                prev_az, prev_ze, _ = solys.get_current_position()
                pos_dif = abs(az - prev_az) +  abs(ze - prev_ze)
                if pos_dif <= 0.01:
                    break
                logger.debug("Position difference too large: {}. Azimuth: {} vs {}. Zenith: {} vs \
{}.".format(pos_dif, az, prev_az, ze, prev_ze))
                time.sleep(1)
        except solys2.SolysException as e:
            logger.error("Error at datetime: {}".format(dt))
            logger.error(e)
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
    measure_seconds : float
        Amount of seconds that the Solys2 will wait on each cross point.
    azimuth_min_offset : float
        Minimum value of azimuth offset in degrees. Included in the interval.
    azimuth_max_offset : float
        Maximum value of azimuth offset in degrees. Not included in the interval.
    azimuth_step : float
        Amount of degrees that are between each azimuth cross point.
    zenith_min_offset : float
        Minimum value of zenith offset in degrees. Included in the interval.
    zenith_max_offset : float
        Maximum value of zenith offset in degrees. Not included in the interval.
    zenith_step : float
        Amount of degrees that are between each zenith cross point.
    """
    measure_seconds: float
    azimuth_min_offset: float
    azimuth_max_offset: float
    azimuth_step: float
    zenith_min_offset: float
    zenith_max_offset: float
    zenith_step: float

def _cross_body(ip: str, body: _TrackBody, logger: logging.Logger, cross_params: CrossParameters,
    port: int = 15000, password: str = "solys", is_finished: _ContainedBool = None):
    """
    Perform a cross over a body

    Parameters
    ----------
    ip : str
        IP of the solys.
    body : _TrackBody
        Body that where the cross will be performed on. Moon or Sun.
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
    """
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    get_position, mi_coords = _get_position_function(solys, body, logger)
    if body == _TrackBody.SUN:
        logger.info("Performing a solar cross. Connected with Solys2.")
    else:
        logger.info("Performing a lunar cross. Connected with Solys2.")
    sleep_time = 0
    cp = cross_params
    logger.info("Performing cross waiting {} seconds, with azimuth range [{},{}), steps {}, and \
zenith range [{},{}), steps {}.".format(cp.measure_seconds, cp.azimuth_min_offset,
        cp.azimuth_max_offset, cp.azimuth_step, cp.zenith_min_offset, cp.zenith_max_offset,
        cp.zenith_step))
    offsets = [(i, 0) for i in np.arange(cp.azimuth_min_offset, cp.azimuth_max_offset, cp.azimuth_step)]
    offsets += [(0, i) for i in np.arange(cp.zenith_min_offset, cp.zenith_max_offset, cp.zenith_step)]
    seconds = cp.measure_seconds
    t0 = time.time()
    for offset in offsets:
        dt = datetime.datetime.now(datetime.timezone.utc)
        logger.debug("Waited {} seconds.\n".format(sleep_time))
        az, ze = get_position(mi_coords, dt)
        new_az = min(360, az + offset[0])
        new_ze = min(90, ze + offset[1])
        try:
            prev_az, prev_ze, _ = solys.get_current_position()
            qsi, total_intens, _ = solys.get_sun_intensity()
            solys.set_azimuth(new_az)
            solys.set_zenith(new_ze)
            logger.info("Datetime: {}".format(dt))
            logger.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
            logger.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
            logger.info("Sent positions: Azimuth: {} + {}. Zenith: {} + {}.\n".format(az, offset[0],
                ze, offset[1]))
            while True:
                # get_queue_status is not that reliable
                prev_az, prev_ze, _ = solys.get_current_position()
                pos_dif = abs(new_az - prev_az) +  abs(new_ze - prev_ze)
                if pos_dif <= 0.01:
                    break
                logger.debug("Position difference too large: {}. Azimuth: {} vs {}. Zenith: {} vs \
{}.".format(pos_dif, new_az, prev_az, new_ze, prev_ze))
                time.sleep(1)
        except solys2.SolysException as e:
            logger.error("Error at datetime: {}".format(dt))
            logger.error(e)
        tf = time.time()
        tdiff = tf - t0
        sleep_time = seconds
        if sleep_time > 0:
            time.sleep(sleep_time)
        t0 = time.time()
    solys.close()
    if is_finished:
        is_finished.value = True
    logger.info("Tracking stopped and connection closed.")

def lunar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None):
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
    """
    return _cross_body(ip, _TrackBody.MOON, logger, cross_params, port, password, is_finished)

def solar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None):
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
    """
    return _cross_body(ip, _TrackBody.SUN, logger, cross_params, port, password, is_finished)

def black_moon(ip: str, logger: logging.Logger, offset: float = 15, port: int = 15000,
    password: str = "solys", is_finished: _ContainedBool = None):
    """
    Perform a black for the moon. Point to a position where the moon is not present so the noise
    can be calculated.

    Parameters
    ----------
    ip : str
        IP of the solys.
    logger : logging.Logger
        Logger that will log out the log messages
    offset : float
        Amount of degrees that will differ from the lunar position when this function is executed.
        By default is 15.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    is_finished : _ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    """
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    get_position, mi_coords = _get_position_function(solys, _TrackBody.MOON, logger)
    logger.info("Performing a lunar black of {} degrees. Connected with Solys2.".format(offset))

    dt = datetime.datetime.now(datetime.timezone.utc)
    az, ze = get_position(mi_coords, dt)
    prev_az, prev_ze, _ = solys.get_current_position()
    qsi, total_intens, _ = solys.get_sun_intensity()
    az_offset = ze_offset = offset
    if az > 180:
        az_offset *= -1
    if ze > 45:
        ze_offset *= -1
    new_az = min(360, az + az_offset)
    new_ze = min(90, ze + ze_offset)
    solys.set_azimuth(new_az)
    solys.set_zenith(new_ze)
    logger.info("Datetime: {}".format(dt))
    logger.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
    logger.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
    logger.info("Sent positions: Azimuth: {} + {}. Zenith: {} + {}.\n".format(az, az_offset,
        ze, ze_offset))
    while True:
        # get_queue_status is not that reliable
        prev_az, prev_ze, _ = solys.get_current_position()
        pos_dif = abs(new_az - prev_az) +  abs(new_ze - prev_ze)
        if pos_dif <= 0.01:
            break
        logger.debug("Position difference too large: {}. Azimuth: {} vs {}. Zenith: {} vs \
{}.".format(pos_dif, new_az, prev_az, new_ze, prev_ze))
        logger.debug("Sleeping 1 sec...")
        time.sleep(1)
    dt = datetime.datetime.now(datetime.timezone.utc)
    prev_az, prev_ze, _ = solys.get_current_position()
    qsi, total_intens, _ = solys.get_sun_intensity()
    logger.info("Datetime: {}".format(dt))
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
    def __init__(self, ip: str, seconds: float, body: _TrackBody, port: int = 15000,
        password: str = "solys", log: bool = False, logfile: str = ""):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each change of position of zenith and azimuth.
        body : _TrackBody
            Body that will be tracked. Moon or Sun.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        """
        self.mutex_cont = Lock()
        self.cont_track = _ContainedBool(True)
        self._configure_logger(log, logfile)
        self._is_finished = _ContainedBool(False)
        # Create thread
        self.thread = Thread(target = _track_body, args = (ip, seconds, body, self.mutex_cont,
            self.cont_track, self.logger, port, password, self._is_finished))
        self.thread.start()
    
    def _configure_logger(self, log: bool, logfile: str):
        """Configure the logging output
        
        Shell logging at warning level and file logger at debug level if log is True.

        Parameters
        ----------
        log : bool
            True if some logging is required. Otherwise silent except for warnings and errors.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in stderr.
        """
        randstr = _gen_random_str(20)
        logging.basicConfig(level=logging.WARNING)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.WARNING)
        self.logger = logging.getLogger('autotrack._BodyTracker-{}'.format(randstr))
        if logfile != "":
            log_handler = logging.FileHandler(logfile, mode='w')
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
        log: bool = False, logfile: str = ""):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each change of position of zenith and azimuth.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        """
        super().__init__(ip, seconds, _TrackBody.MOON, port, password, log, logfile)

class SunTracker(_BodyTracker):
    """SunTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the Sun.
    """
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = ""):
        """
        Parameters
        ----------
        ip : str
            IP of the solys.
        seconds : float
            Amount of seconds waited between each change of position of zenith and azimuth.
        port : int
            Access port. By default 15000.
        password : str
            Ethernet user password. By default is "solys".
        log : bool
            True if some logging is required. Otherwise silent. Default is silent.
        logfile : str
            Path of the file where the logging will be stored. In case that it's not used, it will be
            printed in standard output error.
        """
        super().__init__(ip, seconds, _TrackBody.SUN, port, password, log, logfile)
