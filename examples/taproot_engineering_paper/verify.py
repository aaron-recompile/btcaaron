#!/usr/bin/env python3
"""
verify.py — one-command reconstruction of the output key Q for the §6.3 four-leaf
Taproot address, from PUBLIC data only (the published control block + scripts).

This is exactly the check a Taproot verifier performs: re-derive Q from the control
block's Merkle proof and confirm it matches the address. No private keys are used.

    $ python3 verify.py
    PASS: reconstructed address == tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse

Deps: coincurve (libsecp256k1).  pip install coincurve
"""
import hashlib

# ---- public inputs (from §6.1/§6.3 of the paper) -------------------------------
ALICE_XONLY = "dfc128fa3547debab1b46e752a8280fbc28163dbdc76f26c97f42d6bebf1c448"  # internal key P
BOB_XONLY   = "e2f04ea98062e16da2bec87f0c5b2854a78dc37c2f1df5a003c0c504b2d8ceb7"
PREIMAGE    = b"helloworld"
CSV_BLOCKS  = 2
ADDRESS     = "tb1pf5rhd89h6hpgcf9eah2xxp4wnn9qzadlp56yj2vck8uu86erre4qg9vcse"  # signet, HRP tb
HRP         = "tb"
# Published control block for Script 1 (Multisig), §6.3 — 0xc0 ∥ P ∥ sib1 ∥ sib2:
CONTROL_BLOCK = (
    "c0"
    "dfc128fa3547debab1b46e752a8280fbc28163dbdc76f26c97f42d6bebf1c448"   # internal key P
    "fe78d8523ce9603014b28739a51ef826f791aa17511e617af6dc96a8f10f659e"   # sibling-1 = H_TapLeaf(Script0)
    "5639dd69fe8ffe3090783afdb3513a5a6872e99730f5866addcc5a4ae4555e75"   # sibling-2 = Branch1
)

# ---- BIP340 tagged hash + BIP341 leaf/branch ----------------------------------
def tagged(tag, *data):
    th = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(th + th + b"".join(data)).digest()

def push(b):                      # minimal CScript push of <b> (len < 0x4c)
    return bytes([len(b)]) + b

def compact_size(n):
    return bytes([n]) if n < 0xfd else b"\xfd" + n.to_bytes(2, "little")

def op(n):                        # small int opcodes OP_0..OP_16
    return b"\x00" if n == 0 else bytes([0x50 + n])

# ---- rebuild Script 1 (multisig) bytes exactly as committed --------------------
a = bytes.fromhex(ALICE_XONLY); b = bytes.fromhex(BOB_XONLY)
OP_CHECKSIGADD, OP_EQUAL = b"\xba", b"\x87"
script1 = op(0) + push(a) + OP_CHECKSIGADD + push(b) + OP_CHECKSIGADD + op(2) + OP_EQUAL
leaf1 = tagged("TapLeaf", b"\xc0", compact_size(len(script1)), script1)

# ---- parse the published control block and reconstruct the Merkle root ----------
cb = bytes.fromhex(CONTROL_BLOCK)
assert cb[0] & 0xfe == 0xc0, "leaf version byte must be 0xc0/0xc1"
internal = cb[1:33]
assert internal.hex() == ALICE_XONLY, "control-block internal key != Alice"
sib1, sib2 = cb[33:65], cb[65:97]

def branch(x, y):                 # H_TapBranch(sort(x, y))
    return tagged("TapBranch", *sorted([x, y]))

branch0 = branch(leaf1, sib1)     # Branch0 = H(Script0, Script1)
root    = branch(branch0, sib2)   # Root    = H(Branch0, Branch1)

# ---- Q = lift_x(P) + t*G, t = H_TapTweak(P ∥ root) -----------------------------
from coincurve import PublicKeyXOnly
t = tagged("TapTweak", internal, root)
# BIP341 x-only tweak-add: Q = lift_x(P) + t*G  (coincurve mutates in place, returns parity)
xo = PublicKeyXOnly(internal)
parity = xo.tweak_add(bytes(t))
q_xonly = xo.format()                                    # 32-byte x-only Q

# ---- bech32m encode (BIP350) ---------------------------------------------------
CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
def bech32_polymod(values):
    GEN = [0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3]; chk=1
    for v in values:
        b=chk>>25; chk=((chk&0x1ffffff)<<5)^v
        for i in range(5):
            chk^=GEN[i] if (b>>i)&1 else 0
    return chk
def hrp_expand(hrp): return [ord(x)>>5 for x in hrp]+[0]+[ord(x)&31 for x in hrp]
def convertbits(data,frm,to,pad=True):
    acc=0;bits=0;ret=[];maxv=(1<<to)-1
    for b in data:
        acc=(acc<<frm)|b;bits+=frm
        while bits>=to: bits-=to; ret.append((acc>>bits)&maxv)
    if pad and bits: ret.append((acc<<(to-bits))&maxv)
    return ret
def encode_p2tr(hrp, prog):
    data=[1]+convertbits(prog,8,5)
    poly=bech32_polymod(hrp_expand(hrp)+data+[0,0,0,0,0,0])^0x2bc830a3
    chk=[(poly>>5*(5-i))&31 for i in range(6)]
    return hrp+"1"+"".join(CHARSET[d] for d in data+chk)

addr = encode_p2tr(HRP, q_xonly)
print("reconstructed Merkle root :", root.hex())
print("reconstructed Q (x-only)  :", q_xonly.hex())
print("reconstructed address     :", addr)
print("published address         :", ADDRESS)
print("PASS" if addr == ADDRESS else "FAIL", ": reconstructed address",
      "==" if addr == ADDRESS else "!=", "published")
