

# btcaaron

A simple Bitcoin Testnet toolkit for developers.  
Easily generate addresses, scan UTXOs, build and broadcast transactions — with full support for Legacy, SegWit, and Taproot.

---

## 🔧 Features

- ✅ Generate Legacy / SegWit / Taproot addresses from WIF
- 🔍 Scan UTXOs and check balance via public APIs
- 🧠 Build & sign transactions (manual or quick mode)
- 🚀 Broadcast to Blockstream or Mempool endpoints
- 🧪 Simple test suite for local debugging

---

## 📦 Installation

```bash
pip install btcaaron

Or install from source:

git clone https://github.com/aaron-recompile/btcaaron.git
cd btcaaron
pip install .


⸻

🚀 Quick Start

from btcaaron import WIFKey, quick_transfer

# Your testnet WIF private key
wif = ""

# Generate addresses
key = WIFKey(wif)
print("Taproot:", key.get_taproot().address)

# Check balance
balance = key.get_taproot().get_balance()
print("Balance:", balance, "sats")

# Quick transfer
if balance > 1000:
    txid = quick_transfer(wif, "taproot", "tb1q...", amount=500, fee=300)
    print("Broadcasted:", txid)


⸻

📁 Project Structure

btcaaron/
├── btcaaron.py          # Main library
├── test.py              # Example-based test runner
├── README.md            # This file
├── setup.py             # Install and packaging
├── LICENSE              # MIT License


⸻

👨‍💻 Author

Aaron Zhang
https://x.com/aaron_recompile

⸻

📄 License

MIT License - Free for commercial and personal use.

