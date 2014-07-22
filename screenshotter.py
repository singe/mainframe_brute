#!/usr/bin/env python

# A tool to take a screenshot of a TN3270 screen. It will do so and output an
# HTML file of the same name as the host and port provided. A sample invocation
# could be:
# cat mainframes.txt|xargs -P100 -I% ./screenshotter.py -t %
# This will start 100 threads to take screenshots of all the pretty screens.

# By Dominic White @singe dominic () sensepost.com

# Original credit goes to Mainframed and TSO-Brute https://github.com/mainframed/TSO-Brute
# Actually, he has a NMAP script to do this for you https://github.com/mainframed/NMAP/blob/master/3270_screen_grab.nse

from py3270wrapper import WrappedEmulator
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
	em = WrappedEmulator(visible=True)
elif results.movie_mode and platform.system() == 'Windows':
	whine('ULTRA Hacker Movie Mode not supported on Windows',kind='warn')
	em = WrappedEmulator()
else:
	whine('ULTRA Hacker Movie Mode\t: Disabled',kind='info')
	em = WrappedEmulator(visible=False)
if results.quiet:
	whine('Quiet Mode Enabled\t: Shhhhhhhhh!',type='warn')

connect_zOS(em,results.target) #connect to the host
time.sleep(results.sleep)
em.save_screen(results.target+'.html')

# And we're done. Close the connection
em.terminate()
