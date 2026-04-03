# 统计 AI 代码贡献率：Claude Code 与 OpenClaw 实战指南

> 整理日期：2026-04-01  
> 来源：Claude Code 官方文档、git-ai 项目文档、高德团队实践分享、DeepWiki

---

## 为什么要统计 AI 代码贡献率

"AI 出码率"（AI Code Contribution Rate）是衡量 AI 编程工具实际价值的核心指标。它回答的问题是：**最终提交到代码库的代码里，有多少行是 AI 生成的？**

这个指标的意义在于：它不统计 AI 生成了多少代码，而是统计有多少 AI 代码真正被开发者接受并提交。这是一个"有效产出"指标，而非"生产量"指标。

高德团队的实践表明，通过建立这套指标体系，他们在 3 个月内将前端团队的 AI 出码率从 30% 提升到了 70% 以上。

---

## 核心概念：什么算"AI 代码"

在统计之前，需要明确口径。业界主流有两种统计粒度：

**提交级（Commit-level）**：以 PR 或 commit 为单位，只要包含 AI 生成的代码，整个 PR 就被标记为"AI 辅助"。Claude Code 官方 Analytics 采用这种方式。

**行级（Line-level）**：精确到每一行代码，统计 AI 生成的行数占总提交行数的比例。高德团队的"AI 出码率"采用这种方式，公式为：

```
AI 出码率 = AI 采纳行数 / commit 代码总行数
```

其中"AI 采纳行数"是指：统计周期内，AI 生成的代码与 git commit 提交内容逐行匹配后，确认被采纳的行数。

---

## 方案一：Claude Code 官方 Analytics（团队/企业版）

这是最省力的方案，但需要 Claude for Teams 或 Claude for Enterprise 订阅，并且需要连接 GitHub 组织。

### 能统计什么

官方 Analytics 仪表盘（`claude.ai/analytics/claude-code`）提供：

- **Lines of code with CC**：所有已合并 PR 中，由 Claude Code 辅助编写的代码行数（仅统计"有效行"：去除空行、纯括号行、字符数少于 3 的行）
- **PRs with Claude Code (%)**：包含 Claude Code 辅助代码的 PR 占所有合并 PR 的比例
- **Suggestion accept rate**：用户接受 Claude Code 代码建议的比率（包括 Edit、Write、NotebookEdit 工具）
- **Lines of code accepted**：用户在会话中接受的 AI 代码行数（不追踪后续删除）
- **Leaderboard**：按贡献量排名的开发者列表，可导出 CSV

### 归因原理

当 PR 合并时，系统会：

1. 提取 PR diff 中的新增行
2. 找出在 PR 合并日期前 21 天到后 2 天内，编辑过相关文件的 Claude Code 会话
3. 将 PR 行与 Claude Code 输出进行多策略匹配（归一化处理：去除空白、统一引号、转小写）
4. 超过 20% 差异的代码不归因给 Claude Code

自动排除的文件类型：lock 文件、构建产物、minified 文件、dist/build/node_modules 目录、超过 1000 字符的行。

### 局限性

- 仅支持 Teams/Enterprise 计划，API 用户无法使用贡献指标
- 需要安装 GitHub App，不支持 GitLab 等其他平台
- 开启了 Zero Data Retention 的组织无法使用
- 统计口径保守，是实际影响的低估值

---

## 方案二：git-ai（开源工具，行级精确追踪）

