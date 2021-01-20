#!/usr/bin/python3
# -*- encoding=UTF-8 -*-

import time
import os, struct, array
from fcntl import ioctl
from pynput.keyboard import Key, Controller
from pynput.mouse import Button as Mouse_Button
from pynput.mouse import Controller as Mouse_Controller

GAMEPAD="/dev/input/js0"
ANALOG_THRESHOLD=0.3

# We'll store the states here.
axis_states = {}
button_states = {}

debug=False

pwm_freq=10.0 # Frequency of key pressing, Hz
pwm_deadzone=0.150

pwm_map={"x":["a","d"],
		 "y":["w","s"]}

mouse_map={"rx":["mouse_x",0.5],
		   "ry":["mouse_y",0.5]}

mouse_buttons_map={"tr2":Mouse_Button.left,
				   "tl2":Mouse_Button.right}


# These constants were borrowed from linux/input.h
axis_names = {
	0x00 : 'x',
	0x01 : 'y',
	0x02 : 'z',
	0x03 : 'rx',
	0x04 : 'ry',
	0x05 : 'rz',
	0x06 : 'trottle',
	0x07 : 'rudder',
	0x08 : 'wheel',
	0x09 : 'gas',
	0x0a : 'brake',
	0x10 : 'hat0x',
	0x11 : 'hat0y',
	0x12 : 'hat1x',
	0x13 : 'hat1y',
	0x14 : 'hat2x',
	0x15 : 'hat2y',
	0x16 : 'hat3x',
	0x17 : 'hat3y',
	0x18 : 'pressure',
	0x19 : 'distance',
	0x1a : 'tilt_x',
	0x1b : 'tilt_y',
	0x1c : 'tool_width',
	0x20 : 'volume',
	0x28 : 'misc',
}

button_names = {
	0x120 : 'trigger',
	0x121 : 'thumb',
	0x122 : 'thumb2',
	0x123 : 'top',
	0x124 : 'top2',
	0x125 : 'pinkie',
	0x126 : 'base',
	0x127 : 'base2',
	0x128 : 'base3',
	0x129 : 'base4',
	0x12a : 'base5',
	0x12b : 'base6',
	0x12f : 'dead',
	0x130 : 'a',
	0x131 : 'b',
	0x132 : 'c',
	0x133 : 'x',
	0x134 : 'y',
	0x135 : 'z',
	0x136 : 'tl',
	0x137 : 'tr',
	0x138 : 'tl2',
	0x139 : 'tr2',
	0x13a : 'select',
	0x13b : 'start',
	0x13c : 'mode',
	0x13d : 'thumbl',
	0x13e : 'thumbr',

	0x220 : 'dpad_up',
	0x221 : 'dpad_down',
	0x222 : 'dpad_left',
	0x223 : 'dpad_right',

	# XBox 360 controller uses these codes.
	0x2c0 : 'dpad_left',
	0x2c1 : 'dpad_right',
	0x2c2 : 'dpad_up',
	0x2c3 : 'dpad_down',
}

axis_map = []
button_map = []

keyboard = Controller()
mouse = Mouse_Controller()

cur_time=0.0

