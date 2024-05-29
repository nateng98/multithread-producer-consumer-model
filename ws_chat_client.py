import argparse
import os
import random
import select
import signal
import socket
import sys
import time
import traceback
from base64 import b64encode
from hashlib import sha1
from http import HTTPStatus
from threading import Thread

import a2lib.httplib
import a2lib.wslib
from a2lib.consolelib import *
from a2lib.main_thread_waker import MainThreadWaker, WakingMainThread


def main():
    parser = argparse.ArgumentParser(description="WebSocket chat client.")
    parser.add_argument('host', type=str,
                        help="the port to bind to. Setting to 0 will randomly assign.")
    parser.add_argument('port', type=int,
                        help="the port to bind to. Setting to 0 will randomly assign.")
    parser.add_argument('role', type=str, choices=['producer', 'consumer', 'both'],
                        help="the role that the client should take: 'producer', 'consumer', or 'both'.")
    parser.add_argument('-v', '--verbose', action="store_true",
                        help="whether to print_above_prompt verbose output. Defaults to false.")
    parser.add_argument('-t', '--timeout', type=float, default=20.0,
                        help="How long to wait for responses from the server.")
    args = parser.parse_args()

    # See assignment description and main_thread_waker_example.py for details
    # on how to use this if you need it. It can stay here harmlessly until you
    # decide if/how you do!
    MainThreadWaker.register()
    
    # getting all the arguments
    host = args.host
    port = args.port
    role = args.role
    verbose = args.verbose
    timeout = args.timeout

    # TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    # perform websocket handshake
    perform_handshake(sock)

    print("Exiting successfully.")  
    
def perform_handshake():
        
    
def establish_handshake():
    print('establish')
    
def validate_handshake():
    print('validate')

if __name__ == "__main__":
    main()