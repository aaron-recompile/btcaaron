# btcaaron Faucet Server

Testnet drip endpoint. Deploy anywhere (Render, Railway, Fly.io, VPS).

## Quick Start

```bash
# 1. Clone btcaaron
cd btcaaron

# 2. Install dependencies
pip install flask
pip install -e .   # 在 btcaaron 仓库根目录；或: pip install btcaaron

# 3. Set your testnet WIF (never commit this!)
export FAUCET_WIF="cV..."

# 4. Run
python faucet_server/app.py
# → http://localhost:5050 (默认 5050，避免 macOS 5000 被占)
```

## Endpoints

| Method | Path   | Body            | Response            |
|--------|--------|-----------------|---------------------|
| POST   | /drip  | `{"address":"tb1q..."}` | `{"txid":"...", "amount":5000}` |
| GET    | /status| —               | `{"balance_sats", "remaining_drips", ...}` |

## Deploy to Free VPS

### Render

1. New Web Service, connect repo
2. Root Directory: 留空
3. Build: `pip install -e . && pip install flask gunicorn`
4. Start: `gunicorn -w 1 -b 0.0.0.0:$PORT faucet_server.app:app`
5. Add env var: `FAUCET_WIF`

### Fly.io

```bash
fly launch
# Set FAUCET_WIF secret: fly secrets set FAUCET_WIF=cV...
```

### Railway / DigitalOcean

Same pattern: set `FAUCET_WIF`, run gunicorn.

## Local Test

```bash
# 1. 安装 Flask
pip install flask

# 2. Terminal 1: server（默认 5050 端口）
export FAUCET_WIF="cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT"
python faucet_server/app.py

# 3. Terminal 2: client
python -c "
from btcaaron import faucet
print(faucet.status(url='http://localhost:5050'))
txid = faucet.drip('tb1q2w85fm5g8kfhk9f63njplzu3yzcnluz9dgztjz', url='http://localhost:5050')
print(f'txid: {txid}')
"
```

## 充值 faucet

faucet 地址 = FAUCET_WIF 对应的 Taproot 地址。`GET /status` 会返回 `faucet_address`。

充值方式：
1. **浏览器水龙头**：打开 https://bitcoinfaucet.uo1.net 或 https://testnet-faucet.mempool.co ，输入 `faucet_address`，领取后打到该地址
2. **从自己钱包**：若你有其他 testnet 地址有余额，用 Sparrow/其他钱包转给 `faucet_address`

每次 drip 消耗 5000 + 300 手续费 ≈ 5300 sats，余额需 ≥ 5300 才能发一滴。

## Security

- FAUCET_WIF in env only, never in code
- Rate limit: 1 drip per address per 24h
- Add `.env` to .gitignore
