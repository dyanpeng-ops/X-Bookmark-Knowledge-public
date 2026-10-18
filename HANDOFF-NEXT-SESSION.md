# 交接说明 · 新会话必读（2026-10-18）

> 上一会话极长、经多次上下文压缩，本文件是**权威交接**。新会话请先读本文件，再读 `AGENTS.md`、`tasks/CURRENT.md`。

## 1. 仓库基线（务必核对）

| 项 | 值 |
|---|---|
| 私有库 head | `47c324d`（`feat(cli): pipeline 生产耗时度量` 之后）|
| 公开库 head | `c04ce05`（**与私有同树**，22 提交，全公开库原生历史）|
| 测试 | `768` 用例全绿（约 20s）|
| 队列 | `DISPATCH-QUEUE.md`（Drive file id `1IYqFOU6p0SLu5re_hcM7o5q-oDFgvOCJ`，原地更新）|

## 2. 已完成的功能（队列 #24–#38）

- **#24/#25/#26 md 阅读体验**：本地 OCR（macOS Vision）＋ 配图内嵌（多图并排、caption 可检索）＋ 本地视觉模型（Saluki/mmproj）＋ OCR 质量门（乱码/过碎也补视觉）
- **#27 阅读体验跟进**：文件名改书签标题（`{title}.md`，无标题回退 `YYYYMMDD-{tweet_id}.md`）／frontmatter 只留 `title`＋`tags`（＋`tags_ai`）／删 `## metadata` 段／X 站内链派生卡片／链接封面卡（og:image 下载）
- **#28 标签分类**：预设 12 标签，本地 Saluki，每篇 1–3 个，只收预设
- **#29 测试提速**：`XBK_TRANSLATE=0` 隔离真实模型，双跑 134s → **7.6s**
- **#30 封面卡**：`covers.py` / `covers_pipeline.py` / `_attach_link_covers`；实跑 10 张封面、8 篇出卡
- **#35/#36 审计收口**：两包重出（独立日志）；tagcheck 书面关闭
- **#37 Phase 11 AI 增强分析**：`src/media/ai_analysis.py`，`## ai_analysis` 三段（要点/建议/扩展标签），`tags_ai` 独立字段；48/49 篇已生成
- **#38 pipeline 耗时度量**：`report_stage_timings()`，四阶段墙钟＋最慢＋超阈值告警（默认 120s，可配）

## 3. 关键数据（Phase 13 定时窗口依据）

```
Pipeline 耗时统计（热启动，缓存全命中）
  sync 1.86 / media 0.04 / links 5.19 / process 193.54  → total 200.62s
冷启动（全量模型推理）：~1331s（22 分钟）
```
⇒ 定时窗口建议 **≥25 分钟**（冷启动上限）。

## 4. 未完成 / 已知坑（按优先级）

1. **X-BOOK 全量归档未放到目标文件夹**：`X-BOOK-archive-20261018.zip`（16MB）现在在 Drive **`03_AUDIT`**；用户想放到新建的 `X-BOOK-archive` 文件夹，但浏览器自动化**建文件夹失败**。需要用户给 folder id，或手动拖动。
2. **`F-BYNLUY-02`**：等 komi 在 Obsidian 复验英文标题翻译质量。
3. **`## article` 长文本换行待验证**：`wrap_long_text()` 已实现且单测通过，但实测渲染路径是否生效**未确认**（那篇 Monid 是手工修的）。
4. **`sync --gaps` 是命令行标志**（不是 config 驱动）：匿名只能补部分 X 文章；补不到时用 **browser-use + 用户登录态**抓推文页。
5. **门禁坑**：不要往 `X-Bookmark-Knowledge-Automation/state/` 放大归档 zip（含全项目 ⇒ 必被 denylist 扫到）。
6. **AGENTS.md §10 新增 6 条红线**（2026-10-18）：入口 `html.unescape`、文件名强绑定主键、URL 括号平衡、状态流转自愈、外链语义降噪、优先用 `pipeline` 一键闭环。

## 5. 常用命令

```bash
cd /Users/nanopeng/AI-Agent-Lab/X-BOOK/X-Bookmark-Knowledge

# 测试（务必带 XBK_TRANSLATE=0，否则会调真实 27B 模型导致极慢）
XBK_TRANSLATE=0 .venv/bin/python -m unittest discover -s tests -t .

# 一键端到端（热 ~200s / 冷 ~1331s）
.venv/bin/python -m src.cli pipeline --overwrite

# 单步
.venv/bin/python -m src.cli sync --gaps      # 补文章标题/正文（命令行标志！）
.venv/bin/python -m src.cli links            # 抓外链标题 + 封面（含 og:image）
XBK_AI_ANALYSIS=1 .venv/bin/python -m src.cli process --overwrite   # 含 AI 分析

# 读队列（零激活）
cd X-Bookmark-Knowledge-Automation
BU_NAME=hq BH_HOME=/tmp/bh-home ../.venv/bin/python scripts/drive-sync read-text \
  --file-id 1IYqFOU6p0SLu5re_hcM7o5q-oDFgvOCJ

# 出包 + 自检 + 上传
../.venv/bin/python scripts/build-audit-package --run-id <RID> --out-dir state/<RID> \
  --base-commit <BASE> --git-repo .. --git-range <BASE..HEAD> \
  --test-evidence state/<RID>/test-evidence.json \
  --file task=... --file acceptance=... --require-task --require-claim-evidence \
  --denylist config/pii-denylist.txt
../.venv/bin/python scripts/self-audit-package --run-id <RID>
BH_HOME=/tmp/bh-home ../.venv/bin/python scripts/drive-guard --folder audit --file state/<RID>/<RID>-audit-package.zip --execute --attempts 3
```

## 6. 工作纪律（上一会话踩过的坑，别再踩）

- **不要复用上一个包的测试日志**（#35 审计缺陷）；每个包必须用自己的 base/head 日志，md5 必须不同。
- **别在 `state/` 里放大归档**（门禁会挂，且上传护栏会正确拦截空包）。
- **打包前确认 base 选对**（有一次 base 误设成只含文档的提交，包内容不全，已重出）。
- **多行表达式的脚本插入极易插坏**：优先用 `edit` 工具精确替换，不要用脚本猜锚点。
- **改控制流前先跑测试**：把统计打印塞进 `_cmd_pipeline` 的三条返回路径曾破坏 sync 阶段（`test_pipeline_runs_all_steps` 失败），已回退。
- 交付前必须：`XBK_TRANSLATE=0` 全量测试绿 → `scan-denylist` 0 命中 → 包自检 PASS → 才上传。
