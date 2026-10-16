# 架构决策请示（ARCHITECTURE DECISION REQUEST）

> 版本：2026-10-13 · 状态：**待用户拍板**（开发方不代为决定，越权边界见 AGENTS §2/§8）
> 作用：把 Phase 4→8 推进中被阻塞的**架构/路线决策**汇总成一份正式请示，
> 供你逐项拍板；每项含事实、选项、影响、推荐与细节文档位置。
> 与 `docs/DECISION-REQUESTS.md` 的关系：后者是**一行回复清单**（浓缩），本文档是**带完整背景的正式请示**。

---

## 当前项目状态（2026-10-13）

| 项 | 值 |
|---|---|
| 项目 HEAD | `0fd436f`（已推送，工作区干净）|
| Phase 4（三投影存储）| ✅ 完成（663 用例；SQLite 可重建；审计轮 8–16 全 PASS）|
| Phase 5（CLI 收拢）| 🟡 部分完成（`normalize`/`render`/`rebuild-index`/`status`/`doctor` 已交付；**剩余被 D-1/D-2 阻塞**）|
| Phase 6（跨平台）| ⏸ 方案待批准（D-3）|
| Phase 7（Git 同步）| ⛔ 被 D-4 阻塞（`.gitignore` 与 `ARCHITECTURE §8.2` 相反）|
| Phase 8（Knowledge-Agent）| ⏳ 待 Phase 7 |
| 自动化测试 | 206 用例全绿；变异 项目 10/10 + 自动化 17/17；全树泄漏扫描 0 命中 |
| 审计 | 已处理 23 个文件（轮 8–16 全 PASS）；待审 10 个包 |

---

## 你需要拍板的 7 项决策

### D-1 · S2 — `Collector` Protocol 如何闭合（阻塞 Phase 5 剩余部分）

**事实**（`src/collector/base.py` L194-206）：`Collector` Protocol 声明 `check_ready`/`sync`/`read_bookmarks`/`collect`；
`FieldTheoryCollector`（`src/collector/fieldtheory/adapter.py`）现有 `name`/`adapter`/`data_dir`/`raw_dir`/
`check_ready`/`collect`，**缺 `sync()` 与 `read_bookmarks()`** ⇒ 按 Protocol 取用会在运行期 `AttributeError`。

| 选项 | 做法 | 影响 | 风险 |
|---|---|---|---|
| **a 最小闭合**（推荐）| 加两个委托方法 `sync()`/`read_bookmarks()`（转调 `self.adapter`）| ~10 行 + 2-3 用例；Protocol 立即成立 | "只读收集器也能 sync"，边界略糊 |
| **b 拆协议** | 拆成 `ReadOnlyCollector` + `SyncableCollector` | 语义最干净 | 触及既有 Protocol 消费者，改动面大 |
| **c 仅文档** | 不动代码，注明 Protocol 为"目标态" | 零风险 | 按 Protocol 装配会踩坑 |

**推荐**：a（若 CLI 确需"只读 vs 可同步"类型区分再升级 b）。**请裁定 a/b/c。**

### D-2 · R1 — 新旧模块关系

**现状**：新 `src/storage/`、`src/database/{r6_fields,index_store}.py`（Canonical）与旧 `src/ingest/`、
`src/markdown/`、`src/database/repository.py`（FT 形态）并存，**500+ 既有测试依赖旧路径并通过**。

| 选项 | 影响 | 风险 |
|---|---|---|
| a 并存（现状）| 新流水线独立演进；旧路径服务 `sync`/`process` | 两套栈、概念重复；新 CLI 需明确"哪条是权威" |
| b 原地替换 | 目录干净 | **大面积破坏既有测试**，回归判定失真 |
| **c 并存 + 明确收口时点**（推荐）| 约定"Phase 7 `process` 切 Canonical、旧 `src/markdown` 退兼容层" | 需纪律，但风险/收益最平衡 |

**推荐**：c。**请裁定 a/b/c。**

### D-3 · Phase 6 — 是否批准执行（清零 9 个平台语义失败）

**根因（已查明，全部在测试/桩侧，无产品缺陷）**：A 路径解析 `/var↔/private/var`（4）；
B 桩用 `Path("C:\\...").name`（POSIX 下反斜杠非分隔符，2）；C Windows 盘符语义（3）。

**目标**：9 个已知失败 → **"期望 0 失败"** 干净基线。**代价**：改 `tests/`（不动产品代码）；
会让失败基线作废、需重设基线（并需一轮审计确认）。**请裁定：批准 / 缓批 / 否决。**

### D-4 · Phase 7 — `.gitignore` 与 `ARCHITECTURE §8.2` 相反（阻塞 Phase 7 整条链路）

**事实（实测）**：§8.2 要求 `data/normalized/`、`knowledge/X-Bookmarks/**/*.md`、§8.2.1 的 `assets` **入 Git**；
`.gitignore` 第 15/48 行**全部挡住**。

**后果**：① §8.1 跨设备链路无法成立；② 新机器无法 `rebuild-index`（它只扫 normalized）；③ **富化内容
（article 正文/quoted）只在 normalized JSON，不同步即永久丢失**；④ assets 不入 Git ⇒ Markdown 引用断裂。

| 选项 | 影响 |
|---|---|
| **A 按 §8.2 实现**（推荐 + 三条护栏）| 真实内容进 GitHub **私有**仓库；需确认私有 + `scripts/guard-staged` 提交护栏 + assets 体积策略 |
| B 只同步 Markdown | 无法重建索引 / 富化丢失仍存在 |
| C 不进 Git，改用云盘等 | 与 §8.1 冲突，需重定义同步机制（架构决策）|

