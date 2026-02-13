# Render 部署 faucet 一步步指南

## 前置：代码已推送到 GitHub

确保 btcaaron 仓库已 push 到 GitHub（例如 `aaron-recompile/btcaaron`）。

---

## Step 1：注册 Render

1. 打开 https://render.com
2. 点击 **Get Started**
3. 用 GitHub 账号登录（**Sign up with GitHub**）

---

## Step 2：新建 Web Service

1. 登录后进入 **Dashboard**
2. 点击 **New +** → **Web Service**
3. 在 **Connect a repository** 里选择或连接 `btcaaron` 仓库
4. 若列表没有，点 **Configure account** 授权 Render 访问你的 GitHub

---

## Step 3：填写配置

| 字段 | 值 |
|------|-----|
| **Name** | `btcaaron-faucet`（或任意名称） |
| **Region** | 选离你近的 |
| **Branch** | `feature/terminal-native-ux`（或含 faucet 的分支） |
| **Root Directory** | **留空** |
| **Runtime** | Python 3 |

### Build 配置

| 字段 | 值 |
|------|-----|
| **Build Command** | `pip install -e . && pip install flask gunicorn` |
| **Start Command** | `gunicorn -w 1 -b 0.0.0.0:$PORT faucet_server.app:app` |

### 重要：添加环境变量

1. 滚动到 **Environment** 区域
2. 点击 **Add Environment Variable**
3. Key: `FAUCET_WIF`
4. Value: 你的 testnet Taproot WIF（例如 `cPeon9fBsW2BxwJTALj3hGzh9vm8C52Uqsce7MzXGS1iFJkPF4AT`）
5. 勾选 **Secret**（推荐，避免在日志中明文显示）

---

## Step 4：Deploy

1. 点击 **Create Web Service**
2. Render 自动开始构建和部署（约 2–5 分钟）
3. 日志里出现 `Your service is live at https://xxx.onrender.com` 表示部署成功

---

## Step 5：验证

在浏览器或终端测试：

```bash
# 替换成你的 Render URL
curl https://你的服务名.onrender.com/status
```

应返回类似：

```json
{"balance_sats": 55299, "drip_amount": 5000, "faucet_address": "tb1p...", ...}
```

---

## Step 6（可选）：绑定 faucet.bitcoincoding.dev

1. 在 Render 该服务的 **Settings** → **Custom Domains**
2. **Add Custom Domain** → 输入 `faucet.bitcoincoding.dev`
3. Render 会给出 CNAME 目标，例如 `btcaaron-faucet-xxx.onrender.com`
4. 到 bitcoincoding.dev 的 DNS 管理：
   - 类型：**CNAME**
   - 名称：`faucet`
   - 目标：`btcaaron-faucet-xxx.onrender.com`（用 Render 显示的值）
5. 保存并等待约 5–15 分钟生效

---

## 常见问题

| 问题 | 处理 |
|------|------|
| Build 失败，找不到 btcaaron | 确认 Root Directory 为空，Build 在仓库根目录执行 |
| 500 错误 | 查看 Render 的 **Logs**，常见为 FAUCET_WIF 未设置或余额不足 |
| 冷启动慢 | Render 免费版会 sleep，首次请求可能需几十秒；属正常现象 |
