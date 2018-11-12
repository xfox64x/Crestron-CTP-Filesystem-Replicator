# Crestron-CTP-Filesystem-Replicator
A script for recursively pulling files from a Crestron device using CTP.

## What it is
A highly cannibalized copy of @StephenGenusa "Crestron Device Documenter" (sorry for the comments, in advance), made to automate the process of copying files from a Crestron device to the local filesystem. My hands got tired of copy-paste, so this abomination happened... Overall functionality is questionable. I went down a bunch of rabbit-holes while ripping appart Crestron Device Documenter and thinking about that Crestron presentation at the last DEFCON, losing sight of the end goal more than once. It's largely untested and could lead to general unresponsiveness. A few test devices had no issue surrendering all files. One test device stopped FTP'ing files after a few days of testing. If anything, here's another script someone else can rip apart to make something better.

## What it do
Establishes a Crestron Toolbox Protocol (CTP) session via Paramiko SSH or basic TCP socket, creates a local pyftpdlib FTP server, does a recursive directory listing in the CTP session, creates a matching local directory structure, and calls the CTP FPUTfile command, telling the Crestron device to FTP found files to the local pyftpdlib FTP server.

## How to do it
### Requirements:
- Python 2.7 (Haven't tried 3, but I think everything's written in a version-agnostic way)
- paramiko (pip install)
- pyftpdlib (pip install)

### Command line args:
```
  -h, --help            show this help message and exit
  -i IP_ADDRESS, --ip-address IP_ADDRESS
                        IP address of Crestron device to replicate.
  -d, --dry-run         Do recursive dir and print FPUTfile commands; skip
                        downloading and modifying local filesystem.
  -f FTP_SERVER, --ftp-server FTP_SERVER
                        IP address/hostname of FTP server the Crestron Device
                        will export files to.
  -s, --force-ssh       Force use of SSH rather than CTP 41795.
  -u USERNAME, --username USERNAME
                        Authentication user name.
  -p PASSWORD, --password PASSWORD
                        Authentication password.
  -fd FTP_DIR, --ftp-dir FTP_DIR
                        Directory where FTP server will place transferred files.
  -fp FTP_PASSWORD, --ftp-password FTP_PASSWORD
                        Local/Remote FTP server password.
  -fu FTP_USERNAME, --ftp-username FTP_USERNAME
                        Local/Remote FTP server username.
  -lfs, --local-ftp-server
                        Start a local FTP server.
  -lfi LOCAL_FTP_INTERFACE, --local-ftp-interface LOCAL_FTP_INTERFACE
                        Local FTP server interface (defaults to all local
                        interfaces).
  -lfp LOCAL_FTP_PORT, --local-ftp-port LOCAL_FTP_PORT
                        Local FTP server port (defaults to 21).
```

### Usage
So, usage of the command line args doesn't really make a lot of sense, in retrospect... I guess I was thinking "maybe there's a legit case where the FTP server isn't on my host", but that wouldn't really work - the Crestron devices tested seemed incapable of creating missing FTP directories on the FTP server... The FTP server bits were thrown in, after everything else had been written. The LOCAL_FTP_INTERFACE and LOCAL_FTP_PORT args were kept separate from FTP_SERVER because I was thinking of a few one-off situations that don't matter.

If I wanted to download all files from Crestron device 192.168.1.10 to "C:\Crestron\" on my local host 192.168.1.5:21, I'd probably do something like:
```
CrestronFilesystemReplicator.py -i 192.168.1.10 -f 192.168.1.5 -fd "C:\Crestron\" -lfs
```

Or I'd do the command listing, first, just to see how many things are about to happen:
```
CrestronFilesystemReplicator.py -i 192.168.1.10 -f 192.168.1.5 -fd "C:\Crestron\" -d
```

You can use -fp and -fu if your FTP server has creds OR, if using the local FTP server options (-lfs), a temporary user will be created with the supplied creds. Could be useful if you're worried about anyone else touching the local FTP server and filesystem. I know I don't care. YOLO anonymouse FTP servers for the lazy.
