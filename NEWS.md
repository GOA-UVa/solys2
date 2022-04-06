# NEWS

- _ContainedBool name changed to ContainedBool
- Delays can be inputed by the user.

- Removed _TrackBody enum
- Autotrack: Some functionalities moved to common, others to calibration.

- _BodyTracker, MoonTracker and SunTracker require being called "start_tracking" in order
to start the tracking.

- Automation common functionalities moved to module autohelper.
- Automation modules moved to folder automation.
- Created doc folder and stored component diagram.

- BodyTracker gets the logger as a parameter, it doesn't generate it.
- Default logger function moved to common module.
- File logger function moved to common module.

- File logger and default logger creation functions accept level as a parameter.
- Removed cross and mesh solar and lunar functions, created objects instead, imitating
the functionality of _BodyTracker objects.

- Solys2 object, when sending a command if there is a ConnectionResetError or a BrokenPipeError
it reconnects and tries again. It also reconnects if there are too many nones.

- Corrected error where offset wasn't added.
