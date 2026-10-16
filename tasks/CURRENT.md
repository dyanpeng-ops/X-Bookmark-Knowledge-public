# Current State Board — X Bookmark Knowledge Pipeline（跨平台改造）

> 本文件是「当前状态板」，只放进度总览 + 当前 Phase 指针 + 下一步。
> 每个 Phase 的详细任务书独立成文件：`tasks/PHASE-N-NAME.md`。

## 当前指针（2026-10-15）

- **本会话角色**：**HQ / 收口**（长期职责见下一节）；**不直接做四个 lane 的开发任务**。
- **进行中**：四个并行 lane（worktree `xbk-lane-a`…`xbk-lane-d`）各自实施 D-1 / D-3 / D-2 / D-6；
  任务书在 Drive `01_TASKS/`（`LANE-A-D1-S2-closure` / `LANE-B-D3-Phase6测试修复` /
  `LANE-C-D2-R1并存收口` / `LANE-D-D6-SEC01威胁模型`）。
- **已完成**：Phase 0–4；Phase 5 的 `normalize` / `render` / `rebuild-index` / `status` / `doctor`。
- **测试基线**：项目 **671 用例 / 9 个平台语义失败**（macOS 产生，**不可跨平台比较**）；
  自动化流水线 **206 用例全绿**。
- **审计**：轮 34 包（`RUN-20261014T145026Z-vuv77w`）**PASS**（v24，9/9 强制验收项）；
  待审 11 包；注册表 `state/AUDIT-REGISTRY.json`（33 条，无 `?` 条目）。
- **安全**：F-001（`tests/test_normalizer.py` 真实 author_id）**已修复并推送**（`44f5fde`）；
  D-9=C（公开 git 历史处置）待办。

## ★ 本会话（HQ / 收口）长期职责（2026-10-15 起）

> 来源：Drive `01_TASKS/HQ-主会话收口任务书.md`（file id `1YNgUxmv_xtKeA8m8YpoK46XFQCIjwX8l`）。
> 角色：**总部 / 收口**；工作区 = 本目录 main 分支。

1. **等**：Lane A/B/C/D 的审计包**全部**经 Muse 审计 **PASS**（Muse 在聊天通知用户，用户转告本会话）。
2. **合**：逐个把四个分支合并回 `main`，顺序 **D → C → B → A**：
   `docs/d6-threat-model` → `docs/d2-r1-authority` → `fix/d3-phase6-tests` → `feat/d1-s2-closure`
   （纯文档 → 文档+装配处注释 → 测试 → 产品代码）。有冲突就地解决，解完跑相关测试。
3. **统改共享文件**：`CHANGELOG.md`、`tasks/CURRENT.md` **由本会话统一更新**
   （各 lane 按裁决 L1=B / L2=B **不碰**这两个文件）。
4. **项目级零回归**：合并后跑全量测试 **base vs head 同环境双跑**，失败集**逐字比对**
   （**禁用失败集 md5**；见 `X-Bookmark-Knowledge-Automation/docs/EVIDENCE-CONVENTIONS.md` §1）。
5. **出合并审计包**：按审计包规范出包 → 上传 Drive `03_AUDIT` → 等审计 PASS。
6. **D-4**：合并完成后、**push 前**执行 `.gitignore` 操作
   （须等用户对 `D4-变更文件清单与风险清单.md` 的 5 项确认；**确认前不动 `.gitignore`**）。
7. **B/D lane 的包**：B/D 在本地 Saluki 跑；若其传不上 Drive，本会话从 `xbk-lane-b` / `xbk-lane-d`
   取审计包转交 `03_AUDIT`（或提醒用户手动传）。

**开工 / 合并前先读的裁决文件**：

- Drive `05_APPROVALS/`：`RULING-LANE-A-D1-S2-2026-10-15.md`、`RULING-D8-D9-git-visibility-2026-10-15.md`
- Drive `00_CONTROL/`：`RULING-LANE-C-D2-R1-2026-10-15.md`、`RULING-audit-submission-policy-2026-10-15.md`

**审计提交制度**：各 lane 做完即各自交包，**不等统一时间**；本会话只在四 lane 合并后交**一次合并审计包**。

**本会话约束**：

- **不改写历史、不 force push**（D-8 的纯新增推送除外），除非获用户明确授权。
- 合并完成前**不删除**四个 worktree；合并完成后由本会话统一 `git worktree remove` 清理。
- 任何一步拿不准 → 出 `REQUEST-*` 到 Drive `05_APPROVALS` 请示裁决，**不动手**。

**HQ 动作记录**：

