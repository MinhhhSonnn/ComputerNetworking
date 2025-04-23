import binascii

from scapy.all import Packet, IntField


class PacketHeader(Packet):
    name = "PacketHeader"
    fields_desc = [
        IntField("type", 0),
        IntField("seq_num", 0),
        IntField("length", 0),
        IntField("checksum", 0),
    ]


def compute_checksum(pkt):
    return binascii.crc32(bytes(pkt)) & 0xFFFFFFFF

def to_bytes(self):
    import struct
    header = struct.pack('!II?H', self.seq_num, self.checksum, self.is_ack, self.length)
    return header + self.data