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

stop_thread = False

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
        
        # Print the connection message
        print_color("Connected (press CTRL+C to quit)", "\033[0;32;49m")
        
        # handle role (client type)
        if role == "producer":
            handle_producer(sock, timeout)
        elif role == "consumer":
            handle_consumer(sock, timeout)
        elif role == "both":
            handle_both(sock, timeout)
            
    except Exception as e:
        print(f"Error: {e}")
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
        send_frame(sock, a2lib.wslib.Opcode.PONG, frame.data)
    elif frame.opcode == a2lib.wslib.Opcode.CLOSE:
        close_frame(sock, frame)
        return True
    return False

# helpers
# take user message
def handle_user_input(sock, timeout):
    global stop_thread
    end_time = time.time() + timeout
    # initialize the first '>'
    sys.stdout.write('> ')
    sys.stdout.flush()
    while not stop_thread and time.time() < end_time:
        try:
            if select.select([sys.stdin], [], [], 1)[0]:
                sys.stdout.write('> ')
                sys.stdout.flush()
                message = input()
                
                # Attempt to encode, handle potential errors
                try:
                    message_encoded = message.encode('utf-8')
                except UnicodeEncodeError:
                    print("Error: Invalid characters detected. Please enter text using a compatible encoding.")
                    sys.stdout.write('> ')
                    sys.stdout.flush()
                    continue  # Skip to next iteration of the loop
                
                if message:  # Only send if there's actual input
                    send_frame(sock, a2lib.wslib.Opcode.TEXT, message_encoded)
                    end_time = time.time() + timeout  # Reset timeout
        except (KeyboardInterrupt, EOFError):
            break
    if time.time() >= end_time:
        print("\nTimeout reached, closing client side...")
        stop_thread = True

# get server frame (no messages from other users/clients)
def handle_server_frames(sock):
    global stop_thread
    while not stop_thread:
        try:
            # Receive frame from server
            frame = receive_frame(sock)
            if frame.opcode == a2lib.wslib.Opcode.PING:
                pong_response(sock, frame)
            elif frame.opcode == a2lib.wslib.Opcode.CLOSE:
                stop_thread = True
                close_frame(sock, frame)
                return True  # Exit the loop on close frame
        except Exception as e:
            print(f"Error handling server frames: {e}")
            break

# get server frame as well as message sent to server by other users/clients
def handle_server_frames_both(sock):
    global stop_thread
    while not stop_thread:
        try:
            # Receive frame from server
            frame = receive_frame(sock)
            if frame.opcode == a2lib.wslib.Opcode.PING:
                pong_response(sock, frame)
            elif frame.opcode == a2lib.wslib.Opcode.CLOSE:
                stop_thread = True
                close_frame(sock, frame)
                return True  # Exit the loop on close frame
            elif frame.opcode == a2lib.wslib.Opcode.TEXT:
                # make a newline and clear '>' for incoming messages
                sys.stdout.write("\n\033[F\033[K")
                print_color(f"< {frame.data.decode('utf-8')}", "\033[0;34;49m")
                sys.stdout.write('> ')  # Reprint the input prompt
                sys.stdout.flush()
        except Exception as e:
            print(f"Error handling server frames: {e}")
            break

# handle roles
def handle_producer(sock, t_out):
    # Create threads for handling user and server frames
    user_thread = Thread(target=handle_user_input, args=(sock, t_out))
    user_thread.daemon = True
    server_thread = Thread(target=handle_server_frames, args=(sock,))
    
    def handle_ctrl_c(sig, frame):
        global stop_thread
        stop_thread = True
        user_thread.join(timeout=0)
        server_thread.join(timeout=0)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_ctrl_c)

    # Start the threads
    user_thread.start()
    server_thread.start()

    # wait for server thread but not user thread
    server_thread.join()
    
    if user_thread.is_alive():
        user_thread.join(timeout=0)

def handle_consumer(sock, t_out):
    end_time = time.time() + t_out
    while True and time.time() < end_time:
        try:
            # Use select to check if the socket is ready for reading
            ready, _, _ = select.select([sock], [], [], t_out)
            if sock in ready:
                frame = receive_frame(sock)
                if pong_response(sock, frame):
                    break
                if frame.opcode == a2lib.wslib.Opcode.TEXT:
                    print_color(f"< {frame.data.decode('utf-8')}", "\033[0;34;49m")
                    end_time = time.time() + t_out  # Reset timeout
        except (KeyboardInterrupt, EOFError):
            break
    if time.time() >= end_time:
        print("\nTimeout reached, closing client side...")
        return True

def handle_both(sock, t_out):
    # Create threads for handling user and server frames
    user_thread = Thread(target=handle_user_input, args=(sock, t_out))
    user_thread.daemon = True
    server_thread = Thread(target=handle_server_frames_both, args=(sock,))
    
    def handle_ctrl_c(sig, frame):
        global stop_thread
        stop_thread = True
        user_thread.join(timeout=0)
        server_thread.join(timeout=0)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_ctrl_c)

    # Start the threads
    user_thread.start()
    server_thread.start()

    # Wait for server thread but not user thread
    server_thread.join()
    
    if user_thread.is_alive():
        user_thread.join(timeout=0)
        
# styling
def print_color(str, styling):
    # coloring text on console
    # https://www.kaggle.com/discussions/general/273188
    reset = "\033[0m"
    print(f"{styling}{str}{reset}")

if __name__ == "__main__":
    main()