| 日期 | 动作 | 结果 |
|---|---|---|
| 2026-10-15 | **裁决收到**：`05_APPROVALS/RULING-D8-D9-git-visibility-2026-10-15.md` | **`D-8=A, D-9=C`**；裁决方实测确认仓库公开、且当时 tip `c2b9271` 的 `tests/test_normalizer.py` 第 207/215 行仍含真实 author_id |
| 2026-10-15 | **D-8=A 执行**：`git push origin main` | `c2b9271..44f5fde`；公开 tip 真实标识数 **1 → 0**（已实测复核） |
| 2026-10-15 | 追加推送本文件（HQ 职责记录） | `44f5fde..a61ea60`（纯新增、未改历史） |
| 2026-10-15 | **裁决收到**：`05_APPROVALS/RULING-D9C-2026-10-15.md` | `D9C-1/2/3/5`=接受/确认；`D9C-6`=**纯本地离线加密**存放 bundle；`D9C-4`=**用户本人决定**（用户已答「我去点」，Muse 要求**先别点**，等合并审计通过） |
| 2026-10-15 | **裁决收到**：`05_APPROVALS/RULING-DRIVE-SERIAL-2026-10-15.md` | **`DRIVE-SERIAL=D+C`**：lane 停止一切 Drive 操作；HQ 成为**唯一 Drive 写者**；Drive 自动化**改走 API**；**D-7 正式由选项 1 转选项 2**（§11 的前台激活例外**废止**） |
| 2026-10-15 | **已转达 lane**：4 个 worktree 写入 `HQ-NOTICE-2026-10-15-stop-drive-ops.md` | A/B/C/D 均收到「停止 Drive 操作 + 包留 worktree + 写 `READY-FOR-HQ.md` 等 HQ 收」 |
| 2026-10-15 | **新请示已发 Muse**：`REQUEST-drive-api-credentials-2026-10-15.md`（id `1k5KUHa_-6Wa7Ll3gaTqH-FWxxT2Hwor7`） | **C 的实现前提缺失**：本机**无任何** Drive API 客户端/凭据 |
| 2026-10-15 | **裁决收到**：`05_APPROVALS/RULING-DRIVE-API-2026-10-15.md` | **`DRIVE-API=5（后备 1）`**：保留浏览器路径 + **确定性护栏 + 零 `activate_tab`**；C 修订为 **C' =「浏览器+护栏，rclone 为后备」**；D 不变；§11 选项 1 例外**维持废止** |
| 2026-10-15 | **新请示已发 Muse**：`REQUEST-drive-api5-revision-2026-10-15.md`（id `1u-Yq-91h2sZzHWoTH9Q7DYLI_MHfqaIS`） | **实测冲突**：`list` 在标签未激活时渲染 **0 行**（两次复测，含争用消除后）⇒ 裁决第 1/2 条的「list 零激活 + 按 parents 复核」**不可实现**。请裁 `DRIVE-API5-REV=<C''-a|C''-b|C''-c>`（建议 **C''-a**：去掉 list，改用**上传前 URL 断言 + 上传后 file id + 预览页回读 sha256**） |
| 2026-10-15 | **裁决收到**：`RULING-DRIVE-GUARD-ESCALATE` | **`(b) + 专用 daemon` 批准**；**(c) 预批准**（仅最终合并审计包、3 次重试全挂后允许一次显式激活）；**(a) 暂缓**（今日计数器**清零**，均属争用期）。新增硬规：**HQ 的 Drive 操作必须跑在专用 daemon 上，lane 不得触碰**；#1（标签被换成 about:blank）被定性为**lane 违规** |
| 2026-10-15 | **C''-a 已实现** | `pipeline/drive_guard.py`（G1 落点断言／G2 预览页回读／G3 失败即停 + **重试 1→3 带退避、每次重断言 G1、已得 file id 先回读不盲重传**）＋ `scripts/drive-guard`（**强制专用 daemon `hq`**，护栏失败退 **2**）＋ `drive_browser` 增 `navigate=False` 与 **file id 从上传网络响应捕获** |
| 2026-10-15 | **G1 负向验证通过** ✅ | 标签停 `00_CONTROL`、目标 `approvals` → **退出码 2 且标签未移动**（证「不自动导航」生效）⇒ **"落错文件夹"这一最严重静默破坏已根治** |
| 2026-10-15 | **新阻塞：零激活上传触发不可用** | 专用 daemon、标签已 CDP 导航、页面已渲染 52 行，仍稳定 `menu-or-input-missing`；深挖：点 `span.jYPt8c`(82,99) 菜单不开、点按钮容器 (128,99) 却开出**帮助菜单** ⇒ **坐标/框架错位**。已发 **DRIVE-GUARD-ESCALATE-2** 请裁 **(a) rclone** 或 **(c') 放宽"一次显式激活"到每次上传前告知**（HQ 建议 **c'**） |
| 2026-10-15 | ⚠️ **发现 lane 违规** | `05_APPROVALS` 出现 `RUN-20261015T125336Z-4m5f3e-audit-package.zip`（20:54）——**有 lane 仍在直接上传**，违反 D 条「lane 停一切 Drive 操作」。已报 Muse，待裁是否追责/再次转达 |
| 待办 | **Drive 自动化落地（C'→C''-a）** | ⏳ 阻塞于 `DRIVE-GUARD-ESCALATE-2`（(a) 需**用户**装+OAuth；(c') 无需用户动作） |
| 待办 | **Drive 去重**（Muse 交办，且 lane 违规又新增文件）：跨文件夹重复的请示文件，**以 `05_APPROVALS` 为准** | ⏸ 去重需「列出 + 删除」，而列出必激活；待上传通道定案后一并执行（含 canary 自检文件与误放的审计包） |
| 待办 | **合并四 lane**（D→C→B→A）+ 项目级双跑零回归 + 出合并审计包 | 等 A/B/C/D **全部审计 PASS**；提交改由 **HQ 单写者上传** |
| 待办 | **D-9=C 迁移**：新建 `X-Bookmark-Knowledge-public`（**单 `--orphan` 提交**）+ 旧库**转私有** | 时序：**四 lane 合并审计通过后**；第 4 项由用户操作（**先别点**）；推送前**硬门禁**= `scan-denylist` 0 命中 + 独立二次复核；迁移后须记录新库 URL / 初始提交 SHA（新基线）/ bundle 位置与加密方式 |
| 2026-10-15 | **D-4 无限期暂缓**（用户指令，经 Drive `01_TASKS/DIRECTIVE-fast-lightweight-closeout-2026-10-15.md`） | 5 项确认一直未回 ⇒ **不等了、不阻塞收尾**；`.gitignore` **一律不动**，除非用户另行恢复 |
| 2026-10-15 | **已转达轻量化收尾指令**：4 个 worktree 写入 `HQ-NOTICE-2026-10-15-directive-lightweight.md` | lane 只做**最小交付**（A 断言+重跑出包／B 清零 9 失败／C 4 文档+1 注释／D 威胁模型）；**禁范围蔓延**，lane 外问题**只记 observation** |

**审计提交制度 v2**：`00_CONTROL/RULING-audit-submission-policy-2026-10-15-v2.md` —— lane **不再直交** `03_AUDIT`，一律由 **HQ 单写者上传**。

**其它 lane 裁决（本会话须遵守）**：`00_CONTROL/RULING-LANE-C-D2-R1-2026-10-15.md` → **`L1=B, L2=B`**
（Lane C **不改** `tasks/CURRENT.md` 等共享文件；`CHANGELOG.md` 本轮豁免，**由收口方统一改**；L3=A 项目级零回归以四 lane 合并后统一重跑为准）。
另待读：`05_APPROVALS/RULING-LANE-A-D1-S2-2026-10-15.md`（`RULING-D1-LA-4` 属 Lane A：Muse 已裁 **`D1-LA-4=A`**，授权 Lane A 更新 `test_raw_data.py` 中「不得有 sync/read_bookmarks」的旧断言，条件=新断言须覆盖三点且仅此一次）。

### 🔁 HQ = 唯一上行下达通道（2026-10-15 起长期有效）

依据：Drive `00_CONTROL/DIRECTIVE-hq-relay-2026-10-15.md`（id `1z89vC734ABrV9814XCEbfNjiKTCBNcdz`）。

1. 审计方的 `RULING-*` / `DIRECTIVE-*` **只写 Drive**（`05_APPROVALS` / `00_CONTROL` / `01_TASKS`），**不再经用户逐个转达**。
2. **每次开始工作块前**先扫这三个文件夹有无新文件（以文件名为准）；已转达的记入下表，避免重复。
3. 转达方式：在对应 lane 目录写**纯指针**文件（`HQ-RELAY-<date>.md`），**只指向文件名、不转述不概括**（lane 自读，防传话失真）。
4. lane 面向 → 转对应 lane；HQ 面向 → 自己执行；全局 → 四个 lane。
5. lane 的 `REQUEST-*` 由 lane 自己按 DRIVE-SERIAL 纪律放 Drive；HQ **不代写、不代传**，只把审计方回文传下去。
6. 用户不再承担转达义务。**例外**：需用户本人决定的事项（D9C-4、rclone OAuth）仍由审计方在聊天直接请用户定。

**已转达台账（避免重复转达）**：

