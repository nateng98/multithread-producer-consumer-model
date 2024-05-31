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
                        help="the host to connect to.")
    parser.add_argument('port', type=int,
                        help="the port to connect to.")
    parser.add_argument('role', type=str, choices=['producer', 'consumer', 'both'],
                        help="the role that the client should take: 'producer', 'consumer', or 'both'.")
    parser.add_argument('-v', '--verbose', action="store_true",
                        help="whether to print verbose output. Defaults to false.")
    parser.add_argument('-t', '--timeout', type=float, default=20.0,
                        help="How long to wait for responses from the server.")
    args = parser.parse_args()

    # Register the main thread waker
    MainThreadWaker.register()
    
    host = args.host
    port = args.port
    role = args.role
    verbose = args.verbose
    timeout = args.timeout

    try:
        # TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # Perform WebSocket handshake
        perform_handshake(host, port, role, sock)
        
        # Create and start the appropriate threads based on the role
        if role == 'producer':
            producer_thread = Thread(target=producer, args=(sock,))
            producer_thread.start()
            producer_thread.join()
        elif role == 'consumer':
            consumer_thread = Thread(target=consumer, args=(sock,))
            consumer_thread.start()
            consumer_thread.join()
        elif role == 'both':
            producer_thread = Thread(target=producer, args=(sock,))
            consumer_thread = Thread(target=consumer, args=(sock,))
            producer_thread.start()
            consumer_thread.start()
            producer_thread.join()
            consumer_thread.join()
    except WakingMainThread:
        print("Main thread woken, closing connection.")
    except Exception as e:
        print_above_prompt(f"Error: {e}")
    finally:
        try:
            send_frame(sock, a2lib.wslib.Opcode.CLOSE)
        except:
            pass
        sock.close()
        print("Connection closed.")
        print("Exiting successfully.")

# handle handshake mechanism
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

# send, receive and close frames
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
    close_frame = a2lib.wslib.wrap_close(a2lib.wslib.parse_close(frame))
    sock.sendall(a2lib.wslib.serialize_frame(close_frame))
    
# send pong response - maintain heartbeat
def pong_response(sock, frame):
    if frame.opcode == a2lib.wslib.Opcode.PING:
        send_frame(sock, a2lib.wslib.Opcode.PONG, frame.data)
    elif frame.opcode == a2lib.wslib.Opcode.CLOSE:
        close_frame(sock, frame)
        MainThreadWaker.wake_main_thread()
        return True
    return False

# handle roles
def producer(sock):
    while True:
        try:
            message = input("Enter message: ")
            send_frame(sock, a2lib.wslib.Opcode.TEXT, message.encode('utf-8'))
        except Exception as e:
            print_above_prompt(f"Producer error: {e}")
            break

def consumer(sock):
    while True:
        try:
            frame = receive_frame(sock)
            if frame.opcode == a2lib.wslib.Opcode.TEXT:
                print(f"Received message: {frame.data.decode('utf-8')}")
            elif pong_response(sock, frame):
                break
        except Exception as e:
            print_above_prompt(f"Consumer error: {e}")
            break

if __name__ == "__main__":
    main()