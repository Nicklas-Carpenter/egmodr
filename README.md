# EGMoDr
`EGMoDr` is a Linux userspace driver that allows a gamepad to be used like a
mouse (with some extra features). The name is derived from the project's full
title "**E**vdev-**G**amepad-**Mo**use-**Dr**iver" and is pronounced
"egg modder".

## Overview
`EGMoDr` subscribes to the Linux generic input event interface, `evdev`, to
listen for input events from an attached gamepad device. It then creates a
`uinput` device and maps events it receives from the gamepad to events that a
mouse device would send out. In some cases (such as left and right click), it
simply maps a gamepad button event (e.g. an A-button press) to the desired mouse
event (e.g. a left click). In other cases (such as mapping mouse move to an
analog stick) some additional processing is required. EGMoDr also has some
special mappings that don't correspond to normal mouse actions (e.g. I mapped
the digital left and right trigger buttons to my (multi-key) shortcut to switch
desktops).

## Setup
### Compatibility disclaimer
`EGMoDr` is only guaranteed to work on Linux. I'm not sure if Windows has a
built-in compatibility layer (with or without WSL) or if `python-libevdev`
provides one (I suspect not), but none of these possibilites have been tested.

### Obtaining EGMoDr
The best way to obtain `EGMoDr` is to either clone it or download it from
GitHub. Currently, there is are no releases since this is mostly just a fun demo
project and a release would look identical to the source code anyways.

### Installing EGModr
`EGMoDr` currently consists of a single Python script that can run from
virtually anywhere; it itself doesn't need to be installed. EGMoDr imports the
`python-libevdev`, so you need to ensure that it is installed before attempting
to run the driver. In the future, I'll likely create a virtual environment to
make dependency management easier.

## Usage
### Permissions
`EGMoDr` works by reading from one device file (`/dev/input/event<X>` where
`<X>` is the index of the `evdev` event associated witht the gamepad) and 
writing to another (`/dev/uinput`). As such, `EGMoDr` needs to have permissions
to read and write to and from the specific files and therefore the user running
the program must have these same permissions. An (abbreviated) example of checking the
permision of both sets of files is shown below:

```console 
$ ls -l /dev/input/event* /dev/uinput
...
crw-rw----  1 root input 13,  66 Dec 23 22:55 /dev/input/event2
crw-rw----  1 root input 13,  84 Dec 27 18:17 /dev/input/event20
crw-rw----+ 1 root input 13,  86 Dec 27 12:00 /dev/input/event22
crw-rw----  1 root input 13,  73 Dec 23 22:55 /dev/input/event9
...
crw-rw----+ 1 root root  10, 223 Dec 23 22:55 /dev/uinput

$ getfacl /dev/input/event22
getfacl: Removing leading '/' from absolute path names
# file: dev/input/event22
# owner: root
# group: input
user::rw-
user:me:rw-
group::rw-
mask::rw-
other::---

$ getfacl /dev/uinput
getfacl: Removing leading '/' from absolute path names
# file: dev/uinput
# owner: root
# group: root
user::rw-
user:me:rw-
group::---
mask::rw-
other::---
```

On this system, the event files can be read from or written to by `root` or
members of the `input` group. `uinput` can be read from and written to by root.
Finally, the user `me` can read from and write to both sets of files.

### Starting EGMoDr
`EGMoDr` can be run from the commandline with:

```bash
$ ./egmodr.py
```
or
```bash
$ python egmodr.py
```

`EGMoDr` will initialize the driver and then wait a second for the program that
manages input (usually a display server such as X11) to recognize the new input
device. Assuming no errors occurred, the gamepad should, from then on, be able
to function as a mouse. `EGMoDr` has some initial startup messages that are
printed to `stdout`.

### Using EGMoDr
If everything is working, the controller should now behave like a mouse. The
table below describes the functionality mapped to each feature on the
controller. For clarity, the table describes the mapping of the physical
features on the controller (e.g. the left analog stick) and assumes and XBox
controller layout. The source code is the best place to see exactly how the
`evdev` events are mapped.

