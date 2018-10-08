#!/usr/bin/env python3

import sys
import time
from random import randint, choice, seed
from socket import socket, SOCK_DGRAM, AF_INET

HOST = "localhost"
PORT = 43053

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

def get_domain_name_location(bytes_lst: list) -> int:
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
    # transaction_id = val_to_2_bytes(randint(0, 65535))
    # Hard coding transaction id.
    transaction_id = [79,66]
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
    client_sckt.connect((HOST, PORT))
    client_sckt.sendto(q_message, (HOST, PORT))
    (q_response, _) = client_sckt.recvfrom(2048)
    client_sckt.close()
    
    return q_response

def parse_response(resp_bytes: bytes):
    '''Parse server response'''
    start_of_name, i = resp_bytes[12], 12
    rr_ans = bytes_to_val([resp_bytes[6], resp_bytes[7]]) or bytes_to_val([resp_bytes[8], resp_bytes[9]])
    current = int(hex(start_of_name),16)
    while current != 0:
        i += current + 1
        current = int(hex(resp_bytes[i]),16)
    offset = i + 5
    answers = parse_answers(resp_bytes, offset, rr_ans)
    return answers


def get_name(resp_bytes: bytes, start_of_name: hex, builder: int) -> str:
    '''Get domain name from response'''
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
    # name.pop()
    name = name[:len(name)-1]
    return "".join(name)

def build_info(resp_bytes: bytes, offset: int, q_type: int, length: int, label: bool) -> tuple:
    '''Parse response extracting name, ttl and IP address'''
    # This function modifies the offset that gets passed to parse_answers.
    if label:
        builder = get_domain_name_location([resp_bytes[offset-1], resp_bytes[offset]]) + 1 # returns 13 when labeled c0 0c
    else:
        builder = offset + 1
        
    # Get name and ttl
    start_of_name = resp_bytes[int(hex(resp_bytes[offset]),16)]
    name = get_name(resp_bytes, start_of_name, builder)
    ttl = bytes_to_val([resp_bytes[offset+x] for x in range(5,9)])

    # Control structure that determines how to increase the offset.
    if q_type == 1:
        ip = parse_address_a(length, resp_bytes[offset+11:offset+11+length])
        offset += 15
    elif q_type == 28:
        ip = parse_address_aaaa(length, resp_bytes[offset+11:offset+11+length])
        offset += 11 + length
    else:
        raise Exception("We are ignoring other query types (CNAME, MX, TXT) for now.")

    info = (name, ttl, ip)
    return info, offset

def parse_answers(resp_bytes: bytes, offset: int, rr_ans: int) -> list:
    '''Parse DNS server answers'''
    res = []
    # extract name again (would be so much easier if we passed name as a parameter.
    
    # get two bits of two byte sequence. (offset)
    labeled = False
    if resp_bytes[offset] == 192:
        labeled = True

        # Iterate over however many rr_ans received, extracting the ip address.
        for i in range(rr_ans):
            q_type = bytes_to_val([resp_bytes[offset+2], resp_bytes[offset+3]])
            length = bytes_to_val([resp_bytes[offset+10], resp_bytes[offset+11]])

            # Build info is reponsible for checking the q_type
            # which determines how to increase the offset.
            # The offset is returned as the second value from build_info.
            rv = build_info(resp_bytes, offset+1, q_type, length, labeled)
            info, offset = rv[0], rv[1]

            res.append(info)
    else:
        start_of_name, builder = int(hex(resp_bytes[offset]),16)+1, int(hex(offset),16)
        name = get_name(resp_bytes, start_of_name, builder)[1:]
        loc = offset+len(name)+1
        for i in range(rr_ans):
            ttl = bytes_to_val([resp_bytes[loc+x] for x in range(5,9)])
            q_type = bytes_to_val([resp_bytes[loc+1], resp_bytes[loc+2]])
            length = bytes_to_val([resp_bytes[loc+9], resp_bytes[loc+10]])
            
            if q_type == 1:
                ip = parse_address_a(length, resp_bytes[loc+11:loc+11+length])             
                loc += 16 + len(name)
                info = (name, ttl, ip)
            elif q_type == 28:
                ip = parse_address_aaaa(length, resp_bytes[loc+11:loc+11+length])
                info = (name, ttl, ip)
                loc += 16 + len(name)
            elif q_type == 5:
                raise Exception("We are ignoring CNAME query types for now")
            
            print("ttl", ttl)
            print("qtype", q_type)
            print("length", length)
            print("loc", loc)
            print("ip", ip)
            res.append(info)
            print(res)

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
    print('DNS server used: nameserver.py\n')       
    for a in answers:
        print('Domain: {}'.format(a[0]))
        print('TTL: {}'.format(a[1]))
        print('Address: {}\n'.format(a[2]))

def main(*query):
    '''Main function'''
    if len(query[0]) < 3 or len(query[0]) > 4:
        print('Proper use: python3 resolver.py <type> <domain> <server>')
        exit()
    start = time.time()
    resolve(query)
    end = time.time()
    print("Resolved in {:.3f}s".format(end-start))

if __name__ == '__main__':
    main(sys.argv)
