# DSL vs Miniscript Boundary

## Purpose

This document defines the boundary between `btcaaron` DSL and Miniscript so the project can scale without direction drift.

---

## EN: Boundary Definition

### 1) Core positioning

- **Miniscript** is a policy language layer: composable spending conditions with analyzable properties.
- **btcaaron DSL** is an experiment workflow layer: construct, mutate, validate, classify, and reproduce.

### 2) What btcaaron DSL should do

1. Fast transaction/script construction for testing scenarios.
2. Failure injection hooks (witness, control block, signature, output mutations).
3. Policy/consensus split experiments.
4. Cross-instance consistency checks.
5. Standardized evidence output (`CASE/EXPECT/ACTUAL/VERDICT`).

### 3) What btcaaron DSL should NOT do (for now)

1. Re-implement full Miniscript parser/type system.
2. Promise full Miniscript static analysis guarantees.
3. Become a replacement for Core's functional test framework.
4. Mix too many symbolic language semantics into runtime experiment APIs.

### 4) Interface strategy (recommended)

Use an adapter boundary, not a merger:

- Input path A: btcaaron-native scenario DSL -> descriptor/script -> experiment runner
- Input path B: Miniscript policy -> descriptor/script -> experiment runner

This keeps `btcaaron` focused on experimental execution while allowing policy-language interoperability.

### 5) Proposed future interfaces

1. `compile_policy(policy_str, backend="miniscript") -> descriptor`
2. `run_descriptor_matrix(descriptor, mutations=[...], instances=[...]) -> report`
3. `classify_reject(detail) -> category`
4. `export_evidence(report, format="md|json")`

### 6) Decision guardrails

When evaluating a new feature, ask:

1. Does it reduce experiment startup cost?
2. Does it improve failure localization or reproducibility?
3. Can it be implemented without rebuilding Miniscript internals?
4. Does it strengthen Core-contributor ramp value?

If answers are mostly "no", do not add it to the DSL core.

### 7) Practical roadmap

- Near-term: strengthen experiment matrices and evidence automation.
- Mid-term: add optional Miniscript adapter (import/compile path).
- Long-term: maintain "policy language in, experiment engine out" architecture.

---

## 中文：边界定义

### 1）核心定位

- **Miniscript**：策略语言层，强调可组合与可分析属性。
- **btcaaron DSL**：实验工作流层，强调构造、变异、验证、分类和复现。

### 2）btcaaron DSL 应该做的事

1. 面向测试场景的快速交易/脚本构造。
2. 故障注入能力（witness/control block/签名/输出变异）。
3. policy 与 consensus 分层实验。
4. 跨实例一致性验证。
5. 标准化证据输出（`CASE/EXPECT/ACTUAL/VERDICT`）。

### 3）btcaaron DSL 目前不应做的事

1. 重写完整 Miniscript 解析器与类型系统。
2. 承诺完整 Miniscript 静态分析保证。
3. 试图替代 Core functional test 框架。
4. 在实验 API 中混入过多符号语言语义，导致复杂度上升。

### 4）接口策略（推荐）

采用“适配器边界”，不要“融合重写”：

- 路径 A：btcaaron 场景 DSL -> descriptor/script -> 实验引擎
- 路径 B：Miniscript policy -> descriptor/script -> 实验引擎

这样可以保证 btcaaron 聚焦实验执行，同时支持策略语言互操作。

### 5）建议的未来接口

1. `compile_policy(policy_str, backend="miniscript") -> descriptor`
2. `run_descriptor_matrix(descriptor, mutations=[...], instances=[...]) -> report`
3. `classify_reject(detail) -> category`
4. `export_evidence(report, format="md|json")`

### 6）路线守护规则（防漂移）

评估新功能时先问：

1. 是否降低实验启动成本？
2. 是否提升失败定位或复现能力？
3. 是否可以在不重写 Miniscript 内核的前提下实现？
4. 是否增强 Core 贡献者培养价值？

若大多数答案是否定，则不应进入 DSL 核心层。

### 7）实践路线图

- 近期：继续强化实验矩阵与证据自动化。
- 中期：增加可选 Miniscript 适配器（导入/编译入口）。
- 长期：稳定为“策略语言输入，实验引擎输出”的分层架构。

