#!/usr/bin/python
# -*- coding: UTF-8 -*-

from socket import *
import socket
import os
import sys
import struct
import time
import select

ICMP_ECHO_REQUEST = 8  # ICMP type code for echo request messages
ICMP_ECHO_REPLY = 0  # ICMP type code for echo reply messages
PACKET_SENT = 0
PACKET_RECEIVED = 0
ROUND_TRIP_TIME = []


def checksum(source_string):
    check_sum = 0
    count_to = (len(source_string) // 2) * 2
    count = 0

    while count < count_to:
        this_val = (source_string[count+1]) * 256 + (source_string[count])
        check_sum = check_sum + this_val
        check_sum = check_sum & 0xffffffff
        count = count + 2

    if count_to < len(source_string):
        check_sum = check_sum + (source_string[len(source_string) - 1])
        check_sum = check_sum & 0xffffffff

    check_sum = (check_sum >> 16) + (check_sum & 0xffff)
    check_sum = check_sum + (check_sum >> 16)
    answer = ~check_sum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)

    # Take the right checksum
    if sys.platform == 'darwin':
        # Convert 16-bits integers of hosts to network byte-order
        answer = socket.htons(answer) & 0xffff
    else:
        answer = socket.htons(answer)

    return answer


def receive_one_ping(icmp_socket, ID, timeout, destination_address):
    global PACKET_RECEIVED, ROUND_TRIP_TIME

    while 1:
        # Select ICMP socket in the timeout limit time
        temp = select.select([icmp_socket], [], [], timeout)

        # Determine whether selected the socket
        if temp[0] == []:
            print("Request timeout")
            return 0

        # Compare the time of receipt to time of sending, producing the total network delay
        received_time = time.time()
        received_packet, addr = icmp_socket.recvfrom(1024)
        header = received_packet[20:28]

        # Unpack the packet header for useful information, including the ID
        request_type, code, check_sum, packet_ID, sequence = struct.unpack("bbHHh", header)
        print("The received header of the ICMP reply is: ", request_type, code, check_sum, packet_ID, sequence)

        # Check that the ID matches between the request and reply
        if packet_ID == ID:
            bytes_in_double = struct.calcsize('d')
            sent_time = struct.unpack('d', received_packet[28:28 + bytes_in_double])[0]
            ROUND_TRIP_TIME.append(received_time - sent_time)

            # Increase the count amount of the packet had been received
            PACKET_RECEIVED = PACKET_RECEIVED + 1

            # Return total network delay
            return received_time - sent_time

        elif request_type == 3 and code == 1:
            print("Notification: Destination Host Unreachable")
            return 0

        elif request_type == 3 and code == 0:
            print("Notification: Destination Network Unreachable")
            return 0

        else:
            print("Notification: ID and Received Packet ID are not same")
            return 0


def send_one_ping(icmp_socket, destination_address, ID):
    global PACKET_SENT

    # Header: type (8), code(8), checksum (16), packet_ID (16), sequence (16)
    test_checksum = 0

    # Build ICMP header, encapsulation according specific format
    icmp_header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, test_checksum, ID, 1)

    # Build the time of sending, encapsulation it
    record = struct.pack("d", time.time())

    # Checksum ICMP packet using given function
    test_checksum = checksum(icmp_header + record)

    # Insert checksum into packet
    icmp_header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, test_checksum, ID, 1)

    # Insert time of sending into packet
    icmp_packet = icmp_header + record

    # Send packet using socket
    icmp_socket.sendto(icmp_packet, (destination_address, 1))

    # Increase the count amount of the packet had been sent
    PACKET_SENT = PACKET_SENT + 1


def do_one_ping(destination_address, timeout):
    icmp = socket.getprotobyname("icmp")

    # Create ICMP socket
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, icmp)
    my_ID = os.getpid() & 0xFFFF

    # Call send_one_ping function
    send_one_ping(my_socket, destination_address, my_ID)

    # Call receive_one_ping function
    delay = receive_one_ping(my_socket, my_ID, timeout, destination_address)

    # Close ICMP socket
    my_socket.close()

    # Return total network delay
    return delay


def ping(host, timeout, measurement_count):
    # Taking an IP or host name as an argument
    # Look up hostname, resolving it to an IP address
    destination = socket.gethostbyname(host)

    print("Ping:", host, destination)
    print("")

    for i in range(measurement_count):
        # Call do_one_ping function, approximately every second
        delay = do_one_ping(destination, timeout)

        # Print out the returned delay
        print("The Round Trip Time is: {0:.3f} ms".format(delay*1000))
        print("")

        # Take a break
        time.sleep(1)
        # Continue this process until stopped

    # When stopped, calculate and display the minimum, average, maximum RTT delay and Packet lose rate
    if len(ROUND_TRIP_TIME) > 0:
        min_rtt = min(ROUND_TRIP_TIME)
        max_rtt = max(ROUND_TRIP_TIME)
        avg_rtt = float(sum(ROUND_TRIP_TIME) / len(ROUND_TRIP_TIME))
    else:
        min_rtt = 0
        max_rtt = 0
        avg_rtt = 0

    # Print out the statistics results of PACKET_SENT and PACKET_RECEIVED
    print("STOP: Display the result:")
    print("The packet sent is: ", PACKET_SENT)
    print("The packet received is: ", PACKET_RECEIVED)

    # Determine the packet lose rate
    if PACKET_SENT > 0:
        lose_rate = ((PACKET_SENT - PACKET_RECEIVED) / PACKET_SENT)
    else:
        lose_rate = 0

    # Print out the statistics result of max, min and avg delay
    print("The Minimum Delay is: {0:.3f} ms".format(min_rtt * 1000))
    print("The Average Delay is: {0:.3f} ms".format(avg_rtt * 1000))
    print("The Maximum Delay is: {0:.3f} ms".format(max_rtt * 1000))

    # Print out the Packet Lose Rate, and transform it to percentage
    print("The Packet Lose Rate is: {0:.3f} %".format(lose_rate * 100))


ping("www.lancaster.ac.uk", 1, 10)  # Parameters: ("host", timeout, measurement_count)