| 日期 | 文件 | 文件夹 | 面向 | 发现通道 | 状态 |
|---|---|---|---|---|---|
| 2026-10-15 | `RULING-LANE-C-D2-R1-2026-10-15.md` | 00_CONTROL | Lane C | (b)兜底 | ✅ 指针已留 |
| 2026-10-15 | `RULING-LANE-A-D1-S2-2026-10-15.md`、`RULING-D1-LA-4-2026-10-15.md` | 05_APPROVALS | Lane A | (b)兜底 | ✅ 指针已留 |
| 2026-10-15 | `RULING-audit-submission-policy-2026-10-15.md`(+`-v2`) | 00_CONTROL | 全局 | (b)兜底 | ✅ 指针已留 |
| 2026-10-15 | `DIRECTIVE-fast-lightweight-closeout-2026-10-15.md` | 01_TASKS | 全局 | (b)兜底 | ✅ 指针已留 |
| 2026-10-15 | `DIRECTIVE-hq-relay-2026-10-15.md` | 00_CONTROL | 全局 + HQ | (b)兜底 | ✅ 指针已留，HQ 已执行 |
| 2026-10-15 | `RULING-HQ-RELAY-GAP-2026-10-15.md`（id `1UjCxx0Pc5Vl0AxZosBN2aepz2nLAUWrZ`） | 05_APPROVALS | HQ | **(a)直达** | ✅ 已执行：**(a)+(b) 双通道**获批 |
| 2026-10-15 | `RULING-DRIVE-GUARD-ESCALATE-2-2026-10-15.md`（id `1FltnM5uXahLvCI7n-8yDOWkX5oLrbEpE`） | 05_APPROVALS | HQ + Lane C | **(a)直达** | ✅ 已执行：(c')primary+(a)fallback；Lane C 已重申 D 条 |
| 2026-10-15 | `RULING-D8-D9-git-visibility`／`RULING-D9C`／`RULING-DRIVE-SERIAL`／`RULING-DRIVE-API`／`RULING-DRIVE-API5-REV`／`RULING-DRIVE-GUARD-ESCALATE` | 05_APPROVALS | **HQ 自己执行** | (b)兜底 | ✅ 不转 lane |

**发现通道口径（`RULING-HQ-RELAY-GAP`）**：**(a) 主通道** = 审计方写完文件后在聊天附一行
`裁决完成：<文件夹>/<文件名>，id=<file id>`，HQ 凭 id 直接 `read_text`（**零激活**）；
**(b) 兜底** = 每工作块开始时可**提前告知用户**后用**一次显式激活**对三文件夹做 list 扫描。
`(c) rclone` 继续暂缓。

**🚀 本轮进展（2026-10-15 22:0x）**：

| 项 | 状态 |
|---|---|
| **canary（带一次激活，已提前告知）** | ✅ **PASS** —— 激活后点「新建」(82,99) 正确开出菜单（含「上传文件」）；坐标错位**仅在未激活时**发生 |
| **Lane A 包 zip** | ✅ **已上传 `03_AUDIT`**，file id `1Zgd22MuHUbbRMJLBu9FLFBGEWIhaZXS0`（G1 pass、1 次尝试）|
| Lane A 同级文件（`.sha256`／`.self-audit.json`） | ⛔ 两次护栏触发（G2 疑似 Drive 不预览 `.sha256`；G1 因 G2 回读把标签留在预览页）⇒ **已停止 Drive 操作**并请裁 `DRIVE-GUARD-FIX` |
| **lane 出包状态**（`_coord/scripts/status.py`） | **A ✅ / B ✅ / C ✅ / D ✅ —— 四个 lane 全部出包并写了 `READY-FOR-HQ.md`**（Lane B 于 22:07 完工，晚于当日 22:02 巡检）|
| **协同包 `_coord/`** | ✅ 已解压到 `X-BOOK/_coord/`；**待用户新开一个对话**并粘贴 `COORDINATOR.md`（第 1 句：你的地盘是 `/Users/nanopeng/AI-Agent-Lab/X-BOOK/`，按此文件上岗）|
| 观察（lane A/D 提出） | RELAY 指令要 lane 自读 Drive 文件，而 D 条禁止 lane **任何** Drive 读取 ⇒ **冲突**；lane 选择遵守更严格者。建议由协调员把文件**镜像到 lane 可读处**（`_coord/INBOX/`），HQ 不再要求 lane 读 Drive |

**🚀 进展（2026-10-15 22:2x 更新）**：

| 项 | 状态 |
|---|---|
| **Lane A 审计** | ✅ **PASS**（`RUN-20261015T132014Z-gxcdqj`）|
| **Lane C 审计** | ✅ **PASS**（`RUN-20261015T125336Z-4m5f3e`）|
| **Lane D 包** | ✅ zip 已上传 `03_AUDIT`（file id `1NqkCD4gyFMofvVNHR4Ys54Qd1aSGrYun`），等审计 |
| Lane B | 🔄 实施中（未出包） |
| `RULING-DRIVE-GUARD-FIX` 落地 | ✅ **G0 固定前置**（零激活导航回目标文件夹）＋ **G2 三值**（`match`/`mismatch`/`unverified_no_preview`），已硬编码进 `pipeline/drive_guard.py` |
| canary（每次激活后必做） | ✅ PASS（菜单含「上传文件」）|
| `DRIVE-GUARD-FIX-2` 请示已发 Muse | `.md`/`.json` 连续 G2 `mismatch`（**`.md` 纯文本也判不等** ⇒ 疑**回读本身不可靠**：读到上一个文件/UI 页）⇒ 已停 Drive 操作；建议"回读前置校验：预览页标题/URL 须对应目标 file id，不对应即判 `unverified_no_preview`（非失败）" |
| 待补传（等 FIX-2） | Lane A `.sha256`/`.self-audit.json`；Lane D `.self-audit.json`；聊天送达的 3 份 `REQUEST-*` 归档 |
| **git push** | ⛔ **SSH 22 端口被网络拒**（`Connection closed by 20.205.243.166 port 22`）；**本地提交安全**，待网络恢复或改走 443/PAT |
| 协调员 `_coord` | ⏳ 就位，**待用户新开一个对话**并粘贴 `COORDINATOR.md`（首句：你的地盘是 `/Users/nanopeng/AI-Agent-Lab/X-BOOK/`，按此文件上岗）|

**🚀 进展（2026-10-15 22:4x 更新）**：

| 项 | 状态 |
|---|---|
| `RULING-DRIVE-GUARD-FIX-2` 落地 | ✅ (i) 回读前置校验（URL 须含目标 file id）＋ (ii) `.json` 语义比对 ＋ 回读异常捕获（不再崩溃） |
| **G0 实测微调** | 改为「**已在目标文件夹时跳过导航**」—— 实测"激活后再导航"会让 Drive 工具栏渲染失效（「新建」菜单打不开）；修正后**上传触发已稳定** |
| **根因钉死** | Drive 预览是**渲染后**内容（`.md` 渲染成标题、`.json` 美化重排），与**原始字节**必然不同 ⇒ **"经预览比对原始文件内容"设计上不可实现** |
| **Drive 交付（已完成）** | Lane A zip ✅、Lane D zip ✅、Lane C zip ✅（已在 03_AUDIT）、`REQUEST-drive-guard-fix-2` ✅ 已上传 |
| **sidecar 处置** | 按 FIX 裁决自带出口：**不传 sidecar**，把哈希写进上传日志/转达行（见下表） |
| `DRIVE-GUARD-FIX-3` 请示已发 Muse | 请求把 G2 收口为「仅 (i) 落点/存在校验，不做内容比对」，或转 rclone（可下载字节才能真比对）|

**三份审计包的哈希（供审计方独立核验；`.zip` 本体均已在 `03_AUDIT`）**：

| 包 | package_sha256 | manifest_sha256 | 远端 file id |
|---|---|---|---|
| Lane A `RUN-20261015T132014Z-gxcdqj` | `04084286e2f613a2ba1ad603ed998ead62bb63612284de2db54fd3cd5026f3e2` | `5522fc01b8205f0b3306066cceacca220d94649b38c79a3f27ea8bb2cceed7f8` | `1Zgd22MuHUbbRMJLBu9FLFBGEWIhaZXS0` |
| Lane C `RUN-20261015T125336Z-4m5f3e` | `5f26aa0705d8c9ef7251b975c37634e16116e81d6819806272a3c2510bd2a403` | `7d73472d7b966d044dc66050ba3b0df8224adfefea4b84ee8498717690163e0e` | （审计方 API 复核：仅 `03_AUDIT` 一份）|
| Lane D `RUN-20261015T125734Z-d6sec1` | `e76f4c87fda2a4e85bac166d7a9eeeb0af6a9894ed6e8eca133d54de896cea43` | `1abc742c05da63802aff486b95ad09b38022b12d0bc6eb3f4f04717e2b0b3ab7` | `1NqkCD4gyFMofvVNHR4Ys54Qd1aSGrYun` |
| Lane B `RUN-20261015T140742Z-sfpl1h` | `e358cd5f5f53a74c70b51f186f89b6a85b2ab84f015a0e2d7a4cee4600442b43` | `9c9d1793958f5b94c86e79d0444c52f5817820f0798ccb7daa4fe4267d968a50` | `1Oh-H96uhGfGC6KNP0grbF28IjepGZ_ub` |

**Lane B 完工核对（HQ 只读复核，2026-10-15 22:5x）**：

| 检查 | 结果 |
|---|---|
| 提交 | `27ed698` —— **只改 4 个测试/桩文件**（`test_config.py` / `test_media.py` / `test_external.py` / `support/stub_fieldtheory.py`），**`src/` 零改动** ✅ |
| 共享文件 | ✅ 未碰 `CHANGELOG.md` / `tasks/CURRENT.md` / `PLAN.md` |
| 包哈希 | 本地 zip `e358cd5f…` 与旁文件**逐字一致** ✅ |
| 测试结论 | 修复前 **671 用例 / 9 失败** → 修复后 **671 / 0 失败 0 错误、exit 0** ✅ |
| 自检 | `self-audit-package` **PASS（0 FAIL）** ✅ |
| 主动披露 | ① C7 两条 `stale` 系修复前基线（预期）② 任务书分类偏差：#5 还叠加 A 类根因（A 类实为 5 处）③ C 类未降断言强度（win32 分支原样保留，POSIX 用 `mock.patch` 强制覆盖跨盘符分支）|

**🧪 HQ 合并预演与项目级基线（2026-10-15 23:0x）**：

| 项 | 结果 |
|---|---|
| **合并预演**（`git merge-tree`，按 **D→C→B→A** 链式模拟） | ✅ **四步全无冲突**（仅写临时对象；**未建分支、未改工作区**）|
| 四个 lane 工作区 | ✅ **全部干净**（无未提交的已跟踪改动）；HEAD 与出包一致：A `f7ffe29` / B `27ed698` / C `0bf4b97` / D `d8adaf9` |
| **项目级双跑 · base 半边**（已完成） | ✅ main `bf23c98` → **671 用例 / 9 失败**（failures=7, errors=2）；证据存档 `X-Bookmark-Knowledge-Automation/logs/merge-baseline/base-full-verbose.log` ＋ `base-failures.txt`（排序失败集）|
| **Lane A 独立验证**（HQ 在其 worktree 跑） | ✅ 674 用例 / 9 失败，**失败集与 base 逐条一致**（零回归；+3 为其新增 Protocol 用例）|
| **Lane B 独立验证**（HQ 在其 worktree 跑） | ✅ **671 用例 / OK (skipped=1) / 0 失败** —— 原 9 条**全部清除**（核心主张核实无误）|
| **Lane C 独立验证**（HQ 在其 worktree 跑） | ✅ 671 用例 / 9 失败，**失败集与 base 逐条一致**（零回归）|
| **四份包 HQ 独立复核**（`pipeline.self_audit.audit_run` ＋ 18 项拒绝清单） | ✅ **A / B / C / D 全部 verdict=PASS、fail=0、无未通过检查**（不采信 lane 自述，由 HQ 亲跑）|
| 剩余 | ⏳ **B、D 两份审计结论** → 到齐即执行合并（head 半边双跑预期待 **0 失败**）|

**🎯 四 lane 合并完成 + 项目级双跑（2026-10-16 工作块，队列 #11）**：

| 项 | 结果 |
|---|---|
| **合并（D→C→B→A）** | ✅ 四步全部成功、**零冲突**：`ce4af24`(D) → `c955a49`(C) → `e7ac36a`(B) → `a88ae56`(A) |
| **项目级 base-vs-head 双跑** | base `bf23c98` **671 用例 / 9 失败** → head `a88ae56` **674 用例 / 0 失败 / exit 0** ⇒ **Phase 6 干净基线达成** ✅ |
| 证据存档 | `X-Bookmark-Knowledge-Automation/logs/merge-baseline/{base,head}-full-verbose.log`、`{base,head}-failures.txt`、`{base,head}-commit.txt` |
| **共享文件（HQ 统改）** | ✅ `CHANGELOG.md` 新增「[Phase 5–6 · 四 lane 收口] 2026-10-16」条；`tasks/CURRENT.md` 本条 |
| 队列 #5 / #6（新裁决） | ✅ 已读并执行：`RULING-DRIVE-GUARD-FIX-3` → **G2 只做落点/存在确认、内容比对退役**、G0「已在该文件夹则跳过导航」；`RULING-DRIVE-BATCH` → 单标签页复用、**每天≤1 次激活**、**sidecar 停传**（哈希记台账）|
| 队列 #12 | 🔄 正在写 `REPORT-merge-progress-2026-10-16.md`，将与**合并审计包**一并在同一次激活内批量上传（00_CONTROL / 03_AUDIT）|
| 队列 #1 | ❌ 已按 `DRIVE-BATCH §3` **取消**（sidecar 停传，改为哈希入台账）|

**📦 合并审计包已出并上传（2026-10-16 工作块 · 收口完成）**：

| 项 | 值 |
|---|---|
| `run_id` | **`RUN-20261016T110134Z-yfpuc4`** |
| `package_sha256` | `2b214eb3e058acdc59732aff977990e0031f0c934e29e2aeeb5d58f32e0cbb7a` |
| `manifest_sha256` | `1891ce3212e10a3c9ae578131c89a89bb08a047acbc581127402bc63d608f508` |
| git range | `b4fa77f..26cb0f8`（**17 个文件，diff 全覆盖**）|
| 材料 | 11 项（TASK／ACCEPTANCE／change-summary／test-results ＋ base、head 两份 verbose 日志 ＋ 两份失败集 ＋ scan-denylist 日志）|
| 本包自检 | ✅ **PASS**；C7 = `['stale'(base 基线，预期), 'matches_head']`；C9 拒绝清单 **0 命中** |
| **Drive 落点** | ✅ **`03_AUDIT`**，file id **`1GaXI8PcvYhZnBm38Ti8b18zP0wjcAO3N`**（Drive 搜索页核实）|
| 两份 REPORT | `REPORT-merge-progress-2026-10-16.md`（`1KgYcaIFwpxBOMcMDA0_gFIHB9-kxN9Gv`）／`REPORT-merge-done-2026-10-16.md`（`1y1xSYnWBHdAv3OUvbJIFarGwTdXH1ldr`）→ 均落 **`00_CONTROL`** ✅ |
| 批量上传（`DRIVE-BATCH`） | ✅ **一次激活**内按顺序传完 3 件；**sidecar 一律未传**（哈希即本条台账）；G0 已为"已在该文件夹则跳过导航" |
| **新基线** | **674 用例 / 期望 0 失败**（Phase 6 达成）|
| 下一步 | ⏳ 等**本合并审计结论**；PASS 后由**用户亲手**执行 D-9=C（建库+转私有），HQ 再推单提交树；**审计 PASS 前不清理**四个 worktree |

**🏁 D-9=C 迁移执行完成（2026-10-16 工作块二，队列 #13–#15）**：

| 项 | 值 |
|---|---|
| **合并审计（队列 #14）** | ✅ **PASS** —— 四 lane 改动逐项吻合、项目级双跑 base 9 → head 0 零回归、**建议关闭 F-001** |
| 用户亲手完成 | ✅ 新建空公开库 **`dyanpeng-ops/X-Bookmark-Knowledge-public`** ＋ 旧库**转私有** |
| HQ 迁移前复核 | 旧库未认证 **404**（已私有）；新库 **200**（公开）；新库 `ls-remote` **无任何 refs**（空库）|
| **门禁（推送前，硬性）** | ✅ `scan-denylist` **18 项 / 0 命中**；**130 个跟踪文件真实标识 0 命中**（含 tweet_id/handle/显示名/author_id）|
| **新库单提交** | ✅ **`ef4ad959263d24a19c12844ccf709582c8debeb6`** —— **父提交数 = 0**（无历史）、130 文件、**树与本地 HEAD 逐字节一致** |
| 推送 | ✅ `* [new branch] ef4ad95… -> main`（经 `ssh.github.com:443`；22 端口在本网络被封）|
| **新审计基线** | **新库 `ef4ad95`** —— 后续新包按**新库**出；旧包仍按旧库／**包内 diff** 核验（=R3 约定）|
| 旧库状态 | **私有**（404）；**历史完整保留**（D-5=A 不重写历史；已公开期间的暴露不可撤回=R4，已知并接受）|
| **离线全量历史 bundle** | `X-Bookmark-Knowledge-Automation/backup/xbk-full-history-2026-10-16.bundle`（645K，含 `main` + 4 个 lane 分支；SHA256 `48423a11b6ac27a6799ee91b0b6a98df79ce382f1fbd57cd9a45c212eee380a9`；**已被 gitignore**，不入任何仓库）｜**用户 2026-10-16 显式指令：本地不加密**（用户指令 > D9C-6 的"加密存放"）|
| 本地 main | **未改**（新库推送用的是**孤立提交**，不影响本地历史）；本地 HEAD 仍 `2396fef`，**已推送旧库（私有）** |
| `git push` 通道 | ✅ 已通（改走 **443** `ssh.github.com`）；建议固化 3 行 `~/.ssh/config` |

**🔄 项目「收口」已作废 —— 项目尚未结束（队列 #17，Arlo 2026-10-16 19:41）**：

> **更正：komi 明确项目尚未结束，#16 的收口作废；审计监控已恢复（6 小时间隔），跟踪项已重开。后续动作等 komi 指示。**

| 项 | 值 |
|---|---|
| **#16 收口声明** | ❌ **作废**（Arlo #17 更正，依据 komi 明确表态）|
| 审计监控 `x-bookmark-audit-watch` | 🔄 **已恢复**（6 小时间隔）|
| 跟踪项 `goal_1255914057ed` | 🔄 **已重开** |
| 项目状态 | ⏳ **进行中，未收口**；后续动作**等 komi（用户）指示** |
| 已完成且**有效**的部分 | D-9=C 迁移成果本身**不变**（新库单提交 `ef4ad95`、旧库私有、四 lane + 合并审计均 PASS）—— 作废的是"**项目结束**"这一结论，不是交付物 |

<details>
<summary>（历史记录，已被 #17 作废）队列 #16 的收口声明</summary>

**✅ 项目正式收口（队列 #16，Arlo 2026-10-16 19:34）**：

| 项 | 值 |
|---|---|
| **D-9 独立复核（Arlo）** | ✅ **通过** —— 新库 `X-Bookmark-Knowledge-public` 单提交 **`ef4ad95`**、**提交数 = 1**、**已知真实标识 0 命中**、**无密钥残留**、四 lane 改动齐全 |
| **项目状态** | ~~正式收口~~ ⇒ **【#17 作废】项目尚未结束** |
| 队列状态 | **#1–#16 完成/关闭；#17 更正后项目继续** |
| 遗留（可选，待用户决定） | ① ~~bundle 加密~~ ⇒ **用户 2026-10-16 决定：不加密**（bundle 保持**明文**、仅靠 gitignore 隔离；残余风险见下）② ~~worktree 清理~~ ⇒ **用户 2026-10-16 决定：保留**（四个 lane worktree 与分支**均保留不删**；其改动已全部并入 main，包已在 03_AUDIT，保留无信息风险，仅占磁盘）|
| bundle 明文残余风险（已告知用户） | bundle 含**真实标识**且**明文**：仅靠"位于 gitignored 目录 + 未入任何仓库"隔离；**若误拷贝/误提交/误上传即等同于泄露**。D9C 的既有条件仍适用：**若将来删除旧库，必须先把 bundle 另存异地**（否则全历史只剩本地一份）|
| 新库处理 | **保持 migration 时的单提交快照不动**（审计已复核「提交数 = 1」）；迁移后的记录存于**旧库（私有）** ＋ Drive `00_CONTROL/REPORT-*` |
| 交付物总览 | 四 lane 审计包（03_AUDIT，A/B/C/D 全 PASS）｜合并审计包 `RUN-20261016T110134Z-yfpuc4`（03_AUDIT，PASS）｜新公开库 `ef4ad95`（单提交）｜旧库私有（全历史）｜离线 bundle（明文，按用户指令）|
| **流程缺陷回报** | ✅ 已推 Arlo：`REPORT-queue-fileid-churn-2026-10-16.md` → `00_CONTROL`（file id `13jjsBb7xJTE6qajE_J4DSejqAEgsZXMq`）——**`DISPATCH-QUEUE.md` 每次更新换 file id**，使 `HQ-RELAY-GAP` 的 (a) 零激活通道失效、每个工作块白耗一次激活（与 `DRIVE-BATCH` 每天≤1 次冲突）；含 4 个修法选项（推荐 A：原地编辑） |

</details>

**📌 队列 file id 已稳定（裁决 `RULING-QUEUE-FILEID-STABLE-2026-10-16`）**：

| 项 | 值 |
|---|---|
| **裁决** | `05_APPROVALS/RULING-QUEUE-FILEID-STABLE-2026-10-16.md`（id `1lygMpaloI_nHLn5V5i-8dAcqvDoGoAQJ`）—— HQ 报的缺陷**属实**，系 Arlo「上传新文件 + 删除旧文件」导致 |
| **裁决结论** | **(A) 原地更新**：Arlo 改用 API `hatch_gws_cli drive files update --params '{"fileId":"…"}' --upload <路径>`，内容原地替换、**file id 不变** |
| **稳定 id（即刻生效）** | **`1IYqFOU6p0SLu5re_hcM7o5q-oDFgvOCJ`** —— HQ 今后**凭此 id 直读（零激活）** |
| 兜底规则 | **仅当**该 id 返回「文件不存在」时，才退化为 `HQ-RELAY-GAP §2` 的 (b) 目录扫描（一次显式激活）|
| 适用范围 | 同样适用于**其他需保持 id 稳定的高频更新文件** |
| 验证 | ✅ 已用该 id 零激活直读成功（内容为 #17 版本）|
| 责任认定 | HQ 本次多用的 2 次激活**系流程缺陷所致，不记违规**；`REPORT-queue-fileid-churn-2026-10-16.md` 的呈报方式（本地留档、待批量）**符合 `DRIVE-BATCH`，获表扬** |

**📋 HQ 主动同步与交接（2026-10-16 20:2x，经用户同意）**：

| 项 | 结果 |
|---|---|
| **① 协同包同步** | `_coord/HQ-STATUS-2026-10-16.md`（**HQ 亲口回复**，供协调员按其 §3 取用）＋ `_coord/STATUS.md` **快照已同步**至当前真实状态（原文件备份为 `STATUS.md.bak-2021`）|
| **② 新库交接说明** | `HANDOFF.md`（50 行）—— 说明公开快照性质（单提交、无历史）、审计链与结论（四 lane + 合并全 PASS、双跑 674/0）、新基线、数据与凭据排除口径、文档入口 |
| **新库提交数** | **1 → 2**：`a938d8b`（HANDOFF，**父提交仅 `ef4ad95`**）→ `ef4ad95`（迁移快照）；131 文件；**未引入任何历史** ✅ |
| 本地 main | `f0dff17`（含 HANDOFF）→ 已推**私有旧库** |
| 报告 Arlo | `REPORT-public-repo-handoff-2026-10-16.md` → `00_CONTROL`（file id `1BNADNQ9wfP_H1WTWAFLFNMZA0Mw5mlc5`）——**主动提示"提交数 1→2"**，避免其复核时把新增文档提交误判为异常；并承诺**在你答复前不回退**（如需回退可 `push ef4ad95:refs/heads/main`）|

---

# 🏁 项目正式收口（用户 2026-10-16 显式指示）

> 用户于 **2026-10-16** 直接下达「**项目收口**」。
> 此前队列 **#17** 曾作废 #16 的收口声明（"komi 明确项目尚未结束"）；
> **本次收口依据用户本人的直接指令**（用户显式指令 > 队列条目）——**项目自此正式结束**。

| 收口判据 | 状态 |
|---|---|
| 四 lane 审计 | ✅ **A / B / C / D 全部 PASS**（Arlo 独立复核 ＋ HQ 亲跑 `self_audit` 复核）|
| 四分支合并入 main | ✅ **D→C→B→A，零冲突**（`ce4af24`→`c955a49`→`e7ac36a`→`a88ae56`）|
| 共享文件统改 | ✅ `CHANGELOG.md`（四 lane 收口条）／`tasks/CURRENT.md`（本状态板）／`PLAN.md` **§8 项目状态** |
| **项目级双跑** | ✅ base `bf23c98` **671 用例 / 9 失败** → head **`674 用例 / 0 失败`**（**新基线**；失败集逐条比对，零回归）|
| 合并审计包 | ✅ `RUN-20261016T110134Z-yfpuc4` → Drive `03_AUDIT`（id `1GaXI8PcvYhZnBm38Ti8b18zP0wjcAO3N`），**审计 PASS** |
| D-9=C 公开迁移 | ✅ 公开库 `X-Bookmark-Knowledge-public` @ **`ef4ad95`**（单提交、**0 标识**）＋ 旧库**私有**（保留全历史）|
| 安全门禁 | ✅ `scan-denylist` **18 项 0 命中**；跟踪文件真实标识 **0 命中** |
| 用户裁决的遗留项 | ✅ 离线 bundle **不加密**；四个 lane worktree **保留** |
| 收口文档 | ✅ `PLAN.md §8` ＋ 本状态板 ＋ Drive `00_CONTROL/REPORT-project-closeout-2026-10-16.md`（file id `1KP8DZKlMRCuqDYcNhWYGCqHG7864DxvA`）|
| 收口提交 | ✅ `8b7a468`（含 PLAN §8 ＋ 本收口章）→ 已推**私有旧库** |

**冻结说明**：本项目**不再有新交付物**。如需重启：先读本状态板 ＋ `PLAN.md §8`；
**审计基线 = 新公开库初始提交 `ef4ad95`**；迁移后记录写入私有旧库 ＋ Drive `00_CONTROL/REPORT-*`。

**⏫ 收口后新增改进（队列 #18 / #19 / #20，2026-10-16 22:25 派单）**：

> 收口章保留为历史；以下三项是收口**之后**由 Arlo 追加的改进任务，用户以「读队列开工」启动本工作块执行。

| # | 任务 | 状态 | 交付 |
|---|---|---|---|
| **18** | `fieldtheory` 可执行名跨平台：`src/config.py` 默认写死 `fieldtheory.cmd`（Windows 名）⇒ Mac 上 doctor 报 `upstream executable` 失败 | ✅ **完成** | 新增 `src.config.default_collector_executable()`（`nt`→`.cmd`，其他→裸名）；示例配置改为**留空交平台默认**；新增 `DefaultExecutableTests` 4 例 |
| **19** | F-007：`audit_package.py` 的 evidence provenance 有 **CWD 依赖盲区** | ✅ **完成** | 新增 `DEFAULT_EVIDENCE_ROOT` ＋ `evidence_root` 参数（含 CLI `--evidence-root`）；相对 `log_path`/`state_dir` 固定根解析；每条记录写死 `absolute_source`；`out` 绝对化 |
| **20** | 合并审计三个 LOW（M-001/002/003）转**打包规范** | ✅ **完成** | 新增 `docs/AUDIT-PACKAGING-CHECKLIST.md`（三对齐 + A–E 五组 checklist + 反例表）；**不重做**合并包 |

**#18 验收证据**：config 测试 **26/26 OK**；`doctor` 的 `upstream executable` **[ok]**（`/opt/homebrew/bin/fieldtheory`）、`Doctor result: OK`；
**全量 678 用例 OK（0 失败）**（较 674 新增 4 例）。
**#19 验收证据**：自动化测试 **207 OK**；端到端**从 `/tmp` 与自动化目录两个 CWD 打同一包，provenance 逐字一致 = True**，
且相对路径**首次能真正解析**（此前换目录会静默丢掉 `sha256`，provenance 不可复核）。
**#20 验收**：规范文档已入**仓库文档**（`docs/`，随项目 git 版本化）。

**#19 的版本化说明**：`X-Bookmark-Knowledge-Automation/` **被外层 gitignore 且无独立 git 仓库** ⇒ 自动化侧改动**只落盘**，
其证据即本条台账 ＋ 自动化测试 207 OK；如需版本化，请单独立库（属新的架构决策）。

**🔧 工作块内额外修复：Drive 上传通道三处（2026-10-16，全部零激活验证）**

> 起因：Chrome 远程调试恢复后上传连续 `menu-or-input-missing`。逐层实测定位到三个**独立**根因并修复：

| # | 根因（实测证据） | 修复 |
|---|---|---|
| ① 触发方式 | `elementFromPoint(82,99)` 确认是「新建」，但 `click_at_xy(82,99)` **实际打开 Drive 的「帮助」菜单**（dpr=1、无缩放偏移） | 改为 **DOM 触发**「新建」（mousedown/mouseup/click）；坐标点击降级为兜底；菜单项只认**可见**项并**幂等**（先试直接点，避免把残留打开的菜单关掉） |
| ② 页面刷新 | 首次上传成功后，Drive SPA 过期：再点「上传文件」**不再生成 `input[type=file]`**（恒 0）；**刷新后立刻生成（=1）** | `drive_guard` 的 **G0 恢复为"每次上传前都导航（=刷新）"**（DOM 路径本就无需激活，旧顾虑不成立） |
| ③ 同名冲突 | 冲突选项 **不是 button**（是 `LABEL`/`DIV`，文本「替换已有文件」）⇒ 旧选择器点不到；且**选完还要点「上传」确认** | 冲突处理改按"可见 + 文本前缀"找最小元素点击，**再加一步**点「上传」确认 |

**验证**：`REPORT-improvements-18-20`（新文件）与 `REPORT-drive-dom-trigger`（**同名替换**）**均一次成功**，
`attempts_used=1`、`G1=pass`，**全程未调用 `activate_tab`** ✅；自动化 **207 OK**、项目全量 **678 OK**。
**建议**：`RULING-DRIVE-BATCH` 的"每天 ≤1 次激活"可放宽为"**仅 DOM 路径失败时才申请激活**"（已写 REPORT 请裁）。

**⚠️ 与 `DRIVE-SERIAL` 的冲突（已报 Muse）**：第 2 条要求"扫三个文件夹"，但 `list` 已按 `DRIVE-API5-REV` **废止**
（零激活下恒返回 0 行）⇒ **HQ 缺少"发现新文件 id"的手段**，目前只能靠用户告知文件名或破例激活一次刷新渲染。
请 Muse 补一条可用通道（建议：审计方在写文件时于聊天**带上 file id**，成本为零）。

### ⏳ 等待用户动作（HQ 不得代办；**Muse 一裁决即提醒用户**）

**当前状态**：`DRIVE-API=5（后备 1）` 已裁 ⇒ **本轮不需要用户安装/授权任何东西**。
**待裁决**：`DRIVE-API5-REV`（`REQUEST-drive-api5-revision-2026-10-15.md`）。
**唯一可能重新需要用户动作的触发条件**：① 裁决选 **C''-c**；或 ② 今日大声失败达 **≥2 次**后升级 rclone（**已达标**）⇒ 若要升级，需用户**批准 `brew install rclone` + 完成一次 OAuth 同意**（届时 HQ 立即提醒并给出逐步清单）。
**裁决一到，HQ 立即把对应清单交给用户**（安装 / OAuth 授权均须用户本人完成）：

| 裁决 | 用户需做的事 | HQ 获授权后做什么 |
|---|---|---|
| **1 rclone** | ① 批准联网安装 `brew install rclone`<br>② `rclone config` 新建 remote（名 `gdrive`、类型 `drive`），**浏览器完成 OAuth 同意** | 用 `rclone lsf/lsjson/copy/moveto` 实现 list/read/upload/去重；目标文件夹用 `--drive-root-folder-id` |
| **2 gdrive** | 同上（安装 + OAuth） | 同上（语法按所选工具调整） |
| **3 官方 API** | ① GCP 建项目 + OAuth client（桌面应用）<br>② 下载 `client_secret.json`（**不入 Git**）<br>③ 批准 `pip install google-api-python-client google-auth-oauthlib`<br>④ 首次运行浏览器授权 | 写 `pipeline/drive_api.py`：**create 不带 `parents` → `files.update` `addParents` → `files.list` 按 `'<folder-id>' in parents` 复核** |
| **5 浏览器+护栏** | 无（零新依赖） | 仅对 `list` 停用；upload/read 保持零 `activate_tab`；上传后按 folder id + sha256 复核，失败即报警停止；**同时申请修订 DRIVE-SERIAL** |

> **HQ 铁律**：不自行安装依赖、不自行触发 OAuth、不使用用户凭据 —— 一律先取得用户明确授权。
> 另一项同样只能由用户操作：**D9C-4**（建新库 / 旧库转私有），且 Muse 要求**先别点**（等四 lane 合并审计通过）。

## 进度总览

| Phase | 名称 | 状态 | 任务书 |
| --- | --- | --- | --- |
| 0 | 架构审计 | ✅ 完成 | — |
| 1 | 架构设计 | ✅ 完成 | — |
| 2 | Canonical Schema | ✅ 完成（28 用例绿，已提交 `498236a`） | — |
| **3** | **Collector Adapter** | ✅ **实现完毕、已离线验收、已提交 `498236a`** | `PHASE-3-COLLECTOR-ADAPTER.md` |
| **4** | **Storage** | ✅ **完成**（三投影 + 可重建索引；报告见 `docs/X-Bookmark-Knowledge-Phase4-Report-2026-10-10.md`） | `PHASE-4-STORAGE.md` |
| **5** | **CLI** | 🟡 **部分完成**（`normalize`/`render`/`rebuild-index`/`status`/`doctor` 已交付；**剩余被 D-1/D-2 阻塞**）| `PHASE-5-CLI.md` |
| 6 | Cross Platform | ⏸ **方案待批准**（D-3；方案 `docs/PHASE6-PREP-PLAN.md`）| `PHASE-6-CROSS-PLATFORM.md` |
| 7 | Git Sync | ⛔ **被 D-4 阻塞**：`.gitignore` 与 `ARCHITECTURE §8.2` 相反（方案 `docs/PHASE7-SYNC-PREP-PLAN.md`）| `PHASE-7-GIT-SYNC.md` |
| 8 | Knowledge-Agent | ⏳ 待 Phase 7 | `PHASE-8-KNOWLEDGE-AGENT.md` |

## Phase 3 — Collector Adapter（✅ 已完成，存档）

- **任务书**：`tasks/PHASE-3-COLLECTOR-ADAPTER.md`（33 节，含验收标准 A–J）
- **目标**：建立 `Collector → RawCollectorData → CanonicalBookmark` 解耦链路，让 Field Theory 只是 Collector 实现。
- **交付物**：
  - 新增 `src/collector/raw_data.py`（冻结契约 + `RawDataContractError`）
  - 新增 `src/collector/fieldtheory/{__init__,adapter}.py`（`FieldTheoryCollector`）
  - 新增 `src/normalizer/{__init__,errors,fieldtheory}.py`（`FieldTheoryNormalizer` + `compute_content_hash`）
  - 新增 `tests/test_raw_data.py`（21）、`tests/test_fieldtheory_collector.py`（23）、`tests/test_normalizer.py`（89）
  - 修改 `src/collector/base.py`（`Collector` Protocol 增 `collect()`，+12 行）
  - 文档：`docs/phase3-preflight-review.md` 追加「决策与修正记录」；`PLAN.md` / `CHANGELOG.md` 同步
- **五项决策**（见 `docs/phase3-preflight-review.md` §10.1）：dict 输出 / content_hash 按 §5.4 九项 /
  新建 `fieldtheory/` 包且旧 adapter 不动 / 富化取 `data/raw/` / 时间戳取 `syncedAt`。
- **验收证据**（2026-10-08，全部离线）：
  - 新模块 `python -m unittest tests.test_raw_data tests.test_fieldtheory_collector tests.test_normalizer` → **133 用例全绿**
  - 全量 `python -m unittest discover -s tests -t .` → 524 用例、**9 失败**（全在 `test_config`/`test_media`/`test_external` 的 Windows 路径语义，归 Phase 6）
  - 真实数据只读验收：`data/upstream` + `data/raw` → 5/5 `RawBookmarkItem` → 5/5 `CanonicalBookmark` → Schema 全通过（4 篇 Article、1 媒体、1 外链去重后）
  - 未写 `data/`、`knowledge/`、`schema/`、`config/`；未联网
  - 提交前独立审核：4/4 变异测试被捕获、AST 依赖边界断言、`schema` 键集合与输出完全一致（见 `docs/phase3-preflight-review.md` §10.7）

## Phase 4 — Storage（✅ 已完成，五个 Step 全部交付）

- **Step 2 已完成**：`src/storage/markdown_projection.py` —— Markdown 投影
  （`knowledge/X-Bookmarks/{YYYY}/{MM}/{YYYYMMDD}-{tweet_id}.md`）
  - 布局复用 `src.markdown.render.date_parts`（与 Phase 8 assets 永不分叉）
  - frontmatter 14 键（按 Canonical D2：author=显示名 / author_username=handle）
  - 正文 `## Original Tweet` + `## AI Analysis`（仅占位，不编造分析）
  - **不覆盖内容不同的既有文件**（冲突抛 `MarkdownConflict`，显式 overwrite 才改写）
  - 测试 `tests/test_storage_markdown.py` **30 用例**；变异测试 2/2 捕获；全量 592 用例失败集 md5 未变
  - 与 ARCHITECTURE §7 的差异：不写 `tags`/`categories`（Canonical 无此字段），`engagement` 等同样记 gap
- **Step 3 已完成**（R6 字段二分）：
  - `src/database/r6_fields.py`：内容索引 / 运行态 / 结构列分类（唯一真实来源）+ 完整性护栏
  - `src/database/schema.py`：`MIGRATION_3` 补 `bookmarks.content_hash` + 索引（**原表没有这一列**）
  - `src/database/index_store.py`：幂等写入（同 hash 不写盘；只改内容列）+ 运行态重置
  - `tests/test_database_r6.py` **19 用例**；既有 database 层 70/70；全量失败集与基线一致
- **Step 4 已完成**（`rebuild-index`，D4 + R6）：
  - `src/storage/rebuild.py`：扫描 `data/normalized/*.json` 重建内容索引；两种模式
    （整库重建 ⇒ 运行态回初始态；`--in-place` ⇒ 幂等刷新且**保留运行态**）
  - CLI `rebuild-index`：默认**只演练**，须 `--apply` 才落盘；旧库自动备份 `state.db.bak-<UTC>`
  - **重置语义写进 `--help`**（D4 要求）；`tests/test_storage_rebuild.py` **22 用例**
  - 含任务书指定用例：**删库 → 重建 → 内容索引逐条一致**
- **Step 5 已完成**（只读 dry-run 验收 10/10）：
  5 条真实书签 → Canonical 校验 → JSON/Markdown 投影 → `rebuild-index` 建索引；
  三处 tweet_id 集合一致、content_hash 逐条一致、二次写入 **0 写**、
  整库重建后运行态回初始态、真实 `data/`+`knowledge/` 指纹**前后未变**（只读证明）。
- **Phase 4 五个 Step 全部交付** → 完成报告：`docs/X-Bookmark-Knowledge-Phase4-Report-2026-10-10.md`
- **Phase 5 已起步（决策无关部分，2026-10-10）**：
  - `normalize`（上游 → Canonical JSON）与 `render`（Canonical → Markdown）两个子命令，**均默认只演练**；
  - `pyproject.toml` 声明 `xbk` 入口（需 `pip install -e .` 生效，未执行安装）；
  - `tests/test_cli_canonical.py` 12 用例；全量 647 用例零回归。
- **Phase 5 其余部分仍待裁定**：S2（Collector Protocol 拆分）与 R1（新旧模块关系）——
  选项与影响见 `X-Bookmark-Knowledge-Automation/docs/PHASE5-PREP-BRIEF.md`

- **任务书**：`tasks/PHASE-4-STORAGE.md`（本轮新建；含 5 个 Step 与验收 A–H）
- **Step 1 已完成**：`src/storage/json_projection.py` —— Canonical JSON 投影
  （`data/normalized/{tweet_id}.json`）；原子写 + content_hash 幂等 + 路径穿越防护 + 单条失败隔离
  - 测试：`tests/test_storage_json.py` **24 用例全绿**；变异测试 2/2 被捕获
  - 端到端：5 条真实数据（只读）→ 规范化 → 临时目录落盘 **5/5**；二次运行 **0 写 / 5 跳过**（幂等实证）
- **Step 2–5 待续**：Markdown 投影 → SQLite 索引（R6 两类字段）→ `rebuild-index` → 全量验收
- **待用户决策 R1**：新建 `src/storage/` 与既有 `src/ingest`/`src/markdown`/`src/database`
  **并存**（增量、不破坏 500+ 既有测试）还是**原地替换**（更干净但大面积破坏既有测试）

## 关键状态

- **真实数据已就位**（2026-10-08 从 Windows 包迁移）：`data/upstream/`（5 条 + 6 媒体）、`data/raw/`、`config/config.yaml`、`knowledge/X-Bookmarks/`（5 篇 md + 资产）。
- **已知问题**：全量测试本机 macOS 9 失败（平台语义，非代码 bug）；第三方 Linux 审计复跑为 3 失败 + 16 错误 → **基线口径不可跨平台复现**，Phase 6 必须重建分类基线（见 `docs/phase3-preflight-review.md` §10.8.3）。
- **提交状态**：Phase 2 + Phase 3 交付物已提交并推送 `origin/main`（`498236a`）。
- **Phase 3 已完成第三方审计回应**（2026-10-09）：A1（非 UTF-8 快照拖垮整批，违反 AGENTS §2.7）+ A2/A3/A4/A5 已修复并补 5 个回归用例；S2（Protocol 债务）留待 Phase 4 前架构决策（见 `docs/phase3-preflight-review.md` §10.8）。
- **Phase 3 遗留 gap**（记录，不在本 Phase 修改）：`engagement` 无 Canonical 字段（留 payload）；
  `reply_to`/`thread` 无数据源（恒 `null`）；`quotedTweet` 形状待验证（真实样本均为 `null`）；
  `video`/`animated_gif` 未实测；非绝对 URI 外链被丢弃；`Collector` Protocol 仍含写上游的 `sync()`。

## 下一步（等老板指令）

1. ~~复核 Phase 3 交付物 → 提交~~：已完成（独立审核 + 提交 + 推送 `origin/main`）。
2. 若进入 Phase 4（Storage）：先出「待验证清单」与实现计划，获批准后再动代码。
3. Phase 6 启动前复核全量测试失败基线（9 vs 记录 11）。

## 硬约束（沿用 AGENTS.md）

- 验证分级授权：运行测试 / 联网 / 写盘，必须先列「待验证清单」交老板批准。
- 每 Phase 实现完成后先停下，未获批准不得自行验证。
- 数据与知识分离；敏感信息不进 Git/日志/Markdown。
