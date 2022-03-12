from dataclasses import dataclass
from enum import Enum
from typing import Tuple, List
import time
import datetime
import logging
from threading import Thread, Lock

import pylunar
from pysolar import solar

from . import response
from . import solys2

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
    value : bool

def _track_body(ip: str, seconds: float, body: _TrackBody, mutex_cont: Lock, cont_track : _ContainedBool,
    port: int = 15000, password: str = "solys", log: bool = False, logfile: str = ""):
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
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    log : bool
        True if some logging is required. Otherwise silent. Default is silent.
    logfile : str
        Path of the file where the logging will be stored. In case that it's not used, it will be
        printed in standard output error.

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    if log:
        logging.basicConfig(level=logging.DEBUG)
        if logfile != "":
            logging.basicConfig(filename=logfile, filemode='w')
    # Connect with the Solys2 and set the initial configuration.
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            logging.error("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)))
        else:
            logging.error("ERROR obtaining coordinates. Unknown error.")
    if body == _TrackBody.SUN:
        logging.info("Tracking sun. Connected with Solys2.")
        get_position = _get_sun_position
        mi_coords = (lat, lon)
    else:
        logging.info("Tracking moon. Connected with Solys2.")
        get_position = _get_moon_position
        mi_coords = pylunar.MoonInfo(_decdeg2dms(lat), _decdeg2dms(lon))

    # Start tracking in a loop
    sleep_time = 0
    t0 = time.time()
    mutex_cont.acquire()
    cont_track.value = True
    while cont_track.value:
        mutex_cont.release()
        dt = datetime.datetime.now(datetime.timezone.utc)
        logging.debug("Waited {} seconds.".format(sleep_time))
        az, ze = get_position(mi_coords, dt)
        try:
            prev_az, prev_ze, _ = solys.get_current_position()
            qsi, total_intens, _ = solys.get_sun_intensity()
            solys.set_azimuth(az)
            solys.set_zenith(ze)
            logging.info("Datetime: {}".format(dt))
            logging.info("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
            logging.info("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
            logging.info("Sent positions: Azimuth: {}. Zenith: {}.".format(az, ze))
            logging.info()
            while True:
                q0, q1, _ = solys.get_queue_status()
                queue = q0 + q1
                if queue == 0:
                    break
                logging.debug("Queue size {}. Sleeping 1 sec...".format(queue))
                time.sleep(1)
        except solys2.SolysException as e:
            logging.error("Error at datetime: {}".format(dt))
            logging.error(e)
        tf = time.time()
        tdiff = tf - t0
        sleep_time = (seconds - tdiff)
        if sleep_time > 0:
            time.sleep(sleep_time)
        t0 = time.time()
        mutex_cont.acquire()
    mutex_cont.release()
    solys.close()
    logging.info("Tracking stopped and connection closed.")

def _track_moon(ip: str, seconds: float, mutex_cont: Lock, cont_track : _ContainedBool,
    port: int = 15000, password: str = "solys", log: bool = False, logfile: str = ""):
    """
    Track the moon

    Parameters
    ----------
    ip : str
        IP of the solys.
    seconds : float
        Amount of seconds waited between each change of position of zenith and azimuth.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    log : bool
        True if some logging is required. Otherwise silent. Default is silent.
    logfile : str
        Path of the file where the logging will be stored. In case that it's not used, it will be
        printed in standard output error.

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    return _track_body(ip, seconds, _TrackBody.MOON, mutex_cont, cont_track, port, password,
        log, logfile)

def _track_sun(ip: str, seconds: float, mutex_cont: Lock, cont_track : _ContainedBool,
    port: int = 15000, password: str = "solys", log: bool = False, logfile: str = ""):
    """
    Track the sun

    Parameters
    ----------
    ip : str
        IP of the solys.
    seconds : float
        Amount of seconds waited between each change of position of zenith and azimuth.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : _ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    port : int
        Access port. By default 15000.
    password : str
        Ethernet user password. By default is "solys".
    log : bool
        True if some logging is required. Otherwise silent except for errors. Default is silent.
    logfile : str
        Path of the file where the logging will be stored. In case that it's not used, it will be
        printed in standard output error.

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    return _track_body(ip, seconds, _TrackBody.SUN, mutex_cont, cont_track, port, password,
        log, logfile)

class _BodyTracker:
    def __init__(self, ip: str, seconds: float, body: _TrackBody, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = ""):
        """"""
        self.mutex_cont = Lock()
        self.cont_track = _ContainedBool(True)
        self.thread = Thread(target = _track_body, args = (ip, seconds, body, self.mutex_cont,
            self.cont_track, port, password, log, logfile))
        self.thread.start()
    
    def stop_tracking(self):
        self.mutex_cont.acquire()
        self.cont_track.value = False
        self.mutex_cont.release()

class MoonTracker(_BodyTracker):
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = ""):
        """"""
        super().__init__(ip, seconds, _TrackBody.MOON, port, password, log, logfile)

class SunTracker(_BodyTracker):
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        log: bool = False, logfile: str = ""):
        """"""
        super().__init__(ip, seconds, _TrackBody.SUN, port, password, log, logfile)