[git-ai](https://github.com/git-ai-project/git-ai) 是一个开源的 Git 扩展工具，专门解决"AI 代码归因"问题。它的核心理念是：**不猜测哪些代码是 AI 写的，而是在代码生成的那一刻就打上标记**。

### 工作原理

git-ai 通过 Claude Code 的 Hooks 机制，在每次文件编辑前后捕获快照：

```json
// ~/.claude/settings.json（由 git-ai install-hooks 自动写入）
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{"type": "command", "command": "git-ai checkpoint claude --hook-input stdin"}]
    }],
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{"type": "command", "command": "git-ai checkpoint claude --hook-input stdin"}]
    }]
  }
}
```

每次 Claude Code 执行 Write/Edit/MultiEdit 工具时，git-ai 会：

1. **PreToolUse**：记录文件编辑前的状态（Human Checkpoint）
2. **PostToolUse**：读取 Claude Code 的 JSONL 对话记录（`~/.claude/projects/{project}/{conversation-id}.jsonl`），提取 AI 生成的内容，记录 AI Checkpoint
3. **git commit 时**：通过 post-commit hook，将 AI 归因信息存储在 git notes 中，随 commit 一起保存

### 安装与使用

```bash
# 安装 git-ai
curl -fsSL https://usegitai.com/install.sh | bash

# 在仓库中安装 hooks（会自动配置 Claude Code hooks）
git-ai install-hooks

# 查看 AI 代码归因（类似 git blame）
git-ai blame <file>

# 查看 AI 代码统计
git-ai stats

# 查看 AI 代码 diff
git-ai diff
```

### 支持的 AI 工具

git-ai 通过 Agent Preset 系统支持多种 AI 工具，包括 Claude Code、Cursor、GitHub Copilot 等。对于 Claude Code，它直接解析 `~/.claude/projects/` 下的 JSONL 对话记录。

### 优势与局限

优势：行级精确追踪，归因信息随 git 历史永久保存，支持 rebase/merge/squash 等复杂 git 操作后的归因追踪，开源免费。

局限：需要在每台开发机上安装，不支持 OpenClaw（OpenClaw 是 AI 助手运行时，不是代码编辑工具，没有直接的文件编辑 hook）。

---

## 方案三：MCP 协议标准化采集（适合 Claude Code 和 OpenClaw）

这是高德团队针对 Claude Code 和 Qoder 等 CLI 工具总结的方案，也是目前**最适合同时覆盖 Claude Code 和 OpenClaw** 的方式。

### 核心思路

在 CLAUDE.md（或 OpenClaw 的 SKILL.md/memory.md）中注入强制执行规则，要求 AI 在每次文件变更前后调用自定义 MCP 工具记录出码数据。

### MCP 采集规则（注入到 CLAUDE.md）

```markdown
# MCP 自动数据采集规则（强制执行）

## 触发条件
- 文件内容变更操作前：调用 `beforeEditFile`，传入涉及文件的绝对路径
- 文件内容变更操作后：调用 `afterEditFile`，传入涉及文件的绝对路径
- 每次对话结束：调用 `recordSession`

## 操作分类
需要记录的操作：create_file、delete_file、search_replace、edit_file 等任何修改文件内容的操作
不需要记录的操作：read_file、grep、glob 等只读操作

## 强制要求
- beforeEditFile 和 afterEditFile 必须严格配对，不允许遗漏
- 使用绝对路径
- 整个对话使用统一的 sessionId
```

### MCP 工具实现

MCP 工具的核心逻辑是：记录 `beforeEditFile` 时的文件内容，在 `afterEditFile` 时对比差异，计算本次 AI 出码行数，并上报到统计平台。

```python
# 伪代码示意
@mcp_tool("beforeEditFile")
def before_edit(file_paths: list[str], session_id: str):
    for path in file_paths:
        snapshot_store[session_id][path] = read_file(path)

@mcp_tool("afterEditFile")  
def after_edit(file_paths: list[str], session_id: str):
    for path in file_paths:
        before = snapshot_store[session_id].get(path, "")
        after = read_file(path)
        diff = compute_diff(before, after)
        record_ai_lines(session_id, path, diff.added_lines)

@mcp_tool("recordSession")
def record_session(session_id: str, summary: str):
    flush_session_data(session_id)
```

### 优势与局限

优势：兼容所有支持 MCP 的 AI 工具（Claude Code、OpenClaw、Cursor 等），工程复杂度低，是未来标准化方向。

局限：依赖模型遵守规则，可能因模型幻觉导致 MCP 工具未被调用；无法做到完全无感采集（工具调用会有提示）；数据可能有一定缺失率。

---

## 方案四：本地数据库逆向（Cursor 专用）

Cursor 将 AI 会话数据存储在本地 SQLite 数据库（`.vscdb` 文件）中，可以通过逆向工程直接读取 AI 生成的代码记录。

这种方案准确度最高，支持 Tab 补全、行内补全、会话信息等全量数据，但只适用于 Cursor，且 Cursor 版本升级可能导致数据库结构变化。

对于 Claude Code 和 OpenClaw 用户，这个方案不适用。

---

## 方案五：Git Commit 签名（最轻量，提交级统计）

最简单的方案：在 git commit message 中添加 AI 标识，然后通过 git log 统计。

Claude Code 默认会在 commit message 中添加 `Co-Authored-By: Claude` 标识。可以通过以下命令统计：

```bash
# 统计包含 Claude 辅助的 commit 数量
git log --oneline | grep -i "co-authored-by: claude" | wc -l

# 统计 AI 辅助 commit 占比
total=$(git log --oneline | wc -l)
ai=$(git log --format="%B" | grep -c "Co-Authored-By: Claude")
echo "AI commit 占比: $(echo "scale=2; $ai * 100 / $total" | bc)%"

# 统计 AI 辅助 commit 的代码行数
git log --format="%H %s" | grep "Co-Authored-By: Claude" | \
  awk '{print $1}' | \
  xargs -I{} git show --stat {} | \
  grep -E "^\s+[0-9]+ insertion" | \
  awk '{sum += $1} END {print sum}'
```

这种方案的统计粒度是 commit 级，无法精确到行，但实现成本极低，适合快速了解团队 AI 使用情况。

---

## 方案对比

| 方案 | 统计粒度 | 适用工具 | 实现成本 | 准确度 |
|------|---------|---------|---------|--------|
| Claude Code 官方 Analytics | 行级 + PR 级 | Claude Code | 低（需 Teams/Enterprise） | 高（保守估计） |
| git-ai | 行级 | Claude Code、Cursor、Copilot | 中（需每台机器安装） | 最高 |
| MCP 协议采集 | 行级 | 所有支持 MCP 的工具 | 中（需开发 MCP 工具） | 中（依赖模型遵守规则） |
| 本地数据库逆向 | 行级 | Cursor 专用 | 高（需逆向工程） | 高 |
| Git Commit 签名 | 提交级 | 所有工具 | 极低 | 低 |

---

## 推荐方案

**个人开发者**：使用 git-ai，安装一次，自动追踪，数据随 git 历史永久保存。

**使用 Claude Code Teams/Enterprise 的团队**：直接用官方 Analytics，零成本，数据最权威。

**同时使用 Claude Code 和 OpenClaw 的团队**：MCP 协议采集方案是最佳选择，一套规则覆盖所有工具。将 MCP 采集规则注入 CLAUDE.md（Claude Code）和 OpenClaw 的 memory.md 或 SKILL.md，配合自建统计平台，可以实现跨工具的统一出码率统计。

**快速了解现状**：Git Commit 签名统计，5 分钟内出结果。

---

## 参考资料

- [Claude Code Analytics 官方文档](https://code.claude.com/docs/en/analytics)
- [git-ai 项目](https://github.com/git-ai-project/git-ai) — GitHub 1.5k Stars
- [git-ai Claude Code 集成文档](https://deepwiki.com/acunniffe/git-ai/7.4-claude-code-integration)
- [高德团队：AI 出码率 70%+ 的背后](https://developer.aliyun.com/article/1686822) — 阿里云开发者社区，2025-10
