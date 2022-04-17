# NEWS

## v0.2.0
- \_ContainedBool name changed to ContainedBool
- Delays can be inputed by the user.
- Removed \_TrackBody enum
- Autotrack: Some functionalities moved to common, others to calibration.
- \_BodyTracker, MoonTracker and SunTracker require being called "start\_tracking" in order
to start the tracking.
- Automation common functionalities moved to module autohelper.
- Automation modules moved to folder automation.
- Created doc folder and stored component diagram.
- BodyTracker gets the logger as a parameter, it doesn't generate it.
- Default logger function moved to common module.
- File logger function moved to common module.
- File logger and default logger creation functions accept level as a parameter.
- Removed cross and mesh solar and lunar functions, created objects instead, imitating
the functionality of \_BodyTracker objects.
- Solys2 object, when sending a command if there is a ConnectionResetError or a BrokenPipeError
it reconnects and tries again. It also reconnects if there are too many nones.
- Corrected error where offset wasn't added.
- Fixed bug check\_time\_solys func overwritten by variable. Variable now is
should\_check\_time\_solys.
- Added support for python3.7, although spiceypy might not work.
- Positioncalc module moved into automation
- Calibration takes away time of countdown in case solys delay was too big, and even raises an
error if it's too big even with the countdown.
- Minor logging modifications.
- Countdown is now logging level INFO instead of WARNING.
- Changed CrossParameters class name to CalibrationParameters.
- Created superclass for automation objects called AutomationWorker.
- Functions of AutomationWorkers changed names to "start()" and "stop".
- Added instrument callback as an optional parameter for Calibration Automation Workers.

## Next
- Fixed some solys2 return typing type from int to float.
- Reduced some logging output number of floating point decimals. (.4f)
- Not obtaining sun quadrant sensor information.
- Printing coordinates in debug.
