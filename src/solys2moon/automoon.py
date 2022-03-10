from typing import Tuple
import time
import sys
import datetime

import pylunar

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

def track_moon(ip: str, seconds: float, port: int = 15000, password: str = "solys"):
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
    """
    solys = solys2.Solys2(ip, port, password)
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            print("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)),
                file=sys.stderr)
        else:
            print("ERROR obtaining coordinates. Unknown error.", file=sys.stderr)
    mi = pylunar.MoonInfo(_decdeg2dms(lat), _decdeg2dms(lon))
    while True:
        dt = datetime.datetime.utcnow()
        t0 = time.time()
        mi.update(dt)
        az = mi.azimuth()
        ze = 90-mi.altitude()
        solys.set_azimuth(az)
        solys.set_zenith(ze)
        qsi, intens, output = solys.get_sun_intensity()
        print("Azimuth: {}. Zenith: {}. Quadrants: {}".format(az, ze, qsi))
        tf = time.time()
        tdiff = tf - t0
        sleep_time = seconds - tdiff
        if sleep_time > 0:
            time.sleep(sleep_time)
