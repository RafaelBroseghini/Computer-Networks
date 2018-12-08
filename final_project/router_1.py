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

    with open(filename, "r") as infile:
        full_table = [elem.split() for elem in infile.readlines() if elem.split() != []]

        for router in range(len(full_table)):
            if len(full_table[router]) == 1 and full_table[router][0] == THIS_NODE:
                router += 1
                while router < len(full_table) and len(full_table[router]) != 1:
                    neighbor, cost = full_table[router][0], int(full_table[router][1])
                    ROUTING_TABLE[neighbor] = [cost, neighbor]
                    NEIGHBORS.add(neighbor)
                    router += 1

def format_update():
    """Format update message"""
    msg = bytearray()
    msg.append(0)
    for item in ROUTING_TABLE:
        neigh_parts = [int(elem) for elem in item.split(".")]
        for p in neigh_parts:
            msg.append(p)
        cost = ROUTING_TABLE[item][0]
        msg.append(cost)
    
    return msg


def parse_update(msg, neigh_addr):
    """Update routing table"""
    update_flag = False
    data = [(".".join([str(j) for j in msg[i:i+4]]), msg[i+4]) for i in range(1, len(msg), 5)]

    for neigh_pair in data:
        data_addr, cost = neigh_pair[0], neigh_pair[1]
        if data_addr != THIS_NODE:
            if data_addr in ROUTING_TABLE:
                if ROUTING_TABLE[neigh_addr][0] + cost < ROUTING_TABLE[data_addr][0]:
                    ROUTING_TABLE[data_addr][0] = ROUTING_TABLE[neigh_addr][0] + cost
                    ROUTING_TABLE[data_addr][1] = neigh_addr
                    update_flag = True
            else:
                ROUTING_TABLE[data_addr] = [ROUTING_TABLE[neigh_addr][0] + cost]
                ROUTING_TABLE[data_addr].append(neigh_addr)
                update_flag = True
    
    if update_flag == True:
        return True
    return False


def send_update(node):
    """Send update"""
    client_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sckt.bind((THIS_NODE, 4300))
    packet = format_update()
    CLIENT_PORT = 4300 + int(node[-1])
    client_sckt.sendto(packet, (node, CLIENT_PORT))
    client_sckt.close()


def format_hello(msg_txt, src_node, dst_node):
    """Format hello message"""
    msg = bytearray()
    msg.append(1)
    src_node = src_node.split(".")
    for part in src_node:
        msg.append(int(part))
    dst_node = dst_node.split(".")
    for part in dst_node:
        msg.append(int(part))
    for part in msg_txt:
        msg.append(ord(part))
    
    return msg


def parse_hello(msg):
    """Send the message to an appropriate next hop"""
    src  = ".".join([str(p) for p in msg[1:5]])
    dest = ".".join([str(p) for p in msg[5:9]])
    data  = "".join([chr(p) for p in msg[9:]])

    if dest == THIS_NODE:
        current_time = time.strftime("%H:%M:%S", time.localtime())
        print(f"{current_time} | Received {data} from {src}")
    else:
        send_hello(msg, THIS_NODE, dest)


def send_hello(msg_txt, src_node, dst_node):
    """Send a message"""
    client_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_sckt.bind((THIS_NODE, 4300))
    packet = format_hello(msg_txt, src_node, dst_node)
    CLIENT_PORT = 4300 + int(dst_node[-1])
    client_sckt.sendto(packet, (dst_node, CLIENT_PORT))
    client_sckt.close()


def print_status():
    """Print status"""
    print(f"{'Host':^15} {'Cost':^10} {'Via':^15}")
    for neighbor, data in ROUTING_TABLE.items():
        cost, via = data[0], data[1]
        print(f"{neighbor:^15} {cost:^10} {via:^15}")


def main(args: list):
    """Router main loop"""
    current_time = time.strftime("%H:%M:%S", time.localtime())
    print(f"{current_time} | Router {THIS_NODE} here")

    server_sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"{current_time} | Binding on {THIS_NODE}:{PORT}")
    server_sckt.bind((THIS_NODE, PORT))

    print(f"{current_time} | Listening on {THIS_NODE}:{PORT}")
    
    read_file(args[1])

    print_status()

    time.sleep(4)

    for n in NEIGHBORS:
        send_update(n)

    inputs = [server_sckt]
    outputs = []

    while len(inputs) > 0:
        reads, writes, errors = select.select(
            inputs, outputs, inputs)
        
        for s in reads:
            if s == server_sckt:
                server_sckt.setblocking(False)
                data, client_addr = server_sckt.recvfrom(1024)
            else:
                data, client_addr = s.recvfrom(1024)

            if data[0] == 0:
                if parse_update(data, client_addr[0]) == True:
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    print(f"{current_time} | Table updated with information from {client_addr[0]}")
                    print_status()
                    for neigh_addr in NEIGHBORS:
                        send_update(neigh_addr)
            else:
                parse_hello(data)

        my_choice = random.randint(0,100)

        if my_choice < 10:
            msg = random.choice(MESSAGES)
            dest = random.choice(list(ROUTING_TABLE.keys()))
            current_time = time.strftime("%H:%M:%S", time.localtime())
            next_hop = ROUTING_TABLE[dest][1]
            print(f"{current_time} | Sending {msg} to {dest} via {next_hop}")
            send_hello(msg, THIS_NODE, dest)

if __name__ == "__main__":
    main(sys.argv)