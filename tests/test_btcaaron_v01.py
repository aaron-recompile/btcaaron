#!/usr/bin/env python3
"""
btcaaron - Simple Test Examples (Refactored)
"""
import pytest
from btcaaron import WIFKey, wif_to_addresses, quick_transfer

WIF = "cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT"
RECIPIENT = "tb1q2w85fm5g8kfhk9f63njplzu3yzcnluz9dgztjz"
FEE = 300


def get_addresses(wif):
    key = WIFKey(wif)
    return {
        "Legacy": key.get_legacy(),
        "SegWit": key.get_segwit(),
        "Taproot": key.get_taproot(),
    }

def test_address_generation():
    print("=" * 50)
    print("TEST 1: Address Generation")
    print("=" * 50)
    try:
        addresses = wif_to_addresses(WIF)
        for typ, addr in addresses.items():
            print(f"  {typ}: {addr}")

        print("\nUsing WIFKey object:")
        for typ, addr_obj in get_addresses(WIF).items():
            print(f"  {typ:8}: {addr_obj.address}")

        print("✅ Address generation test passed!")
    except Exception as e:
        print(f"❌ Address generation test failed: {e}")
        raise

def test_utxo_scanning():
    print("\n" + "=" * 50)
    print("TEST 2: UTXO Scanning")
    print("=" * 50)
    try:
        for typ, addr in get_addresses(WIF).items():
            print(f"\n{typ} Address: {addr.address}")
            utxos = addr.scan_utxos(debug=True)
            balance = addr.get_balance()
            print(f"  UTXOs: {len(utxos)} | Balance: {balance:,} sats")
            for i, utxo in enumerate(utxos[:3], 1):
                print(f"    {i}. {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['amount']} sats")
            if len(utxos) > 3:
                print(f"    ... and {len(utxos) - 3} more")

        print("\n✅ UTXO scanning test completed!")
    except Exception as e:
        print(f"❌ UTXO scanning test failed: {e}")
        raise

def test_balance_check():
    print("\n" + "=" * 50)
    print("TEST 3: Balance Check")
    print("=" * 50)
    try:
        balances = [(typ, addr.get_balance(), addr.address) for typ, addr in get_addresses(WIF).items()]
        total = sum(b for _, b, _ in balances)

        for typ, bal, _ in balances:
            print(f"  {typ:8}: {bal:,} sats")
        print(f"  Total   : {total:,} sats")

        if total:
            balances.sort(key=lambda x: x[1], reverse=True)
            typ, bal, addr = balances[0]
            print(f"\nHighest balance: {typ} | {bal:,} sats | {addr}")

        print("\n✅ Balance check test completed!")
    except Exception as e:
        print(f"❌ Balance check test failed: {e}")
        raise

@pytest.mark.skip(reason="Interactive - requires user input for real transfer")
def test_transfer():
    print("\n" + "=" * 50)
    print("TEST 4: Transfer Transaction")
    print("=" * 50)
    AMOUNT = 500
    try:
        candidates = [(t, a, a.get_balance()) for t, a in get_addresses(WIF).items() if a.get_balance() >= AMOUNT + FEE]
        if not candidates:
            print("❌ No address has sufficient balance.")
            raise AssertionError("No address has sufficient balance")

        from_type, from_addr, bal = sorted(candidates, key=lambda x: x[2], reverse=True)[0]
        print(f"From: {from_addr.address} ({from_type}, {bal:,} sats)")
        print(f"To:   {RECIPIENT} | Amount: {AMOUNT} | Fee: {FEE}")
        if input("Proceed? (y/N): ").lower() != 'y':
            print("Cancelled")
            raise AssertionError("User cancelled")

        txid = from_addr.send(RECIPIENT, AMOUNT, fee=FEE, debug=True).broadcast()
        print("✅ Broadcast TXID:", txid)
    except Exception as e:
        print(f"❌ Transfer test failed: {e}")
        raise

@pytest.mark.skip(reason="Interactive - requires user input for real transfer")
def test_quick_transfer():
    print("\n" + "=" * 50)
    print("TEST 5: Quick Transfer")
    print("=" * 50)
    AMOUNT = 400
    FROM = "Taproot"
    try:
        addr = get_addresses(WIF)[FROM]
        bal = addr.get_balance()
        print(f"Using {FROM}: {addr.address} | {bal:,} sats")
        if bal < AMOUNT + FEE:
            print("❌ Insufficient balance.")
            raise AssertionError("Insufficient balance")

        if input("Proceed? (y/N): ").lower() != 'y':
            print("Cancelled")
            raise AssertionError("User cancelled")

        txid = quick_transfer(WIF, FROM.lower(), RECIPIENT, AMOUNT, fee=FEE, debug=True)
        print("✅ Quick TXID:", txid)
    except Exception as e:
        print(f"❌ Quick transfer test failed: {e}")
        raise

def main():
    tests = [
        ("Address Generation", test_address_generation),
        ("UTXO Scanning", test_utxo_scanning),
        ("Balance Check", test_balance_check),
        ("Transfer Transaction", test_transfer),
        ("Quick Transfer", test_quick_transfer)
    ]

    print("\n📦 btcaaron Test Suite")
    for i, (name, _) in enumerate(tests, 1):
        print(f"{i}. {name}")
    print("0. Run All")

    try:
        sel = input("Select (0-N): ").strip()
        if sel == "0":
            for name, fn in tests:
                print(f"\n▶ {name}")
                fn()
        elif sel.isdigit() and 0 < int(sel) <= len(tests):
            name, fn = tests[int(sel) - 1]
            print(f"\n▶ {name}")
            fn()
        else:
            print("❌ Invalid selection")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()