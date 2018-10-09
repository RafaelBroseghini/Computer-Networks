'''
DNS Name Server
'''
#!/usr/bin/env python3

import re
import sys
from random import randint, choice
from socket import socket, SOCK_DGRAM, AF_INET


HOST = "localhost"
PORT = 43053

DNS_TYPES = {
    1: 'A',
    2: 'NS',
    5: 'CNAME',
    12: 'PTR',
    15: 'MX',
    16: 'TXT',
    28: 'AAAA'
}

TTL_SEC = {
    '1s': 1,
    '1m': 60,
    '1h': 60*60,
    '1d': 60*60*24,
    '1w': 60*60*24*7,
    '1y': 60*60*24*365
    }


def val_to_bytes(value: int, n_bytes: int) -> list:
    '''Split a value into n bytes'''
    n_decimal = []
    for i in range(n_bytes):
        result = value & 0xFF
        value >>= 8
        n_decimal.insert(0, result)
    return n_decimal


def bytes_to_val(bytes_lst: list) -> int:
    '''Merge n bytes into a value'''
    result = list(bytes_lst)
    while len(result) > 1:
        temp = []
        # grab every two elements and merge.
        for n in range(len(result)-1):
            merged = result[n] << 8 | result[n+1]
            temp.append(merged)
        result = temp
    return result[0]


def get_left_bits(bytes_lst: list, n_bits: int) -> int:
    '''Extract left n bits of a two-byte sequence'''
    val = bytes_to_val(bytes_lst)
    return val >> (16-n_bits)


def get_right_bits(bytes_lst: list, n_bits) -> int:
    '''Extract right n bits bits of a two-byte sequence'''
    val = bytes_to_val(bytes_lst)
    return val & (2**n_bits) - 1 


def read_zone_file(filename: str) -> tuple:
    '''Read the zone file and build a dictionary'''
    zone = dict()
    with open(filename) as zone_file:
        origin = zone_file.readline().split()[1].rstrip('.')
        default_ttl = zone_file.readline().split()[1].rstrip('\n')
        line = zone_file.readline()
        previous_domain_dame = line[0:15].rstrip()

        while line != "":

            domain_name = line[0:15].rstrip()
            if len(domain_name) == 0:
                domain_name = previous_domain_dame
            else:
                previous_domain_dame = domain_name
            
            if domain_name not in zone:
                zone[domain_name] = []
            
            ttl = line[15:20].rstrip()
            if len(ttl) == 0:
                ttl = default_ttl

            class_ = line[20:25].rstrip()
            req_type = line[25:35].rstrip()
            address = line[35:].rstrip()

            info = (ttl, class_, req_type, address)

            zone[domain_name].append(info)

            line = zone_file.readline()

    return (origin, zone)

def parse_request(origin: str, msg_req: bytes) -> tuple:
    '''Parse the request'''
    trans_id = bytes_to_val([msg_req[0], msg_req[1]])
    runner = msg_req[12]
    i = 12
    full_name = []

    while runner != 0:
        i += 1
        for j in range(runner):
            full_name.append(chr(msg_req[i]))
            i += 1
        full_name.append(".")
        runner = msg_req[i]
    full_name.pop()

    full_name = "".join(full_name)
    first_subdomain = full_name.split(".")[0]

    qry_type = bytes_to_val([msg_req[i+1], msg_req[i+2]])
    class_  = bytes_to_val([msg_req[i+3], msg_req[i+4]])
    query = msg_req[12:]

    
    if qry_type not in DNS_TYPES:
        raise ValueError("Unknown query type")

    if class_ != 1:
        raise ValueError("Unknown class")

    if full_name[len(first_subdomain)+1:] != "cs430.luther.edu" or origin != "cs430.luther.edu":
        raise ValueError("Unknown zone")
        

    return (trans_id, first_subdomain, qry_type, query)


def format_response(zone: dict, trans_id: int, qry_name: str, qry_type: int, qry: bytearray) -> bytearray:
    '''Format the response'''

    if qry_name not in zone:
        raise ValueError("Unknown name")

    response = bytearray()
    for t in val_to_bytes(trans_id, 2):
        response.append(t)
    response.append(int("0x81",16))
    response.append(0)
    response.append(0)
    response.append(1)
    num_answer = 0
    qry_letter = DNS_TYPES[qry_type]
    temp = []

    for t in zone[qry_name]:
        if t[2] == qry_letter:
            temp.append(t)
            num_answer += 1

    for b in val_to_bytes(num_answer, 2):
        response.append(b)

    for i in range(4):
        response.append(0)

    for i in range(len(qry)):
        response.append(qry[i])

    for elem in temp:
        response.append(int("0xc0",16))
        response.append(int("0x0c",16))
        if elem[2] == "A":
            temp_type = 1
        else:
            temp_type = 28

        for e in val_to_bytes(temp_type,2):
            response.append(e)
        response.append(0)
        response.append(1)

        for t in val_to_bytes(TTL_SEC[elem[0]], 4):
            response.append(t)

        if qry_letter == "A":
            for i in val_to_bytes(4, 2):
                response.append(i)

            temp_add = elem[3].split(".")
            for n in temp_add:
                response.append(int(n))
        else:
            for i in val_to_bytes(16, 2):
                response.append(i)

            temp_add = elem[3].split(":")
            for n in temp_add:
                temp_n = list(n)
                while len(temp_n) < 4:
                    temp_n.insert(0, "0")
                
                temp_n = "".join(temp_n)

                response.append(int("0x"+temp_n[:2],16))
                response.append(int("0x"+temp_n[2:],16))

                


    # print(response)
    return response


def run(filename: str) -> None:
    '''Main server loop'''
    server_sckt = socket(AF_INET, SOCK_DGRAM)
    server_sckt.bind((HOST, PORT))
    origin, zone = read_zone_file(filename)
    print("Listening on %s:%d" % (HOST, PORT))

    while True:
        (request_msg, client_addr) = server_sckt.recvfrom(512)
        try:
            trans_id, domain, qry_type, qry = parse_request(origin, request_msg)
            msg_resp = format_response(zone, trans_id, domain, qry_type, qry)
            server_sckt.sendto(msg_resp, client_addr)
        except ValueError as ve:
            print('Ignoring the request: {}'.format(ve))
    server_sckt.close()


def main(*argv):
    '''Main function'''
    if len(argv[0]) != 2:
        print('Proper use: python3 nameserver.py <zone_file>')
        exit()
    run(argv[0][1])
    # run("zoo.zone")


if __name__ == '__main__':
    main(sys.argv)