| Gamepad Physical Feature |                        Action                        |
|--------------------------|------------------------------------------------------|
| A Button                 | Right mouse click                                    |
| B Button                 | Left mouse click                                     |
| X Button                 | Unmapped                                             |
| Y Button                 | Right mouse click                                    |
| Start Button             | Unmapped                                             |
| Select Button            | Unmapped                                             |
| Center Button            | Unmapped                                             |
| Right Analog Stick       | Horizontal and vertical scrollwheel                  |
| Left Analog Stick        | Mouse movement                                       |
| D-Pad                    | Corresponding arrow keys                             |
| Left Digital Trigger     | Move to previous (left) desktop (CTRL+ALT+L\_ARROW)  |
| Right Digital Trigger    | Move to next (right) desktop (CTRL+ALT+R\_ARROW)     |
| Left Analog Trigger      | Unmapped                                             |
| Right Analog Trigger     | Unmapped                                             |

### Troubleshooting
In general, the controller will work as expected or completely fail to start 
(althought there are some [known issues](#known-issues). The most likely issues
include (in no particular order):
  * You don't have the right permissions for either `/dev/input/event<X>` or
    `/dev/uinput`
  * You controller is not plugged in (it happens to the best of us)
  * You have multiple controllers plugged in and the driver chose to use the one
    you are not currently trying to use.
  * Your gamepad or its underlying driver doesn't properly follow the gamepad
    protocol (probably not that likely for most non-sketchy controllers)
  * Your gamepad is not being detected for some unknown reason

If you do run into any issues that you believe are the fault of the driver (and
are not listed under [known issues](#known-issues)), I'd love to hear from you. 
See [the section on contributing](#contributing) for the best way to reach out
to me.

### Known issues
In my experience, the driver works fairly well and without major issues. I have
notices, however, that occasionally the cursor will drift while the driver is in
use.

Based on my debugging, it seems the analog stick would get into a state where
when it was released it didn't completely recenter and continued to report a
small magnitude in a particular direction (it seemed to favor left drifting in
my tests). I made some modifications to the deadzone-related code and that
mitigated the issue to the point where I could no longer consistently reproduce
the issue.

Despite this, I still encounter the issue occasionally. I'd need to some more
debugging to pinpoint the issue, but I have a few theories:

* It's possibly that it might just be the gamepad I'm using (its analog sticks
  are a bit stiff and may have  a tendency to get stuck at small angle offsets
  from the center). If this is the case, simply increasing the deadzone would
  solve the problem.

* The analog sticks report their absolute position and only send updates when
  their position changes. The driver stores the last reported position of the
  analog sticks (actually, `python-libevdev` itself does this). I could see it
  being the case where the last report from the analog stick, when the stick 
  settles in the center, is somehow dropped somewhere along the pipeline and the
  second-to-last report gave a value right outside the deadzone. I'm not sure
  how likely this would be, but if it did happen drift would be expected since
  the driver translates magnitude (and direction) of the analog stick position
  into mouse movements.

* It's possible that there is an error in some of the calculations done to
  transform the absolute stick position into a relative mouse motion. Given how
  incosistently the issue arises, I don't think this is likely.

Aside from drift problem, all of the mappings and configurations are currently
hard-coded. I don't think this is technically an "issue", but it is a current
limitation. Time and interest permitting, I'd like to address this.

## Future work
I created `EGMoDr` as part of an effort to understand the Linux input subsystem
as well as fulfill a goal I had when I first started getting into computers
(being able to write code to let me use a gamepad as a mouse). As such, I don't
anticipate any serious, long-term effort being put into `EGMoDr`. That said, it
was education, fun to work on, and ended up working better than I expected.
While it certainly won't become a part of my normal workflow, I found using the
gamepad as an input device to be surprisingly intutitive. I could definitely see
revisting this project to do some updates and new tests. Here is a
non-exhaustive list of some things I'd like to try:
  * Adding a mapping configuration file (harder than you'd expect because
    certain kinds of mappings are non-trivial
  * Enhancements and improvements (e.g. reduce/eliminate polling)
  * Experimental new mappings
  * On-the-fly profile (mapping) switching
  * Fix the drift issue once and for all (or at least confirm its related to
    physical conditions of the gamepad)
  * Create a virtual environment to make installing dependencies easier and more
    self-contained

## Contributing
As mentioned above, I don't expect to put dedicated work into this project, but
if there are any feature ideas or bug fixes you are interested in, definitely
let me know and I'll look into it. The best way to do this would probably be to
open up an issue.

If you want to try your hand at adding a feature you think would be useful or
fixing an issue, feel free to fork the project, add your changes, and make a
pull request. I can't promise the changes will be pulled in, but I'd be happy to
review them

## License
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this 
program. If not, see <https://www.gnu.org/licenses/>.
