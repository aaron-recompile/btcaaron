"""
btcaaron - Lightweight Bitcoin Testnet Toolkit

A simple, clean toolkit for Bitcoin testnet operations including address generation,
UTXO querying, transaction creation, signing, and broadcasting.

Author: Aaron Zhang (https://x.com/aaron_recompile)
Version: 0.1.1
License: MIT
"""

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .tree.program import TaprootProgram
import requests
import concurrent.futures
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, P2pkhAddress, P2wpkhAddress, P2trAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput, TxWitnessInput
from bitcoinutils.script import Script

# Initialize testnet environment
setup('testnet')

# Network configuration
TIMEOUT = 5
MAX_WORKERS = 2
DEFAULT_FEE = 300
DUST_LIMIT = 546
# Taproot dust limit (Bitcoin Core); outputs below this get "dust" rejection
DUST_LIMIT_TAPROOT = 330


class WIFKey:
    """
    WIF Private Key Manager
    
    Generate different types of Bitcoin addresses from a WIF private key
    """
    
    def __init__(self, wif_str: str):
        """
        Initialize WIF private key
        
        Args:
            wif_str: WIF format private key string
            
        Raises:
            ValueError: When WIF format is invalid
        """
        try:
            self.wif = wif_str
            self.private_key = PrivateKey(wif_str)
            self.public_key = self.private_key.get_public_key()
        except Exception as e:
            raise ValueError(f"Invalid WIF private key: {str(e)}")
    
    def get_legacy(self) -> 'BTCAddress':
        """Get Legacy address object (P2PKH)"""
        address = self.public_key.get_address().to_string()
        return BTCAddress(self.wif, address, "legacy", self.private_key, self.public_key)
    
    def get_segwit(self) -> 'BTCAddress':
        """Get SegWit address object (P2WPKH)"""
        address = self.public_key.get_segwit_address().to_string()
        return BTCAddress(self.wif, address, "segwit", self.private_key, self.public_key)
    
    def get_taproot(self) -> 'BTCAddress':
        """Get Taproot address object (P2TR)"""
        address = self.public_key.get_taproot_address().to_string()
        return BTCAddress(self.wif, address, "taproot", self.private_key, self.public_key)


