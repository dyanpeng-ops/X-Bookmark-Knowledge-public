# 审计打包 checklist（出包前逐项过）

> 适用：`X-Bookmark-Knowledge-Automation/scripts/build-audit-package` 出的**任何**审计包。
> 来源：合并审计包 `RUN-20261016T110134Z-yfpuc4` 的三个 LOW（**M-001 / M-002 / M-003**，2026-10-16）
> ＋ `X-Bookmark-Knowledge-Automation/docs/EVIDENCE-CONVENTIONS.md` 既有约定。
> 状态：**自本文件起生效**；**不重做**已交付的合并包。

---

## 0. 一句话

**打包三对齐**：

```text
manifest.base_commit  ==  项目级双跑的 base
package.head_commit   ==  项目级双跑的 head
diff.patch            ==  带 commit header（或包内附合并顺序说明）
```

---

## 1. 三条硬规则（由本轮三个 LOW 转正）

| # | 规则 | 原 LOW 现象（为什么要有这条） | 怎么做到 |
|---|---|---|---|
| **M-001** | **manifest 的 `base_commit` 必须与项目级双跑的 base 同口径** | 上次 manifest 的 base 与双跑所用 base 不是同一个 commit ⇒ 审计方**无法**把"零回归"结论直接对齐到包 | 双跑 base 一定下来（如"合并前 main tip"），`--base-commit` 就用**同一个 SHA**；若二者**必须**不同，在 `change-summary.md` 显式写明差异与理由 |
| **M-002** | **包的 `head_commit` 必须等于双跑的 head** | 上次包的 head 比双跑 head **多两个纯文档提交** ⇒ 日志的 `produced_at_commit` 与包 head 对不上，`evidence_provenance` 判 `stale`（即便只是文档提交） | 顺序固定为：**先提交全部要入包的改动 → 在该 head 上跑双跑 → 再打包**；**打包后不再产生任何提交**（含纯文档）；若已提交则**重跑双跑** |
| **M-003** | **`diff.patch` 必须保留 commit header**（或附合并顺序说明） | 上次 diff 无 `commit …` / `Author` / `Date` 头 ⇒ 审计方无法从 patch 本身还原**提交边界与合并顺序** | 生成时保留 header（`git log -p` / `format-patch` 风格）；或在包内附**合并顺序说明**（如 `MERGES.md`：`D→C→B→A` ＋ 各 merge commit SHA） |

---

## 2. 出包前 checklist（逐项打勾）

### A. 对齐（M-001 / M-002）

- [ ] 双跑 base 与 head **已确定并冻结**（写进 `test-evidence.json` 的 `produced_at_commit`）
- [ ] `--base-commit` == 双跑 base
- [ ] 包 head（`--git-range` 末端） == 双跑 head
- [ ] 打包后**未再产生提交**（含纯文档提交；若已产生 ⇒ 重跑双跑再打包）

### B. 测试证据（EVIDENCE-CONVENTIONS §1）

- [ ] 改动**前/后两份全量 verbose 日志**都在包内
- [ ] 失败集**逐条比对**（**禁用**失败集 md5 / 摘要哈希）
- [ ] `test-evidence.json` 每条含：`command` / `executed` / `exit_code` / `result` / `log_path` / `produced_at_commit`
- [ ] 相对 `log_path` 与 `--evidence-root` 一致（默认 = 自动化目录）；**F-007** 已修：provenance 与执行时的 CWD 无关
- [ ] `skipped` 若非 0，说明是否为**环境性跳过**且改动前即存在

### C. 材料与声明

- [ ] `role=task` 材料（`TASK.md`）在包内（`--require-task`）
- [ ] 每条 claim 都指向**包内**证据（`--require-claim-evidence`）
- [ ] `ACCEPTANCE.md` 与任务书判据**逐条对应**
- [ ] 文件 basename **唯一**（避免包内重名）

### D. 安全

- [ ] `--denylist config/pii-denylist.txt`（命中即 **fail closed**，不出包）
- [ ] 全树 `scan-denylist` **0 命中**，日志随包
- [ ] sidecar（`.sha256` / `.self-audit.json`）**不上传 Drive**，哈希写台账（`RULING-DRIVE-BATCH §3`）

### E. 出包与自检

- [ ] `scripts/self-audit-package --run-id <RUN>` → **verdict=PASS**（C1–C11）
- [ ] `C7` 的 `stale` **只允许**是"改动前基线日志"（预期），并在包内说明
- [ ] `package_sha256` / `manifest_sha256` 写入 `tasks/CURRENT.md` 台账 ＋ 上传日志

---

## 3. 反例（上次合并包的三个 LOW，勿重犯）

| 现象 | 后果 | 本表对应 |
|---|---|---|
| manifest base ≠ 双跑 base | 零回归结论无法对齐到包 | **M-001** |
| 双跑 head ≠ 包 head（差两个纯文档提交） | provenance 误判 `stale`，审计方需额外追认 | **M-002** |
| `diff.patch` 无 commit header | 合并顺序与提交边界无法从 patch 还原 | **M-003** |

---

## 4. 相关文件

| 文件 | 作用 |
|---|---|
| `X-Bookmark-Knowledge-Automation/docs/EVIDENCE-CONVENTIONS.md` | 证据口径（双跑、失败集比对、禁用 md5） |
| `X-Bookmark-Knowledge-Automation/scripts/build-audit-package` | 打包器（`--base-commit` / `--evidence-root` / `--denylist`） |
| `X-Bookmark-Knowledge-Automation/scripts/self-audit-package` | 包自检（C1–C11） |
| `X-Bookmark-Knowledge-Automation/scripts/scan-denylist` | 拒绝清单全树扫描 |
