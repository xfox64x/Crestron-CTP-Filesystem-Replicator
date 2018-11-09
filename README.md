# Crestron-CTP-Filesystem-Replicator
A script for recursively pulling files from a Crestron device using CTP.

## What it is
A highly cannibalized copy of @StephenGenusa "Crestron Device Documenter" (sorry for the comments, in advance), made to automate the process of copying files from a Crestron device to the local filesystem. My hands got tired of copy-paste, so this abomination happened... Overall functionality is questionable. I went down a bunch of rabbit-holes while ripping appart Crestron Device Documenter, losing sight of the end goal more than once. It's largely untested and could lead to general unresponsiveness. A few test devices had no issue surrendering all files. One test device stopped FTP'ing files after a few days of testing.

## What it do
Establishes a Crestron Toolbox Protocol (CTP) session via Paramiko SSH or basic TCP socket, creates a local pyftpdlib FTP server, does a recursive directory listing in the CTP session, creates a matching local directory structure, and calls the CTP FPUTfile command, telling the Crestron device to FTP found files to the local pyftpdlib FTP server.
