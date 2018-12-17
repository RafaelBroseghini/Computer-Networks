'''
GEO TCP Client
'''
#!/usr/bin/env python3

from socket import socket, AF_INET, SOCK_STREAM

HOST = 'localhost'
PORT = 4300


def client():
    '''Main client loop'''
    # TODO: Implement client-side tasks
    with socket(AF_INET, SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print('Connected to {}:{}'.format(HOST, PORT))

        target = input(">Enter a country or BYE to quit: \n")

        while target != "BYE":
            s.sendall("{}".format(target).encode())
            data = s.recv(1024)

            print('+{}'.format(data.decode()))
            target = input(">Enter a country or BYE to quit: \n")

        # Close the socket.
        s.close()
        print('Connection closed')

def main():
    '''Main function'''
    client()


if __name__ == "__main__":
    main()
