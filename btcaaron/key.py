"""
btcaaron.key - Key Management

The Key class provides a clean interface for Bitcoin key operations.
"""

import hashlib
from typing import Optional
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey


def _normalize_network(network: str) -> str:
    """
    Normalize app-level network labels to bitcoinutils setup labels.

    bitcoinutils distinguishes mainnet/testnet/regtest. For signet-family
    networks we use testnet address/version rules.
    """
    n = (network or "testnet").lower()
    if n == "mainnet":
        return "mainnet"
    if n == "regtest":
        return "regtest"
    return "testnet"


def set_network(network: str) -> str:
    """
    Set bitcoinutils global network context and return normalized value.
    """
    normalized = _normalize_network(network)
    setup(normalized)
    return normalized


def _default_coin_type(network: str) -> int:
    """
    Default BIP44/86 coin type by network.

    mainnet -> 0, testnet/regtest/signet-family -> 1
    """
    return 0 if _normalize_network(network) == "mainnet" else 1


def wif_secret_bytes(wif: str) -> bytes:
    """
    Decode WIF and return 32-byte raw private key bytes.

    Supports both compressed and uncompressed WIF.
    """
    try:
        import base58
    except ImportError as exc:
        raise ValueError("Missing dep: pip install base58") from exc

    try:
        decoded = base58.b58decode(wif)
    except Exception as exc:
        raise ValueError(f"Invalid WIF encoding: {exc}") from exc

    if len(decoded) not in (37, 38):
        raise ValueError("Invalid WIF length")

    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise ValueError("Invalid WIF checksum")

    prefix = payload[0]
    if prefix not in (0x80, 0xEF):
        raise ValueError("Invalid WIF network/version byte")

    if len(payload) == 34:
        # Compressed key marker must be present.
        if payload[-1] != 0x01:
            raise ValueError("Invalid compressed WIF marker")
        secret = payload[1:-1]
    else:
        secret = payload[1:]

    if len(secret) != 32:
        raise ValueError("Invalid private key length in WIF")
    return secret


def derive_wif_from_tprv(
    tprv: str,
    *,
    branch: int = 0,
    index: int = 0,
    purpose: int = 86,
    coin_type: Optional[int] = None,
    account: int = 0,
    network: str = "testnet",
) -> str:
    """
    Derive a compressed child WIF from an account-level xpriv/tprv.

    Default path follows BIP86:
      m / 86' / coin_type' / account' / branch / index
    """
    try:
        from bip32 import BIP32, HARDENED_INDEX
        import base58
    except ImportError as exc:
        raise ValueError("Missing deps: pip install bip32 base58") from exc

    if min(branch, index, purpose, account) < 0:
        raise ValueError("branch/index/purpose/account must be non-negative")

    ct = _default_coin_type(network) if coin_type is None else coin_type
    if ct < 0:
        raise ValueError("coin_type must be non-negative")

    path = [
        purpose | HARDENED_INDEX,
        ct | HARDENED_INDEX,
        account | HARDENED_INDEX,
        branch,
        index,
    ]
    try:
        bip32_obj = BIP32.from_xpriv(tprv)
        private_key = bip32_obj.get_privkey_from_path(path)
    except Exception as exc:
        raise ValueError(f"Invalid tprv/xpriv or derivation path: {exc}") from exc

    prefix = b"\x80" if _normalize_network(network) == "mainnet" else b"\xEF"
    payload = prefix + private_key + b"\x01"
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return base58.b58encode(payload + checksum).decode()


def taproot_descriptor_from_tprv(
    tprv: str,
    *,
    branch: int = 0,
    purpose: int = 86,
    coin_type: Optional[int] = None,
    account: int = 0,
    network: str = "testnet",
    wildcard: bool = True,
    index: int = 0,
) -> str:
    """
    Build a BIP86-style taproot descriptor string from xpriv/tprv.

    Example:
      tr(tprv.../86h/1h/0h/0/*)
    """
    ct = _default_coin_type(network) if coin_type is None else coin_type
    suffix = "*" if wildcard else str(index)
    return f"tr({tprv}/{purpose}h/{ct}h/{account}h/{branch}/{suffix})"


# Default module context remains testnet-first.
set_network("testnet")


