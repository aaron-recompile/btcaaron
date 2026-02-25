# feature_taproot.py 重写可行性评估（btcaaron + btcrun）

日期：2026-02-21  
性质：研究分析（不改 btcaaron 实现代码）

## 1）文件概览

- 目标文件：`bitcoin/test/functional/feature_taproot.py`
- 对照文件：`bitcoin/test/functional/wallet_taproot.py`（仅用于能力边界对比）
- 总行数：
  - `feature_taproot.py`: 1899
  - `wallet_taproot.py`: 505
- `feature_taproot.py` 核心架构：
  - Context signing framework（`DEFAULT_CONTEXT`、`get`、`override`、`getter`）用于可组合签名流程与故障注入。
  - `make_spender()`：统一构造脚本、有效/无效签名路径、标准性与错误预期。
  - `add_spender()`：注册测试场景进入大规模随机执行池。
  - `test_spenders()`：批量造 UTXO、随机多输入交易、预计算 success/failure witness、同时检查 mempool policy 和区块共识。
  - `run_test()`：执行三段主流程：
    1) `gen_test_vectors()` 确定性向量场景  
    2) `sample_spenders + spenders_taproot_active` 共识主场景  
    3) `spenders_taproot_nonstandard` 非标准场景（单独 + 混合）

### Spender 规模（实测）

运行时生成数量：

- `spenders_taproot_active()`: 2793
- `spenders_taproot_nonstandard()`: 4
- `sample_spenders()`: 3

`run_test` 总计使用：2800 个 spender。

`spenders_taproot_active` 前缀分布：

- `unkver` 756, `opsuccess` 696, `sighash` 569, `applic` 256, `alwaysvalid` 169, `legacy` 128, `tapscript` 79, `sighashcache` 50, `siglen` 40, `compat` 32, `spendpath` 10, `sig` 5, `output` 2, `case24765` 1。

## 2）架构要点

### make_spender / Spender 字段语义

`Spender = (script, comment, is_standard, sat_function, err_msg, sigops_weight, no_fail, need_vin_vout_mismatch)`

- `script`：待花费 UTXO 的 scriptPubKey
- `comment`：场景标签（也是分类依据）
- `is_standard`：有效分支是否预期为标准交易
- `sat_function(tx, idx, utxos, valid)`：返回 `(scriptSig, witness_stack)`；`valid=False` 时走故障覆盖路径
- `err_msg`：失败时期望的报错片段
- `sigops_weight`：预 Taproot sigops 权重贡献
- `no_fail`：该场景是否不提供失败分支
- `need_vin_vout_mismatch`：是否要求输入/输出索引错位（`SIGHASH_SINGLE` 特测）

### Context signing framework 设计价值

- 模式：惰性表达式数据流图；通过覆盖 context key 注入错误。
- `sat_function` + `failure` 的意义：在同一交易骨架上稳定地产生“正确签名”和“定向错误签名”，极大减少重复代码并提升边界覆盖。

### add_spender 与批量执行机制

- `add_spender` 只负责登记场景。
- `test_spenders` 负责随机组合（输入数、版本、锁定时间、顺序、标准性）并逐输入切换 fail 位，构成压力测试。

### run_test 如何批量提交

- 构造 funding 交易生成测试 UTXO
- 为每个输入预先计算 success/failure witness
- 对同一交易依次提交：
  - 标准性检查（mempool）
  - 共识检查（打包区块）

## 3）场景分类与重写评估表

说明：
- “行范围”指类别注册逻辑所在范围
- “场景数”指运行时 spender 数
- `Core行数 / btcaaron预估` 为保守估计（含场景脚手架）

