"""Router implementation using UDP sockets"""
#!/usr/bin/env python3
# encoding: UTF-8


import os
import random
import select
import socket
import struct
import sys
import time

HOST_ID = os.path.splitext(__file__)[0].split("_")[-1]
THIS_NODE = f"127.0.0.{HOST_ID}"
PORT = 4300 + int(HOST_ID)
NEIGHBORS = set()
ROUTING_TABLE = {}
TIMEOUT = 5
MESSAGES = [
    "Cosmic Cuttlefish",
    "Bionic Beaver",
    "Xenial Xerus",
    "Trusty Tahr",
    "Precise Pangolin"
]

def read_file(filename: str) -> None:
    """Read config file"""
    ROUTING_TABLE[THIS_NODE] = {}

    with open(filename, "r") as infile:
        full_table = [elem.split() for elem in infile.readlines() if elem.split() != []]

        for router in range(len(full_table)):
            if len(full_table[router]) == 1 and full_table[router][0] == THIS_NODE:
                router += 1
                while router < len(full_table) and len(full_table[router]) != 1:
                    neighbor, cost = full_table[router][0], int(full_table[router][1])
                    ROUTING_TABLE[THIS_NODE][neighbor] = [cost, neighbor]
                    router += 1

def format_update():
    """Format update message"""
    raise NotImplementedError


def parse_update(msg, neigh_addr):
    """Update routing table"""
    raise NotImplementedError


def send_update(node):
    """Send update"""
    raise NotImplementedError


def format_hello(msg_txt, src_node, dst_node):
    """Format hello message"""
    raise NotImplementedError


def parse_hello(msg):
    """Send the message to an appropriate next hop"""
    raise NotImplementedError


def send_hello(msg_txt, src_node, dst_node):
    """Send a message"""
    raise NotImplementedError


def print_status():
    """Print status"""
    print(f"{'Host':^15} {'Cost':^10} {'Via':^15}")
    for neighbor, data in ROUTING_TABLE[THIS_NODE].items():
        # cost, via = data[0], data[1]
        cost, via = data[0], data[1]
        print(f"{neighbor:^15} {cost:^10} {via:^15}")


def main(args: list):
    """Router main loop"""
    current_time = time.strftime("%H:%M:%S", time.localtime())
    print(f"{current_time} | Router {THIS_NODE} here")

    server_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"{current_time} | Binding on {THIS_NODE}:{PORT}")
    server_sckt.bind((THIS_NODE, PORT))

    print(f"{current_time} | Listtening on {THIS_NODE}:{PORT}")
    

    read_file(args[1])

    print_status()

    while True:
        exit()
        (data, client_addr) = server_sckt.recvfrom(1024)


if __name__ == "__main__":
    main(sys.argv)