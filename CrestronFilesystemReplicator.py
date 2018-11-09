#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import argparse
import os
import paramiko
import re
import socket
import urllib

from time import sleep
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

SSH_PORT = 22
CTP_PORT = 41795
MAX_RETRIES = 3
BUFF_SIZE = 20000
SOCKET_TIMEOUT = 5.0
GLOBAL_SLEEP_VALUE = 0.5
CR = "\r"

"""
A class for interacting with Crestron devices over CTP.
"""
class CrestronDevice(object):
    
    def __init__(self, args):
        self.args = args
        self.console_prompt = ""
        self.device_ip_address = self.args.ip_address
        self.dry_run = self.args.dry_run
        self.forcessh = self.args.force_ssh
        self.ftp_output_path = self.args.ftp_dir
        self.ftp_server = None
        self.ftp_server_ip_address = self.args.ftp_server
        self.local_path = self.args.ftp_dir
        
        self.sshclient = None
        self.sock = None
        
    def start_ftp_server(self):
        if not self.dry_run and self.args.local_ftp_server:
            self.ftp_server = None
            try:
                handler = FTPHandler
                authorizer = DummyAuthorizer()
                
                if(self.args.ftp_username and self.args.ftp_username != ""):
                    authorizer.add_user(self.args.ftp_username, self.args.ftp_password, self.ftp_output_path, perm='elradfmwMT')
                else:
                    authorizer.add_anonymous(self.ftp_output_path, perm='elradfmwMT')
                
                handler.authorizer = authorizer
                self.ftp_server = ThreadedFTPServer((self.args.local_ftp_interface, self.args.local_ftp_port), handler)
                self.ftp_server.serve_forever(blocking=False)
                
                if self.args.local_ftp_interface == "":
                    print("Started local FTP server: ::%s" % (self.args.local_ftp_port))
                else:
                    print("Started local FTP server: %s:%s" % (self.args.local_ftp_interface, self.args.local_ftp_port))
                    
            except:
                if self.args.local_ftp_interface == "":
                    print("Failed to start local FTP server on: ::%s" % (self.args.local_ftp_port))
                else:
                    print("Failed to start local FTP server on: %s:%s" % (self.args.local_ftp_interface, self.args.local_ftp_port))
                exit()
                
    def stop_ftp_server(self):
        if self.ftp_server:
            print("[*] Stopping local FTP server...")
            try:
                self.ftp_server.close_all()
                print("[+] Local FTP server stopped.")
            except:
                print("[-] Failed to stop local FTP server.")
                pass
            
    def open_device_connection(self):
        if self.forcessh:
            print("[*] Establishing Paramiko SSH session with %s:%s ..." % (self.device_ip_address, SSH_PORT))
            self.sshclient = paramiko.client.SSHClient()
            try:
                self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.sshclient.load_system_host_keys()
                self.sshclient.connect(self.device_ip_address, port=22, username=self.args.username, password=self.args.password, timeout=SOCKET_TIMEOUT)
                print("[+] Successfully established Paramiko SSH session.")
                return True
            except:
                self.sshclient = None
                print("[-] Error: Unable to establish Paramiko SSH session with device.")
                return False
                
        else:
            print("[*] Establishing CTP session with %s:%s ..." % (self.device_ip_address, CTP_PORT))
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(SOCKET_TIMEOUT)
                self.sock.connect((self.device_ip_address, CTP_PORT))
                print("[+] Successfully established CTP session.")
                return True
            except:
                self.sock = None
                print("[-] Error: Unable to establish CTP session with device.")
                return False

    def close_device_connection(self):
        print("[*] Shutting down device connections...")
        if self.sshclient:
            try:
                self.sshclient.close()
                print("[+] Closed Paramiko SSH session.")
            except:
                print("[-] Failed to close Paramiko SSH session.")
                pass
        
        if self.sock:
            try:
                self.sock.close()
                print("[+] Closed CTP session.")
            except:
                print("[-] Failed to close CTP session.")
                pass
            
            
    def get_console_prompt(self):
        """
        Determine the device console prompt
        """
        data = ""
        for _unused in range(0, MAX_RETRIES):
            if self.sshclient:
                stdin,stdout,stderr=self.sshclient.exec_command("ver")
                data = str(stdout.readlines())
                search = re.findall("([\w-]{3,30})\ ", data, re.MULTILINE)
            else:
                self.sock.sendall(CR+CR)
                data += self.sock.recv(BUFF_SIZE)
                search = re.findall("[\n\r]([\w-]{3,30})>", data, re.MULTILINE)
            
            sleep(GLOBAL_SLEEP_VALUE)
            if search:
                self.console_prompt = search[0]
                print("[!] Console prompt is: %s" % (self.console_prompt))
                
                if self.console_prompt == "MERCURY":
                    print("[-] Mercury currently unsupported due to Crestron engin.err.uity (I guess...).")
                    return False
                
                self.ftp_output_path = os.path.join(self.local_path, ("Crestron_Device_%s" % (self.console_prompt)))
                if not os.path.isdir(self.ftp_output_path) and not self.dry_run and self.args.local_ftp_server:
                    try:
                        os.makedirs(self.ftp_output_path)
                    except:
                        self.ftp_output_path = os.path.join(self.local_path, ("Crestron_Device_%s" % (self.device_ip_address)))
                        try:
                            os.makedirs(self.ftp_output_path)
                        except:
                            self.ftp_output_path = self.local_path
                
                print("[+] Crestron local FTP working directory set to:\r\n\t%s\r\n" % (self.ftp_output_path))
                
                return True
        print("[-] Console prompt not found on device.")
        return False

    def find_console_prompt(self, data, key_value="", minimum_next_prompt_location=0, maximum_next_prompt_location=0, return_position=False, reverse=False):
        """
        Description:    Monolithic function for locating and verifying the presence of a supplied key value.
        Parameters:     data - the string value to check for the key_value.
                        key_value - either a string to look for or an empty string.
                            If a non-empty string is supplied, data is checked for the supplied value.
                            If an empty string is supplied, data is checked for the presence of the console_prompt.
                        minimum_next_prompt_location - the position to start searching for the key_value.
                            Default value of 0 means the whole string is checked.
                        maximum_next_prompt_location - the position to stop searching for the key_value.
                            Default value of 0 means everything past the minimum_next_prompt_location is checked.
                        return_position - returns the position of the key_value instead of a bool.
                        reverse - use rfind instead of find, to find the highest index of key_value.
        Output:         Returns True if the key_value is found in data, at the minimum_next_prompt_location supplied.
        """
        # If the minimum_next_prompt_location specifies a location outside of the data string, return -1 if looking for a position or
        #   return False, signifying that the key_value was not found.
        if minimum_next_prompt_location >= len(data) or minimum_next_prompt_location < 0:
            if return_position:
                return -1
            else:
                return False
                
        # If the maximum_next_prompt_location comes before the minimum_next_prompt_location or is less than 0, set it to the length of the data.
        if maximum_next_prompt_location <= minimum_next_prompt_location or maximum_next_prompt_location < 0:
            # Purposefully overshooting the end of the string in case minimum_next_prompt_location is or is near the end of the string.
            # Doesn't really matter if this value is larger than the actual data value.
            maximum_next_prompt_location = len(data)
            
        # If no key_value supplied, use the console prompt as the key_value.
        if not key_value or key_value == "":
            key_value = ("%s>" % (self.console_prompt))
            
        if return_position:
            if reverse:
                return data.rfind(key_value, minimum_next_prompt_location, maximum_next_prompt_location)
            else:
                return data.find(key_value, minimum_next_prompt_location, maximum_next_prompt_location)
        else:
            return data.find(key_value, minimum_next_prompt_location, maximum_next_prompt_location) != -1
    
    def remove_prompt(self, data, char_limit=0):
        """
        Remove the console prompt from the text within the specified character limit.
        """
        # If 0, remove the first occurrence of the prompt.
        if char_limit == 0:
            return data.replace(self.console_prompt+">", "", 1)
            
        # If less than 0, remove all instances of the prompt.
        elif char_limit <= 0:
            return data.replace(self.console_prompt+">", "")

        # Else if the first console prompt is found within the first char_limit characters, remove it.
        elif data.find(self.console_prompt+">") < char_limit:
            return data.replace(self.console_prompt+">", "", 1)
        
        return data

    def send_command_wait_prompt(self, command, minimum_next_prompt_location=0, done_string=""):
        """
        Send a command and wait for the following console prompt or done_string to appear.
        """
        if self.sshclient:
            stdin,stdout,stderr=self.sshclient.exec_command(command)
            data = stdout.readlines()
            data = "".join(data)
        else:
            data = ""
            is_checking_for_data = False
            
            wait_count = 0
            
            self.sock.sendall((CR+command+CR))
            sleep(GLOBAL_SLEEP_VALUE)
            
            data = (self.sock.recv(BUFF_SIZE)).replace((CR+command+CR), "")
            sleep(GLOBAL_SLEEP_VALUE)
            
            last_data_length = len(data)
            data_check_count = 0
            if done_string and done_string != "":
                is_checking_for_data = (not self.find_console_prompt(data, done_string))
            else:
                is_checking_for_data = (not self.find_console_prompt(data, minimum_next_prompt_location=minimum_next_prompt_location))
            
            while is_checking_for_data:
                # "Deal with newer firmware that executes commands / doesn't return a prompt instead of printing help"
                #   I'm not entirely sure what this means or looks like. It seems we're waiting for data that may or may not show up.
                #   If the recv errors, we send a return, though we also send a return every 5 iterations, regardless...
                #   We were also stuck in this while loop, waiting for a string that may never appear in the received data...
                
                try:
                    data += self.sock.recv(BUFF_SIZE)
                except:
                    self.sock.sendall(CR)
                sleep(GLOBAL_SLEEP_VALUE)
                
                wait_count += 1
                if wait_count == 5:
                    self.sock.sendall(CR)
                    sleep(GLOBAL_SLEEP_VALUE)
                    wait_count = 0
                    
                    # A shitty attempt at breaking the while loop.
                    # Every 5 loops, this segment execs, checking if the size of data has changed since the last 5 loops.
                    # If the size of the data hasn't changed in the last 15 loops, break out of the while loop.
                    # Results will vary.
                    data_check_count += 1
                    if data_check_count > 3 and last_data_length == len(data):
                        break
                    elif last_data_length != len(data):
                        data_check_count = 0
                    last_data_length = len(data)
                
                if done_string and done_string != "":
                    is_checking_for_data = (not self.find_console_prompt(data, done_string))
                else:
                    is_checking_for_data = (not self.find_console_prompt(data, minimum_next_prompt_location=minimum_next_prompt_location))
        return data
        
    def get_dir_listing(self, path=''):
        """
        Get a directory list for the supplied path. If no path supplied, lists out the root.
        """
        if path == '':
            path = '\\'
        data = self.send_command_wait_prompt(("dir %s" % (path)), 40)
        if not self.sshclient:
            return self.remove_prompt(data)
        else:
            return data.strip()
        
    def get_file(self, ftp_path, remote_path):
        """
        Get a file from the device using the FPUTfile command. This tells the device to FTP the file at remote_path
            to the supplied FTP server, at the ftp_path.
        """
        ftp_url = "ftp://%s%s" % (self.ftp_server_ip_address, urllib.quote(ftp_path))
        
        command = "FPUTfile %s \"%s\"" % (ftp_url, remote_path)
        
        if remote_path.find(" ") >= 0:
            command = "%s \"%s\"" % (command, remote_path)
        else:
            command = "%s %s" % (command, remote_path)
        
        if(self.args.ftp_username and self.args.ftp_username != ""):
            command = "%s %s:%s" % (command, self.args.ftp_username, self.args.ftp_password)
            
        print(command)
        
        if not self.dry_run:
            data = self.send_command_wait_prompt(command, done_string="End Progress")
        
    def replicate_filesystem(self, current_path=''):
        """
        Replicate the device's filesystem. Recursively lists and gets files from the device using get_dir_listing and get_file.
            Creates any necessary local directories, along the way.
        """
        if not os.path.isdir(self.ftp_output_path+current_path) and not self.dry_run and self.args.local_ftp_server:
            os.makedirs(self.ftp_output_path+current_path)
        
        data = self.get_dir_listing(current_path)
        directory_re = "\[DIR\]\s+\d+-\d+-\d+ \d+:\d+:\d+ (?P<directory_name>.+?)\r\n"
        file_re = "\d+\s+\d+-\d+-\d+ \d+:\d+:\d+ (?P<file_name>.+?)\r\n"
        
        for directory_name in re.findall(directory_re, data, re.MULTILINE):
            remote_directory_path = '\\'.join([current_path,directory_name])
            self.replicate_filesystem(remote_directory_path)
        
        for file_name in re.findall(file_re, data, re.MULTILINE):
            remote_file_path = '\\'.join([current_path,file_name])
            ftp_path = '/'.join([current_path.replace('\\','/'),file_name])
            data = self.get_file(ftp_path, remote_file_path)

