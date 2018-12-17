'''Simple client program'''
import socket
import sys

HOST = 'localhost'
PORT = 4300


def main(name: str):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print('Connected to {}:{}'.format(HOST, PORT))
        # This sends the name passed in as cmd line argument through the socket. (I assume)
        s.sendall("{}".format(name).encode())
        # Below we receive data from the server greeting the user. Also 1024bytes.
        data = s.recv(1024)
        print('Received: {}'.format(data.decode()))
        # Close the socket.
        s.close()
        print('Connection closed')


if __name__ == '__main__':
    main(sys.argv[1])
