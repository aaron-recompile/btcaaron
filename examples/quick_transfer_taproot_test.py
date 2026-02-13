#!/usr/bin/env python3
"""
quick_transfer taproot 实际转账测试

Alice 的 Taproot 地址 → Bob 的 Taproot 地址
使用 testnet 密钥，两边都是你可控的。

前提：Alice 的 taproot 地址有余额（可从水龙头或之前转账获得）

Run: PYTHONPATH=. python examples/quick_transfer_taproot_test.py
"""

from btcaaron import Key, TapTree, quick_transfer

# 测试网密钥（与 test_btcaaron_v02 / ch09 相同）
ALICE_WIF = "cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT"
BOB_WIF = "cSNdLFDf3wjx1rswNL2jKykbVkC6o56o5nYZi4FUkWKjFn2Q5DSG"

alice = Key.from_wif(ALICE_WIF)
bob = Key.from_wif(BOB_WIF)
alice_addr = TapTree(internal_key=alice).build().address
bob_addr = TapTree(internal_key=bob).build().address

print("=" * 50)
print("quick_transfer 实际转账测试 (Taproot)")
print("=" * 50)
print(f"  发送 (Alice): {alice_addr}")
print(f"  接收 (Bob):   {bob_addr}")
print(f"  金额: 500 sats, 手续费: 300 sats (输出须 ≥330, 建议 ≥546)")
print()
print("  若需充值，打 testnet 币到上面的 Alice 地址即可。")
print()

txid = quick_transfer(ALICE_WIF, "taproot", bob_addr, 500, fee=300, debug=True)

if txid:
    print()
    print(f"✅ 成功! TxID: {txid}")
    print(f"   查看: https://mempool.space/testnet/tx/{txid}")
else:
    print()
    print("❌ 广播失败（有 UTXO 则为节点/API 问题，非余额）")
