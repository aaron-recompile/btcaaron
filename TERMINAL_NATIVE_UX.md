# Terminal-Native UX 实现说明

## 已实现

### P2: broadcast 并行化 ✅
- `Transaction.broadcast(provider="auto")` 并行请求 Mempool + Blockstream，先成功者返回
- 新增 `btcaaron.network.broadcast_parallel(tx_hex, network)`

### P3: from_balance() ✅
- `program.spend("hash").from_balance().to(addr, sats).unlock(...).build()`
- 自动 fetch program 地址的 UTXO，选最小可覆盖 amount+fee 的一笔

### P1: faucet 服务端 + 客户端 ✅
- **客户端** `btcaaron.faucet`: `faucet.drip(addr)`, `faucet.status()`
- **服务端** `faucet_server/`: Flask app，可部署到任意 VPS

---

## 本地测试

### 1. get_balance / fetch_utxos
```bash
python examples/test_get_balance.py -v
```

### 2. from_balance
```python
from btcaaron import Key, TapTree

alice = Key.from_wif("cRxebG1hY6vVgS9CSLNaEbEJaXkpZvc6nFeqqGT7v6gcW7MbzKNT")
program = (TapTree(internal_key=alice).hashlock("secret", label="h").build())

tx = (program.spend("h")
    .from_balance()           # 自动选 UTXO
    .to("tb1q...", 500)
    .unlock(preimage="secret")
    .build())
tx.broadcast()
```

### 3. faucet 本地
```bash
# 先安装 Flask
pip install flask

# 终端 1（默认 5050 端口）
export FAUCET_WIF="cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT"
python faucet_server/app.py

# 终端 2
python -c "
from btcaaron import faucet
print(faucet.status(url='http://localhost:5050'))
print(faucet.drip('tb1q2w85fm5g8kfhk9f63njplzu3yzcnluz9dgztjz', url='http://localhost:5050'))
"
```

---

## 部署 faucet 到免费 VPS

### 选项 A: Render（免费）
1. 新建 Web Service，连接 GitHub 仓库
2. Root directory: 留空（整个 btcaaron 仓库）
3. Build Command: `pip install -e . && pip install flask gunicorn`
4. Start Command: `gunicorn -w 1 -b 0.0.0.0:$PORT faucet_server.app:app`
5. Environment: `FAUCET_WIF` = 你的 testnet Taproot WIF

### 选项 B: Fly.io（免费 256MB）
```bash
cd btcaaron
fly launch
fly secrets set FAUCET_WIF=cVxxxx...
# 需配置 fly.toml 的 build/start
```

### 选项 C: Railway
1. 导入仓库
2. Root: 仓库根目录
3. Build: `pip install -e . && pip install flask gunicorn`
4. Start: `gunicorn -w 1 -b 0.0.0.0:$PORT faucet_server.app:app`

### 部署后
- 获得公网 URL，例如 `https://xxx.onrender.com`
- 客户端: `faucet.drip(addr, url="https://xxx.onrender.com")`
- 或设置 env: `export FAUCET_URL=https://xxx.onrender.com`，之后直接 `faucet.drip(addr)`

---

## 你这边需要配合的

1. **测试**：本地起 faucet_server，用上面的命令验证 drip
2. **部署**：选一个平台（Render 最简单），按步骤配置，把 FAUCET_WIF 设为环境变量
3. **域名（可选）**：若用 bitcoincoding.dev，在 DNS 加 A 记录指到 VPS，客户端默认 URL 即可用
