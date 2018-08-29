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
        data = s.recv(1024)
        print('Received: {}'.format(data.decode()))
        s.close()
        print('Connection closed')


if __name__ == '__main__':
    main(sys.argv[1])
