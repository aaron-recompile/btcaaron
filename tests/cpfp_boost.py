#!/usr/bin/env python3
from btcaaron import quick_transfer, WIFKey

# 父交易 UTXO
PARENT_TXID = "5534b524df6d96822036ce4dc6037beb07cb536bd81a1dc822c19d5776615f1e"
PARENT_VOUT = 1
UTXO_AMOUNT = 47537

# 你的 WIF
WIF = "cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT"

# 收款地址
RECIPIENT = "tb1q2w85fm5g8kfhk9f63njplzu3yzcnluz9dgztjz"

# 手续费
HIGH_FEE = 5000
SEND_AMOUNT = UTXO_AMOUNT - HIGH_FEE


def main():
    if SEND_AMOUNT <= 0:
        print("❌ Fee 太高，剩余金额不足。")
        return

    addr = WIFKey(WIF).get_taproot()
    print("=" * 50)
    print("CPFP Accelerator (quick_transfer)")
    print("=" * 50)
    print(f"From: {addr.address}")
    print(f"To:   {RECIPIENT}")
    print(f"Amount: {SEND_AMOUNT} sats | Fee: {HIGH_FEE} sats")

    confirm = input("Proceed with CPFP? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled")
        return

    try:
        txid = quick_transfer(WIF, "taproot", RECIPIENT, SEND_AMOUNT, fee=HIGH_FEE, debug=True)
        print("✅ CPFP TXID:", txid)
    except Exception as e:
        print("❌ CPFP failed:", e)


if __name__ == "__main__":
    main()