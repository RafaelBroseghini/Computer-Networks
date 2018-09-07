'''
GEO TCP Server
'''
#!/usr/bin/env python3

import time
from socket import socket, AF_INET, SOCK_STREAM

FILE_NAME = 'geo_world.txt'
HOST = 'localhost'
PORT = 4300


def read_file(filename: str) -> dict:
    '''Read world territories and their capitals from the provided file'''
    world = dict()
    print("Reading a file...")
    start = time.time()
    with open(filename, "r+") as infile:
        for line in infile:
            line = line.split(" - ")
            world[line[0]] = line[1].replace("\n","")
    end = time.time()
    print("Read in {:.4f} sec".format(end-start))
    return world


def server(world: dict) -> None:
    '''Main server loop'''
    # TODO: Implement server-side tasks
    with socket(AF_INET, SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print('Listening on localhost:{}'.format(PORT))
        conn, addr = s.accept()
        with conn:
            print('Connected to {}'.format(addr[0]))
            while True:
                data = conn.recv(1024)
                if not data:
                    print('Disconnected: {}'.format(addr[0]))
                    break
                country = data.decode()
                print("User query: {}".format(country))
                if country not in world:
                    conn.sendall("{}".format("There is no such country.").encode())
                else:
                    capital = world[country]
                    conn.sendall("{}".format(capital).encode())


def main():
    '''Main function'''
    world = read_file(FILE_NAME)
    server(world)


if __name__ == "__main__":
    main()