class BTCAddress:
    """
    Bitcoin Address Handler
    
    Handles specific address type operations (UTXO queries, transfers, etc.)
    """
    
    def __init__(self, wif: str, address: str, addr_type: str, private_key, public_key):
        self.wif = wif
        self.address = address
        self.type = addr_type
        self.private_key = private_key
        self.public_key = public_key
        
        # Create address object
        if addr_type == "legacy":
            self.addr_obj = P2pkhAddress(address)
        elif addr_type == "segwit":
            self.addr_obj = P2wpkhAddress(address)
        elif addr_type == "taproot":
            self.addr_obj = P2trAddress(address)
        else:
            raise ValueError(f"Unsupported address type: {addr_type}")
    
    def __str__(self) -> str:
        return f"{self.type.upper()} Address: {self.address}"
    
    def scan_utxos(self, debug: bool = False) -> List[Dict]:
        """
        Scan all available UTXOs for this address
        
        Args:
            debug: Whether to output debug information
            
        Returns:
            List[Dict]: List of UTXOs
        """
        if debug:
            print(f"Scanning UTXOs for {self.type} address: {self.address}")
        
        # API endpoints
        apis = [
            ("Blockstream testnet", f"https://blockstream.info/testnet/api/address/{self.address}/utxo"),
            ("Mempool testnet", f"https://mempool.space/testnet/api/address/{self.address}/utxo"),
        ]
        
        def fetch_utxos(api_info) -> Optional[List[Dict]]:
            """Fetch UTXOs from a single API"""
            api_name, api_url = api_info
            try:
                response = requests.get(api_url, timeout=TIMEOUT)
                if response.status_code == 200:
                    raw_utxos = response.json()
                    if debug:
                        print(f"  {api_name}: Found {len(raw_utxos)} UTXOs")
                    
                    utxos = []
                    for utxo in raw_utxos:
                        processed_utxo = {
                            'txid': utxo['txid'],
                            'vout': utxo['vout'],
                            'amount': utxo['value'],
                            'scriptPubKey': self.addr_obj.to_script_pub_key().to_hex(),
                            'type': self.type.upper()
                        }
                        utxos.append(processed_utxo)
                        
                        if debug:
                            print(f"    - {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['value']} sats")
                    
                    return utxos
                else:
                    if debug:
                        print(f"  {api_name}: HTTP {response.status_code}")
            except Exception as e:
                if debug:
                    print(f"  {api_name}: Error - {str(e)}")
            return None
        
        # Try APIs sequentially (simpler than concurrent)
        for api_name, api_url in apis:
            result = fetch_utxos((api_name, api_url))
            if result is not None:
                if debug:
                    total = sum(utxo['amount'] for utxo in result)
                    print(f"  Success: {len(result)} UTXOs, Total: {total} sats")
                return result
        
        if debug:
            print("  All APIs failed")
        return []
    
    def get_balance(self, debug: bool = False) -> int:
        """
        Get address balance
        
        Args:
            debug: Whether to output debug information
            
        Returns:
            int: Address balance in satoshis
        """
        if debug:
            print(f"Checking balance for {self.type} address: {self.address}")
            
        utxos = self.scan_utxos(debug=debug)
        balance = sum(utxo['amount'] for utxo in utxos)
        
        if debug:
            print(f"  Balance: {balance:,} sats")
            
        return balance
    
    def send(self, to_addr: str, amount: int, fee: int = DEFAULT_FEE, debug: bool = False) -> 'BTCTransaction':
        """
        Create and sign a transfer transaction
        
        Args:
            to_addr: Recipient address
            amount: Transfer amount in satoshis
            fee: Transaction fee in satoshis
            debug: Whether to output debug information
            
        Returns:
            BTCTransaction: Signed transaction object
            
        Raises:
            ValueError: When insufficient balance or invalid parameters
        """
        if debug:
            print(f"Creating transaction from {self.type} address:")
            print(f"  From: {self.address}")
            print(f"  To: {to_addr}")
            print(f"  Amount: {amount:,} sats")
            print(f"  Fee: {fee:,} sats")
        
        # Get UTXOs
        utxos = self.scan_utxos(debug=debug)
        if not utxos:
            raise ValueError(f"No UTXOs available for address {self.address}")
        
        # Check balance
        total_needed = amount + fee
        total_available = sum(utxo['amount'] for utxo in utxos)
        
        if total_available < total_needed:
            raise ValueError(f"Insufficient balance. Need: {total_needed:,}, Available: {total_available:,}")
        
        # Select UTXOs (largest first)
        utxos.sort(key=lambda x: x['amount'], reverse=True)
        selected_utxos = []
        total_input = 0
        
        for utxo in utxos:
            selected_utxos.append(utxo)
            total_input += utxo['amount']
            if total_input >= total_needed:
                break
        
        if debug:
            print(f"  Selected UTXOs:")
            for i, utxo in enumerate(selected_utxos, 1):
                print(f"    {i}. {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['amount']:,} sats")
            print(f"  Total input: {total_input:,} sats")
        
        # Create transaction inputs
        tx_inputs = []
        for utxo in selected_utxos:
            tx_input = TxInput(utxo['txid'], utxo['vout'])
            tx_inputs.append(tx_input)
        
        # Create transaction outputs
        tx_outputs = []
        
        # 1. Output to recipient
        to_addr_obj = self._create_address_object(to_addr)
        tx_out = TxOutput(amount, to_addr_obj.to_script_pub_key())
        tx_outputs.append(tx_out)
        
        if debug:
            print(f"  Output 1: {amount:,} sats -> {to_addr}")
        
        # 2. Change output (check dust limit)
        change_amount = total_input - amount - fee
        if change_amount > 0:
            if change_amount < DUST_LIMIT:
                # Change too small, add to fee
                if debug:
                    print(f"  Warning: Change amount {change_amount} sats < {DUST_LIMIT} sats (dust limit)")
                    print(f"  Adding change to fee: {fee} + {change_amount} = {fee + change_amount} sats")
            else:
                change_out = TxOutput(change_amount, self.addr_obj.to_script_pub_key())
                tx_outputs.append(change_out)
                if debug:
                    print(f"  Change: {change_amount:,} sats -> {self.address}")
        elif debug:
            print(f"  No change (exact amount match)")
        
        # Create transaction
        has_segwit = self.type in ['segwit', 'taproot']
        tx = Transaction(tx_inputs, tx_outputs, has_segwit=has_segwit)
        
        if debug:
            print(f"  Created {'SegWit' if has_segwit else 'Legacy'} transaction")
        
        # Sign transaction
        self._sign_transaction(tx, selected_utxos, debug=debug)
        
        signed_hex = tx.serialize()
        
        if debug:
            print(f"  Signing complete!")
            print(f"  Transaction size: {len(signed_hex)//2} bytes")
        
        return BTCTransaction(signed_hex, debug=debug)
    
    def _create_address_object(self, address: str):
        """Create address object from address string"""
        if address.startswith(('1', 'm', 'n')):  # Legacy
            return P2pkhAddress(address)
        elif address.startswith(('bc1q', 'tb1q')):  # SegWit v0
            return P2wpkhAddress(address)
        elif address.startswith(('bc1p', 'tb1p')):  # Taproot
            return P2trAddress(address)
        else:
            raise ValueError(f"Unsupported address format: {address}")
    
    def _sign_transaction(self, tx: Transaction, selected_utxos: List[Dict], debug: bool = False):
        """Sign transaction based on address type"""
        if debug:
            print(f"  Signing with {self.type} method...")
        
        if self.type == 'legacy':
            # P2PKH signing
            for i, tx_input in enumerate(tx.inputs):
                previous_locking_script = self.addr_obj.to_script_pub_key()
                sig = self.private_key.sign_input(tx, i, previous_locking_script)
                pk = self.private_key.get_public_key().to_hex()
                unlocking_script = Script([sig, pk])
                tx_input.script_sig = unlocking_script
                
        elif self.type == 'segwit':
            # P2WPKH signing
            for i, tx_input in enumerate(tx.inputs):
                script_code = self.public_key.get_address().to_script_pub_key()
                input_amount = selected_utxos[i]['amount']
                sig = self.private_key.sign_segwit_input(tx, i, script_code, input_amount)
                public_key_hex = self.private_key.get_public_key().to_hex()
                tx_input.script_sig = Script([])
                tx.witnesses.append(TxWitnessInput([sig, public_key_hex]))
                
        elif self.type == 'taproot':
            # P2TR signing
            input_amounts = [utxo['amount'] for utxo in selected_utxos]
            input_scripts = [self.addr_obj.to_script_pub_key() for _ in selected_utxos]
            
            for i, tx_input in enumerate(tx.inputs):
                sig = self.private_key.sign_taproot_input(tx, i, input_scripts, input_amounts)
                tx_input.script_sig = Script([])
                tx.witnesses.append(TxWitnessInput([sig]))


