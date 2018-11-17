"""Python Pinger"""
#!/usr/bin/env python3
# encoding: UTF-8

import binascii
import os
import select
import struct
import sys
import time
import socket
from statistics import mean, stdev

ECHO_REQUEST_TYPE = 8
ECHO_REPLY_TYPE = 0
ECHO_REQUEST_CODE = 0
ECHO_REPLY_CODE = 0
REGISTRARS = ["afrinic.net", "apnic.net", "arin.net", "lacnic.net", "ripe.net"]
# REGISTRARS = ["example.com"]


def print_raw_bytes(pkt: bytes) -> None:
    """Printing the packet bytes"""
    for i in range(len(pkt)):
        sys.stdout.write("{:02x} ".format(pkt[i]))
        if (i + 1) % 16 == 0:
            sys.stdout.write("\n")
        elif (i + 1) % 8 == 0:
            sys.stdout.write("  ")
    sys.stdout.write("\n")


def checksum(pkt: bytes) -> int:
    """Calculate checksum"""
    csum = 0
    count = 0
    count_to = (len(pkt) // 2) * 2

    while count < count_to:
        this_val = (pkt[count + 1]) * 256 + (pkt[count])
        csum = csum + this_val
        csum = csum & 0xFFFFFFFF
        count = count + 2

    if count_to < len(pkt):
        csum = csum + (pkt[len(pkt) - 1])
        csum = csum & 0xFFFFFFFF

    csum = (csum >> 16) + (csum & 0xFFFF)
    csum = csum + (csum >> 16)
    result = ~csum
    result = result & 0xFFFF
    result = result >> 8 | (result << 8 & 0xFF00)

    return result


def parse_reply(my_socket: socket.socket, req_id: int, timeout: int, addr_dst: str) -> tuple:
    """Receive an Echo reply"""
    time_left = timeout
    while True:
        started_select = time.time()
        what_ready = select.select([my_socket], [], [], time_left)
        how_long_in_select = time.time() - started_select
        if what_ready[0] == []:  # Timeout
            raise TimeoutError("Request timed out after 1 sec")

        time_rcvd = time.time()
        pkt_rcvd, addr = my_socket.recvfrom(1024)
        if addr[0] != addr_dst:
            raise ValueError(f"Wrong sender: {addr[0]}")
        
        ip_header = pkt_rcvd[:20]
        destination, packet_size, round_trip_time, ttl = ip_header[12:16], len(pkt_rcvd), time_rcvd-started_select, ip_header[8]
        destination = ".".join([str(sub) for sub in destination])
        round_trip_time = "{:.2f}".format(round_trip_time*1000)

        # TODO: Extract ICMP header from the IP packet and parse it
        # *destination address*, *packet size*, *roundtrip time*, *time to live*
        # DONE: End of ICMP parsing
        time_left = time_left - how_long_in_select
        if time_left <= 0:
            raise TimeoutError("Request timed out after 1 sec")

        return destination, packet_size, round_trip_time, ttl


def format_request(req_id: int, seq_num: int) -> bytes:
    """Format an Echo request"""
    my_checksum = 0
    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    data = struct.pack("d", time.time())
    my_checksum = checksum(header + data)

    if sys.platform == "darwin":
        my_checksum = socket.htons(my_checksum) & 0xFFFF
    else:
        my_checksum = socket.htons(my_checksum)

    header = struct.pack(
        "bbHHh", ECHO_REQUEST_TYPE, ECHO_REQUEST_CODE, my_checksum, req_id, seq_num
    )
    packet = header + data
    return packet


def send_request(addr_dst: str, seq_num: int, timeout: int = 1) -> tuple:
    """Send an Echo Request"""
    result = None
    proto = socket.getprotobyname("icmp")
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, proto)
    my_id = os.getpid() & 0xFFFF

    packet = format_request(my_id, seq_num)
    my_socket.sendto(packet, (addr_dst, 1))

    try:
        result = parse_reply(my_socket, my_id, timeout, addr_dst)
    except ValueError as ve:
        print(f"Packet error: {ve}")
    finally:
        my_socket.close()
    return result


def ping(host: str, pkts: int, timeout: int = 1) -> None:
    """Main loop"""
    # TODO: Implement the main loop
    ip = socket.gethostbyname(host)  
    print("--- Ping {} ({}) using Python ---\n".format(host, ip))

    rtt_array, pkts_sent, pkts_received = [], 0, 0
    for p in range(1, pkts+1):
        pkts_sent += 1
        try:
            destination, packet_size, round_trip_time, ttl = send_request(ip, p)
            print(f"{packet_size} bytes from {destination}: icmp_seq={p} TTL={ttl} time={round_trip_time} ms")
            rtt_array.append(float(round_trip_time))
            pkts_received += 1
        except TimeoutError or ValueError as error:
            print(f"No response: {error}")

    pkt_loss = pkts_sent - pkts_received

    print("\n--- {} ping statistics ---".format(host))
    print(f"{pkts_sent} packets transmitted, {pkts_received} received, {int(pkt_loss/pkts_sent)*100}% packet loss")
    
    if len(rtt_array) > 0:
        min_rtt, avg_rtt, max_rtt, mdev_rtt = min(rtt_array), mean(rtt_array), max(rtt_array), stdev(rtt_array)
        print(f"rtt min/avg/max/mdev = {min_rtt}/{avg_rtt:.2f}/{max_rtt}/{mdev_rtt:.2f} ms\n")

    # DONE
    return


if __name__ == "__main__":
    for rir in REGISTRARS:
        ping(rir, 5)
