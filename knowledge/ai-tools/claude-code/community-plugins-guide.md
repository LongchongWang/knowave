---
title: Claude Code 社区插件实战指南
---

# Claude Code 社区插件实战指南

> 整理日期：2026-03-26  
> 数据来源：GitHub 仓库实时核查（2026-03-26）

---

## 背景：为什么需要这些插件

Claude Code 的原生能力是"能写代码"，但在实际工程实践中，开发者很快会遇到三类问题：AI 写着写着方向跑偏、不知道 AI 在干什么、用久了 AI 变笨。这三个问题分别催生了本文介绍的三个核心插件。加上一个可视化状态面板，这四个插件基本覆盖了 Claude Code 日常使用中最高频的痛点。

---

## 一、Superpowers — 工程化开发工作流

**GitHub**：[obra/superpowers](https://github.com/obra/superpowers)  
**Stars**：114k（2026-03-26）  
**作者**：Jesse（obra），社区开发者，已被 Anthropic 官方 Marketplace 收录  
**当前版本**：v5.0.6

### 它解决什么问题

用 AI 写代码最大的问题不是模型不够强，而是一上来就让模型写代码，写着写着方向就歪了。Superpowers 的核心洞察是：**AI 需要先想清楚再动手**。

### 工作原理

Superpowers 是一套完整的软件开发工作流，由一组可组合的 Skills 构成。它的核心机制是强制 Claude 在写代码之前先走完一个规范化的流程：

1. **brainstorming**（头脑风暴）：Claude 看到你要构建什么时，不会直接写代码，而是先通过提问把你的真实需求挖清楚，生成设计文档
2. **using-git-worktrees**（Git 工作树）：设计确认后，在独立分支上创建隔离工作区，验证测试基线
3. **writing-plans**（编写计划）：把工作分解成每个 2-5 分钟的小任务，每个任务包含精确的文件路径、完整代码和验证步骤
4. **subagent-driven-development**（子 Agent 驱动开发）：为每个任务启动独立子 Agent，完成后进行两阶段 Review（规格合规性 + 代码质量）
5. **test-driven-development**（TDD）：强制执行 RED-GREEN-REFACTOR 循环，先写失败测试，再写最小实现
6. **requesting-code-review**（代码审查）：任务间自动 Review，严重问题阻断进度
7. **finishing-a-development-branch**（收尾）：验证测试，提供合并/PR/保留/丢弃选项，清理工作树

这套流程让 Claude 能够连续自主工作数小时而不偏离计划。

### Skills 库全览

除了核心工作流，Superpowers 还包含以下专项技能：

**测试类**：`test-driven-development`（含测试反模式参考）

**调试类**：`systematic-debugging`（4 阶段根因分析）、`verification-before-completion`（确认真正修复）

**协作类**：`requesting-code-review`、`brainstorming`、`writing-plans`

**代码质量**：`inline-self-review`（写代码时实时自我审查）

**工具类**：`using-git-worktrees`、`subagent-driven-development`、`executing-plans`

### 安装方式

**方式一：官方 Marketplace（推荐）**

```bash
/plugin install superpowers@claude-plugins-official
```

**方式二：通过 Superpowers 自己的 Marketplace**

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

**方式三：手动安装**

```bash
git clone https://github.com/obra/superpowers ~/.claude/plugins/superpowers
```

**其他平台**：
- Cursor：`/add-plugin superpowers`
- Gemini CLI：`gemini extensions install https://github.com/obra/superpowers`
- Codex/OpenCode：告诉 AI 去 fetch 对应的 INSTALL.md

### 验证安装

新开一个会话，说"帮我规划这个功能"，Claude 应该自动触发 brainstorming skill，开始提问而不是直接写代码。

### 最佳实践

Superpowers 的 Skills 是**强制性工作流，不是建议**。安装后不需要手动触发，Claude 会在合适的时机自动调用。如果你发现 Claude 跳过了某个步骤直接写代码，可以明确说"先走 brainstorming 流程"来强制触发。

对于长任务，`subagent-driven-development` 比 `executing-plans` 更可靠，因为每个子 Agent 都有独立的上下文，不会受到主会话上下文污染的影响。

---

## 二、Claude HUD — 运行状态可视化面板

**GitHub**：[jarrodwatts/claude-hud](https://github.com/jarrodwatts/claude-hud)  
**Stars**：13.4k（2026-03-26）  
**作者**：Jarrod Watts，社区开发者  
**当前版本**：v0.0.11

### 它解决什么问题

使用 Claude Code 时，你根本不知道它在干什么——上下文用了多少、在读哪个文件、子 Agent 跑到哪了。Claude HUD 把这些信息实时显示在终端底部，就像赛车的 HUD 仪表盘。

### 工作原理

Claude HUD 利用 Claude Code 原生的 **statusline API**，在终端底部渲染一个持久化状态栏。它通过读取 Claude Code 的 stdin JSON 流和 transcript JSONL 文件，实时解析工具调用、Agent 状态和 Todo 进度，每 ~300ms 更新一次。

**不需要单独的窗口，不需要 tmux，任何终端都能用。**

默认显示两行：

```
[Opus] │ my-project git:(main*) Context █████░░░░░ 45% │ Usage ██░░░░░░░░ 25% (1h 30m / 5h)
```

可选显示（通过 `/claude-hud:configure` 开启）：

```
◐ Edit: auth.ts | ✓ Read ×3 | ✓ Grep ×2    ← 工具活动
◐ explore [haiku]: Finding auth code (2m 15s) ← Agent 状态
▸ Fix authentication bug (2/5)               ← Todo 进度
```

显示内容包括：模型名称、项目路径、Git 分支、上下文使用率（绿→黄→红渐变）、速率限制用量、当前工具活动、子 Agent 状态、Todo 完成进度。

### 安装方式

```bash
# Step 1：添加 Marketplace
/plugin marketplace add jarrodwatts/claude-hud

# Step 2：安装插件
/plugin install claude-hud

# Step 3：配置状态栏
/claude-hud:setup
```

安装完成后重启 Claude Code，HUD 即出现。

**Linux 用户注意**：如果 `/tmp` 是独立的 tmpfs 文件系统，安装时会报 `EXDEV: cross-device link not permitted`。解决方法：

```bash
mkdir -p ~/.cache/tmp && TMPDIR=~/.cache/tmp claude
```

然后在这个会话里执行安装命令。

**Windows 用户注意**：如果 setup 提示找不到 JavaScript 运行时，先安装 Node.js：

```bash
winget install OpenJS.NodeJS.LTS
```

### 配置

安装后随时可以调整：

```bash
/claude-hud:configure
```

提供引导式配置流程，可以选择预设（Full/Essential/Minimal），切换各元素的显示/隐藏，调整 Git 显示风格。高级配置（自定义颜色、阈值）通过直接编辑配置文件实现。

### 最佳实践

上下文使用率是最重要的指标。当上下文条变黄（约 70%）时，就应该考虑开新会话或使用 GSD 的 `/gsd:checkpoint` 命令保存状态。等到变红（90%+）再处理往往已经太晚，Claude 的输出质量会明显下降。

---

## 三、GET SHIT DONE（GSD）— 上下文工程系统

**GitHub**：[gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)  
**Stars**：42k（2026-03-26）  
**作者**：TÂCHES（glittercowboy），社区开发者  
**当前版本**：v1.29.0  
**npm 包**：`get-shit-done-cc`

### 它解决什么问题

长时间使用 Claude Code 后，模型会"变笨"。根本原因是上下文窗口被填满，模型不知道前面做了什么，开始重复错误、忘记约定、产生矛盾。这个现象叫做 **Context Rot（上下文腐烂）**。

GSD 的核心思路是：**不要把一个聊天线程当作你的构建系统**。它通过元提示（meta-prompting）和规格驱动开发（spec-driven development）来管理上下文生命周期。

### 工作原理

GSD 是一个轻量级的元提示系统，它不替换 Claude Code，而是在 Claude Code 之上加了一层上下文管理协议：

**规格文件（Spec）**：在 `.planning/` 目录下维护项目规格文档，每次新会话时 Claude 先读取规格，而不是依赖对话历史。

**Checkpoint 机制**：在关键节点保存当前状态到规格文件，下次会话可以从这里继续，而不是从头开始。

**上下文压缩**：当上下文接近满时，GSD 帮助提炼出关键信息，丢弃噪音，让新会话能以最小的上下文启动。

**支持平台**：Claude Code、OpenCode、Gemini CLI、Codex、Copilot、Cursor、Windsurf、Antigravity。

### 安装方式

**方式一：npx 一键安装（推荐）**

```bash
npx get-shit-done-cc@latest
```

这会在当前项目目录下初始化 GSD 配置。

**方式二：Claude Code 插件市场**

```bash
/plugin marketplace add gsd-build/get-shit-done
/plugin install get-shit-done
```

**方式三：全局安装**

```bash
npm install -g get-shit-done-cc
```

### 核心命令

安装后，在 Claude Code 中可以使用以下命令：

```bash
/gsd:start          # 开始新任务，创建规格文件
/gsd:checkpoint     # 保存当前进度到规格文件
/gsd:resume         # 从上次 checkpoint 继续
/gsd:status         # 查看当前规格和进度
/gsd:compress       # 压缩上下文，提炼关键信息
```

### 最佳实践

GSD 的核心使用模式是：**每个功能开一个新会话，用规格文件传递上下文，而不是在一个超长会话里做所有事情**。

具体来说：开始新功能时用 `/gsd:start` 创建规格，描述清楚要做什么；完成一个阶段后用 `/gsd:checkpoint` 保存；下次继续时用 `/gsd:resume` 加载规格，Claude 会立刻知道上下文，不需要重新解释。

当你感觉 Claude 开始"变笨"时，不要继续在同一个会话里挣扎，立刻用 `/gsd:checkpoint` 保存，开新会话用 `/gsd:resume` 继续。这比等到上下文完全腐烂再处理要好得多。

---

## 四、Anthropic 官方插件库

**GitHub**：[anthropics/claude-code](https://github.com/anthropics/claude-code/tree/main/plugins)  
**Stars**：82.9k（2026-03-26）  
**作者**：Anthropic 官方  
**Marketplace**：`claude-plugins-official`（启动时自动可用）

### 定位

这不是一个单独的插件，而是 Anthropic 在 `claude-code` 主仓库中维护的**官方插件集合**，同时也是官方 Marketplace（`claude-plugins-official`）的来源。

### 官方插件列表

以下是 `anthropics/claude-code/plugins/` 目录下的官方插件（截至 2026-03-26）：

| 插件名 | 功能描述 |
|--------|---------|
| `feature-dev` | 7 阶段功能开发工作流（需求分析→设计→实现→测试→文档→Review→合并） |
| `code-review` | 4 个并行 Review Agent，从不同角度审查代码质量 |
| `commit-commands` | 规范化 Git 提交流程，自动生成符合约定的 commit message |
| `hookify` | 用自然语言描述 Hook，自动生成 hooks.json 配置 |
| `pr-review-toolkit` | PR Review 工具集，支持内联评论、批量审查 |
| `frontend-design` | 前端设计工作流，含组件设计、样式规范、响应式适配 |
| `plugin-dev` | 开发 Claude Code 插件的辅助工具，含脚手架和最佳实践 |
| `agent-sdk-dev` | Agent SDK 开发辅助，含 API 参考和示例 |
| `security-guidance` | 安全编码指导，自动检测常见安全问题 |
| `learning-output-style` | 调整 Claude 的输出风格为教学模式，适合学习场景 |
| `explanatory-output-style` | 调整输出风格为详细解释模式 |
| `claude-opus-4-5-migration` | 迁移到 Claude Opus 4.5 的辅助工具 |
| `ralph-wiggum` | 彩蛋插件（The Simpsons 角色风格） |

### 安装方式

官方 Marketplace 在 Claude Code 启动时自动可用，无需手动添加。直接安装插件：

```bash
# 安装单个官方插件
/plugin install feature-dev@claude-plugins-official
/plugin install code-review@claude-plugins-official
/plugin install commit-commands@claude-plugins-official

# 查看所有可用官方插件
/plugin
```

### 最值得安装的官方插件

**feature-dev** 是最完整的功能开发工作流，适合需要从需求到上线全流程管理的场景。它的 7 阶段流程比 Superpowers 更结构化，但也更重，适合正式项目。

**code-review** 的 4 个并行 Agent 设计很有意思——不同 Agent 关注不同维度（安全性、性能、可维护性、测试覆盖），比单一 Agent Review 更全面。

**hookify** 解决了 Hooks 配置门槛高的问题。你只需要用自然语言描述"每次写完文件后自动格式化"，它帮你生成对应的 hooks.json。

---

## 插件组合建议

这四个插件（或插件集）并不互斥，可以同时使用：

**日常开发标配**：Superpowers + Claude HUD。Superpowers 保证工作流规范，Claude HUD 提供可观测性。

**长任务场景**：在上面的基础上加 GSD。当任务跨越多个会话时，GSD 的 checkpoint 机制能有效防止上下文腐烂。

**团队项目**：官方插件库中的 `feature-dev`、`code-review`、`commit-commands` 更适合团队协作，因为它们有更标准化的流程和输出格式。

**个人实验项目**：Superpowers 的灵活性更高，适合快速迭代。

---

## 参考资料

- [obra/superpowers](https://github.com/obra/superpowers) — Superpowers 主仓库
- [obra/superpowers-marketplace](https://github.com/obra/superpowers-marketplace) — Superpowers 插件市场
- [jarrodwatts/claude-hud](https://github.com/jarrodwatts/claude-hud) — Claude HUD 主仓库
- [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) — GSD 主仓库
- [anthropics/claude-code/plugins](https://github.com/anthropics/claude-code/tree/main/plugins) — Anthropic 官方插件集
- [claude.com/plugins](https://claude.com/plugins) — 官方 Plugin Marketplace