class BTCTransaction:
    """
    Bitcoin Transaction Handler
    
    Handles signed transaction broadcasting
    """
    
    def __init__(self, tx_hex: str, debug: bool = False):
        self.tx_hex = tx_hex
        self.debug = debug
        self.txid = None
    
    def __str__(self) -> str:
        status = f"(TxID: {self.txid})" if self.txid else "(Not broadcasted)"
        return f"BTCTransaction {status}"
    
    def broadcast(self) -> Optional[str]:
        """
        Broadcast transaction to network
        
        Returns:
            Optional[str]: Transaction ID if successful, None if failed
        """
        if self.debug:
            print(f"Broadcasting transaction:")
            print(f"  Transaction size: {len(self.tx_hex)//2} bytes")
        
        # Broadcast endpoints
        broadcast_apis = [
            ("Blockstream testnet", "https://blockstream.info/testnet/api/tx"),
            ("Mempool testnet", "https://mempool.space/testnet/api/tx"),
        ]
        
        # Try each API sequentially
        for api_name, api_url in broadcast_apis:
            try:
                if self.debug:
                    print(f"  Trying {api_name}...")
                
                response = requests.post(
                    api_url,
                    data=self.tx_hex,
                    timeout=TIMEOUT,
                    headers={'Content-Type': 'text/plain'}
                )
                
                if response.status_code == 200:
                    response_text = response.text.strip()
                    # Validate response is a valid transaction ID
                    if len(response_text) == 64 and all(c in '0123456789abcdef' for c in response_text.lower()):
                        self.txid = response_text
                        if self.debug:
                            print(f"    Success: {response_text}")
                        return response_text
                    else:
                        if self.debug:
                            print(f"    Invalid response format: {response_text}")
                else:
                    if self.debug:
                        print(f"    HTTP {response.status_code}: {response.text[:100]}...")
                        
            except Exception as e:
                if self.debug:
                    print(f"    Error: {e}")
        
        if self.debug:
            print("  All broadcast attempts failed")
        return None


# Convenience functions
def wif_to_addresses(wif: str) -> Dict[str, str]:
    """
    Generate all address types from WIF
    
    Args:
        wif: WIF private key string
        
    Returns:
        Dict[str, str]: Dictionary containing all address types
    """
    wif_key = WIFKey(wif)
    return {
        'legacy': wif_key.get_legacy().address,
        'segwit': wif_key.get_segwit().address,
        'taproot': wif_key.get_taproot().address
    }