| 类别 | 行范围 | 场景数 | Core行数 | btcaaron预估 | 减少比例 | 优先级 | 备注 |
|---|---:|---:|---:|---:|---:|---:|---|
| BIP340 签名扰动（`sig`） | 684-699 | 5 | 16 | 10-14 | 10-35% | 4 | 适合快速迁移 |
| 无效内部公钥（`output`） | 700-737 | 2 | 38 | 20-28 | 25-47% | 4 | 需要无效 x-only 处理一致性 |
| Taproot sighash 矩阵（`sighash`） | 738-805 | 569 | 105 | 70-95 | 10-33% | 3 | annex/codesep 可配置仍有缺口 |
| 签名长度边界（`siglen`） | 807-842 | 40 | 36 | 28-40 | -10%-22% | 3 | 字节级变异重，收益一般 |
| BIP341 适用性（`applic`） | 843-864 | 256 | 22 | 22-40 | -80%-0% | 2 | Core 循环已很精炼 |
| Spend path 完整性（`spendpath`） | 865-916 | 10 | 53 | 30-40 | 25-43% | 4 | control block 变异很适合 |
| BIP342 边界（`tapscript`） | 918-1140 | 79 | 223 | 160-210 | 6-28% | 2 | 共识细节密集，迁移成本高 |
| 未知 leaf version（`unkver`） | 1142-1167 | 756 | 26 | 30-60 | -130%~-15% | 2 | 运行量大但源码循环短 |
| OP_SUCCESS 家族（`opsuccess`） | 1168-1211 | 696 | 44 | 50-90 | -105%~-14% | 1 | 同上，不一定更短 |
| 非 success opcode 守卫（`alwaysvalid`） | 1200-1211 | 169 | 12 | 12-20 | -66%-0% | 2 | 小而精，价值中等 |
| #24765 回归（`case24765`） | 1212-1217 | 1 | 6 | 8-12 | -100%~-33% | 2 | 必要但体量小 |
| legacy 混合（`legacy`） | 1218-1229 | 128 | 12 | 30-70 | -483%~-150% | 1 | 非 taproot 主战场 |
| 兼容性守卫（`compat`） | 1231-1237 | 32 | 7 | 15-30 | -329%~-114% | 1 | 低层 opcode 引擎校验 |
| sighash 缓存压力（`sighashcache`） | 1238-1302 | 50 | 65 | 45-65 | 0-31% | 3 | 可做，但需精细脚本控制 |
| 非标准但有效（`inactive`） | 1305-1322 | 4 | 20 | 12-18 | 10-40% | 4 | 很适合 btcrun 展示 |
| 教学样例（`tutorial`） | 1326-1359 | 3 | 34 | 12-18 | 47-65% | 5 | 最佳首批重写入口 |

## 4）依赖关系与可迁移性

### feature_taproot 对 Core test_framework 依赖

重度依赖：

- `blocktools`（`create_block` / `create_coinbase` / witness commitment）
- `messages`（`CTransaction` / `CTxIn` / `CTxOut` 级别构造）
- `script` 内部实现（`TaprootSignatureMsg`、BIP341 哈希片段、opcode）
- `key` 内部函数（`compute_xonly_pubkey`、`sign_schnorr`、tweak）
- 钱包/RPC断言辅助工具

### test_framework 独有能力（btcaaron 无直接等价）

- Python 端区块级精细拼装与 sigops 权重压测
- 与 fuzz 向量格式打通的确定性导出流程
- 大规模随机场景混合执行（policy + consensus + fail toggles）

### btcaaron / python-bitcoinutils / btcrun 已具备能力

- Taproot key-path/script-path 构造与签名
- taptree / merkle / control block 基本能力
- 自定义脚本叶（`RawScript`）与自定义 witness
- PSBT v0/v2（含 Taproot 字段）
- `btcrun` 多链实例与 RPC 命令统一调度（regtest/testnet3/signet/mainnet）

## 5）wallet_taproot vs feature_taproot（定位区别）

- `wallet_taproot.py`：钱包行为测试（descriptor 导入、地址推导、sendtoaddress、PSBT 流程）
- `feature_taproot.py`：协议规则与边界压力测试（错误 witness、错误 sighash、脚本边界、区块共识）

结论：`wallet_taproot.py` 更容易做“高层迁移演示”；`feature_taproot.py` 更能体现“协议测试脚手架”的研究价值。

## 6）推荐第一批重写目标（3-5 类）

### A. `tutorial`（优先级 5）

- 原因：逻辑清晰，减量最高，最适合作为对外展示样例。
- 思路：`TapTree.custom` + `SpendBuilder` + btcrun RPC 验证（valid/invalid 双分支）。

### B. `spendpath`（优先级 4）

- 原因：Taproot 价值核心（control block、merkle depth、negflag）。
- 思路：直接复用 `control_block()`，对关键字节做系统化突变并回放。

### C. `sig` + `output`（优先级 4）

- 原因：体量小但协议含金量高，利于快速产出结果。
- 思路：基线有效签名 + key/sighash/signature 变异 + invalid internal key 专项。

