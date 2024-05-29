#!/usr/bin/python3

# started with https://docs.python.org/3/library/socket.html#example

# chat-hopper!
# Give the message to the next person

import select
import socket
import sys

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 8998 		  # Arbitrary non-privileged port

lastWord = "F1rst p0st"

receiving = []

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # blocking, by default
    # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # overall timeout
    #s.settimeout(5)
    # or, set non-blocking
    #s.setblocking(False)
    s.bind((HOST, PORT))
    s.listen()

    receiving.append(s)

    print(f'Port: {PORT}')
    while True:
        try:
            r_ready, _, _ = select.select(receiving, [], [])

            for r in r_ready:
                if r == s:
                    # Server socket is ready to accept a new connection
                    try:
                        # print("Waiting for new connection")
                        conn, addr = r.accept()
                        # I can set a timeout here, for the client socket, too.
                        # conn.settimeout(5)
                        print('Connected by', addr)
                        receiving.append(conn)
                    except Exception as e:
                        print("Something happened... I guess...")
                        print(e)
                else:
                    # Client socket has data for me!  
                    data = r.recv(1024)
                    print(data)
                    if data:
                        print('swapping')
                        currWord = lastWord
                        lastWord = data.strip()
                    if type(currWord) == bytes:
                        r.sendall(currWord)
                    else:
                        r.sendall(currWord.encode())
                    r.sendall(b'\nBye!\n')
                    r.close()
                    receiving.remove(r)
        except KeyboardInterrupt as e:
            print("RIP")
            # clean up socket
            s.close() # with does this? Maybe? But we're inside it?
            sys.exit(0)
        except OSError as e:
            pass