def quick_transfer(wif: str, from_type: str, to_addr: str, amount: int,
                  fee: int = DEFAULT_FEE, debug: bool = False) -> Optional[str]:
    """
    Quick transfer using specified address type.

    Taproot path uses v0.2 Key + TapTree + SpendBuilder with auto UTXO selection.
    Legacy and SegWit paths use the original BTCAddress.send() flow.

    Args:
        wif: WIF private key
        from_type: Sender address type ('legacy', 'segwit', 'taproot')
        to_addr: Recipient address
        amount: Transfer amount in satoshis
        fee: Transaction fee in satoshis
        debug: Whether to output debug information

    Returns:
        Optional[str]: Transaction ID if successful, None if failed
    """
    try:
        if debug:
            print(f"Quick transfer ({from_type}):")

        if from_type.lower() == 'taproot':
            if amount < DUST_LIMIT_TAPROOT:
                raise ValueError(
                    f"Output {amount} sats below Taproot dust limit ({DUST_LIMIT_TAPROOT}). "
                    f"Use at least {DUST_LIMIT_TAPROOT} sats."
                )
            # v0.2 flow: Key + TapTree keypath + auto UTXO selection
            from .key import Key
            from .tree import TapTree
            from .network.utxo import fetch_utxos, select_utxos

            key = Key.from_wif(wif)
            program = TapTree(internal_key=key).build()
            utxos = fetch_utxos(program.address, network="testnet", debug=debug)
            if not utxos:
                if debug:
                    print("  No UTXOs available")
                return None

            total_needed = amount + fee
            selected = select_utxos(utxos, total_needed)
            if not selected:
                if debug:
                    avail = sum(u["amount"] for u in utxos)
                    print(f"  Insufficient balance. Need: {total_needed:,}, Available: {avail:,}")
                return None

            if debug:
                for i, u in enumerate(selected, 1):
                    print(f"    {i}. {u['txid'][:16]}...:{u['vout']} = {u['amount']:,} sats")

            utxo_list = [(u["txid"], u["vout"], u["amount"]) for u in selected]
            total_input = sum(u["amount"] for u in selected)
            change = total_input - amount - fee

            builder = (program.keypath()
                .from_utxos(utxo_list)
                .to(to_addr, amount))
            if change >= DUST_LIMIT:
                builder = builder.to(program.address, change)
            elif debug and change > 0:
                print(f"  Change {change} sats < {DUST_LIMIT} (dust), added to fee")

            tx = builder.sign(key).build()

            txid = tx.broadcast()
            if debug:
                print(f"  Transfer successful! TxID: {txid}")
            return txid

        # Legacy and SegWit: use original flow
        wif_key = WIFKey(wif)
        if from_type.lower() == 'legacy':
            from_addr = wif_key.get_legacy()
        elif from_type.lower() == 'segwit':
            from_addr = wif_key.get_segwit()
        else:
            raise ValueError(f"Unsupported address type: {from_type}")

        tx = from_addr.send(to_addr, amount, fee, debug=debug)
        txid = tx.broadcast()

        if txid:
            if debug:
                print(f"  Transfer successful! TxID: {txid}")
            return txid
        if debug:
            print("  Transfer failed")
        return None

    except Exception as e:
        if debug:
            print(f"Quick transfer failed: {str(e)}")
            import traceback
            traceback.print_exc()
        return None


def fund_program(
    wif: str,
    program: "TaprootProgram",
    amount: int,
    fee: int = DEFAULT_FEE,
    debug: bool = False,
) -> Optional[str]:
    """
    Fund a Taproot commit address from your taproot wallet.

    One-liner for IDE workflow — no need to leave the editor to fund
    intermediate/commit addresses when building complex scripts.

    Example:
        program = (TapTree(internal_key=alice).hashlock(...).multisig(...)).build()
        txid = fund_program(MY_WIF, program, 10_000)  # 打 10000 sats 到 commit 地址

    Args:
        wif: Your taproot wallet WIF (used as source)
        program: TaprootProgram from TapTree(...).build()
        amount: Sats to send (must be >= 330 for Taproot dust limit)
        fee: Transaction fee (default 300)
        debug: Print UTXO selection and tx details

    Returns:
        Transaction ID if successful, None otherwise
    """
    return quick_transfer(wif, "taproot", program.address, amount, fee, debug)


# Module information
__version__ = "0.1.1"
__author__ = "Aaron Zhang"
__all__ = [
    'WIFKey',
    'BTCAddress',
    'BTCTransaction',
    'wif_to_addresses',
    'quick_transfer',
    'fund_program',
]