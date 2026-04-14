# Markdown Import 特性与 AI Agent 上下文工程

整理日期：2026-04-13

---

## 一、Markdown 本身没有 import

这是理解这个话题的起点。

标准 Markdown（CommonMark 规范）**不包含任何文件引入机制**。CommonMark 是目前最权威的 Markdown 规范，由 John MacFarlane 等人于 2014 年发起，目标是消除各实现之间的歧义，但它刻意保持了语言的简洁性，没有定义 `include`、`import` 或 `transclusion`（嵌入引用）语法。

这意味着，所有"Markdown 文件引入"能力，都是各工具、框架或平台在 Markdown 之上**自行扩展**的。

---

## 二、各生态的扩展实现

### MDX：面向 React 生态的 import

MDX 是 Markdown 的超集，允许在 `.mdx` 文件中直接写 JSX 并使用 ES Module 的 `import` 语法：

```mdx
import Chart from './Chart'
import { Table } from '../components'

# 我的文档

<Chart data={salesData} />
```

MDX 的 import 是真正的 JavaScript 模块导入，编译后会生成 JS 代码。它主要用于文档站点（Docusaurus、Next.js、Astro 等），让文档可以嵌入交互式组件。这是"组件化文档"的方向，与 AI Agent 的上下文工程关系不大。

### 文档工具的 include 扩展

VuePress、Fumadocs、MkDocs 等文档工具各自实现了文件嵌入语法，例如：

```markdown
<!-- VuePress -->
<<< @/snippets/example.ts

<!-- Fumadocs -->
<include>./shared-content.md</include>
```

这些都是工具私有语法，不具备跨工具通用性。

### Python 扩展：mdx_include

`mdx_include` 是一个 Python Markdown 扩展，支持将本地或远程文件内容嵌入到 Markdown 中：

```markdown
{!path/to/file.md!}
```

---

## 三、AI Agent 领域的 import：上下文工程的核心工具

AI Agent 领域对"Markdown import"的需求来自一个根本性问题：**如何在有限的上下文窗口内，把正确的知识送到 AI 面前？**

这催生了一套以 Markdown 文件为载体、以 import/include 为组织手段的**上下文工程**（Context Engineering）实践。

### 3.1 Claude Code 的 @import 语法

Claude Code 在 `CLAUDE.md` 中实现了一套专有的文件引入机制，语法是 `@path/to/file`：

```markdown
# 项目说明

参见 @README 了解项目概览，@package.json 查看可用命令。

## Git 工作流
@docs/git-instructions.md

## 个人偏好（不提交到版本库）
@~/.claude/my-project-instructions.md
```

**关键特性：**

- 支持相对路径和绝对路径（含 `~` 展开）
- 相对路径以**包含 import 语句的文件**为基准，而非工作目录
- 支持递归引入，最大深度为 **5 层**
- 被引入的文件在会话启动时**展开并注入上下文**，与 CLAUDE.md 本体一同加载
- 可以引入任意文本文件，不限于 Markdown（如 `package.json`、`README`）

**设计意图：** 解决 CLAUDE.md 文件膨胀问题。官方建议单个 CLAUDE.md 控制在 200 行以内，超出后应通过 import 拆分到专题文件，或使用 `.claude/rules/` 目录。

**跨 worktree 共享：** 对于同一仓库的多个 git worktree，gitignored 的 `CLAUDE.local.md` 只存在于创建它的 worktree 中。要跨 worktree 共享个人指令，可以 import home 目录下的文件：

```markdown
# CLAUDE.local.md
@~/.claude/my-project-instructions.md
```

**与 .claude/rules/ 的分工：**

| 机制 | 适用场景 |
|------|---------|
| `@import` | 引入已有文档（README、package.json、通用规范文件） |
| `.claude/rules/` | 按文件路径或类型作用域化的规则（如只对 `src/api/**` 生效的规则） |
| Skills | 多步骤操作流程，不适合放在 CLAUDE.md 的内容 |

### 3.2 AGENTS.md：跨工具的开放标准

AGENTS.md 是由 OpenAI Codex 团队发起、现由 Linux Foundation 下属的 Agentic AI Foundation（AAIF）维护的开放格式。

**核心理念：** "README for agents"——给 AI 编程 Agent 一个清晰、可预测的指令入口，就像 README.md 是给人类开发者的入口一样。

**格式规范：** 纯标准 Markdown，无任何必填字段，无专有语法。内容完全由项目自定义。

**冲突解决规则：**
- 距离被编辑文件**最近**的 AGENTS.md 优先（就近原则）
- 用户在对话中的**显式指令**优先级最高，覆盖所有文件内容

**生态支持（截至 2026 年）：** OpenAI Codex、Cursor、GitHub Copilot Coding Agent、Devin、Windsurf、Amp、JetBrains Junie、Google Jules、Gemini CLI、Aider、RooCode、VS Code、Warp、Zed、goose 等 20+ 工具。GitHub 上已有超过 60,000 个开源项目采用。

**与 CLAUDE.md 的关系：** AGENTS.md 是跨工具的通用层，CLAUDE.md 是 Claude Code 的专有层（支持 @import、Skills、Hooks 等 Claude 特有功能）。如果团队同时使用多种 AI 编程工具，推荐用 AGENTS.md 写共享指令，用 CLAUDE.md 写 Claude 专属配置。

