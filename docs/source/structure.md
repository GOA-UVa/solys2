# Structure

The package is composed of different modules:
- **connection**: Module that encapsulates and abstracts functions that allow the low-level communication
with the Solys2.
- **response**: Module that contains functionalities for processing the Solys2 responses.
- **solys2**: Module that encapsulates and abstracts an interface for interacting with the Solys2.
- **positioncalc**: Module that contains the objects that allow the calculation of the position of the moon
and the sun using different libraries, like ephem, pysolar or SPICE (spicedmoon and spicedsun).
- **common**: Module containing common constants, functions and datatypes.
- **autohelper**: Module that contains the functionalities that are used for performing automatic actions
with the Solys2.
- **autotrack**: Module that contains the functionalities of performing automatic actions with the Solys2.
- **calibration**: This module contains the functionalities related to different calibration methods,
most of them used by the GOA-UVa.

The main modules that can be used are the module **solys2**, which allowes the user to interact
with the SOLYS2 easily, and **autotrack** and **calibration**, which let the user perform automated
functions like tracking the moon or performing a calibration cross over the moon.

![Component diagram](https://raw.githubusercontent.com/GOA-UVa/solys2/master/docs/img/solys2_components.png)
