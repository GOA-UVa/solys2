# solys2

![Version 0.1.11](https://img.shields.io/badge/version-0.1.11-informational)

Python package for connecting and communicating with the Solys 2 via TCP/IP
and setting it up to automatically track the moon or the sun.

## Requirements

python>=3.8
numpy>=1.22.2
pylunar>=0.6.0
pysolar>=0.10
ephem>=4.1.3
spicedmoon>=0.1.2
spicedsun>=0.0.1

## Installation

```sh
pip install solys2
```

## Usage

### Direct communication

```python
from solys2 import solys2

# Connect with the Solys2
solys = solys2.Solys2(ip, port, password)

# Tell the Solys2 to point at azimuth 30.
solys.set_azimuth(30)

# Get the current position at which the solys is pointing.
az, ze, _ = solys.get_current_position()

# Send the command "HO" to the Solys2
output = solys.send_command("HO")
# Another option would have been calling solys.home()
```

### Automatic tracking

```python
from solys2 import autotrack

# Track the sun, sending a new position each 15 seconds, and logging the
# information (movements, etc) to a file called "solys.log"
st = autotrack.SunTracker(ip, 15, port, password, True, "solys.log")

# Stop tracking the Sun
st.stop_tracking()
```
