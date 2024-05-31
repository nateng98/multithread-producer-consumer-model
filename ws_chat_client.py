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
                        help="whether to print verbose output. Defaults to false.")
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
    
    try:
        # TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # perform websocket handshake
        perform_handshake(host, port, role, sock)
        
        # handle role (client type)
        t = Thread(target=websocket_listener, args=(sock, role))
        t.start()
        
        if role in ['producer', 'both']:
            send_mess_t = Thread(target=handle_sending_message, args=(sock,))
            send_mess_t.start()
            send_mess_t.join()
        
        t.join()
          
    except Exception as e:
        print(f'Error: {e}')
    finally:
        try:
            send_frame(sock, a2lib.wslib.Opcode.CLOSE)
        except:
            pass
        sock.close()
        print("Connection closed.")
        print("Exiting successfully.")  

# Handshake protocol   
def perform_handshake(host, port, role, sock):
    request, websocket_key = establish_handshake(host, port, role)
    sock.sendall(request.serialize())
    response = a2lib.httplib.get_http_response(sock)
    validate_handshake(response, websocket_key)
    
def establish_handshake(host, port, role):
    websocket_key = b64encode(os.urandom(16))
    headers = {
        "Host": f"{host}:{port}",
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-Websocket-Key": f"{websocket_key.decode('utf-8')}",
        "Sec-Websocket-Protocol": "chat",
        "Sec-Websocket-Version": "13"
    }
    request = a2lib.httplib.HttpRequest("GET", f"/{role}", headers)
    return request, websocket_key
    
def validate_handshake(response: a2lib.httplib.HttpResponse, websocket_key: bytes):
    if response.status != HTTPStatus.SWITCHING_PROTOCOLS:
        raise Exception("Invalid handshake response")
    
    accept_key = response.headers["Sec-WebSocket-Accept"]
    expected_key = b64encode(sha1((websocket_key + a2lib.wslib.MAGIC_VAL)).digest()).decode('utf-8')
    if accept_key != expected_key:
        raise Exception("Invalid Sec-WebSocket-Accept")

# send, receive & close frames
def send_frame(sock, opcode, payload=b''):
    frame = a2lib.wslib.Frame(opcode, payload)
    serialized_frame = a2lib.wslib.serialize_frame(frame)
    sock.sendall(serialized_frame)

def receive_frame(sock):
    frame_data = sock.recv(a2lib.httplib._RECV_BUFFER_SIZE)
    frame = a2lib.wslib.parse_frame(frame_data)
    if frame:
        return frame
    else:
        raise Exception("Failed to parse frame")
    
def close_frame(sock, frame):
    # wrap close object with a close frame
    close_frame = a2lib.wslib.wrap_close(a2lib.wslib.parse_close(frame))
    # then let the server know that the client side is closing
    sock.sendall(a2lib.wslib.serialize_frame(close_frame))

# send PONG response
def pong_response(sock, frame):
    if frame.opcode == a2lib.wslib.Opcode.PING:
        # print(f"server sent: 0x{frame.opcode} \nclient sent: 0x{a2lib.wslib.Opcode.PONG}")
        send_frame(sock, a2lib.wslib.Opcode.PONG, frame.data)
    elif frame.opcode == a2lib.wslib.Opcode.CLOSE:
        # print(f"server sent: 0x{frame.opcode}")
        close_frame(sock, frame)
        return True
    return False

# handle roles
# handle consumer
def handle_consumer(sock, frame):
    try:
        if frame.opcode == a2lib.wslib.Opcode.TEXT:
            message = frame.data.decode('utf-8')
            print(message)
    except (KeyboardInterrupt, EOFError):
        send_frame(sock, a2lib.wslib.Opcode.CLOSE)

# handle producer and both
def handle_sending_message(sock):
    while True:
        try:
            message = input()
            send_frame(sock, a2lib.wslib.Opcode.TEXT, message.encode('utf-8'))
        except WakingMainThread:
            pass
        except Exception as e:
            print(f"Input Error: {e}")
            continue

# helper functions
def websocket_listener(sock, role):
    try:
        while True:
            frame = receive_frame(sock)
            # pong_response return True when opcode is CLOSE
            if pong_response(sock, frame):
                break
            if role in ['consumer', 'both']:
                handle_consumer(sock, frame)
    except WakingMainThread:
        pass
    # except Exception as e:
    #     print(f"Websocket Error: {e}")
    finally:
        MainThreadWaker.main_awake()

if __name__ == "__main__":
    main()