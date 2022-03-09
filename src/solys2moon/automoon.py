from typing import Tuple
import time
import sys
import datetime

import ephem

from . import response
from . import solys2

def track_moon(ip: str, port: int, seconds: float, password: str = "solys"):
    solys = solys2.Solys2(ip, port, password)
    lat, lon, _, ll_com = solys.get_location_pressure()
    if ll_com.out != response.OutCode.ANSWERED:
        if ll_com.err != None:
            print("ERROR obtaining coordinates: {}".format(solys2.translate_error(ll_com.err)),
                file=sys.stderr)
        else:
            print("ERROR obtaining coordinates. Unknown error.", file=sys.stderr)
    home = ephem.Observer()
    moon = ephem.Moon()
    home.lat, home.lon = lat, lon
    while True:
        home.date = datetime.datetime.utctimetuple()
        t0 = time.time()
        moon.compute(home)
        az = moon.az
        ze = moon.ze
        solys.set_azimuth(az)
        solys.set_zenith(ze)
        tf = time.time()
        tdiff = tf - t0
        time.sleep(seconds - tdiff)
