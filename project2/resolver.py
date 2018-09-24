#!/usr/bin/env python3

import sys
from random import randint, choice, seed
from socket import socket, SOCK_DGRAM, AF_INET

PORT = 53

DNS_TYPES = {
    'A': 1,
    'AAAA': 28,
    'CNAME': 5,
    'MX': 15,
    'NS': 2,
    'PTR': 12,
    'TXT': 16
}

PUBLIC_DNS_SERVER = [
    '1.0.0.1',  # Cloudflare
    '1.1.1.1',  # Cloudflare
    '8.8.4.4',  # Google
    '8.8.8.8',  # Google
    '8.26.56.26',  # Comodo
    '8.20.247.20',  # Comodo
    '9.9.9.9',  # Quad9
    '64.6.64.6',  # Verisign
    '208.67.222.222',  # OpenDNS
    '208.67.220.220'  # OpenDNS
]


def val_to_2_bytes(value: int) -> list:
    '''Split a value into 2 bytes'''
    val_left = value >> 8 # shift right 8 bits.
    val_right = value & 0xFF # get right most 8 bits.
    return [val_left, val_right]

def val_to_n_bytes(value: int, n_bytes: int) -> list:
    '''Split a value into 2 bytes'''
    n_decimal = []
    for i in range(n_bytes):
        result = value & 0xFF
        value >>= 8
        n_decimal.insert(0, result)
    return n_decimal

def bytes_to_val(bytes_lst: list) -> int:
    '''Merge 2 bytes into a value'''
    result = list(bytes_lst)
    while len(result) > 1:
        temp = []
        # grab every two elements and merge.
        for n in range(len(result)-1):
            combined = result[n] << 8 | result[n+1]
            temp.append(combined)
        result = temp
    return result[0]

def get_2_bits(bytes_lst: list) -> int:
    '''Extract first two bits of a two-byte sequence'''
    # shift right.
    # combine.
    result = []
    for num in bytes_lst:
        shifter = len(bin(num)) - 3
        val = num >> shifter
        result.append(val)
    return result[0] << 1 | result[1]

def get_offset(bytes: list) -> int:
    '''Extract size of the offset from a two-byte sequence'''
    raise NotImplementedError

def parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple:
    '''Parse command-line query'''
    q_type = DNS_TYPES[q_type]
    q_domain = q_domain.split(".")
    if not q_server:
        q_server = choice(PUBLIC_DNS_SERVER)
    
    print(parse_cli_query.__annotations__)
    return q_type, q_domain, q_server

def format_query(q_type: int, q_domain: list) -> bytearray:
    '''Format DNS query'''
    transaction_id = val_to_2_bytes(randint(0, 65535))
    query = bytearray([transaction_id[0], transaction_id[1], 1, 0])

    # Flags
    flags = [1,0,0,0]
    for n in flags:
        res = val_to_2_bytes(n)
        query.append(res[0])
        query.append(res[1])
    # Domain
    for sub_domain in q_domain:
        query.append(len(sub_domain))
        for char in sub_domain:
            query.append(ord(char))
    query.append(0)

    # Type
    q_type = val_to_2_bytes(q_type)
    query.append(q_type[0])
    query.append(q_type[1])

    # Class
    query.append(0)
    query.append(1)

    print(query)
    return # return query

def send_request(q_message: bytearray, q_server: str) -> bytes:
    '''Contact the server'''
    client_sckt = socket(AF_INET, SOCK_DGRAM)
    client_sckt.sendto(q_message, (q_server, PORT))
    (q_response, _) = client_sckt.recvfrom(2048)
    client_sckt.close()
    
    return q_response

def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    raise NotImplementedError

def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''
    raise NotImplementedError

def parse_address_a(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv4 address'''
    raise NotImplementedError

def parse_address_aaaa(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv6 address'''
    raise NotImplementedError

def resolve(query: str) -> None:
    '''Resolve the query'''
    q_type, q_domain, q_server = parse_cli_query(*query[0])
    query_bytes = format_query(q_type, q_domain)
    response_bytes = send_request(query_bytes, q_server)
    answers = parse_response(response_bytes)
    print('DNS server used: {}'.format(q_server))
    for a in answers:
        print('Domain: {}'.format(a[0]))
        print('TTL: {}'.format(a[1]))
        print('Address: {}'.format(a[2]))

def main(*query):
    '''Main function'''
    if len(query[0]) < 3 or len(query[0]) > 4:
        print('Proper use: python3 resolver <type> <domain> <server>')
        exit()
    resolve(query)


if __name__ == '__main__':
    main(sys.argv)