if __name__ == "__main__":
    print("\nCrestron CTP Filesystem Replicator\n")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ip-address", help="IP address of Crestron device to replicate.")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Do recursive dir and print FPUTfile commands; skip downloading and modifying local filesystem.")
    parser.add_argument("-f", "--ftp-server", default="", type=str, help="IP address/hostname of FTP server the Crestron Device will export files to.")
    parser.add_argument("-s", "--force-ssh", action="store_true", help="Force use of SSH rather than CTP 41795.")
    parser.add_argument("-u", "--username", default="crestron", type=str, help="Authentication user name.")
    parser.add_argument("-p", "--password", default="", type=str, help="Authentication password.")
    parser.add_argument("-fd", "--ftp-dir", default="", type=str, help="Directory where FTP server will place transferred files.")
    parser.add_argument("-fp", "--ftp-password", default="", type=str, help="Local/Remote FTP server password.")
    parser.add_argument("-fu", "--ftp-username", default="", type=str, help="Local/Remote FTP server username.")
    parser.add_argument("-lfs", "--local-ftp-server", action="store_true", help="Start a local FTP server.")
    parser.add_argument("-lfi", "--local-ftp-interface", default="", type=str, help="Local FTP server interface (defaults to all local interfaces).")
    parser.add_argument("-lfp", "--local-ftp-port", default=21, type=int, help="Local FTP server port.")
    
    parser_args = parser.parse_args()
    
    if not parser_args.ip_address:
        parser.print_help()
        exit()
        
    if not parser_args.ftp_server or parser_args.ftp_server == "":
        print("[!] Error: IP address/hostname of FTP server the Crestron Device will export files to is required.")
        exit()
        
    if parser_args.ftp_dir == "":
        parser_args.ftp_dir = os.getcwd()
            
    device = CrestronDevice(parser_args)
    
    if device.open_device_connection():
        if device.get_console_prompt():
            try:
                device.start_ftp_server()
                device.replicate_filesystem()
            finally:
                device.close_device_connection()
                device.stop_ftp_server()
                
    device.stop_ftp_server()
