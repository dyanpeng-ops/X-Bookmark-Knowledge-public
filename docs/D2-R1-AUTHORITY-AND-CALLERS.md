# D-2 R1 权威路径声明与调用方清单（C4 证据）

> 依据：`docs/DECISION-REQUESTS.md` **D-2 = c**（2026-10-13 用户裁定）＋裁决
> `RULING-LANE-C-D2-R1-2026-10-15`（`L1=B, L2=B, L3=A, L4=A, L5=A, L6=A, L7=B`）。
> Lane C 任务书：`LANE-C-D2-R1并存收口任务书.md`；基线 commit：`c2b9271`。
> 本文件是任务书验收 **C4**（调用方清单 + Phase 7 退出条件）的证据；与
> `ARCHITECTURE.md` §3.5、`PLAN.md` §4.6、`tasks/PHASE-5-CLI.md` §6 为同一结论的四份表述。

---

## 1. 声明（Canonical 为权威 · 旧模块为兼容层 · Phase 7 再评估）

| 项 | 声明 |
|---|---|
| **权威路径** | `src/collector/fieldtheory/adapter.py`（Canonical Collector）→ `src/normalizer/fieldtheory.py`（L2）→ `src/canonical/`（契约与校验）→ `src/storage/`（JSON / Markdown / SQLite 三投影） |
| **CLI 装配点** | `src/cli/main.py::_cmd_normalize`（`python -m src.cli normalize`）；本轮在该装配处加**权威路径代码注释**（裁决 L4=A），不改业务逻辑 |
| **兼容层（保留不动）** | `src/collector/fieldtheory_adapter.py`（旧 Windows 版 `FieldTheoryAdapter`）、`src/markdown/` |
| **★ 在役加注** | 两个兼容层模块**仍在运行时依赖路径上**，不是「已退役、无调用方」。**不得据「兼容层」一词直接删除**（裁决 L5=A） |
| **收口时点** | Phase 7 的 `process` 切 Canonical 时**再评估**；**不直接删旧模块**（裁定原文） |
| **不在本轮范围** | `src/collector/base.py` 的 `Collector` Protocol（属 D-1 S2，Lane A 处置） |

---

## 2. 调用方清单

### 2.1 旧 `src/collector/fieldtheory_adapter.py`（`FieldTheoryAdapter`）——共 9 类

| # | 调用方 | 位置 | 用途 | 迁 Canonical 的兼容性结论 |
|---|---|---|---|---|
| 1 | `src/collector/__init__.py` | `:29`（import）、`:35`（`__all__`） | 公开导出面（Phase 5 API 冻结） | **必须保留**至 Phase 7；对外符号 `FieldTheoryAdapter` 被测试直接使用 |
| 2 | **Canonical Collector 自身** ★ | `src/collector/fieldtheory/adapter.py`：`:27`（import）、`:50`（类型标注）、`:60`（缺省构造）、`:80`（`adapter` 属性）、`:91`（`check_ready()` 透传）、`:105`（`read_bookmarks()`） | Canonical 采集复用旧 adapter 的上游读取与错误分类 | **语义兼容**（只读读取）；差异仅在输出形态（`UpstreamBookmark` vs `RawCollectorData`）。**这是 Phase 7 前无法删除旧模块的根本原因** |
| 3 | CLI 旧采集链 | `src/cli/main.py`：`:31`（import）、`:262-267`（`_build_adapter`） | `sync` 构造 adapter | 兼容；`sync` 属旧链，Phase 7 收敛 |
| 4 | CLI `normalize` 装配 | `src/cli/main.py`：`_cmd_normalize`（装配处，2026-10-15 加权威路径注释） | 构造旧 adapter 后**注入** Canonical Collector | **已是 Canonical 路径**；旧 adapter 在此仅为上游只读读取器 |
| 5 | CLI 读取辅助 | `src/cli/main.py`：`:675`、`:696`、`:749`、`:761`（类型标注 + `_collect_upstream` / `_load_enrichment` / `_load_media_entries`） | 旧 `sync` 链的富化与媒体读取 | 兼容；随 `sync` 链在 Phase 7 收敛 |
| 6 | `src/external/fetcher.py` | `:24` | 仅注释引用（重试语义对齐） | 无依赖，无需迁移 |
| 7 | 反向边界断言 | `src/normalizer/fieldtheory.py:8`（docstring 声明「不 import 上游适配器」）＋ `tests/test_normalizer.py:795`（`FORBIDDEN_IMPORTS = ("fieldtheory_adapter", "FieldTheoryAdapter")`） | 强制 L2 不依赖 L1 包内部 | **必须保持**；迁移后不得破坏该边界 |
| 8 | 测试 | `tests/test_collector_fieldtheory.py`：`:32`（import）、`:55`、`:68`（构造）；`tests/test_fieldtheory_collector.py`：`:28`（直接 import）、`:68`、`:167`（Canonical 测试的 fixture） | 旧 adapter 验收 + Canonical 测试夹具 | **直接替换会大面积破坏**（旧 adapter 验收用例 + Canonical 夹具）→ 印证裁定 b（原地替换）不可取 |
| 9 | 文档与历史 | `ARCHITECTURE.md`、`PLAN.md`、`README.md`、`CHANGELOG.md`、`docs/CURRENT_ARCHITECTURE.md`、`docs/phase3-preflight-review.md`、`memory/*` | 表述与历史记录 | 本轮起以本文件与 §3.5/§4.6/§6 为准 |

