# 裁决留存 — Lane C · D-2（R1 并存收口）＋ 审计提交制度

> 来源：Google Drive `X-Bookmark-Knowledge-Automation/00_CONTROL/`（2026-10-15 读取）
> 本文件为**转录留存**，供 Lane C 审计包追溯；原文以 Drive 为准。

| 裁决文件 | Drive 文件 id | 大小 |
|---|---|---|
| `RULING-LANE-C-D2-R1-2026-10-15.md` | `1ecUU9wz7-URmK0rD-VNxYeYSGgFr7cIe` | ~2 KB |
| `RULING-audit-submission-policy-2026-10-15.md` | `1ojHZ0_TZonb8QuJsxmKHc4AA47bvtkQ9` | ~1 KB |

对应请示：`REQUEST-LANE-C-D2-R1-conflicts-2026-10-14.md`
（Drive id `1fdhtsLWBsMVzB6jWw5vL5FCALamhTIaj`）。

---

## 裁决 1 · Lane C D-2 R1

> 呈交：Lane C 开发 agent ｜ 裁决方：Muse（独立审计 / 裁决）｜ 日期：2026-10-15

### 裁决（一行）

```text
L1=B, L2=B, L3=A, L4=A, L5=A, L6=A, L7=B
```

### 依据（逐项）

- **L1=B**：Lane C **不改** `tasks/CURRENT.md` 等共享文件；D-2 收口结论只写
  `tasks/PHASE-5-CLI.md` + `docs/`；CURRENT 由收口方（主会话）在四 lane 合并时统一刷新。
  本裁决同时解决开工指南与 Lane C 任务书之间的写权冲突——**以本裁决为准**。
- **L2=B**：`CHANGELOG.md` 本轮豁免，收口统一改，与 A/B/D 纪律一致。
- **L3=A**：Lane C 以「本 lane base vs head 同环境双跑、逐字比对」自证零回归；
  **项目级零回归**以四 lane 合并后统一重跑为准，合并前不得声称「项目级零回归」。
  （符合 `docs/EVIDENCE-CONVENTIONS.md` §1：禁用不可复算的失败集 md5。）
- **L4=A**：C2 合格标准 = `_cmd_normalize` 装配处加权威路径代码注释 + 四处文档声明；
  **不动任何业务逻辑**（`process` 切 Canonical 是 Phase 7 的事）。
- **L5=A**：保留裁定词「兼容层」，但在四处文档显式加注「仍在依赖中；Phase 7 解耦后方可退役」，
  防止后续读者据此误删在役模块。
- **L6=A**：认可 E1–E6 为 Phase 7 退出条件，写入四处文档。
- **L7=B**：等 L1/L2/L5/L6 裁定落地后**一次出包**，避免「改了又包」；不阻塞其它 lane。

### 附注

Lane C 只读盘点中关于旧模块「在役 + 待解耦」（非「已退役 + 仅兼容」）的事实认定准确，
审计方采信。调用方清单（旧 adapter 9 类 / 旧 markdown 4 类）将作为 C4 证据随包送审。

---

## 裁决 2 · 审计提交制度（2026-10-15 起长期有效）

> 制定：Muse（独立审计 / 协调）｜ 生效：2026-10-15 ｜ 存放：`00_CONTROL/`

### 规则：各 lane 各自提交，不设统一提交时间

1. **各 lane 做完即各自出审计包**，上传 Drive `03_AUDIT`，**不等**别的 lane，不等统一时间点。
   - 理由：审计监控每 6 小时自动扫描，天然分批；统一时间会让快 lane 空等慢 lane
     （B/D 在本地 Saluki 上本来就慢），纯属浪费。
2. **主会话**：四 lane 分支全部合并回 main 后，**统一出一个合并审计包**
   （含四分支合并 + 全量 base-vs-head 双跑零回归），这是唯一的「统一」动作。
3. **请示类文件**（`REQUEST-*`）：继续放 `05_APPROVALS`（需批准的动作）或 `00_CONTROL`（备案/说明），
   由审计方在聊天中向用户汇报裁决。
4. **裁决类文件**（`RULING-*`）：由审计方放在与请示**相同目录**，开发 agent 开工前先读同目录有无新的
   `RULING-*`，有则先执行裁决再动手。
5. 审计报告（`-audit-result.json` / `-audit-report.md`）只写回 Drive `x-bookmark-audit report`，
   不在聊天贴全文；每轮只在聊天告知「审计完成 + 结论」（2026-10-15 用户要求）。

---

## 本轮执行映射（Lane C）

| 裁决 | 落地位置 |
|---|---|
| L1=B（不改共享文件） | `tasks/CURRENT.md` 零改动；结论写 `tasks/PHASE-5-CLI.md` §2.2/§6 + `docs/` |
| L2=B（CHANGELOG 豁免） | `CHANGELOG.md` 零改动 |
| L3=A（双跑口径） | 见审计包 `test-evidence.json` + `baseline-full-suite.log` 对照 |
| L4=A（装配处注释） | `src/cli/main.py::_cmd_normalize` 注释（零业务逻辑改动） |
| L5=A（在役加注） | `ARCHITECTURE.md` §3.5/§14/附录B · `PLAN.md` §4.6 · `tasks/PHASE-5-CLI.md` §6 · 本目录 `D2-R1-AUTHORITY-AND-CALLERS.md` |
| L6=A（E1–E6） | 同上四处文档 |
| L7=B（一次出包） | 本 lane 一份审计包（制度 2 的合并包由主会话负责） |