**推荐**：A（配套护栏已就绪）。**请裁定 A/B/C。** 详见 `docs/PHASE7-SYNC-PREP-PLAN.md`。

### D-5 · git 历史中的真实标识

**事实**：`4922ae4` 只清了工作树；**历史提交仍含** 5 个文件的真实标识（tweet_id/handle/显示名）。

**关键副作用**：重写历史会改变受影响提交后的**全部 SHA** ⇒ **既有审计包声明的
`base_commit`/`head_commit`/`git_range` 全部失效**，须标记 `SUPERSEDED` 并重跑基线。

| 选项 | 影响 |
|---|---|
| **A 不处理**（私有仓库 + 非凭据，推荐）| 作为"已知并接受"记录 |
| B 重写历史（filter-repo）| 强推 + 作废既有审计基线 |
| C 另起干净仓库（优于 B）| 避免强推与失效链；需迁移 remote，应在**下一轮审计前**完成 |

**推荐**：A；若必须清则 C。**请裁定 A/B/C。** 详见 `docs/GIT-HISTORY-CLEANUP-PLAN.md`。

### D-6 · SEC-01 — 安全加固路线

出站请求加固路线（含 DNS rebinding 防护方案取舍）。**请先指定范围**，我再出选项简报，
避免给出与实际威胁不匹配的方案。**我不自行选择路线。**

### D-7 · Drive 文件清单来源（2026-10-13 已拍板为「选项 1」）

**背景**：Drive 文件列表**懒加载且要求标签激活才渲染**；按"后台完成"偏好完全前台化时
`drive-sync list` 返回 **0 项**（实测）。

**已拍板＝选项 1**：仅 `list`（及依赖它的 audit-intake/registry）取清单时**短暂激活**触发展开；
`upload`/`read_text` 保持纯后台。**已落地**并固化进 `EVIDENCE-CONVENTIONS §11`。
（备用选项 2＝改用 `state/AUDIT-REGISTRY.json` 作清单来源，彻底不碰浏览器——未选。）

---

## 建议顺序

**D-4 → D-3 → D-2 → D-1 → D-5 → D-6**（D-7 已落地）。

理由：D-4 决定"真实内容是否/如何进版本库"，影响后续所有回归与同步判定，且阻塞 Phase 7；
D-3 提供干净失败基线；D-2/D-1 决定 Phase 5 收尾与权威路径；D-5 若重写历史必须**最早**做。

---

## 回复格式

一行即可，例如：`D-1=a, D-2=c, D-3=批准, D-4=A, D-5=A, D-6=<范围>, D-7=选项1(已拍板)`。
裁定后我即按对应方案实施，并全程走「自验 → 打包 → 上传 → 等审计」循环。

---

## 裁定结果（2026-10-13 用户已裁定）

| 项 | 裁定 | 实施前置条件（须先满足再动手）|
|---|---|---|
| D-1 S2 | **a 有条件批准** | ① 确认 `FieldTheoryCollector.adapter` 真支持 `sync`/`read_bookmarks` 语义，**不得空操作/伪造成功**；② 若语义不成立，停止并重新提交 D-1=b |
| D-2 R1 | **c 批准** | ① 声明 Canonical 为权威路径；② Phase 7 再评估 `process` 切换；③ 迁移前确认调用方、兼容性、回归测试、退出条件；**不直接删旧模块** |
| D-3 Phase 6 | **有条件批准** | ① 仅修测试/桩的跨平台语义；② **保留修复前失败证据**；③ 重设基线并提交审计；④ 不降断言、不跳测、不动产品代码；⑤ 发现产品问题/需改目标即暂停重请示 |
| D-4 Phase 7 | **A 有条件批准** | ① 确认远端私有、访问权限、提交护栏、敏感信息排除、资源体积策略；② **先提交待变更文件清单与风险清单，经确认后再批量调整 `.gitignore`/提交**；③ 禁传凭据/Cookies/token/浏览器配置/未批准原始数据 |
| D-5 git 历史 | **A 暂不重写** | ① 记录风险、确认仓库权限；② 发现凭据/token 即暂停单独立案；**不以"非凭据"为由自动认定所有历史个人数据可接受** |
| D-6 SEC-01 | **限定范围后实施** | ① 范围=外部 URL 抓取的 SSRF/DNS rebinding/重定向绕过/资源耗尽；② 先交威胁模型/方案比较/测试计划/待验证清单，批准后再改；③ 不扩无关模块、不碰真实内网 |
| D-7 Drive 清单 | **维持选项 1** | 已落地，不重复实施、不擅自改选项 2 |

## 全局执行约束（用户裁定附带）

1. 本裁定只批准**决策方向**，不等于批准任何具体文件写入 / 测试 / 网络访问 / 依赖安装 / Git 提交推送。
2. 每项实施前先列**待验证清单、拟修改文件、风险、验证方式**；需批准的操作先等待批准。
3. 每项保留可追溯 `run_id`、基线提交、差异、测试证据、审计包。
4. 严格执行自验→打包→上传→等审计流程；审计结果与对应 `run_id`、文件哈希匹配。
5. **不得自动推送到主分支、发布、删除真实数据或进入下一 Phase。**
6. 每项完成后汇报实际结果、未解决问题与证据位置，并**停止等待下一步指示**。
