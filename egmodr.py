#!/usr/bin/env python3
from fcntl import fcntl, F_SETFL
from libevdev import Device, InputEvent, EV_REL, EV_ABS, EV_KEY, EV_SYN
from math import ceil
from os import O_NONBLOCK
from pathlib import Path
from sys import exit
from time import sleep


# TODO Some of this can be queried from device, some should be in config file
X_MAX =  32767
X_MIN = -32768
X_DIV = 15 / X_MAX
X_DEAD_ZONE = 1600

# TODO Some of this can be queried from device, some should be in config file
Y_MAX =  32767
Y_MIN = -32768
Y_DIV = 15 / Y_MAX
Y_DEAD_ZONE = 1600


INPUT_DEVICES_DIRECTORY = '/dev/input'


class GamepadMouseDriver:
  def __init__(self, evdev_file):
    self._device_fd = open(evdev_file)
    fcntl(self._device_fd, F_SETFL, O_NONBLOCK)
    self._device = Device(self._device_fd)

    self._virtual_device = Device()
    self._init_virtual_device_events()
    self._virtual_device.name = "Gamepad Mouse"

    self._uinput_device = self._virtual_device.create_uinput_device()

  # TODO Probably should have some config file to do mapping
  def _init_virtual_device_events(self):
    self._virtual_device.enable(EV_REL.REL_X)
    self._virtual_device.enable(EV_REL.REL_Y)
    self._virtual_device.enable(EV_KEY.BTN_LEFT)
    self._virtual_device.enable(EV_KEY.BTN_RIGHT)
    self._virtual_device.enable(EV_KEY.KEY_LEFTCTRL)
    self._virtual_device.enable(EV_KEY.KEY_LEFTALT)
    self._virtual_device.enable(EV_KEY.KEY_LEFT)
    self._virtual_device.enable(EV_KEY.KEY_RIGHT)
    self._virtual_device.enable(EV_KEY.KEY_UP)
    self._virtual_device.enable(EV_KEY.KEY_DOWN)
    self._virtual_device.enable(EV_REL.REL_WHEEL_HI_RES)
    self._virtual_device.enable(EV_REL.REL_HWHEEL_HI_RES)

  def __del__(self):
    # TODO Probably a cleaner way to do this
    if '_device_fd' in self.__dict__ and not self._device_fd.closed:
      self._device_fd.close()

  def _handle_event(self, event, translated_events):
    match event.code:
      case EV_KEY.BTN_EAST:
        translated_events.append(InputEvent(EV_KEY.BTN_LEFT, event.value))
      case EV_KEY.BTN_WEST | EV_KEY.BTN_SOUTH:
        translated_events.append(InputEvent(EV_KEY.BTN_RIGHT, event.value))
      case EV_KEY.BTN_TR:
        translated_events.append(InputEvent(EV_KEY.KEY_LEFTCTRL, event.value))
        translated_events.append(InputEvent(EV_KEY.KEY_LEFTALT, event.value))
        translated_events.append(InputEvent(EV_KEY.KEY_RIGHT, event.value))
      case EV_KEY.BTN_TL:
        translated_events.append(InputEvent(EV_KEY.KEY_LEFTCTRL, event.value))
        translated_events.append(InputEvent(EV_KEY.KEY_LEFTALT, event.value))
        translated_events.append(InputEvent(EV_KEY.KEY_LEFT, event.value))
      case EV_ABS.ABS_HAT0X:
        if event.value == 1:
          translated_events.append(InputEvent(EV_KEY.KEY_RIGHT, 1))
        elif event.value == -1:
          translated_events.append(InputEvent(EV_KEY.KEY_LEFT, 1))
        else:
          translated_events.append(InputEvent(EV_KEY.KEY_RIGHT, 0))
          translated_events.append(InputEvent(EV_KEY.KEY_LEFT, 0))
      case EV_ABS.ABS_HAT0Y:
        if event.value == 1:
          translated_events.append(InputEvent(EV_KEY.KEY_DOWN, 1))
        elif event.value == -1:
          translated_events.append(InputEvent(EV_KEY.KEY_UP, 1))
        else:
          translated_events.append(InputEvent(EV_KEY.KEY_UP, 0))
          translated_events.append(InputEvent(EV_KEY.KEY_DOWN, 0))

  def _handle_abs_values(self, translated_events):
    adj_x = self._device.absinfo[EV_ABS.ABS_X].value
    adj_y = self._device.absinfo[EV_ABS.ABS_Y].value

    adj_rx = self._device.absinfo[EV_ABS.ABS_RX].value
    adj_ry = self._device.absinfo[EV_ABS.ABS_RY].value

    if abs(adj_x) > X_DEAD_ZONE:
      delta_x = ceil(adj_x * X_DIV)
      translated_events.append(InputEvent(EV_REL.REL_X, delta_x))
    if abs(adj_y) > Y_DEAD_ZONE:
      delta_y = ceil(adj_y * Y_DIV)
      translated_events.append(InputEvent(EV_REL.REL_Y, delta_y))

    # X - Right is negative, left is positive
    # Y - Down is negative, up is positive
    if abs(adj_rx) > X_DEAD_ZONE:
      delta_x = ceil(adj_rx * X_DIV)
      translated_events.append(InputEvent(EV_REL.REL_HWHEEL_HI_RES, delta_x))
    if abs(adj_ry) > Y_DEAD_ZONE:
      delta_y = ceil(adj_ry * Y_DIV)
      translated_events.append(InputEvent(EV_REL.REL_WHEEL_HI_RES, -delta_y))

  def run(self):
    while True:
      translated_events = []

      events = list(self._device.events())
      if len(events) > 0:
        for event in events:
          self._handle_event(event, translated_events)

      self._handle_abs_values(translated_events)

      if len(translated_events) > 0:
        translated_events.append(InputEvent(EV_SYN.SYN_REPORT, 0))
        self._uinput_device.send_events(translated_events)

      # Simple way to avoid input spamming. Will do this better later
      sleep(0.01)


if __name__ == '__main__':
  # Try to find the first evdev that supports the Linux gamepad protocol. Note
  # that if there are multiple connected gamepads, there is no deterministic way
  # to determine which one will be found first (and use)
  gamepad_evdev_file = None
  events = Path(INPUT_DEVICES_DIRECTORY)
  for evdev_file in events.iterdir():
    # Ignore non-event-file files (e.g. the "by-path" subdirectory)
    if 'event' in evdev_file.name:
      evdev_fd = open(evdev_file)
      device = Device(evdev_fd)

      # According to the kernel docs (/Documentation/input/gamepad.rst) gamepads
      # compliant to the Linux gamepad protocol will always map BTN_GAMEPAD
      # which aliases to BTN_A or BTN_SOUTH. python-libevdev only supports the
      # name BTN_SOUTH
      if EV_KEY in device.evbits and EV_KEY.BTN_SOUTH in device.evbits[EV_KEY]:
        gamepad_evdev_file = evdev_file
        evdev_fd.close()
        break # For now, just use the first gamepad we find

      evdev_fd.close()

  if gamepad_evdev_file is None:
    print('Unable to detect gamepad')
    exit(-1)

  try:
    print('Initializing gamepad mouse driver')
    drv = GamepadMouseDriver(evdev_file)
    sleep(1) # Sleep to give driver time to be recognized (e.g. by X11)
    print('Starting driver')
    drv.run()
  except KeyboardInterrupt:
    print('Stopping driver')
    exit()
