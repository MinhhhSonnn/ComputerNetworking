import argparse
import socket


from utils import PacketHeader, compute_checksum


def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))

    expected_seq = 0
    received_data = []
    session_active = False
    output_file ="received.txt"



    while True:
        # Receive packet; address includes both
        # IP and port
        pkt, address = s.recvfrom(2048)

        # Extract header and payload
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        # Verity checksum
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            print("checksums not match")
        print(msg)
        if pkt_header.type == 0:
            if not session_active:
                session_active = True
                expected_seq = 0
                received_data = {}

        elif pkt_header.type == 2 and session_active:
            seq_num = pkt_header.seq_num

            if seq_num >= expected_seq + window_size:
                continue

            if seq_num == expected_seq:
                while expected_seq in received_data:
                    expected_seq += 1

            ack_header = PacketHeader(type = 1, seq_num = expected_seq, length = 0)
            ack_header.checksum = compute_checksum(ack_header/b"")
            ack_pkt = ack_header/b" "
            s.sendto(bytes(ack_pkt), address)

        elif pkt_header.type == 3 and session_active:
            ack_header = PacketHeader(type=1, seq_num=expected_seq, length=0)
            ack_header.checksum = compute_checksum(ack_header / b"")
            ack_pkt = ack_header / b""
            s.sendto(bytes(ack_pkt), address)

            with open(output_file, "wb") as f:
                seq = 0
                while seq in received_data:
                    f.write(received_data[seq])
                    seq += 1
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

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()