# 多 Agent 并行开工指南 — X-Bookmark-Knowledge

> 适用：DSH（DeepSeek Harness）。一个对话 = 一个独立 agent 会话。

## 核心概念（先看懂这段）

- **开 4 个 DSH 对话 = 4 个 agent 同时干活**。每个对话里的 agent 互不知道对方在干嘛。
- **别让它们在同一个目录里跑**：两个 agent 同时改同一份文件会互相覆盖、git 状态会打架。
- 解法是 **git worktree**：同一个仓库，分出 4 个独立的工作目录，每个 agent 进自己的目录、在自己的分支上干活。

## 第一步：在 Mac 上建 4 个工作目录（跑一次就行）

在项目根目录 `/Users/nanopeng/AI-Agent-Lab/X-BOOK/X-Bookmark-Knowledge/` 执行：

```bash
cd /Users/nanopeng/AI-Agent-Lab/X-BOOK/X-Bookmark-Knowledge
git pull origin main   # 先同步最新（你昨天有进度没推送，确认都在了再分）

git worktree add ../xbk-lane-a -b feat/d1-s2-closure
git worktree add ../xbk-lane-b -b fix/d3-phase6-tests
git worktree add ../xbk-lane-c -b docs/d2-r1-authority
git worktree add ../xbk-lane-d -b docs/d6-threat-model
```

完成后你会有 4 个目录：`../xbk-lane-a` … `../xbk-lane-d`，各在各的分支上。

## 第二步：开 4 个 DSH 对话

在 DSH 网页端（http://127.0.0.1:3080）新开 4 个对话。每个对话的第一句话这样写：

> 你在这个目录工作：`/Users/nanopeng/xbk-lane-a`（不要离开这个目录）。
> 你的分支是 `feat/d1-s2-closure`，只在这个分支上提交。
> 任务书见附件 `LANE-A-D1-S2-closure.md`，先读它，再按里面的"开工前"步骤做。

（把 lane-a/b/c/d 和对应的任务文档换掉即可。）

## 第三步：收口（合并）

1. 每个 agent 按任务书走完"待验证清单 → 实现 → 自验 → 出审计包 → 上传 → 等审计"，审计 PASS 后**停下等指示**（不许自己合 main）。
2. 你（或一个协调 agent）在主目录逐个 `git merge` 四个分支。
3. 共享文件（`CHANGELOG.md`、`tasks/CURRENT.md`）的冲突在合并时手动解决——各 agent 已被要求不碰这些文件，冲突应该很少。

## 纪律（四个 agent 都要遵守）

- 只改自己任务书"范围"里的文件，范围外的文件**连看都不用看**，更不许改。
- `config/config.yaml`、真实 `data/`、`knowledge/`：只读或不动，按任务书要求。
- 任何联网、装依赖、写真实数据的操作，先列待验证清单等批准（AGENTS.md 硬约束）。
- 每轮产出审计包时 `run_id` 必须唯一（6 位随机后缀，别撞车）。
