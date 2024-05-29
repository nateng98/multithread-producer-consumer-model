import argparse
import socket
import threading
import os
from base64 import b64encode
from hashlib import sha1
from http import HTTPStatus
from collections import defaultdict
from websockets import frames
from a2lib.httplib import HttpRequest, HttpResponse, get_http_response

_RECV_BUFFER_SIZE = 4096

def build_handshake_request(host, port, client_type):
    key = b64encode(os.urandom(16)).decode('utf-8')
    headers = defaultdict(str)
    headers["Host"] = f"{host}:{port}"
    headers["Upgrade"] = "websocket"
    headers["Connection"] = "Upgrade"
    headers["Sec-WebSocket-Key"] = key
    headers["Sec-WebSocket-Version"] = "13"
    request = HttpRequest("GET", f"/{client_type}", headers)
    return request, key

def validate_handshake_response(response: HttpResponse, key: str):
    if response.status != HTTPStatus.SWITCHING_PROTOCOLS:
        raise Exception("Invalid handshake response")

    accept_key = response.headers["Sec-WebSocket-Accept"]
    expected_accept = b64encode(sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode('utf-8')).digest()).decode('utf-8')
    if accept_key != expected_accept:
        raise Exception("Invalid Sec-WebSocket-Accept key")

def handle_heartbeat(sock: socket.socket, frame: frames.Frame):
    if frame.opcode == frames.Opcode.PING:
        sock.sendall(frames.Pong(frame.data).serialize())
    elif frame.opcode == frames.Opcode.PONG:
        pass

def handle_close(sock: socket.socket, frame: frames.Frame):
    sock.sendall(frames.Close(frame.data).serialize())
    sock.close()

def consumer(sock: socket.socket):
    buffer = b''
    while True:
        data = sock.recv(_RECV_BUFFER_SIZE)
        if not data:
            break
        buffer += data
        while True:
            try:
                frame, buffer = frames.Frame.parse(buffer, mask=False)
                if frame.opcode == frames.Opcode.TEXT:
                    print(frame.data.decode('utf-8'))
                elif frame.opcode in [frames.Opcode.PING, frames.Opcode.PONG]:
                    handle_heartbeat(sock, frame)
                elif frame.opcode == frames.Opcode.CLOSE:
                    handle_close(sock, frame)
                    return
            except frames.PayloadTooShort:
                break

def producer(sock: socket.socket):
    while True:
        try:
            message = input()
            if message.lower() == "/quit":
                sock.sendall(frames.Close().serialize())
                break
            sock.sendall(frames.Text(message).serialize())
        except EOFError:
            break

def main():
    parser = argparse.ArgumentParser(description="WebSocket Chat Client")
    parser.add_argument("host", type=str, help="Server host")
    parser.add_argument("port", type=int, help="Server port")
    parser.add_argument("type", choices=["producer", "consumer", "both"], help="Client type")
    args = parser.parse_args()

    host = args.host
    port = args.port
    client_type = args.type

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    request, key = build_handshake_request(host, port, client_type)
    sock.sendall(request.serialize())
    response = get_http_response(sock)
    validate_handshake_response(response, key)

    if client_type == "consumer":
        consumer(sock)
    elif client_type == "producer":
        producer(sock)
    elif client_type == "both":
        producer_thread = threading.Thread(target=producer, args=(sock,))
        consumer_thread = threading.Thread(target=consumer, args=(sock,))
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()

    sock.close()

if __name__ == "__main__":
    main()