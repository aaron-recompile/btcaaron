"""
Inquisition opcode definitions and script-building helpers.
Experimental opcodes: OP_CAT, CTV, CSFS, INTERNALKEY.
"""

OP_CAT = 0x7e
OP_CHECKTEMPLATEVERIFY = 0xb3
OP_CHECKSIGFROMSTACK = 0xcc
OP_CHECKSIGFROMSTACKVERIFY = 0xcd
OP_INTERNALKEY = 0xcb

OP_0 = 0x00
OP_1 = 0x51
OP_DUP = 0x76
OP_SWAP = 0x7c
OP_OVER = 0x78
OP_ROT = 0x7b
OP_2DUP = 0x6e
OP_SIZE = 0x82
OP_NOT = 0x91
OP_SHA256 = 0xa8
OP_EQUAL = 0x87
OP_EQUALVERIFY = 0x88
OP_CHECKSIG = 0xac
OP_CHECKSIGVERIFY = 0xad
OP_DROP = 0x75
OP_NIP = 0x77
OP_VERIFY = 0x69


def push_bytes(data: bytes) -> bytes:
    n = len(data)
    if n == 0:
        return bytes([OP_0])
    if n <= 75:
        return bytes([n]) + data
    if n <= 0xFF:
        return b"\x4c" + bytes([n]) + data
    if n <= 0xFFFF:
        return b"\x4d" + n.to_bytes(2, "little") + data
    return b"\x4e" + n.to_bytes(4, "little") + data


def build_script(*elements) -> str:
    out = b""
    for e in elements:
        if isinstance(e, int):
            out += bytes([e & 0xFF])
        elif isinstance(e, bytes):
            out += e
        else:
            raise TypeError(f"Unknown element type: {type(e)}")
    return out.hex()