### D. `inactive`（优先级 4）

- 原因：能突出 btcrun 的“同场景跨链/跨标准性检查”价值。
- 思路：标准性拒绝 vs 区块可接受分离验证。

### E. `sighashcache`（优先级 3，可选）

- 原因：有一定工程价值，但实现难度高于展示收益。

## 7）btcaaron Gap 清单（按重写需求）

- Annex 一等配置能力  
  - 现状：高层 API 无显式 annex 控制  
  - 难度：中等

- codeseparator 位置 / leaf version / sighash 细粒度覆盖  
  - 现状：Core 上下文模型可覆写，btcaaron 暂无同等级抽象  
  - 难度：中高

- “valid/failure 双路径”统一抽象（类似 Core `failure` overlay）  
  - 现状：目前需手工写每个故障分支  
  - 难度：中等

- blocktools 等价层  
  - 现状：btcrun 强在 RPC 与多链管理，不是区块拼装工具  
  - 难度：中等

- legacy/witv0 混合矩阵  
  - 现状：可做但不符合 btcaaron Taproot 主线定位  
  - 难度：高，ROI 低

- P2P 传播层行为  
  - 现状：非 btcaaron 目标（RPC 驱动）  
  - 难度：不现实

## 8）评估框架修订（重要）

本报告原始口径偏向“逐行替换”。修订后改为：

1. **独立可运行性**（不依赖 Core 内部测试框架）  
2. **启动成本**（从零到跑通测试）  
3. **认知成本**（新开发者要理解多少底层框架）  
4. **教学可读性**（脚本能否直接作为课程/文档材料）

因此，不把“覆盖率 34%-47%”作为核心 KPI；更推荐使用“首批高价值场景完成度 + 启动成本下降”做对外叙事。

### 启动成本对比（建议用于申请材料）

- Core 路径：编译 Core（约 30 分钟）→ 理解 test_framework（约 2 小时）→ 跑测试
- btcaaron 路径：安装依赖（约 1 分钟）→ 阅读脚本（约 10 分钟）→ 跑测试

## 9）开工前候选任务与执行顺序（修订）

执行顺序采用：

**5 → 6 → 1 → 8 → 2 → 3 → 4 → 7 → 9**

理由：
- 先做 5/6（基础设施），1-4 的开发与复盘成本显著下降；
- 任务 1 后立刻做 8，用真实教学反馈驱动后续优先级。

### 阶段一边界（当前）

- 先做“外层实验框架”，落在 `examples/core_test/`
- 暂不修改 `btcaaron` 内核 API
- 待 2-3 个场景验证稳定后，再评估是否内核化

### 任务清单（按修订顺序）

1. **轻量 failure injection 机制（feature opportunity）**  
   - 场景：统一表达“valid vs failure overlay”  
   - 产出：实验 API 草案 + 2 个样例

2. **可复现实验输出规范**  
   - 场景：统一 `CASE / EXPECT / ACTUAL / VERDICT` 输出  
   - 产出：日志格式 + 报告模板

3. **`tutorial` 三件套重写**  
   - 场景：valid/invalid/nonstandard 各 1 个  
   - 产出：脚本 + README + 预期结果

4. **教学版文档打包（Chaincode cohort）**  
   - 场景：每个脚本配 5-10 分钟讲解稿  
   - 产出：`examples/core_test/lessons/`

5. **`spendpath` control block 变异实验**  
   - 场景：negflag/merkle/control block 截断与填充  
   - 产出：矩阵脚本 + 通过/失败表

6. **`sig` / `output` 基线正确性实验**  
   - 场景：签名扰动、sighash 变异、invalid internal key  
   - 产出：最小回归集

7. **`inactive`（非标准但有效）分离验证**  
   - 场景：policy 与 block acceptance 双通道  
   - 产出：btcrun 验证模板

8. **跨链一致性回归脚本（regtest/testnet3/mainnet）**  
   - 场景：同一变异跨实例复测  
   - 产出：一键矩阵 runner

9. **sighashcache 小型化 PoC（可选）**  
   - 场景：先做代表性子集  
   - 产出：可运行 PoC（非全量）

一句话定位（修订版）：

> btcaaron + btcrun 的价值不在于“替换 Core 多少行”，而在于把高价值 Taproot 协议测试降维成可独立运行、可教学、可复现的工程资产。

