"""
Faucet server - testnet drip endpoint

Deploy: set FAUCET_WIF, run with gunicorn or similar.
"""
import os
import sys

# 强制优先使用当前仓库的 btcaaron（解决 inquisition-lab 等副本抢包问题）
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)  # 即 btcaaron 仓库根目录
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import time

# 启动时检查：确保用的是带 get_balance 的 btcaaron
def _check_btcaaron():
    try:
        from btcaaron import get_balance
    except ImportError:
        import btcaaron as B
        pkg = getattr(B, "__path__", [""])[0] or getattr(B, "__file__", "")
        print("WARN: btcaaron 缺少 get_balance。当前加载自:", pkg)
        print("  修复: 在 btcaaron 仓库根目录执行: pip uninstall btcaaron -y && pip install -e .")

from flask import Flask, request, jsonify

app = Flask(__name__)

FAUCET_WIF = os.environ.get("FAUCET_WIF")
DRIP_AMOUNT = int(os.environ.get("DRIP_AMOUNT", "5000"))
FEE = 300
# Simple in-memory rate limit: address -> last drip timestamp
_last_drip: dict = {}
RATE_LIMIT_SEC = 86400  # 24 hours


@app.route("/")
def index():
    """Simple landing for browser visits."""
    return jsonify({
        "service": "btcaaron faucet",
        "endpoints": {"GET /status": "faucet balance", "POST /drip": '{"address":"tb1q..."}'},
        "docs": "https://github.com/aaron-recompile/btcaaron",
    })


def _valid_testnet_address(addr: str) -> bool:
    """Basic format check for testnet addresses."""
    if not addr or not isinstance(addr, str):
        return False
    a = addr.strip()
    prefixes = ("tb1q", "tb1p", "m", "n", "2")
    return any(a.startswith(p) for p in prefixes) and 26 <= len(a) <= 90


@app.route("/drip", methods=["POST"])
def drip():
    data = request.get_json(silent=True) or {}
    address = data.get("address", "").strip()

    if not _valid_testnet_address(address):
        return jsonify({"error": "invalid address"}), 400

    if not FAUCET_WIF:
        return jsonify({"error": "faucet not configured"}), 503

    # Rate limit
    now = time.time()
    if address in _last_drip and (now - _last_drip[address]) < RATE_LIMIT_SEC:
        return jsonify({"error": "limit 1 per address per day"}), 429

    try:
        from btcaaron import quick_transfer
        txid = quick_transfer(FAUCET_WIF, "taproot", address, DRIP_AMOUNT, fee=FEE)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    if not txid:
        return jsonify({"error": "broadcast failed"}), 500

    _last_drip[address] = now
    return jsonify({"txid": txid, "amount": DRIP_AMOUNT})


@app.route("/status", methods=["GET"])
def status():
    if not FAUCET_WIF:
        return jsonify({"error": "faucet not configured"}), 503

    try:
        from btcaaron import wif_to_addresses, get_balance
        addrs = wif_to_addresses(FAUCET_WIF)
        faucet_addr = addrs["taproot"]
        balance = get_balance(faucet_addr, network="testnet")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    per_drip = DRIP_AMOUNT + FEE
    remaining = balance // per_drip if per_drip else 0

    return jsonify({
        "balance_sats": balance,
        "drip_amount": DRIP_AMOUNT,
        "remaining_drips": remaining,
        "network": "testnet3",
        "faucet_address": faucet_addr,  # 充值地址：往这里打 testnet 币
    })


if __name__ == "__main__":
    _check_btcaaron()
    if not FAUCET_WIF:
        print("WARN: FAUCET_WIF not set. Set it before deploying.")
    port = int(os.environ.get("PORT", "5050"))  # 5050 避免 macOS AirPlay 占 5000
    app.run(host="0.0.0.0", port=port)