class Key:
    """
    Bitcoin Key Manager (Immutable)
    
    Handles private key operations, signing, and public key derivation.
    
    Example:
        alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
        print(alice.xonly)  # x-only pubkey for Taproot
    """
    
    def __init__(self, private_key: PrivateKey):
        """Internal constructor. Use from_wif() or generate() instead."""
        self._private_key = private_key
        self._public_key = private_key.get_public_key()
    
    @classmethod
    def from_wif(cls, wif: str) -> "Key":
        """
        Create Key from WIF (Wallet Import Format) string.
        
        Args:
            wif: WIF-encoded private key
            
        Returns:
            Key instance
            
        Raises:
            ValueError: If WIF format is invalid
        """
        try:
            private_key = PrivateKey(wif)
            return cls(private_key)
        except Exception as e:
            raise ValueError(f"Invalid WIF private key: {e}")
    
    @classmethod
    def from_hex(cls, hex_privkey: str) -> "Key":
        """
        Create Key from hex-encoded private key.
        
        Args:
            hex_privkey: 32-byte hex string
            
        Returns:
            Key instance
        """
        try:
            private_key = PrivateKey(secret_exponent=int(hex_privkey, 16))
            return cls(private_key)
        except Exception as e:
            raise ValueError(f"Invalid hex private key: {e}")

    @classmethod
    def from_tprv(
        cls,
        tprv: str,
        *,
        branch: int = 0,
        index: int = 0,
        purpose: int = 86,
        coin_type: Optional[int] = None,
        account: int = 0,
        network: str = "testnet",
    ) -> "Key":
        """
        Create Key by deriving child private key from xpriv/tprv.

        Default derivation path:
          m/86'/coin_type'/account'/branch/index
        """
        set_network(network)
        wif = derive_wif_from_tprv(
            tprv,
            branch=branch,
            index=index,
            purpose=purpose,
            coin_type=coin_type,
            account=account,
            network=network,
        )
        return cls.from_wif(wif)
    
    @classmethod
    def generate(cls, network: str = "testnet") -> "Key":
        """
        Generate a new random key.
        
        Uses the underlying bitcoin-utils PrivateKey() which generates
        a cryptographically secure random private key via os.urandom().
        
        Args:
            network: "testnet" | "mainnet" (default: testnet)
            
        Returns:
            Key instance
        """
        set_network(network)
        private_key = PrivateKey()
        return cls(private_key)
    
    @property
    def wif(self) -> str:
        """WIF-encoded private key"""
        return self._private_key.to_wif()
    
    @property
    def pubkey(self) -> str:
        """33-byte compressed public key (hex)"""
        return self._public_key.to_hex()
    
    @property
    def xonly(self) -> str:
        """32-byte x-only public key for Taproot (hex)"""
        return self._public_key.to_x_only_hex()
    
    @property
    def _internal(self) -> PrivateKey:
        """Access to underlying bitcoinutils PrivateKey (internal use)"""
        return self._private_key
    
    @property
    def _internal_pub(self):
        """Access to underlying bitcoinutils PublicKey (internal use)"""
        return self._public_key
    
    def __repr__(self) -> str:
        return f"Key(xonly={self.xonly[:16]}...)"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Key):
            return False
        return self.xonly == other.xonly
    
    def __hash__(self) -> int:
        return hash(self.xonly)

    def sign_taproot_script_bip118(
        self,
        tx,
        txin_index: int,
        utxo_scripts: list,
        amounts: list[int],
        tapleaf_script,
        hash_type: int = 0x41,
        annex: bytes | None = None,
    ) -> str:
        """
        Tapscript signature using BIP118 ``Msg118`` / ``Ext118`` (e.g. ``hash_type=0x41``).

        The leaf must use a BIP118 pubkey (``0x01`` || 32-byte x-only) before ``OP_CHECKSIG``.
        Pass the underlying ``bitcoinutils.transactions.Transaction`` (not the btcaaron wrapper).
        """
        from bitcoinutils.script import Script as BUScript
        from bitcoinutils.schnorr import schnorr_sign
        from bitcoinutils.transactions import Transaction as BUTransaction
        from bitcoinutils.utils import b_to_h

        from .bip118 import bip118_sighash

        if not isinstance(tx, BUTransaction):
            raise TypeError("tx must be bitcoinutils.transactions.Transaction")
        if not isinstance(tapleaf_script, BUScript):
            raise TypeError("tapleaf_script must be bitcoinutils.script.Script")

        digest = bip118_sighash(
            tx,
            txin_index,
            utxo_scripts,
            amounts,
            tapleaf_script,
            hash_type=hash_type,
            annex=annex,
        )
        byte_key = self._private_key.to_bytes()
        rand_aux = bytes(32)
        sig = schnorr_sign(digest, byte_key, rand_aux)
        sig += hash_type.to_bytes(1, "big")
        return b_to_h(sig)
