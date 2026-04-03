# Claude Code 插件体系深度指南

> 整理日期：2026-03-26  
> 来源：[官方文档 - MCP](https://docs.anthropic.com/en/docs/claude-code/mcp) · [Skills](https://docs.anthropic.com/en/docs/claude-code/skills) · [Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins) · [Discover Plugins](https://docs.anthropic.com/en/docs/claude-code/discover-plugins) · [Plugins Reference](https://docs.anthropic.com/en/docs/claude-code/plugins-reference)

---

## 一、先把概念理清楚

Claude Code 的"插件"体系容易让人困惑，因为它有好几个层次的扩展机制，名字相近但定位不同。在深入之前，先把这张地图画清楚：

```
Claude Code 扩展体系
├── MCP（Model Context Protocol）   ← 连接外部工具和数据源
├── Skills（技能）                   ← 给 Claude 注入特定领域的指令
├── Plugins（插件）                  ← 打包分发 Skills/Agents/Hooks/MCP 的容器
│   └── 通过 Marketplace 分发
└── Hooks（钩子）                    ← 响应 Claude 生命周期事件
```

**MCP** 是最底层的协议，解决"Claude 怎么调用外部工具"的问题。**Skills** 是最轻量的扩展方式，一个 Markdown 文件就能给 Claude 增加一项能力。**Plugins** 是打包和分发机制，把 Skills、Agents、Hooks、MCP 服务器捆绑在一起，方便团队共享和版本管理。

---

## 二、MCP：连接外部世界的协议

### 定位

MCP（Model Context Protocol）是 Anthropic 主导的开放标准，解决的核心问题是：**让 AI 工具能以统一的方式接入各种外部服务**。有了 MCP，Claude Code 可以直接操作 GitHub、查询数据库、读取 Figma 设计稿，而不需要为每个服务写专门的集成代码。

### 实现原理

MCP 采用客户端-服务器架构。Claude Code 是客户端，各种外部服务通过 MCP Server 暴露工具（Tools）、资源（Resources）和提示（Prompts）。Claude 在对话中可以调用这些工具，就像调用内置的 Bash、Read、Write 工具一样。

MCP Server 支持三种传输方式：

- **stdio**：本地进程，通过标准输入输出通信，适合需要直接访问本地系统的工具
- **HTTP**：远程服务，最广泛支持的方式，适合云端服务
- **SSE**（Server-Sent Events）：已废弃，建议迁移到 HTTP

### 安装方式

```bash
# 添加远程 HTTP 服务器（推荐）
claude mcp add --transport http notion https://mcp.notion.com/mcp

# 添加本地 stdio 服务器
claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable \
  -- npx -y airtable-mcp-server

# 查看已配置的服务器
claude mcp list

# 在会话中检查状态
/mcp
```

### 作用域（Scope）

MCP 服务器有三个作用域，决定配置存储在哪里：

| 作用域 | 说明 | 配置文件位置 |
|--------|------|------------|
| `local`（默认） | 仅当前项目对你可见 | 本地配置，不提交到 git |
| `project` | 整个项目团队共享 | `.mcp.json`，提交到 git |
| `user` | 你的所有项目都可用 | `~/.claude/` 全局配置 |

**选择建议**：API Key 等敏感信息用 `local` 或 `user`；团队共用的工具（如 GitHub、Jira）用 `project` 并提交到仓库。

### 官方 Marketplace 中的 MCP 插件

Anthropic 官方 Marketplace 提供了一批预配置好的 MCP 插件，安装即用，无需手动配置：

- 源代码管理：`github`、`gitlab`
- 项目管理：`atlassian`（Jira/Confluence）、`asana`、`linear`、`notion`
- 设计：`figma`
- 基础设施：`vercel`、`firebase`、`supabase`
- 通信：`slack`
- 监控：`sentry`

---

## 三、Skills：最轻量的扩展方式

### 定位

Skills 是给 Claude 注入"专项能力"的机制。本质上是一个 Markdown 文件，里面写着"当遇到 X 情况时，按照 Y 方式处理"。Claude 会在合适的时机自动加载并遵循这些指令，也可以通过 `/skill-name` 手动触发。

Skills 遵循 [Agent Skills](https://agentskills.io) 开放标准，这意味着同一个 Skill 文件理论上可以在 Claude Code、Cursor 等多个 AI 工具中复用。

### 与 Commands 的关系

历史上 Claude Code 有 `.claude/commands/` 目录，用于定义自定义命令。现在 Skills 已经将 Commands 合并进来：`.claude/commands/deploy.md` 和 `.claude/skills/deploy/SKILL.md` 效果完全相同，都会创建 `/deploy` 命令。官方推荐迁移到 Skills，因为它支持更多特性（支持文件、调用控制、子 Agent 执行等）。

### 文件结构

每个 Skill 是一个目录，核心是 `SKILL.md` 文件：

```
~/.claude/skills/
└── code-review/
    ├── SKILL.md          # 主指令文件（必须）
    ├── checklist.md      # 辅助参考文件（可选）
    └── scripts/
        └── lint.sh       # Claude 可执行的脚本（可选）
```

`SKILL.md` 的结构：

```markdown
---
name: code-review
description: 审查代码质量和安全性。当用户要求 review 代码、检查 PR 时使用。
disable-model-invocation: false   # 是否禁止 Claude 自动触发（默认 false）
---

当审查代码时，检查以下方面：
1. 代码组织和结构
2. 错误处理
3. 安全隐患
4. 测试覆盖率
```

### 存储位置与优先级

| 位置 | 路径 | 适用范围 |
|------|------|---------|
| 企业级 | 管理员配置 | 组织内所有用户 |
| 个人级 | `~/.claude/skills/<name>/SKILL.md` | 你的所有项目 |
| 项目级 | `.claude/skills/<name>/SKILL.md` | 当前项目 |
| 插件级 | `<plugin>/skills/<name>/SKILL.md` | 插件启用的地方 |

优先级：企业 > 个人 > 项目。插件级 Skills 使用 `plugin-name:skill-name` 命名空间，不会与其他级别冲突。

### 两种调用方式

**用户手动触发**：直接输入 `/skill-name`，适合明确的操作型任务（部署、提交、生成报告等）。建议在 frontmatter 中加 `disable-model-invocation: true`，防止 Claude 在不合适的时机自动触发。

**Claude 自动触发**：Claude 根据 `description` 字段判断当前任务是否需要加载这个 Skill。适合参考型内容（代码规范、API 约定、领域知识等）。

### 内置 Skills（Bundled Skills）

Claude Code 自带几个强大的内置 Skill，值得了解：

| Skill | 功能 |
|-------|------|
| `/batch <instruction>` | 大规模并行代码变更。自动分解任务，每个子任务在独立 git worktree 中执行，完成后开 PR |
| `/simplify [focus]` | 并行启动三个 review agent，聚合发现并修复代码质量问题 |
| `/loop [interval] <prompt>` | 按间隔重复执行某个 prompt，适合轮询部署状态、监控 PR 等 |
| `/debug [description]` | 开启 debug 日志并分析当前会话的问题 |
| `/claude-api` | 加载 Claude API 参考文档，当代码中 import anthropic SDK 时自动激活 |

---

## 四、Plugins：打包与分发的容器

### 定位

Plugin 是一个**打包机制**，把 Skills、Agents、Hooks、MCP 服务器捆绑在一起，形成一个可分发、可版本管理的扩展单元。

**什么时候用 Plugin 而不是直接配置 Skills/MCP？**

- 需要与团队共享同一套工具配置
- 需要版本管理和更新机制
- 需要在多个项目中复用
- 准备发布到 Marketplace 供社区使用

如果只是个人项目的快速实验，直接在 `.claude/` 目录下配置 Skills 更简单。

### 目录结构

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # 插件清单（必须）
├── skills/                  # Skills 目录
│   └── code-review/
│       └── SKILL.md
├── agents/                  # 自定义 Agent 定义
│   └── reviewer.md
├── hooks/
│   └── hooks.json           # 事件钩子配置
├── .mcp.json                # MCP 服务器配置
├── .lsp.json                # LSP 服务器配置（代码智能）
└── settings.json            # 插件默认设置
```

**重要**：`commands/`、`agents/`、`skills/`、`hooks/` 这些目录必须放在插件根目录，不能放在 `.claude-plugin/` 里面。`.claude-plugin/` 只放 `plugin.json`。

### plugin.json 清单

```json
{
  "name": "my-plugin",
  "description": "插件功能描述，显示在插件管理器中",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  },
  "homepage": "https://github.com/you/my-plugin",
  "repository": "https://github.com/you/my-plugin"
}
```

`name` 字段同时作为 Skills 的命名空间前缀，例如插件名为 `my-plugin`，其中的 `hello` Skill 会变成 `/my-plugin:hello`。

### 插件包含的组件

**Skills**：放在 `skills/` 目录，每个子目录对应一个 Skill，包含 `SKILL.md`。

**Agents**：放在 `agents/` 目录，Markdown 文件定义专用 Agent：

```markdown
---
name: code-reviewer
description: 专注于代码审查的 Agent，当需要深度 review 时自动调用
model: sonnet
effort: medium
maxTurns: 20
disallowedTools: Write, Edit
---

你是一个专业的代码审查员...
```

**Hooks**：放在 `hooks/hooks.json`，响应 Claude 的生命周期事件：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format-code.sh"
          }
        ]
      }
    ]
  }
}
```

Hook 支持的事件类型非常丰富，包括 `SessionStart`、`PreToolUse`、`PostToolUse`、`SubagentStart`、`FileChanged`、`CwdChanged`、`PreCompact`、`PostCompact` 等 20+ 个事件。

**MCP 服务器**：放在 `.mcp.json`，可以使用 `${CLAUDE_PLUGIN_ROOT}` 引用插件目录内的文件：

```json
{
  "mcpServers": {
    "plugin-db": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
    }
  }
}
```

**LSP 服务器**：放在 `.lsp.json`，为特定语言提供代码智能（跳转定义、查找引用、实时错误检测）：

```json
{
  "go": {
    "command": "gopls",
    "args": ["serve"],
    "extensionToLanguage": {
      ".go": "go"
    }
  }
}
```

### 安装方式

```bash
# 从官方 Marketplace 安装
/plugin install github@claude-plugins-official

# 从 GitHub 仓库安装
/plugin marketplace add anthropics/claude-code
/plugin install commit-commands@anthropics-claude-code

# 本地开发测试（不安装，直接加载）
claude --plugin-dir ./my-plugin

# 安装后热重载（无需重启）
/reload-plugins
```

### 作用域

插件安装也有三个作用域：

- **User scope**：对你的所有项目生效
- **Project scope**：对当前仓库的所有协作者生效（写入 `.claude/` 配置）
- **Local scope**：仅对你在当前仓库生效

---

## 五、代码智能插件（LSP Plugins）

这是一类特殊的插件，值得单独说明。LSP（Language Server Protocol）插件让 Claude 获得真正的代码理解能力，而不只是文本搜索。

安装 LSP 插件后，Claude 能做到：

- **实时诊断**：每次编辑文件后，语言服务器自动分析变更，Claude 立即看到类型错误、缺失 import、语法问题，并在同一轮对话中修复
- **代码导航**：跳转到定义、查找引用、获取类型信息、列出符号、追踪调用链

官方 Marketplace 提供了主流语言的 LSP 插件：

| 语言 | 插件名 | 需要安装的二进制 |
|------|--------|----------------|
| TypeScript | `typescript-lsp` | `typescript-language-server` |
| Python | `pyright-lsp` | `pyright-langserver` |
| Go | `gopls-lsp` | `gopls` |
| Rust | `rust-analyzer-lsp` | `rust-analyzer` |
| Java | `jdtls-lsp` | `jdtls` |
| C/C++ | `clangd-lsp` | `clangd` |

安装方式：

```bash
/plugin install typescript-lsp@claude-plugins-official
```

注意：插件只是配置，实际的语言服务器二进制需要单独安装（如 `npm install -g typescript-language-server`）。

---

## 六、最佳实践

### 个人工作流搭建

从最简单的 Skills 开始，不要一上来就搞 Plugin。在 `~/.claude/skills/` 下创建个人 Skills，积累一段时间后，如果发现某些 Skills 在多个项目都有用，再考虑打包成 Plugin。

推荐的个人 Skills 方向：
- 代码规范和风格指南（让 Claude 了解你的项目约定）
- 常用操作流程（提交规范、部署步骤、测试流程）
- 领域知识注入（业务术语、架构约定、API 规范）

### 团队协作

把团队共用的工具配置放在 `.mcp.json`（project scope）提交到仓库，让所有人自动获得相同的工具集。把团队的代码规范、开发流程打包成 Plugin，通过内部 Marketplace 分发。

### MCP 服务器选择

优先使用官方 Marketplace 中的预配置插件（如 `github`、`atlassian`），它们经过验证且配置简单。自建 MCP 服务器适合内部系统（如公司内部 API、私有数据库）。

使用第三方 MCP 服务器时要谨慎，特别是那些会抓取外部内容的服务器，存在 Prompt Injection 风险。

### 环境变量管理

MCP 服务器的 API Key 等敏感信息，用 `--env` 参数传入，不要硬编码在配置文件里：

```bash
claude mcp add --transport stdio --env GITHUB_TOKEN=$GITHUB_TOKEN github \
  -- npx @modelcontextprotocol/server-github
```

### 调试技巧

- 用 `claude --plugin-dir ./my-plugin` 在不安装的情况下测试插件
- 用 `/mcp` 命令检查 MCP 服务器连接状态
- 用 `/plugin` 的 Errors 标签页查看插件加载错误
- 用 `/debug` Skill 开启 debug 日志分析问题

---

## 七、常见误区

**误区一：Skills 和 CLAUDE.md 是一回事**。CLAUDE.md 是项目级的全局上下文，每次会话都会加载，适合放项目背景、架构说明等。Skills 是按需加载的专项指令，Claude 根据任务相关性决定是否加载，或由用户手动触发。两者互补，不要把所有东西都塞进 CLAUDE.md。

**误区二：Plugin 就是 MCP**。Plugin 是一个容器，MCP 只是它可以包含的组件之一。一个 Plugin 可以同时包含 Skills、Agents、Hooks 和 MCP 服务器。

**误区三：Skills 只能手动触发**。Skills 有两种调用模式：用户手动触发（`/skill-name`）和 Claude 自动触发（根据 description 判断）。默认是两种都支持，加 `disable-model-invocation: true` 才变成只能手动触发。

**误区四：LSP 插件安装后就能用**。LSP 插件只是配置，还需要在系统上安装对应的语言服务器二进制（如 `gopls`、`pyright-langserver`）。

---

## 参考资料

- [MCP 官方文档](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Skills 官方文档](https://docs.anthropic.com/en/docs/claude-code/skills)
- [创建 Plugins](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [发现和安装 Plugins](https://docs.anthropic.com/en/docs/claude-code/discover-plugins)
- [Plugins 技术参考](https://docs.anthropic.com/en/docs/claude-code/plugins-reference)
- [Agent Skills 开放标准](https://agentskills.io)
- [官方 Plugin Marketplace](https://claude.com/plugins)
