"""AutoTrack

Module that contains the functionalities of performing automatic actions with the Solys2.

It exports the following classes:
    * MoonTracker : Object that contains the thread that controls the Solys2 for tracking \
automatically the Moon.
    * SunTracker : Object that contains the thread that controls the Solys2 for tracking \
automatically the Sun.
"""

"""___Built-In Modules___"""
from typing import List
import time
import logging
from threading import Thread, Lock

"""___Third-Party Modules___"""
# import here

"""___Solys2 Modules___"""
try:
    from . import autohelper
    from .. import solys2
    from . import positioncalc as psc
    from .. import common
except:
    from solys2.automation import autohelper
    from solys2.automation import positioncalc as psc
    from solys2 import common
    from solys2 import solys2

"""___Authorship___"""
__author__ = 'Javier Gatón Herguedas, Juan Carlos Antuña Sánchez, Ramiro González Catón, \
Roberto Román, Carlos Toledano, David Mateos'
__created__ = "2022/03/10"
__maintainer__ = "Javier Gatón Herguedas"
__email__ = "gaton@goa.uva.es"
__status__ = "Development"

def _track_body(ip: str, seconds: float, library: psc._BodyLibrary, mutex_cont: Lock,
    cont_track: common.ContainedBool, logger: logging.Logger, port: int = 15000,
    password: str = "solys", is_finished: common.ContainedBool = None,
    altitude: float = 0, kernels_path: str = "./kernels",
    solys_delay: float = common.SOLYS_APPROX_DELAY):
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
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    logger : logging.Logger
        Logger that will log out the log messages
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
    solys_delay : float
        Approximate delay in seconds between telling the Solys2 to move to a position and
        the Solys2 saying that it reached that position.

    Raises
    ------
    SolysException
        If an error happens when stablishing connection with the Solys2 for the first time.
    """
    try:
        # Connect with the Solys2 and set the initial configuration.
        solys = solys2.Solys2(ip, port, password)
        solys.set_power_save(False)
        body_calc = autohelper.get_body_calculator(solys, library, logger, altitude, kernels_path)
        if library.value in [l.value for l in psc.SunLibrary]:
            logger.info("Tracking sun. Connected with Solys2.")
        else:
            logger.info("Tracking moon. Connected with Solys2.")
        autohelper.check_time_solys(solys, logger)
        # Start tracking in a loop
        sleep_time = 0
        time_offset = ((seconds - solys_delay) / 2.0) + solys_delay
        t0 = time.time()
        mutex_cont.acquire()
        cont_track.value = True
        while cont_track.value:
            mutex_cont.release()
            logger.debug("Waited {} seconds.\n".format(sleep_time))
            autohelper.read_and_move(solys, body_calc, logger, datetime_offset=time_offset)
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
    except Exception as e:
        autohelper.exception_tracking(logger, e, solys, is_finished)

class _BodyTracker(autohelper.AutomationWorker):
    """_BodyTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the selected body.

    Attributes
    ----------
    mutex_cont : Lock
        Mutex that controls the access to the variable cont_track
    cont_track : ContainedBool
        Container for the boolean value that represents if the tracking must stop or if it should
        continue.
    logger : logging.Logger
        Logger that will log out the log messages.
    thread : Thread
        Thread that will execute the tracking function.
    _is_finished : ContainedBool
        Container for the boolean value that initially will be False, but it will be True
        when the thread has successfully ended execution.
    """
    def __init__(self, ip: str, seconds: float, library: psc._BodyLibrary, port: int = 15000,
        password: str = "solys", logger: logging.Logger = None,
        altitude: float = 0, kernels_path: str = "./kernels",
        solys_delay: float = common.SOLYS_APPROX_DELAY):
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
        logger : Logger
            Logger that will log out the log messages. If None, it will print them out on stderr
            if they are level WARNING or higher.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        solys_delay : float
            Approximate delay in seconds between telling the Solys2 to move to a position and
            the Solys2 saying that it reached that position.
        """
        self.mutex_cont = Lock()
        self.cont_track = common.ContainedBool(True)
        if logger == None:
            logger = common.create_default_logger()
        self.logger = logger
        self._is_finished = common.ContainedBool(False)
        # Create thread
        self.thread = Thread(target = _track_body, args = (ip, seconds, library, self.mutex_cont,
            self.cont_track, self.logger, port, password, self._is_finished, altitude,
            kernels_path, solys_delay))

    def start(self):
        """Start tracking the previously selected body."""
        self.thread.start()

    def stop(self):
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
        logger: logging.Logger = None, library: psc.MoonLibrary = psc.MoonLibrary.EPHEM_MOON,
        altitude: float = 0, kernels_path: str = "./kernels",
        solys_delay: float = common.SOLYS_APPROX_DELAY):
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
        logger : Logger
            Logger that will log out the log messages. If None, it will print them out on stderr
            if they are level WARNING or higher.
        library : MoonLibrary
            Lunar library that will be used to track the Moon. By default is ephem.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        solys_delay : float
            Approximate delay in seconds between telling the Solys2 to move to a position and
            the Solys2 saying that it reached that position.
        """
        super().__init__(ip, seconds, library, port, password, logger, altitude,
            kernels_path, solys_delay)

class SunTracker(_BodyTracker):
    """SunTracker
    Object that when created will create a thread executing the function of controlling the
    Solys2 so it tracks the Sun.
    """
    def __init__(self, ip: str, seconds: float, port: int = 15000, password: str = "solys",
        logger: logging.Logger = None, library: psc.SunLibrary = psc.SunLibrary.PYSOLAR,
        altitude: float = 0, kernels_path: str = "./kernels",
        solys_delay: float = common.SOLYS_APPROX_DELAY):
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
        logger : Logger
            Logger that will log out the log messages. If None, it will print them out on stderr
            if they are level WARNING or higher.
        library : SunLibrary
            Solar library that will be used to track the Sun. By default is pysolar.
        altitude : float
            Altitude in meters of the observer point. Used only if SPICE library is selected.
        kernels_path : str
            Directory where the needed SPICE kernels are stored. Used only if SPICE library
            is selected.
        solys_delay : float
            Approximate delay in seconds between telling the Solys2 to move to a position and
            the Solys2 saying that it reached that position.
        """
        super().__init__(ip, seconds, library, port, password, logger, altitude,
            kernels_path, solys_delay)
