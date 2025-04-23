
import argparse
import socket
import sys
import time

from utils import PacketHeader, compute_checksum


def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)

    message = sys.stdin.buffer.read()

    #devide message into packets
    MAX_PAYLOAD = 1400
    packets = [message[i:i + MAX_PAYLOAD] for i in range(0, len(message), MAX_PAYLOAD)]

    #init window
    base = 0
    next_seq = 0
    window = {}

    #send start
    start_header = PacketHeader(type=0, seq_num=0, length=0)
    start_header.checksum = compute_checksum(start_header / b"")
    start_pkt = start_header / b""
    s.sendto(bytes(start_pkt), (receiver_ip, receiver_port))
    print("Sent START packet")

    while base < len(packets):
        while next_seq < base + window_size and next_seq < len(packets):
            data = packets[next_seq]
            header = PacketHeader(type = 2, seq_num = next_seq, length = len(data))
            header.checksum = compute_checksum(header/data)
            pkt = header/data
            s.sendto(bytes(pkt), (receiver_ip, receiver_port))
            window[next_seq] = pkt
            print(f"send packet {next_seq}")
            next_seq += 1
        start_time = time.time()
        while True:
            try:
                data, addr = s.recvfrom(1024)
                ack_header = PacketHeader(data[:16])
                if ack_header.type == 1:
                    ack_seq = ack_header.seq_num
                    print(f"Received ACK seq {ack_seq}")
                    if ack_seq > base:
                        for seq in range(base, ack_seq):
                            window.pop(seq)
                        base = ack_seq
            except socket.timeout:
                print("Time out, resending window")
                for seq, pkt in window.items():
                    s.sendto(bytes(pkt), receiver_ip, receiver_port)
                    print(f"resend packet {seq}")

            if time.time() - start_time >= 0.5:
                for seq, pkt in window.items():
                    s.sendto(bytes(pkt), (receiver_ip, receiver_port))
                start_time = time.time()

                # send end
    end_header = PacketHeader(type=3, seq_num= next_seq, length=0)
    end_header.checksum = compute_checksum(end_header / b"")
    end_pkt = end_header / b""
    s.sendto(bytes(end_pkt), (receiver_ip, receiver_port))
    print("Sent END packet")

    end_start_time = time.time()
    while time.time() - end_start_time < 0.5:
        try:
            data, addr = s.recvfrom(1024)
            ack_header = PacketHeader(data[:16])
            if ack_header.type == 1 and ack_header.seq_num == next_seq:
                break
        except socket.timeout:
            continue

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
