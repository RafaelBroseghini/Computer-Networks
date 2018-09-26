#!/usr/bin/env python3

import sys
import time
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
            merged = result[n] << 8 | result[n+1]
            temp.append(merged)
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
    return ((bytes_lst[0] & 0x3f) << 8) + bytes_lst[1]

def parse_cli_query(filename, q_type, q_domain, q_server=None) -> tuple:
    '''Parse command-line query'''
    if q_type == "MX":
        raise ValueError("Unknown query type")
    q_type = DNS_TYPES[q_type]
    q_domain = q_domain.split(".")
    if not q_server:
        q_server = choice(PUBLIC_DNS_SERVER)
    
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

    return query

def send_request(q_message: bytearray, q_server: str) -> bytes:
    '''Contact the server'''
    client_sckt = socket(AF_INET, SOCK_DGRAM)
    client_sckt.sendto(q_message, (q_server, PORT))
    (q_response, _) = client_sckt.recvfrom(2048)
    client_sckt.close()
    
    return q_response

def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    start_of_name, i = resp_bytes[12], 12
    rr_ans = bytes_to_val([resp_bytes[6], resp_bytes[7]]) or bytes_to_val([resp_bytes[8], resp_bytes[9]])
    j = int(hex(start_of_name),16)
    current = int(hex(start_of_name),16)
    while current != 0:
        i += j + 1
        current = int(hex(resp_bytes[i]),16)
        j = int(hex(resp_bytes[i]),16)
    offset = i + 5
    answers = parse_answers(resp_bytes, offset, rr_ans)
    return answers


def get_name(resp_bytes: bytes, start_of_name: hex, builder: int) -> str:
    current_subname_len = int(hex(start_of_name),16)
    name = []
    while current_subname_len != 0:
        for m in range(current_subname_len):
            char = chr(int(hex(resp_bytes[builder]),16))
            name.append(char)
            builder += 1
        name.append(".")
        current_subname_len = int(hex(resp_bytes[builder]),16)
        builder += 1
    name.pop()
    return "".join(name)

def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''
    res = []
    # extract name again (would be so much easier if we passed name as a parameter.)
    # this works when we get 0c c0
    
    if get_2_bits([resp_bytes[offset],resp_bytes[offset+1]]) == 3:
        # iterate however many rr_ans received, extracting the ip address.
        for i in range(rr_ans):
            # getname
            # ========================================================
            start_of_name, builder = resp_bytes[int(hex(resp_bytes[offset+1]),16)], int(hex(resp_bytes[offset+1]),16) + 1
            name = get_name(resp_bytes, start_of_name, builder)
            # ========================================================
            ## ttl use offset
            ttl = bytes_to_val([resp_bytes[offset+x] for x in range(6,10)])
            q_type = bytes_to_val([resp_bytes[offset+2], resp_bytes[offset+3]])
            length = bytes_to_val([resp_bytes[offset+10], resp_bytes[offset+11]])
            if q_type == 1:
                ip = parse_address_a(length, resp_bytes[offset+12:offset+12+length])
                offset += 16
                info = (name, ttl, ip)
            elif q_type == 28:
                ip = parse_address_aaaa(length, resp_bytes[offset+12:offset+12+length])
                info = (name, ttl, ip)
                offset += 12 + length
            else:
                raise Exception("We are ignoring other query types (CNAME, MX, TXT) for now.")

            res.append(info)
    else:
        for i in range(rr_ans):
            # getname
            # ========================================================
            start_of_name, builder = int(hex(offset),16), int(hex(offset),16) + 1
            name = get_name(resp_bytes, start_of_name, n, builder)
            # ========================================================
            loc = offset+len(name)
            ttl = bytes_to_val([resp_bytes[loc+x] for x in range(6,10)])
            q_type = bytes_to_val([resp_bytes[loc+2], resp_bytes[loc+3]])
            length = bytes_to_val([resp_bytes[loc+10], resp_bytes[loc+11]])
            if q_type == 1:
                ip = parse_address_a(length, resp_bytes[loc+12:loc+12+length])
                loc += 16
                info = (name, ttl, ip)
            elif q_type == 28:
                ip = parse_address_aaaa(length, resp_bytes[loc+12:loc+12+length])
                info = (name, ttl, ip)
                loc += 12 + length
            elif q_type == 5:
                raise Exception("We are ignoring CNAME query types for now")

            res.append(info)

    return res
        
def parse_address_a(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv4 address'''
    return ".".join([str(addr_bytes[sub]) for sub in range(addr_len)])

def parse_address_aaaa(addr_len: int, addr_bytes: bytes) -> str:
    '''Extract IPv6 address'''
    addr_bytes = [addr_bytes.hex()[i:i+4] for i in range(0, addr_len*2,4)]
    address = []
    # get rid of starting zeroes.
    for g in range(len(addr_bytes)):
        if addr_bytes[g] == "0000":
            addr_bytes[g] = "0"
        elif addr_bytes[g].startswith("0"):
            all_zeroes = True
            i = 0
            while all_zeroes:
                if addr_bytes[g][i] == "0":
                    i += 1
                else:
                    all_zeroes = False
                    addr_bytes[g] = addr_bytes[g][i:]
        # append to the address
        address.append(addr_bytes[g])
        address.append(":")
    address.pop() #this pops overflow ':'

    return "".join(address)

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
        print('Address: {}\n'.format(a[2]))

def main(*query):
    '''Main function'''
    if len(query[0]) < 3 or len(query[0]) > 4:
        print('Proper use: python3 resolver <type> <domain> <server>')
        exit()
    start = time.time()
    resolve(query)
    end = time.time()
    print("Resolved in {:.3f}s".format(end-start))

if __name__ == '__main__':
    main(sys.argv)
