The Unimaginative Mainframe Bruter/Screen Automation Tool
=========================================================

Tool to brute force APPLIDs on a z/OS mainframe where you can connect to VTAM
Truthfully, it's just a useful way of automating mainframe screen interactions,
i.e. I make copies of this to perform specific fuzzing/user enum/password
bruting attacks against custom apps It is a fork from mainframed's
https://github.com/mainframed/TSO-Brute and most of the credit goes to him If
you want to brute TSO usernames/passwords rather use his psiotik tool
https://github.com/mainframed/psikotik Two most useful improvements are the
error-aware safe_send and find_response extensions of py3270

The original was GPL'ed and hence so is this

Dominic White @singe dominic () sensepost.com

Usage
-----
	Usage: mainframe_bruter.py [-h] -x TARGET [-t] [-v] [-c] [-s SLEEP] [-u USERFILE] [-p PASSFILE] [-a APPFILE] [-i TRANSFILE] [-m] [-e] [-q]
	
	z/OS Mainframe Bruteforcer
	
	optional arguments:
	
	  -h, --help            show this help message and exit
	  -x TARGET, --target TARGET
							Target IP address or Hostname and port: TARGET[:PORT] default port is 23
	  -t, --tso             Enable TSO user brute forcing
	  -v, --vtam            Enable VTAM APPLID brute forcing
	  -c, --cics            Enable CICS transID brute forcing
	  -s SLEEP, --sleep SLEEP
	                        Seconds to sleep between actions (increase on slower
	                        systems). The default is 0 seconds.
	  -u USERFILE, --userfile USERFILE
	                        File containing list of usernames
	  -p PASSFILE, --passfile PASSFILE
	                        File containing list of passwords
	  -a APPFILE, --appfile APPFILE
	                        File containing list of APPLIDs
	  -i TRANSFILE, --transfile TRANSFILE
	                        File containing list of TRANSIDs
	  -m, --moviemode       Enables ULTRA AWESOME Movie Mode. Watch the system get hacked in real time!
	  -e, --enumerate       Enables TSO Enumeration Mode Only. Default is password brute force mode
	  -q, --quiet           Only display found users / found passwords

Example
-------

	./mainframe_bruter.py -x my.mainframe.com:992 -v -a applids_quick.txt
	
	[+] z/OS Mainframe Bruteforcer
	[+] Target Acquired		: 74.168.206.164
	[+] APPLID Bruting		: Enabled
	[+] APPLID File			: applids_quick.txt
	[+] Slowdown is			: 0
	[+] Attack platform		: Darwin
	[+] ULTRA Hacker Movie Mode	: Disabled
	[+] Connecting to 74.168.206.164
	[+] Checking if in VTAM
	
		[+] Starting APPLID Enumeration
		[*] APPLID: TSO APPLID Found!
		[*] MACRO: TSO MACRO Found!
		[*] MACRO: LOGON MACRO Found!
		[!] MACRO: L CICS Invalid (bad response)
		[!] MACRO: OVMS Invalid (bad response)
		[!] MACRO: CICS Invalid (bad response)
		[!] MACRO: IMS Invalid (bad response)
	
	[*] Found 3 valid APPLIDs:
		APPLID -> TSO
		MACRO -> TSO
		MACRO -> LOGON

APPLID File
-----------

In the APPLID file, an entry preceeded with an exclamation mark (!) will be attempted as a direct command, otherwise it will be attempted as a full LOGON APPLID('x') command. For example, if we had an APPLID brute file containing the entries:

TSO
!TSO

The tool would attempt the following commands:

LOGON APPLID(TSO)
TSO

Screenshotter
=============

As an added bonus the screenshotter tool is included. Screenshotter is a tool
to take a screenshot of a TN3270 screen. It will do so and output an HTML file
of the same name as the host and port provided.


By Dominic White @singe dominic () sensepost.com

Original credit goes to Mainframed and TSO-Brute
https://github.com/mainframed/TSO-Brute Actually, he has a NMAP script to do
this for you
https://github.com/mainframed/NMAP/blob/master/3270_screen_grab.nse

Usage
-----

	usage: screenshotter.py [-h] -t TARGET [-s SLEEP] [-m] [-q]
	
	z/OS Mainframe Screenshotter
	
	optional arguments:
	
	  -h, --help            show this help message and exit
	  -t TARGET, --target TARGET
	                        Target IP address or Hostname and port: TARGET[:PORT]
	                        default port is 23
	  -s SLEEP, --sleep SLEEP
	                        Seconds to sleep between actions (increase on slower
	                        systems). The default is 0 seconds.
	  -m, --moviemode       Enables ULTRA AWESOME Movie Mode. Watch the system get
	                        hacked in real time!
	  -q, --quiet           Be more quieter

Get to it!

Example
-------

A sample invocation could be:

cat mainframes.txt|xargs -P10 -I% ./screenshotter.py -t %

This will start 10 threads to take screenshots of all the pretty screens.
