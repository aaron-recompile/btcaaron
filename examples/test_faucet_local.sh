#!/bin/bash
# 本地测试 faucet：先起服务端，再调客户端
# 用法：./examples/test_faucet_local.sh

set -e
WIF="${FAUCET_WIF:-cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT}"
RECIPIENT="tb1q2w85fm5g8kfhk9f63njplzu3yzcnluz9dgztjz"

echo "=== 1. 启动服务端（后台，3 秒后继续）==="
export FAUCET_WIF="$WIF"
python faucet_server/app.py &
sleep 3

echo ""
echo "=== 2. 客户端测试 ==="
python -c "
from btcaaron import faucet
s = faucet.status(url='http://localhost:5000')
print('Status:', s)
txid = faucet.drip(\"$RECIPIENT\", url='http://localhost:5000')
print('Drip txid:', txid)
"

echo ""
echo "✅ 完成。可 kill 后台服务。"
kill %1 2>/dev/null || true
