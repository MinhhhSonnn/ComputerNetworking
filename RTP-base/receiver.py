import argparse
import socket
import sys


from utils import PacketHeader, compute_checksum


def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    PKT_TYPE_START = 0
    PKT_TYPE_END = 1
    PKT_TYPE_DATA = 2
    PKT_TYPE_ACK = 3

    expected_seq = 1
    received_data = {}
    session_active = False

    while True:
        pkt, address = s.recvfrom(2048)

        # Extract header
        pkt_header = PacketHeader.from_bytes(pkt[:16])
        msg = pkt[16:16 + pkt_header.length]

        # Verity checksum
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)

        if pkt_checksum != computed_checksum:
            if session_active and pkt_header.type == PKT_TYPE_DATA:
                ack_header = PacketHeader(type=PKT_TYPE_ACK, seq_num=expected_seq, length=0)
                ack_header.checksum = compute_checksum(ack_header / b"")
                s.sendto(bytes(ack_header / b""), address)
            continue


        if pkt_header.type == PKT_TYPE_START:
            if not session_active:
                session_active = True
                expected_seq = 1
                received_data = {}

                ack_header = PacketHeader(type=PKT_TYPE_ACK, seq_num=1, length=0)
                ack_header.checksum = compute_checksum(ack_header / b"")
                s.sendto(bytes(ack_header / b""), address)

        elif pkt_header.type == PKT_TYPE_START and session_active:
            pass

        elif pkt_header.type == PKT_TYPE_DATA and session_active:
            seq_num = pkt_header.seq_num

            if seq_num >= expected_seq + window_size:
                ack_header = PacketHeader(type=PKT_TYPE_ACK, seq_num=expected_seq, length=0)
                ack_header.checksum = compute_checksum(ack_header / b"")
                s.sendto(bytes(ack_header / b""), address)
                continue

            if pkt_header.seq_num not in received_data and pkt_header.seq_num >= expected_seq:
                received_data[pkt_header.seq_num] = msg



        elif pkt_header.type == PKT_TYPE_END and session_active:
            ack_header = PacketHeader(type=PKT_TYPE_ACK, seq_num=pkt_header.seq_num + 1, length=0)
            ack_header.checksum = compute_checksum(ack_header / b"")
            s.sendto(bytes(ack_header / b""), address)
            break

    while expected_seq in received_data:
        sys.stdout.buffer.write(received_data[expected_seq])
        sys.stdout.buffer.flush()

        del received_data[expected_seq]
        expected_seq += 1

    ack_header = PacketHeader(type=PKT_TYPE_ACK, seq_num=expected_seq, length=0)
    ack_header.checksum = compute_checksum(ack_header / b"")
    s.sendto(bytes(ack_header / b""), address)

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

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()