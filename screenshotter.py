#!/usr/bin/env python

# A tool to take a screenshot of a TN3270 screen. It will do so and output an
# HTML file of the same name as the host and port provided. A sample invocation
# could be:
# cat mainframes.txt|xargs -P100 -I% ./screenshotter.py -t %
# This will start 100 threads to take screenshots of all the pretty screens.

# By Dominic White @singe dominic () sensepost.com

# Original credit goes to Mainframed and TSO-Brute https://github.com/mainframed/TSO-Brute
# Actually, he has a NMAP script to do this for you https://github.com/mainframed/NMAP/blob/master/3270_screen_grab.nse

from py3270 import EmulatorBase,CommandError,FieldTruncateError
import time
import sys 
import argparse
import re
import platform

# Print output that can be surpressed by a CLI opt
def whine(text, kind='clear', level=0):
	if results.quiet and (kind == 'warn' or kind == 'info'):
			return
	else:
		typdisp = ''
		lvldisp = ''
		if kind == 'warn': typdisp = '[!] '
		elif kind == 'info': typdisp = '[+] '
		elif kind == 'err': typdisp = '[#] '
		elif kind == 'good': typdisp = '[*] '
		if level == 1: lvldisp = "\t"
		elif level == 2: lvldisp = "\t\t"
		elif level == 3: lvldisp = "\t\t\t"
		print lvldisp+typdisp+text

# Override some behaviour of py3270 library
class EmulatorIntermediate(EmulatorBase):
	def send_enter(self): #Allow a delay to be configured
		self.exec_command('Enter')
		if results.sleep > 0:
			time.sleep(results.sleep)

	def screen_get(self):
		response = self.exec_command('Ascii()')
		return response.data
	
# Set the emulator intelligently based on your platform
if platform.system() == 'Darwin':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/usr/local/bin/x3270' #'MAC_Binaries/x3270'
		s3270_executable = '/usr/local/bin/s3270' #'MAC_Binaries/s3270'
elif platform.system() == 'Linux':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/usr/bin/x3270' #comment this line if you do not wish to use x3270 on Linux
		s3270_executable = '/usr/bin/s3270'
elif platform.system() == 'Windows':
	class Emulator(EmulatorIntermediate):
		#x3270_executable = 'Windows_Binaries/wc3270.exe'
		s3270_executable = 'Windows_Binaries/ws3270.exe'
else:
	whine('Your Platform:', platform.system(), 'is not supported at this time.',kind='err')
	sys.exit(1)

def connect_zOS(em, target):
	whine('Connecting to ' + results.target,kind='info')
	em.connect(target)

	if not em.is_connected():
		whine('Could not connect to ' + results.target + '. Aborting.',kind='err')
		sys.exit(1)

# Define and fetch commandline arguments
parser = argparse.ArgumentParser(description='z/OS Mainframe Screenshotter', epilog='Get to it!')
parser.add_argument('-t', '--target', help='Target IP address or Hostname and port: TARGET[:PORT] default port is 23', required=True, dest='target')
parser.add_argument('-s', '--sleep', help='Seconds to sleep between actions (increase on slower systems). The default is 0 seconds.', default=0, type=float, dest='sleep')
parser.add_argument('-m', '--moviemode', help='Enables ULTRA AWESOME Movie Mode. Watch the system get hacked in real time!', default=False, dest='movie_mode', action='store_true')
parser.add_argument('-q', '--quiet', help='Be more quieter', default=False, dest='quiet', action='store_true')
results = parser.parse_args()

# Parse commandline arguments
whine('z/OS Mainframe Screenshotter',kind='info')
whine('Target Acquired\t\t: ' + results.target,kind='info')
whine('Slowdown is\t\t\t: ' + str(results.sleep),kind='info')
whine('Attack platform\t\t: ' + platform.system(),kind='info')

if results.movie_mode and not platform.system() == 'Windows':
	whine('ULTRA Hacker Movie Mode\t: Enabled',kind='info')
	#Enables Movie Mode which uses x3270 so it looks all movie like 'n shit
	em = Emulator(visible=True)
elif results.movie_mode and platform.system() == 'Windows':
	whine('ULTRA Hacker Movie Mode not supported on Windows',kind='warn')
	em = Emulator()
else:
	whine('ULTRA Hacker Movie Mode\t: Disabled',kind='info')
	em = Emulator()
if results.quiet:
	whine('Quiet Mode Enabled\t: Shhhhhhhhh!',type='warn')

connect_zOS(em,results.target) #connect to the host
time.sleep(results.sleep)
em.save_screen(results.target+'.html')

# And we're done. Close the connection
em.terminate()
