import socket

def send_request(host, port, path):
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connect to the server
        s.connect((host, port))
        
        # Send the request
        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\n\r\n"
        s.sendall(request.encode())
        
        # Receive response
        response = b""
        while True:
            data = s.recv(1024)
            if not data:
                break
            response += data
        
        # Print the response
        print(response.decode())

# Change these values as per your server configuration
host = 'localhost'
port = 8001  # Change to the port your server is running on
path = '/producer'  # Specify the path: /producer, /consumer, or /both

# Send request
send_request(host, port, path)
