"""Position Calc

Module that contains the objects that allow the calculation of the position of the moon
and the sun using different libraries, like ephem, pysolar or SPICE (spicedmoon and spicedsun).

It exports the following classes:
    * MoonLibrary : Enum that contains all available moon calculation libraries.
    * SunLibrary : Enum that contains all available sun calculation libraries.
    * BodyCalculator : Abstract class of an object that calculates a celestial body's zenith \
and azimuth for a given location at a given datetime.
    * MoonCalculator : Abstract class of an object that calculates the lunar zenith and \
azimuth for a given location at a given datetime.
    * SunCalculator : Abstract class of an object that calculates the solar zenith and \
azimuth for a given location at a given datetime.
    * PylunarMoonCalc : Object that calculates the lunar zenith and azimuth for a given \
location at a given datetime, using pylunar library.
    * EphemMoonCalc : Object that calculates the lunar zenith and azimuth for a given location \
at a given datetime, using ephem library.
    * SpiceMoonCalc : Object that calculates the lunar zenith and azimuth for a given location \
at a given datetime, using spicedmoon (SPICE) library.
    * PysolarSunCalc : Object that calculates the solar zenith and azimuth for a given location \
at a given datetime, using pysolar library.
    * EphemSunCalc : Object that calculates the solar zenith and azimuth for a given location \
at a given datetime, using ephem library.
    * SpiceSunCalc : Object that calculates the solar zenith and azimuth for a given location \
at a given datetime, using spicedsun (SPICE) library.
"""

"""___Built-In Modules___"""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import logging
from typing import Tuple
import math

"""___Third-Party Modules___"""
import pylunar
from pysolar import solar
import ephem
import spicedmoon
import spicedsun

"""___Solys2 Modules___"""
# import here

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/03/16"
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

class BodyCalculator(ABC):
    """
    Object that calculates a celestial body's zenith and azimuth for a given location
    at a given datetime.
    """

    @abstractmethod
    def __init__(self, lat: float, lon: float):
        """
        Parameters
        ----------
        lat : float
            Latitude of the location for which to calculate the celestial body's
            zenith and azimuth
        lon : float
            Longitude of the location for which to calculate the celestial body's
            zenith and azimuth
        """
        pass

    @abstractmethod
    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain body's azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the body's position will be calculated.

        Returns
        -------
        azimuth : float
            Body's azimuth calculated.
        zenith : float
            Body's zenith calculated.
        """
        pass

class _BodyLibrary(Enum):
    EPHEM_MOON = 0
    SPICEDMOON = 1
    PYLUNAR = 2
    SPICEDMOONSAFE = 3
    PYSOLAR = 100
    EPHEM_SUN = 101
    SPICEDSUN = 102
    SPICEDSUNSAFE = 103

class MoonLibrary(Enum):
    """
    Enum that represents the library that can be used for calculating the lunar position.

    EPHEM: Library that is very close to the correct data from SPICE, and doesn't require the presence of extra
files. This is the default one, although the error might be too big for some users.
    SPICEDMOON: Library that uses NASA's data. The most exact one, but requires the presence of kernels files.
    PYLUNAR: Library that is very incorrect for some punctual data. Usage not recommended.
    SPICEDMOONSAFE: Like SPICEDMOON, but in case that it fails (which is very rare but possible) it uses EPHEM
library as a backup library instead of raising an Exception.
    """
    EPHEM_MOON = 0
    SPICEDMOON = 1
    PYLUNAR = 2
    SPICEDMOONSAFE = 3

class SunLibrary(Enum):
    """
    Enum that represents the library that can be used for calculating the solar position.
    
    PYSOLAR: Library that is very close to the correct data from SPICE, and doesn't require the presence of extra
files. This is the default one. The errors are related to the sunrise and sunset.
    EPHEM: Library that is also close to the correct data from SPICE, but not as much as pysolar. The errors
are related to the sunrise and sunset.
    SPICEDSUN: Library that uses NASA's data. The most exact one, but requires the presence of kernels files.
    SPICEDSUNSAFE: Like SPICEDSUN, but in case that it fails (which is very rare but possible) it uses PYSOLAR
library as a backup library instead of raising an Exception.
    """
    PYSOLAR = 100
    EPHEM_SUN = 101
    SPICEDSUN = 102
    SPICEDSUNSAFE = 103

class MoonCalculator(BodyCalculator):
    """
    Object that calculates the lunar zenith and azimuth for a given location
    at a given datetime.
    """

    @abstractmethod
    def __init__(self, lat: float, lon: float):
        pass

    @abstractmethod
    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain lunar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the lunar position will be calculated.

        Returns
        -------
        azimuth : float
            Lunar azimuth calculated.
        zenith : float
            Lunar zenith calculated.
        """
        pass

class SunCalculator(BodyCalculator):
    """
    Object that calculates the solar zenith and azimuth for a given location
    at a given datetime.
    """

    @abstractmethod
    def __init__(self, lat: float, lon: float):
        pass

    @abstractmethod
    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain solar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the solar position will be calculated.

        Returns
        -------
        azimuth : float
            Solar azimuth calculated.
        zenith : float
            Solar zenith calculated.
        """
        pass

class PylunarMoonCalc(MoonCalculator):
    """
    Object that calculates the lunar zenith and azimuth for a given location
    at a given datetime, using pylunar library.
    """

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self.mi = pylunar.MoonInfo(_decdeg2dms(lat), _decdeg2dms(lon))

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain lunar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the lunar position will be calculated.

        Returns
        -------
        azimuth : float
            Lunar azimuth calculated.
        zenith : float
            Lunar zenith calculated.
        """
        self.mi.update(dt)
        az = self.mi.azimuth()
        ze = 90 - self.mi.altitude()
        return az, ze