> 动态导入检查：全仓库无 `importlib` / `__import__` 方式加载本模块（`importlib` 仅用于 `src.cli.main`）；
> `scripts/`、`schema/` 无引用。

### 2.2 旧 `src/markdown/` —— 共 4 类

| # | 调用方 | 位置 | 用途 | 结论 |
|---|---|---|---|---|
| 1 | CLI `process` | `src/cli/main.py::_cmd_process`（局部 `from src.markdown import MarkdownWriter, RenderOptions`） | 旧 Markdown 链（`COLLECTED → PROCESSED`） | Phase 7 才切 Canonical `render`；本轮不动 |
| 2 | **Canonical Markdown 投影** ★ | `src/storage/markdown_projection.py:25`（`from ..markdown.render import date_parts`） | 复用 `YYYY/MM` 布局，保证与 `assets/` **永不漂移** | **刻意复用**；迁移须先把 `date_parts` 提取为中性模块（E3），否则会造成布局分叉风险 |
| 3 | media / external | `src/media/localizer.py:55`、`src/external/resolver.py:54`（`date_parts`） | 同一布局复用 | 同 #2 |
| 4 | 旧包内部与测试 | `src/markdown/render.py:25`、`src/markdown/writer.py:240`（间接依赖 `src/collector/contract.parse_twitter_datetime`）；`tests/test_markdown.py:32`、`tests/test_media.py:38`、`tests/test_external.py:68` | 渲染与验收 | 旧链测试随 Phase 7 迁移或显式退役（E5） |

---

## 3. Phase 7 收口门槛（退出条件 E1–E6）

```text
E1 旧 sync/process/media/links 链与 Canonical normalize/render 完成收敛；
E2 上游 CLI 调用与重试逻辑迁入 src/collector/fieldtheory/，消除 Canonical → 旧模块的依赖边
   （对应 §2.1 第 2 类）；
E3 date_parts 迁出 src/markdown/（中性模块），media/external/storage 不再依赖旧包
   （对应 §2.2 第 2/3 类）；
E4 全仓库 grep 旧模块引用仅剩文档 / CHANGELOG / 历史；
E5 旧链测试迁移或显式退役（不跳测、不降断言）；
E6 审计 PASS + 用户批准（裁定原文：「不直接删旧模块」）。
```

> 任何一项删除动作前须重跑本文件的清单（E4 的 grep 命令）并取得 E6 的批准。

---

## 4. 本轮验证口径与证据（C3 / C5）

| 判据 | 证据 |
|---|---|
| C3 旧模块零改动 | 改动后 `git diff --name-only <base>..<head>` 的输出不含 `src/collector/fieldtheory_adapter.py`、`src/markdown/**`、`src/collector/base.py` |
| C5 本 lane 零回归（裁决 L3=A） | 同环境 base vs head 双跑 `python -m unittest discover -s tests -t . -v`，失败集逐字比对；**项目级零回归**以四 lane 合并后统一重跑为准，合并前不得声称 |
| C2 装配处注释（裁决 L4=A） | `src/cli/main.py::_cmd_normalize` 权威路径注释（零业务逻辑改动） |
| C1 文档一致 | 本文件 + `ARCHITECTURE.md` §3.5 + `PLAN.md` §4.6 + `tasks/PHASE-5-CLI.md` §6 |

**基线（`platform=darwin`）**：671 用例 / 9 失败（failures=7, errors=2, skipped=1），
失败集与历史记录的 9 条平台语义失败一致；用例数 663→671 系后续轮次新增测试所致。
平台限定：macOS 失败集**不可跨平台比较**（`docs/EVIDENCE-CONVENTIONS.md` §1）。

运行时环境：`/Users/nanopeng/AI-Agent-Lab/X-BOOK/X-Bookmark-Knowledge/.venv/bin/python`（Python 3.13.12）。