### 3.3 各工具的指令文件对照

| 工具 | 指令文件 | import 支持 | 备注 |
|------|---------|------------|------|
| Claude Code | `CLAUDE.md` / `.claude/rules/*.md` | ✅ `@path/to/file` | 最完整，支持递归、绝对路径 |
| OpenAI Codex | `AGENTS.md` | ❌（纯 Markdown） | 就近原则，子目录覆盖父目录 |
| Cursor | `.cursor/rules/*.mdc` | ❌ | 支持 frontmatter 配置作用域 |
| GitHub Copilot | `.github/copilot-instructions.md` | ❌ | 全局生效，无路径作用域 |
| Windsurf | `.windsurfrules` | ❌ | 类似 .cursorrules |
| Aider | `AGENTS.md`（配置后） | ❌ | 通过 `.aider.conf.yml` 指定 |
| Gemini CLI | `AGENTS.md`（配置后） | ❌ | 通过 `.gemini/settings.json` 指定 |

### 3.4 llms.txt：面向网站的 AI 上下文标准

`llms.txt` 是 Answer.AI 联合创始人 Jeremy Howard 于 2024 年 9 月提出的网站级标准，类比 `robots.txt`，但面向 LLM 推理时的信息消费。

**格式：** 放置在网站根目录 `/llms.txt` 的 Markdown 文件，结构如下：

```markdown
# 项目名称

> 一段简短的项目摘要

可选的详细说明段落

## 文档

- [快速入门](https://example.com/docs/quickstart.md): 简短描述
- [API 参考](https://example.com/docs/api.md): 完整 API 文档

## Optional

- [完整规范](https://example.com/spec.md): 可在上下文不足时跳过
```

**核心机制：** `llms.txt` 本身是一个**目录文件**，通过链接指向各个 `.md` 格式的详细文档页面。工具（如 `llms_txt2ctx` CLI）可以将这些链接展开，生成适合注入 LLM 上下文的完整文本。

**与 CLAUDE.md/@import 的本质区别：** `llms.txt` 是网站对外暴露给 AI 的"知识地图"，解决的是"AI 如何理解一个网站"的问题；CLAUDE.md 的 @import 是开发者在项目内部组织 AI 指令的工具，解决的是"AI 如何理解这个代码库"的问题。

---

## 四、为什么 import 在 AI Agent 上下文工程中如此重要

### 上下文窗口是稀缺资源

Claude 的上下文窗口约 200K tokens，看起来很大，但一个中等规模项目的所有文档加起来轻松超过这个限制。更关键的是，**注入上下文的内容越多，AI 对其中每一条指令的遵循度越低**。

这产生了一个核心矛盾：你想给 AI 更多背景，但给得越多，效果越差。

### import 提供了两种解法

**解法一：按需加载（Lazy Loading）**

Claude Code 的子目录 CLAUDE.md 只在 AI 读取该目录下的文件时才加载。这意味着 `src/api/CLAUDE.md` 里的 API 规范，只有在 AI 处理 API 相关文件时才会出现在上下文中，不会在处理前端代码时占用宝贵的 token。

**解法二：模块化组织（Modular Organization）**

通过 @import 将大型指令文件拆分为专题模块：

```
CLAUDE.md                    # 主文件，200 行以内
  @docs/architecture.md      # 架构说明
  @docs/testing-guide.md     # 测试规范
  @docs/git-workflow.md      # Git 工作流
  @~/.claude/personal.md     # 个人偏好（不提交）
```

每个模块独立维护，主文件保持简洁，同时所有内容在会话启动时完整注入。

### import 的一个重要特性：抗压缩

CLAUDE.md（及其 import 的文件）在 `/compact` 压缩上下文后会**重新从磁盘读取并注入**。这意味着写在 CLAUDE.md 里的规则是持久的，而在对话中口头说的规则在压缩后会丢失。这是 import 机制在长会话中的关键价值。

---

## 五、实践建议

**什么内容适合放在 CLAUDE.md 并通过 @import 组织：**
- 构建和测试命令（AI 无法从 package.json 推断的部分）
- 项目特有的架构约束（"所有 API 返回 `{ data, error }` 结构"）
- 不应修改的遗留模块说明
- 团队 Git 工作流规范

**什么内容不适合放在 CLAUDE.md：**
- 代码格式规则（交给 linter + hooks，不要依赖 AI 遵守）
- 会频繁变化的信息（过时的指令比没有指令更糟糕）
- AI 本来就知道的通用最佳实践

**import 深度建议：** 虽然 Claude Code 支持 5 层递归，但实践中建议控制在 2 层以内，避免引入链过长导致难以追踪哪些内容被加载。

**跨工具兼容策略：**
- 用 `AGENTS.md` 写所有工具都能读的通用指令
- 用 `CLAUDE.md` 写 Claude 专属配置，并通过 `@AGENTS.md` 引入通用部分，避免重复维护

---

## 参考来源

- [Claude Code 官方文档 - Memory](https://code.claude.com/docs/en/memory)
- [AGENTS.md 官网](https://agents.md/)
- [llms.txt 规范](https://llmstxt.org/)
- [CLAUDE.md: The Complete Guide - morphllm.com](https://www.morphllm.com/claude-md-guide)
- [File import in CLAUDE.md - GitHub Issue #6321](https://github.com/anthropics/claude-code/issues/6321)