class EphemMoonCalc(MoonCalculator):
    """
    Object that calculates the lunar zenith and azimuth for a given location
    at a given datetime, using ephem library.
    """

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self.obs = ephem.Observer()
        self.obs.lat = math.radians(lat)
        self.obs.long = math.radians(lon)
        self.m = ephem.Moon()

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain lunar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the lunar position will be calculated.

        Returns
        -------
        azimuth : float
            Lunar azimuth calculated.
        zenith : float
            Lunar zenith calculated.
        """
        self.obs.date = dt
        self.m.compute(self.obs)
        az = math.degrees(self.m.az)
        ze = 90 - math.degrees(self.m.alt)
        return az, ze

class SpiceMoonCalc(MoonCalculator):
    """
    Object that calculates the lunar zenith and azimuth for a given location
    at a given datetime, using spicedmoon (SPICE) library.
    """

    def __init__(self, lat: float, lon: float, alt: float = 0, kernels = "./kernels",
        retry_nospice: bool = False, logger: logging.Logger = None):
        """
        Parameters
        ----------
        lat : float
            Latitude of the location for which to calculate the Moon's
            zenith and azimuth
        lon : float
            Longitude of the location for which to calculate the Moon's
            zenith and azimuth
        alt : float
            Height (in meters) of the location for which to calculate the Moon's
            zenith and azimuth
        kernels : str
            Path where the directory containing the SPICE kernel files is located
        retry_nospice : bool
            SPICE rarely fails, but in case it does, if this parameter is true it will
            try to calculate the result with the most similar library instead of raising
            an Exception.
        logger : Logger
            Logger that will log out important messages, like when has SPICE failed and it
            has used the backup library.
        """
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.kernels = kernels
        self.retry_nospice = retry_nospice
        self.logger = logger

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain lunar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the lunar position will be calculated.

        Returns
        -------
        azimuth : float
            Lunar azimuth calculated.
        zenith : float
            Lunar zenith calculated.
        """
        dts_str = [dt.strftime('%Y-%m-%d %H:%M:%S')]
        try:
            mds = spicedmoon.get_moon_datas(self.lat, self.lon, self.alt, dts_str, self.kernels)
            az = mds[0].azimuth
            ze = mds[0].zenith
        except Exception as e:
            if self.retry_nospice:
                if self.logger:
                    self.logger.warning(str(e))
                    self.logger.warning("SPICE failed, using ephem instead")
                calc = EphemMoonCalc(self.lat, self.lon)
                az, ze = calc.get_position(dt)
            else:
                raise e
        return az, ze

class PysolarSunCalc(SunCalculator):
    """
    Object that calculates the solar zenith and azimuth for a given location
    at a given datetime, using pysolar library.
    """

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain solar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the solar position will be calculated.

        Returns
        -------
        azimuth : float
            Solar azimuth calculated.
        zenith : float
            Solar zenith calculated.
        """
        lat, lon = self.lat, self.lon
        az = solar.get_azimuth(lat, lon, dt)
        ze = 90 - solar.get_altitude(lat, lon, dt)
        return az, ze

class EphemSunCalc(SunCalculator):
    """
    Object that calculates the solar zenith and azimuth for a given location
    at a given datetime, using ephem library.
    """

    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon
        self.obs = ephem.Observer()
        self.obs.lat = math.radians(lat)
        self.obs.long = math.radians(lon)
        self.s = ephem.Sun()

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain solar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the solar position will be calculated.

        Returns
        -------
        azimuth : float
            Solar azimuth calculated.
        zenith : float
            Solar zenith calculated.
        """
        self.obs.date = dt
        self.s.compute(self.obs)
        az = math.degrees(self.s.az)
        ze = 90 - math.degrees(self.s.alt)
        return az, ze

class SpiceSunCalc(SunCalculator):
    """
    Object that calculates the solar zenith and azimuth for a given location
    at a given datetime, using spicedmoon (SPICE) library.
    """

    def __init__(self, lat: float, lon: float, alt: float = 0, kernels = "./kernels",
        retry_nospice: bool = False, logger: logging.Logger = None):
        """
        Parameters
        ----------
        lat : float
            Latitude of the location for which to calculate the Moon's
            zenith and azimuth
        lon : float
            Longitude of the location for which to calculate the Moon's
            zenith and azimuth
        alt : float
            Height (in meters) of the location for which to calculate the Moon's
            zenith and azimuth
        kernels : str
            Path where the directory containing the SPICE kernel files is located
        retry_nospice : bool
            SPICE rarely fails, but in case it does, if this parameter is true it will
            try to calculate the result with the most similar library instead of raising
            an Exception.
        logger : Logger
            Logger that will log out important messages, like when has SPICE failed and it
            has used the backup library.
        """
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.kernels = kernels
        self.retry_nospice = retry_nospice
        self.logger = logger

    def get_position(self, dt: datetime) -> Tuple[float, float]:
        """
        Obtain solar azimuth and zenith.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime at which the solar position will be calculated.

        Returns
        -------
        azimuth : float
            Solar azimuth calculated.
        zenith : float
            Solar zenith calculated.
        """
        dts_str = [dt.strftime('%Y-%m-%d %H:%M:%S')]
        try:
            mds = spicedsun.get_sun_datas(self.lat, self.lon, self.alt, dts_str, self.kernels)
            az = mds[0].azimuth
            ze = mds[0].zenith
        except Exception as e:
            if self.retry_nospice:
                if self.logger:
                    self.logger.warning(str(e))
                    self.logger.warning("SPICE failed, using pysolar instead")
                calc = PysolarSunCalc(self.lat, self.lon)
                az, ze = calc.get_position(dt)
            else:
                raise e
        return az, ze
