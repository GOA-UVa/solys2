from typing import Tuple
import time
import sys
import datetime

import pylunar
from pysolar import solar

from . import response
from . import solys2

_TIME_DELAY = 0.001

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

def track_moon(ip: str, seconds: float, port: int = 15000, password: str = "solys", log: bool = False):
    """
    Track the moon

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
    """
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            print("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)),
                file=sys.stderr)
        else:
            print("ERROR obtaining coordinates. Unknown error.", file=sys.stderr)
    mi = pylunar.MoonInfo(_decdeg2dms(lat), _decdeg2dms(lon))
    if log: print("Tracking sun. Connected with Solys2.")
    while True:
        dt = datetime.datetime.now(datetime.timezone.utc)
        t0 = time.time()
        mi.update(dt)
        az = mi.azimuth()
        ze = 90-mi.altitude()
        try:
            prev_az, prev_ze, _ = solys.get_current_position()
            qsi, total_intens, _ = solys.get_sun_intensity()
            solys.set_azimuth(az)
            solys.set_zenith(ze)
            if log:
                print("Datetime: {}".format(dt))
                print("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
                print("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
                print("Sent positions: Azimuth: {}. Zenith: {}.".format(az, ze))
                print()
            while True:
                q0, q1, _ = solys.get_queue_status()
                queue = q0 + q1
                if queue == 0:
                    break
                if log: print("Queue size {}. Sleeping 1 sec...".format(queue))
                time.sleep(1)
        except solys2.SolysException as e:
            print("Error at datetime: {}".format(dt), file=sys.stderr)
            print(e, file=sys.stderr)
        tf = time.time()
        tdiff = tf - t0
        sleep_time = (seconds - tdiff) - _TIME_DELAY
        if sleep_time > 0:
            time.sleep(sleep_time)

def track_sun(ip: str, seconds: float, port: int = 15000, password: str = "solys", log: bool = False):
    """
    Track the sun

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
    """
    solys = solys2.Solys2(ip, port, password)
    solys.set_power_save(False)
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            print("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)),
                file=sys.stderr)
        else:
            print("ERROR obtaining coordinates. Unknown error.", file=sys.stderr)
    if log: print("Tracking sun. Connected with Solys2.")
    while True:
        dt = datetime.datetime.now(datetime.timezone.utc)
        t0 = time.time()
        az = solar.get_azimuth(lat, lon, dt)
        ze = 90-solar.get_altitude(lat, lon, dt)
        try:
            prev_az, prev_ze, _ = solys.get_current_position()
            qsi, total_intens, _ = solys.get_sun_intensity()
            solys.set_azimuth(az)
            solys.set_zenith(ze)
            if log:
                print("Datetime: {}".format(dt))
                print("Current Position: Azimuth: {}, Zenith: {}.".format(prev_az, prev_ze))
                print("Quadrants: {}. Total intensity: {}.".format(qsi, total_intens))
                print("Sent positions: Azimuth: {}. Zenith: {}.".format(az, ze))
                print()
            while True:
                q0, q1, _ = solys.get_queue_status()
                queue = q0 + q1
                if queue == 0:
                    break
                if log: print("Queue size {}. Sleeping 1 sec...".format(queue))
                time.sleep(1)
        except solys2.SolysException as e:
            print("Error at datetime: {}".format(dt), file=sys.stderr)
            print(e, file=sys.stderr)
        tf = time.time()
        tdiff = tf - t0
        sleep_time = (seconds - tdiff) - _TIME_DELAY
        if sleep_time > 0:
            time.sleep(sleep_time)
