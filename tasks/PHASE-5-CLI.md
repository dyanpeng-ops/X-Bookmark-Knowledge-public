# Phase 5 任务书 — CLI

> 目的：给 Phase 5 一个**明确的任务边界**，使每个审计包都能附上 `TASK.md`（协议 §2 第 1 项）。
> 本文件只定义范围与验收，**不裁定**架构决策（那些见文末"待裁定"）。

## 1. 目标

把 Phase 4 的 Canonical 投影（JSON / Markdown / SQLite / rebuild-index）与既有采集链路，
收拢为**一致的 CLI 入口**，并引入 `xbk` 命令（`ARCHITECTURE.md` §10 决策 D4）。

## 2. 范围

### 2.1 已交付（决策无关部分）

| 命令 | 行为 | 默认 |
|---|---|---|
| `normalize` | 上游 `bookmarks.jsonl`(+`data/raw/` 富化) → Canonical 校验 → `data/normalized/{tweet_id}.json` | **只演练**（`--apply` 落盘）|
| `render` | `data/normalized/*.json` → `knowledge/X-Bookmarks/{YYYY}/{MM}/{YYYYMMDD}-{tweet_id}.md`；**内容不同不覆盖**（AGENTS §14）| **只演练**（`--apply` 落盘；`--overwrite` 才改写）|
| `rebuild-index` | `normalized/*.json` → SQLite 内容索引；**运行态重建即重置**（R6）| **只演练**（`--apply` 落盘）|
| `status` | 只读展示：配置/库/上游 + **`canonical` 段**（normalized 目录与计数）| 只读 |
| `doctor` | 环境自检 + **`canonical normalized`** 非关键检查项 | 只读 |

### 2.2 决策状态（D-1 / D-2 已裁定）

| 事项 | 决策 | 现状 |
|---|---|---|
| 按 `Collector` Protocol 装配 Collector | **D-1 = a**（最小闭合；Lane A 实施）| 待 Lane A 交付后由主会话统一合并 |
| 旧 `process`/`media`/`links` 与 Canonical 流水线的最终关系 | **D-2 = c**（并存 + Canonical 为权威 + Phase 7 再评估）| ✅ 本轮收口，见 §6 |

> 依据：`docs/DECISION-REQUESTS.md` D-2 = c（2026-10-13 用户裁定）
> + 裁决 `RULING-LANE-C-D2-R1-2026-10-15`（`L1=B, L2=B, L3=A, L4=A, L5=A, L6=A, L7=B`）。

## 3. 验收标准

| # | 判据 |
|---|---|
| A1 | 写真实 `data/`、`knowledge/` 的命令**默认都是演练**；演练模式不创建、不修改任何文件 |
| A2 | `render` **绝不覆盖内容不同的既有 Markdown**（除非显式 `--overwrite`）；冲突须计入报告并以非零退出码体现 |
| A3 | `rebuild-index` 的「运行态重建即重置」语义写入 `--help`（R6 要求），并提供 `--in-place` 保留运行态 |
| A4 | 单条失败不拖垮整批（AGENTS §2.7）：坏 JSON / 非法 Canonical 记入 failures 并继续 |
| A5 | 零回归：全量失败集与改动前**逐条一致**（判据见 `X-Bookmark-Knowledge-Automation/docs/EVIDENCE-CONVENTIONS.md`）|
| A6 | 不触碰真实 `data/`、`knowledge/`（除显式 `--apply`）|
| A7 | `xbk` 入口在 `pyproject.toml` 声明；**未执行 `pip install -e .` 时 `python -m src.cli` 等价可用** |

## 4. 明确不在范围

- Phase 6 跨平台（9 个平台语义失败清零）——方案见 `docs/PHASE6-PREP-PLAN.md`；
- Phase 7 Git 同步、Phase 8 Knowledge-Agent；
- AI 分析（Phase 11）；
- 任何 `schema/` 契约变更、任何安全加固路线选择（SEC-01）。

## 5. 待裁定（**不由开发方自行决定**）

1. **S2**：Collector Protocol 拆分/闭合方式 → ✅ **已裁定 D-1 = a**（2026-10-13，Lane A 实施）；
2. **R1**：新旧模块关系 → ✅ **已裁定 D-2 = c**（2026-10-13，本轮收口，见 §6）；
3. **git 历史**：真实书签标识是否重写历史清除 → ✅ 已裁定 D-5 = A（暂不重写；仓库可见性另有 D-8/D-9 请示）；
4. **Phase 6 方案**是否批准执行 → ✅ 已裁定 D-3（有条件批准，Lane B 实施）。

选项与影响：`X-Bookmark-Knowledge-Automation/docs/PHASE5-PREP-BRIEF.md`。

---

## 6. 权威路径与 Phase 7 收口门槛（D-2 R1 · 2026-10-15）

> 完整版：`ARCHITECTURE.md` §3.5、`PLAN.md` §4.6、`docs/D2-R1-AUTHORITY-AND-CALLERS.md`。
> 裁决：`RULING-LANE-C-D2-R1-2026-10-15`（`L1=B, L2=B, L3=A, L4=A, L5=A, L6=A, L7=B`）。

| 项 | 结论 |
|---|---|
| 权威路径 | Canonical：`src/collector/fieldtheory/adapter.py` + `src/normalizer/fieldtheory.py` + `src/canonical/` + `src/storage/` 三投影；CLI 装配点 `src/cli/main.py::_cmd_normalize` |
| 兼容层 | 旧 `src/collector/fieldtheory_adapter.py`（Windows 版）、`src/markdown/` **保留不动** |
| ★ 在役加注 | 两者**仍在依赖路径上**，不是「已退役、无调用方」——**不得据「兼容层」直接删除** |
| 依赖边 | ① Canonical Collector → 旧 adapter（`read_bookmarks()` / `check_ready()`）；② `markdown_projection` / `media.localizer` / `external.resolver` → `src.markdown.render.date_parts`；③ CLI `process` → 旧 `MarkdownWriter` |
| C2 合格标准（裁决 L4=A）| `_cmd_normalize` 装配处有权威路径**代码注释** + 四处文档声明；**不动业务逻辑**（`process` 切换属 Phase 7） |
| 裁定时点 | Phase 7 的 `process` 切 Canonical 时**再评估**；不直接删旧模块 |

**Phase 7 收口门槛（退出条件 E1–E6）**

```text
E1 旧 sync/process/media/links 链与 Canonical normalize/render 完成收敛；
E2 上游 CLI 调用与重试逻辑迁入 src/collector/fieldtheory/，消除 Canonical → 旧模块的依赖边；
E3 date_parts 迁出 src/markdown/（中性模块），media/external/storage 不再依赖旧包；
E4 全仓库 grep 旧模块引用仅剩文档 / CHANGELOG / 历史；
E5 旧链测试迁移或显式退役（不跳测、不降断言）；
E6 审计 PASS + 用户批准（裁定原文：「不直接删旧模块」）。
```
