
import argparse
import socket
import sys
import time
from threading import Timer

from utils import PacketHeader, compute_checksum



def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)


    message = sys.stdin.buffer.read()

    PKT_TYPE_START = 0
    PKT_TYPE_END = 1
    PKT_TYPE_DATA = 2
    PKT_TYPE_ACK = 3

    #devide message into packets
    MAX_PAYLOAD = 1400



    chunks = [message[i:i + MAX_PAYLOAD] for i in range(0, len(message), MAX_PAYLOAD)]

    #init window
    base = 0
    next_seq = 0
    seq_num = 0

    #send start
    start_header = PacketHeader(type= PKT_TYPE_START, seq_num=seq_num, length=0)
    start_header.checksum = compute_checksum(start_header / b"")
    start_pkt = start_header / b""
    s.sendto(bytes(start_pkt), (receiver_ip, receiver_port))

    try:
        data, _ = s.recvfrom(2048)
        ack_header = PacketHeader(data[:16])

        if ack_header.type != PKT_TYPE_ACK or ack_header.seq_num != 1:
            return


        seq_num = 1
    except socket.timeout:
        return

    packets = []
    for chunk in chunks:
        pkt_header = PacketHeader(type=PKT_TYPE_DATA, seq_num=seq_num, length=len(chunk))
        pkt_header.checksum = compute_checksum(pkt_header / chunk)
        packets.append((pkt_header / chunk, seq_num))
        seq_num += 1

    timer = None

    def start_timer():
        nonlocal timer
        if timer:
            timer.cancel()
        timer = Timer(0.5, timeout_handler)
        timer.start()

    def timeout_handler():
        nonlocal base, seq_num
        for i in range(base, min(base + window_size, len(packets))):
            s.sendto(bytes(packets[i][0]), (receiver_ip, receiver_port))
        start_timer()



    while base < len(packets):
        while next_seq < base + window_size and next_seq < len(packets):
            s.sendto(bytes(packets[next_seq][0]), (receiver_ip, receiver_port))
            if base == next_seq:
                start_timer()
            next_seq += 1


        try:
            data, addr = s.recvfrom(2048)
            ack_header = PacketHeader(data)

            if ack_header.type == PKT_TYPE_ACK:
                if ack_header.seq_num > packets[base][1]:
                    old_base = base

                    while base < len(packets) and packets[base][1] < ack_header.seq_num:
                        base += 1

                    if base < len(packets) and old_base != base:
                        start_timer()
                    elif base == len(packets):
                        if timer:
                            timer.cancel()
                        break

        except socket.timeout:
            pass

    #send end
    end_seq_num = seq_num
    end_header = PacketHeader(type=PKT_TYPE_END, seq_num=end_seq_num, length=0)
    end_header.checksum = compute_checksum(end_header / b"")
    end_packet = end_header / b""
    s.sendto(bytes(end_packet), (receiver_ip, receiver_port))


    end_timer_start = time.time()
    end_timer_duration = 0.5


    while time.time() - end_timer_start < end_timer_duration:
        try:
            s.settimeout(end_timer_duration - (time.time() - end_timer_start))
            data, _ = s.recvfrom(2048)
            ack_header = PacketHeader.from_bytes(data)

            if ack_header.type == PKT_TYPE_ACK and ack_header.seq_num == end_seq_num + 1:
                break
        except socket.timeout:
            break


    s.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
