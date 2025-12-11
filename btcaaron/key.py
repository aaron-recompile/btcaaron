"""
btcaaron.key - Key Management

The Key class provides a clean interface for Bitcoin key operations.
"""

from typing import Optional
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey

# Ensure testnet is set up
setup('testnet')


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
    def generate(cls, network: str = "testnet") -> "Key":
        """
        Generate a new random key.
        
        Args:
            network: "testnet" | "mainnet" (default: testnet)
            
        Returns:
            Key instance
        """
        # TODO: Implement secure random generation
        raise NotImplementedError("Key generation not yet implemented")
    
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
