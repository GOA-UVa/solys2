#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone
from typing import Tuple
import math

from pysolar import solar
import ephem

def _decdeg2dms(dd: float) -> Tuple[int, int, int]:
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return int(deg), int(mnt), int(sec)

def datetime_range(start, end, delta):
    current = start
    while current < end:
        yield current
        current += delta

def print_result(az, ze):
    print("{},{}".format(az, ze))

def print_pysolar(dts_str, lat, lon, alt):
    for dt_s in dts_str:
        dt = datetime.strptime(dt_s, '%Y-%m-%d %H:%M:%S %z')
        az = solar.get_azimuth(lat, lon, dt)
        ze = 90 - solar.get_altitude(lat, lon, dt)
        print_result(az, ze)
    return az, ze

def print_ephem(dts_str, lat, lon, alt):
    obs = ephem.Observer()
    obs.lat = math.radians(lat)
    obs.long = math.radians(lon)
    s = ephem.Sun()
    for dt_s in dts_str:
        dt = datetime.strptime(dt_s, '%Y-%m-%d %H:%M:%S %z')
        obs.date = dt
        s.compute(obs)
        az = math.degrees(s.az)
        ze = 90 - math.degrees(s.alt)
        print_result(az, ze)


def main():
    dts = [dt.strftime('%Y-%m-%d %H:%M:%S %z') for dt in 
       datetime_range(datetime(2022, 4, 18, 0, tzinfo=timezone.utc), datetime(2022, 4, 18, 23, 31, tzinfo=timezone.utc), 
       timedelta(minutes=30))]
    # izana
    lat = 28.309283
    lon = -16.499143
    alt = 2400
    print_ephem(dts, lat, lon, alt)

if __name__ == "__main__":
    main()