def joy_init():
	# Iterate over the joystick devices.
	print('Available devices:')
	
	for fn in os.listdir('/dev/input'):
		if fn.startswith('js'):
			print('  /dev/input/%s' % (fn))
	# Open the joystick device.
	fn = GAMEPAD
	print('Opening %s...' % fn)
	jsdev = os.open(fn, os.O_RDONLY | os.O_NONBLOCK)
	
	# Get the device name.
	#buf = bytearray(63)
	buf = array.array('B', [0] * 64)
	ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf) # JSIOCGNAME(len)
	js_name = buf.tobytes().decode("utf-8")
	print('Device name: %s' % js_name)
	
	# Get number of axes and buttons.
	buf = array.array('B', [0])
	ioctl(jsdev, 0x80016a11, buf) # JSIOCGAXES
	num_axes = buf[0]
	
	buf = array.array('B', [0])
	ioctl(jsdev, 0x80016a12, buf) # JSIOCGBUTTONS
	num_buttons = buf[0]
	
	# Get the axis map.
	buf = array.array('B', [0] * 0x40)
	ioctl(jsdev, 0x80406a32, buf) # JSIOCGAXMAP
	
	for axis in buf[:num_axes]:
		axis_name = axis_names.get(axis, 'unknown(0x%02x)' % axis)
		axis_map.append(axis_name)
		axis_states[axis_name] = 0.0
	
	# Get the button map.
	buf = array.array('H', [0] * 200)
	ioctl(jsdev, 0x80406a34, buf) # JSIOCGBTNMAP
	
	for btn in buf[:num_buttons]:
		btn_name = button_names.get(btn, 'unknown(0x%03x)' % btn)
		button_map.append(btn_name)
		button_states[btn_name] = 0
	
	print ('%d axes found: %s' % (num_axes, ', '.join(axis_map)))
	print ('%d buttons found: %s' % (num_buttons, ', '.join(button_map)))
	return jsdev

def scan_joy():
	global jsdev
	try:
		evbuf = os.read(jsdev,8)
	except BlockingIOError:
		pass
	else:
		if evbuf:
			time_, value, type, number = struct.unpack('IhBB', evbuf)
			if type & 0x80:
				pass
				if debug: print( "(initial)",)
			if type & 0x01:
				button = button_map[number]
				if button:
					button_states[button] = value
					if value:
						pass
						if debug: print ("%s pressed" % (button))
					else:
						pass
						if debug: print ("%s released" % (button))
			if type & 0x02:
				axis = axis_map[number]
				if axis:
					fvalue = value / 32767.0
					axis_states[axis] = fvalue
					if debug: print ("%s: %.3f" % (axis, fvalue))

def get_time_delta():
	global cur_time
	d=time.time()-cur_time
	cur_time=time.time()
	return d


def main():
	global jsdev
	tmax=1.0/pwm_freq
	jsdev=joy_init()
	get_time_delta()
	dx=0
	dy=0
	x=0
	y=0
	for p in pwm_map.keys():
		pwm_map[p].append(0.0)
		pwm_map[p].append(0)
	while True:
		scan_joy()
		d=get_time_delta()
		for axis in pwm_map.keys():
			pwm_map[axis][2]+=d
			if pwm_map[axis][2]>=tmax:
				pwm_map[axis][3]=0
				pwm_map[axis][2]=0.0
			if pwm_map[axis][3]==0 and abs(axis_states[axis])>pwm_deadzone:
				if axis_states[axis]<0: keyboard.press(pwm_map[axis][0])
				else: keyboard.press(pwm_map[axis][1])
				pwm_map[axis][3]=1
			if pwm_map[axis][3]==1:
				if (pwm_map[axis][2])>abs(axis_states[axis]*tmax):
					if axis_states[axis]<0: keyboard.release(pwm_map[axis][0])
					else: keyboard.release(pwm_map[axis][1])
					pwm_map[axis][3]=2
		for axis in mouse_map.keys():
			if mouse_map[axis][0]=="mouse_x":
				dx+=axis_states[axis]*mouse_map[axis][1]
			if mouse_map[axis][0]=="mouse_y":
				dy+=axis_states[axis]*mouse_map[axis][1]
		if int(abs(dx))>0:
			x=x+int(dx)
			dx=dx-(int(dx))
		if int(abs(dy))>0:
			y=y+int(dy)
			dy=dy-int(dy)
		if x!=0 or y!=0:
			mouse.move(x,y)
			x=0
			y=0
		for button in mouse_buttons_map.keys():
			if button_states[button]: mouse.press(mouse_buttons_map[button])
			else: mouse.release(mouse_buttons_map[button])
				
		time.sleep(0.00001)



main()
