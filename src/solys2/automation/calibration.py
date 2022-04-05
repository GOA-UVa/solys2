"""Calibration

This module contains the functionalities related to different calibration methods,
most of them used by the GOA-UVa.
"""

"""___Built-In Modules___"""
from dataclasses import dataclass
from typing import Tuple, List
import time
import datetime
import logging
from threading import Lock

"""___Third-Party Modules___"""
import numpy as np

"""___Solys2 Modules___"""
from .. import solys2
from .. import positioncalc as psc
from . import autohelper
from .. import common as _common

@dataclass
class CrossParameters:
    """
    Parameters needed when performing a cross or a mesh over a Body.

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
    mutex_cont: Lock = None, cont_track: _common.ContainedBool = None,
    solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    stoppable: bool = False
    if mutex_cont and cont_track:
        stoppable = True
    sleep_time0 = 0
    sleep_time1 = 0
    solys_tot_delay = solys_delay + solys_delay_margin
    dt_offset = cp.countdown + instrument_delay/2.0 + solys_tot_delay
    for offset in offsets:
        if stoppable:
            mutex_cont.acquire()
        if stoppable and not cont_track.value:
            logger.info("Operation stopped manually.")
            break
        if stoppable:
            mutex_cont.release()
        t0 = time.time()
        autohelper.read_and_move(solys, body_calc, logger, offset, datetime_offset=dt_offset)
        sleep_time0 = cp.countdown
        tf = time.time()
        diff_td = tf - t0
        wait_time = (dt_offset - _common.ASD_DELAY/2.0) - (diff_td + sleep_time0)
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

def _cross_body(ip: str, library: psc._BodyLibrary, logger: logging.Logger,
    cross_params: CrossParameters, port: int = 15000, password: str = "solys",
    is_finished: _common.ContainedBool = None, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    try:
        # Connect with the Solys2 and set the initial configuration.
        solys = solys2.Solys2(ip, port, password)
        solys.set_power_save(False)
        body_calc = autohelper.get_body_calculator(solys, library, logger, altitude, kernels_path)
        if library in psc.SunLibrary:
            logger.info("Performing a solar cross. Connected with Solys2.")
        else:
            logger.info("Performing a lunar cross. Connected with Solys2.")
        cp = cross_params
        logger.info("Performing cross with azimuth range [{},{}], steps {}, and zenith range \
[{},{}], steps {}. Countdown of {} and post wait of {} seconds".format(cp.azimuth_min_offset,
            cp.azimuth_max_offset, cp.azimuth_step, cp.zenith_min_offset, cp.zenith_max_offset,
            cp.zenith_step, cp.countdown, cp.post_wait))
        autohelper.check_time_solys(solys, logger)
        # Generating the offsets
        offsets: List[Tuple[float, float]] = \
            [(i, 0) for i in np.arange(cp.azimuth_min_offset, cp.azimuth_max_offset +
                cp.azimuth_step, cp.azimuth_step)]
        offsets += [(0, i) for i in np.arange(cp.zenith_min_offset, cp.zenith_max_offset +
            cp.zenith_step, cp.zenith_step)]
        logger.debug("Moving next to the body...")
        autohelper.read_and_move(solys, body_calc, logger, (0,0))
        logger.debug("Moved next to the body.")
        logger.info("Starting cross")
        _perform_offsets_body(solys, logger, offsets, body_calc, cp, mutex_cont, cont_track,
            solys_delay, solys_delay_margin, instrument_delay)
        solys.close()
        if is_finished:
            is_finished.value = True
        logger.info("Tracking stopped and connection closed.")
    except Exception as e:
        autohelper.exception_tracking(logger, e, solys, is_finished)

def lunar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _common.ContainedBool = None,
    library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    return _cross_body(ip, library, logger, cross_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track, solys_delay, solys_delay_margin,
        instrument_delay)

def solar_cross(ip: str, logger: logging.Logger, cross_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _common.ContainedBool = None,
    library: psc.SunLibrary = psc.SunLibrary.PYSOLAR, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN, instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    return _cross_body(ip, library, logger, cross_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track, solys_delay, solys_delay_margin,
        instrument_delay)

def _mesh_body(ip: str, library: psc._BodyLibrary, logger: logging.Logger, mesh_params: CrossParameters,
    port: int = 15000, password: str = "solys", is_finished: _common.ContainedBool = None,
    altitude: float = 0, kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
        Container for the boolean value that initially will be False, but it should be changed
        to True when exiting the function.
    altitude : float
        Altitude in meters of the observer point. Used only if SPICE library is selected.
    kernels_path : str
        Directory where the needed SPICE kernels are stored. Used only if SPICE library
        is selected.
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    try:
        # Connect with the Solys2 and set the initial configuration.
        solys = solys2.Solys2(ip, port, password)
        solys.set_power_save(False)
        body_calc = autohelper.get_body_calculator(solys, library, logger, altitude, kernels_path)
        if library in psc.SunLibrary:
            logger.info("Performing a solar mesh. Connected with Solys2.")
        else:
            logger.info("Performing a lunar mesh. Connected with Solys2.")
        cp = mesh_params
        logger.info("Performing mesh with azimuth range [{},{}], steps {}, and zenith range \
[{},{}], steps {}. Countdown of {} and post wait of {} seconds".format(cp.azimuth_min_offset,
            cp.azimuth_max_offset, cp.azimuth_step, cp.zenith_min_offset, cp.zenith_max_offset,
            cp.zenith_step, cp.countdown, cp.post_wait))
        autohelper.check_time_solys(solys, logger)
        # Generating the offsets
        offsets: List[Tuple[float, float]] = []
        for i in np.arange(cp.azimuth_min_offset, cp.azimuth_max_offset + cp.azimuth_step,
                cp.azimuth_step):
            for j in np.arange(cp.zenith_min_offset, cp.zenith_max_offset + cp.zenith_step,
                    cp.zenith_step):
                offsets.append((i,j))
        logger.debug("Moving next to the body...")
        autohelper.read_and_move(solys, body_calc, logger, (0,0))
        logger.debug("Moved next to the body.")
        logger.info("Starting mesh")
        _perform_offsets_body(solys, logger, offsets, body_calc, cp, mutex_cont, cont_track,
            solys_delay, solys_delay_margin, instrument_delay)
        solys.close()
        if is_finished:
            is_finished.value = True
        logger.info("Tracking stopped and connection closed.")
    except Exception as e:
        autohelper.exception_tracking(logger, e, solys, is_finished)

def lunar_mesh(ip: str, logger: logging.Logger, mesh_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _common.ContainedBool = None,
    library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    return _mesh_body(ip, library, logger, mesh_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track, solys_delay, solys_delay_margin,
        instrument_delay)

def solar_mesh(ip: str, logger: logging.Logger, mesh_params: CrossParameters, port: int = 15000,
    password: str = "solys", is_finished: _common.ContainedBool = None,
    library: psc.SunLibrary = psc.SunLibrary.PYSOLAR, altitude: float = 0,
    kernels_path: str = "./kernels", mutex_cont: Lock = None,
    cont_track: _common.ContainedBool = None, solys_delay: float = _common.SOLYS_APPROX_DELAY,
    solys_delay_margin: float = _common.SOLYS_DELAY_MARGIN,
    instrument_delay: float = _common.ASD_DELAY):
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
    is_finished : ContainedBool
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.
    solys_delay_margin : float
        Time margin in seconds where solys_delay + solys_delay_margin = enough time for the
        Solys2 to move to a position and confirm that it has reached it, since the moment when
        the "move position" command was sent, (for most cases).
    instrument_delay : float
        Approximate time in seconds that the measure instrument takes in each measurement.
    """
    return _mesh_body(ip, library, logger, mesh_params, port, password, is_finished,
        altitude, kernels_path, mutex_cont, cont_track, solys_delay, solys_delay_margin,
        instrument_delay)

def black_moon(ip: str, logger: logging.Logger, port: int = 15000,
    password: str = "solys", is_finished: _common.ContainedBool = None,
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
    is_finished : ContainedBool
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
    try:
        solys = solys2.Solys2(ip, port, password)
        solys.set_power_save(False)
        body_calc = autohelper.get_body_calculator(solys, library, logger, altitude, kernels_path)
        autohelper.check_time_solys(solys, logger)

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
        autohelper.read_and_move(solys, body_calc, logger, (az_offset, ze_offset))
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
    except Exception as e:
        autohelper.exception_tracking(logger, e, solys, is_finished)
