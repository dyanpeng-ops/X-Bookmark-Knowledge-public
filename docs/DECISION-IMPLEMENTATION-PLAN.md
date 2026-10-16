# 架构决策实施计划（按裁定分批）

> 版本：2026-10-13 · 依据：《ARCHITECTURE-DECISION-REQUEST.md》裁定结果 + 全局执行约束
> 原则：**每次只做一项** → 提交该批待验证清单 → 等批准 → 实施 → 自验 → 打包 → 上传 → 等审计 → 汇报并停止。

---

## 批次划分（建议顺序，逐批推进）

| 批次 | 决策 | 前置条件（先只读确认，再动代码）| 拟修改范围 | 验证方式 |
|---|---|---|---|---|
| **批 1** | **D-1** S2 最小闭合 | ① 只读确认 `FieldTheoryCollector.adapter` 是否真暴露 `sync`/`read_bookmarks`；② 确认其语义与 Protocol 匹配 | `src/collector/fieldtheory/adapter.py`（委托方法）+ 对应测试 | 单元测试 + Protocol 运行期取用测试 + 零回归（失败集逐条一致）|
| 批 2 | **D-2** R1 并存+收口 | ① 声明 Canonical 为权威（写 PLAN）；② 盘点旧模块调用方 | `tasks/PLAN.md` / 文档 + 旧模块兼容层（仅记录，不删）| 全量回归确认旧模块测试仍绿 |
| 批 3 | **D-3** Phase 6 | ① 先**保留修复前失败证据**（9 条失败逐条存根因快照）；② 只改测试/桩 | `tests/`（test_config/test_media/test_external 的路径语义桩）| 修复前快照 vs 修复后；重设基线；提交审计 |
| 批 4 | **D-4** Phase 7 | ① 确认远端私有/权限/护栏/敏感排除/体积；② **先提交变更文件清单与风险清单，经确认后再动 `.gitignore`** | `.gitignore` + `scripts/guard-staged` 校验 | 提交护栏拦截测试 + 端到端（clone→rebuild-index）|
| 批 5 | **D-5** git 历史 | 仅记录风险 + 确认仓库权限（**不重写、不强推**）| `docs/` 记录 + 权限核对 | 无需代码；汇报风险清单 |
| 批 6 | **D-6** SEC-01 | ① 先交威胁模型/方案比较/测试计划/待验证清单 | `src/external/` 抓取封装的 SSRF/DNS rebinding/重定向/资源耗尽防护 | 专项测试 + 待验证清单批准后再改 |

> D-7（Drive 清单）已落地为选项 1，**不重复实施**。

---

## 批次 1 · D-1 S2 最小闭合 —— 第一批待验证清单

### 目标
给 `FieldTheoryCollector` 补 `sync()` / `read_bookmarks()` 委托方法，使 `Collector` Protocol **真正**成立
（运行期按 Protocol 取用不再 `AttributeError`），**且不空操作、不伪造成功**。

### 步骤 0（只读确认，先行）
1. `src/collector/fieldtheory/adapter.py`：确认 `self.adapter` 的公开方法里是否**确实**有 `sync` 与 `read_bookmarks`（或其等价语义方法）。
2. 若 adapter **没有**这些方法：**停止**，改报 D-1=b（拆协议）。
3. 若 adapter 有：记录其签名与语义，与 Protocol 比对（`collect()` 已兼容：多一个可选 kwarg）。

### 拟修改文件（待批准后执行）
- `src/collector/fieldtheory/adapter.py`：新增 `sync(**options)` / `read_bookmarks()` 委托方法。
- `tests/`：新增 2-3 用例（委托调用正确、返回值透传、无伪造成功）。

### 风险
- adapter 语义与 Protocol 不完全匹配 → 方法名对上了但行为不符（需靠步骤 0 的只读确认规避）。
- 新增方法不影响既有行为（纯新增委托），回归风险低。

### 验证方式
- `python -m unittest tests.test_fieldtheory_collector tests.test_cli_canonical`（新增用例 + 相关回归）。
- 全量 `python -m unittest discover -s tests -t .` → **失败集与基线逐条一致**（零回归，md5 `31571afa…`）。
- 按 Protocol 运行期取用 `FieldTheoryCollector` 不再抛 `AttributeError`。

### 需要你批准
**本批次（批 1 · D-1）是否开始？** 我将：
1. 先做步骤 0 的只读确认（不改任何文件）；
2. 报告 adapter 是否真支持 `sync`/`read_bookmarks`；
3. 若支持，列出具体补丁草案等你批准；若不支持，停止并改报 D-1=b。

> 在收到你的批准前，**不写盘、不跑测试、不提交**。