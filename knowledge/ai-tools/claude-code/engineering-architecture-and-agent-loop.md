---
title: 'Claude Code 工程架构与 Agent Loop 深度解析'
---

# Claude Code 工程架构与 Agent Loop 深度解析

> 整理日期：2026-03-25  
> 资料来源：Anthropic 官方文档（code.claude.com）、Claude Code v2.1.34 逆向工程分析（cc.bruniaux.com）、DeepWiki 架构文档、GitHub 逆向研究仓库（shareAI-lab/learn-claude-code）

---

## 一、整体定位：Claude Code 是什么

要理解 Claude Code 的架构，先要理解它的定位。它不是一个代码补全插件，而是一个**以终端为宿主的 Agentic 系统**。Anthropic 的设计哲学是"给 AI 一台电脑"——让语言模型像人类程序员一样，拥有终端、文件系统和开发工具的完整访问权。

从工程角度看，Claude Code 是一个**围绕 Claude 模型构建的 Agentic Harness（代理执行框架）**。它本身不做推理，推理由 Claude 模型完成；它负责的是：提供工具、管理上下文、控制权限、维护会话状态。这个分工很重要，理解它才能理解后面所有设计决策的来源。

---

## 二、整体架构分层

Claude Code 的架构可以分为四层，从上到下依次是：

**用户交互层**负责接收用户输入，包括 CLI 终端、VS Code 插件、JetBrains 插件、Web 界面（claude.ai/code）、Slack 集成等。这些界面的底层逻辑完全相同，差异只在于交互形式。

**Agent 核心调度层**是整个系统的心脏，包含主循环引擎（Agent Loop）、异步消息队列（h2A）、会话流生成器和消息压缩器。这一层负责驱动整个任务执行过程。

**工具执行与管理层**包含工具引擎、并发调度器、SubAgent 管理器和权限验证网关。所有对外部世界的操作（读文件、执行命令、搜索代码）都经过这一层。

**持久化与扩展层**负责会话存储、CLAUDE.md 记忆系统、MCP 服务器集成和 Hooks 系统。

---

## 三、Agent Loop：核心引擎

### 3.1 本质：一个极简的 while 循环

Claude Code 的 Agent Loop 本质上是一个 `while(tool_call)` 循环。没有 DAG（有向无环图），没有分类器，没有 RAG 检索，没有复杂的状态机。模型自己决定一切。

```
while (model_response.has_tool_calls) {
  results = execute_tools(model_response.tool_calls)
  model_response = call_claude(context + results)
}
return model_response.text
```

这个设计看起来简单，但背后有深刻的工程哲学：**把复杂性交给模型，而不是框架**。Anthropic 在内部将这个原则称为"Less Scaffolding, More Model"。

### 3.2 三个阶段

每次循环迭代包含三个相互融合的阶段：

**收集上下文（Gather Context）**：Claude 通过工具读取文件、搜索代码、查询文档，建立对任务的理解。这个阶段可能涉及十几次文件读取。

**采取行动（Take Action）**：Claude 执行修改操作，包括编辑文件、运行命令、创建新文件。

**验证结果（Verify Results）**：Claude 运行测试、检查输出、确认修改是否达到预期。

这三个阶段不是严格顺序的，而是在一次任务中反复交织。一个"修复 bug"的任务可能经历：读错误日志 → 搜索相关文件 → 读文件 → 修改代码 → 运行测试 → 发现新问题 → 再次修改 → 再次测试。

### 3.3 循环的终止条件

循环在以下情况下终止：

- 模型返回的响应中不包含任何 `tool_use` 块（即 `stop_reason: end_turn`）
- 用户主动中断（Ctrl+C）
- 上下文窗口达到压缩阈值并完成压缩后，模型判断任务已完成
- 工具执行遇到权限拒绝且无法继续

**重要澄清**：Claude Code 没有硬编码的"最多 N 轮"限制。循环是否继续完全由模型的输出决定——只要模型还在调用工具，循环就继续。

### 3.4 并行工具调用

当模型判断多个工具调用之间没有依赖关系时，它会在同一个响应中返回多个 `tool_use` 块，这些调用会被并行执行。例如，同时读取三个不相关的文件，或同时搜索多个关键词。这是 Claude Code 效率的重要来源之一。

---

## 四、上下文管理：最精密的工程部分

### 4.1 上下文窗口的构成

Claude Code 使用 200K token 的上下文窗口，这个窗口在所有组件之间共享：

| 组件 | Token 消耗 | 说明 |
|------|-----------|------|
| 系统提示（System Prompt） | ~1-3K | 内置指令，包含工具描述和行为规范 |
| CLAUDE.md | 可变，通常 0.5-2K | 用户定义的项目级指令 |
| Auto Memory（MEMORY.md 前 200 行） | ~1-2K | 跨会话自动保存的学习内容 |
| Rules（.claude/rules/*.md） | 可变 | 条件加载的规则文件 |
| Skill 描述 | ~2-5K | 按需加载完整内容 |
| MCP 工具 Schema | 每个服务器 ~200-1K | 会话开始时全部加载 |
| 对话历史 | 可变，持续增长 | 直到触发压缩 |
| 工具调用结果 | 可变 | 压缩时优先清除最旧的 |

### 4.2 上下文加载顺序

会话开始时，上下文按以下顺序加载：

1. 读取 CLAUDE.md 文件（优先级：managed → user → project → local）
2. 加载 MEMORY.md 的前 200 行（来自 `~/.claude/projects/*/memory/`）
3. 加载匹配路径条件的 Rules 文件
4. 加载 Skill 描述（完整内容延迟到调用时加载）
5. 连接 MCP 服务器，获取工具定义列表
6. 从 `~/.claude/*/sessions/` 加载会话历史

### 4.3 自动压缩（Auto-Compaction）

这是 Claude Code 上下文管理中最有特色的设计。当上下文使用量接近阈值时，系统自动触发压缩：

- **触发阈值**：约 75-92%（逆向工程发现的数值，官方未公开精确值）
- **压缩策略**：优先清除最旧的工具调用结果，然后对对话历史进行摘要
- **保留内容**：关键决策、重要发现、当前任务状态

与 Gemini CLI（70% 触发）相比，Claude Code 的 92% 阈值相当激进——它要榨干上下文窗口的每一个 token，直到最后一刻才开始压缩。这是一种"极限压榨"策略，代价是压缩时可能丢失更多细节，但好处是在压缩前能保留更完整的工作历史。

用户也可以手动触发压缩：在会话中执行 `/compact` 命令。

---

## 五、工具系统：Agent 的手脚

### 5.1 八个核心工具

Claude Code 的内置工具只有八个，但这八个工具覆盖了编程工作的全部需求：

**Bash**：万能适配器。任何 Claude Code 无法直接完成的操作，都可以通过 Bash 调用系统命令实现。这是工具系统的"逃生舱"。

**Read**：读取文件内容或 PDF 页面。直接访问文件系统，不创建 Checkpoint。

**Edit**：基于行差异（line-based diff）修改文件。执行前会创建 Checkpoint，支持撤销。

**Write**：创建新文件。如果文件已存在，执行前创建 Checkpoint。

**Glob**：按模式匹配查找文件。直接扫描文件系统。

**Grep**：用正则表达式搜索文件内容。底层调用 ripgrep 子进程。

**Task（Agent）**：派生子 Agent。在独立的上下文窗口中执行任务，完成后将结果返回给主 Agent。

**TodoWrite**：管理任务列表。这是 Claude Code 内置的任务规划工具，让 Agent 能够追踪复杂任务的进度。

### 5.2 搜索策略的演进

早期版本的 Claude Code 曾尝试使用 Voyage 嵌入向量做语义代码搜索（RAG）。后来 Anthropic 切换到了基于 ripgrep 的主动搜索策略，原因是内部 benchmark 显示后者性能更好，且运营复杂度更低——不需要维护索引同步，也没有外部嵌入服务商带来的安全风险。

这个"搜索而非索引"（Search, Don't Index）的哲学，用更多的 token 消耗换取了更简单的架构和更高的安全性。

### 5.3 Edit 工具的工作原理

Edit 工具是 Claude Code 中最精密的工具之一，值得单独说明。它的工作流程是：

1. 接收 `old_string` 和 `new_string` 参数
2. 在目标文件中精确匹配 `old_string`（支持模糊匹配，容忍少量空白差异）
3. 验证匹配唯一性（如果有多个匹配，要求提供更多上下文）
4. 执行替换，写入文件
5. 如果替换后文件语法错误，触发回滚

这个设计要求 Claude 在调用 Edit 时提供足够的上下文来唯一定位修改位置，这也是为什么 Claude 在编辑前通常会先读取文件。

---

## 六、Sub-Agent 架构：隔离与并发

### 6.1 为什么需要 Sub-Agent

主 Agent 的上下文窗口是有限的。当任务足够复杂时，把所有工作都放在一个上下文里会导致两个问题：上下文被大量中间结果填满，以及不同子任务之间的信息相互干扰。

Sub-Agent 解决了这个问题：主 Agent 通过 `Task` 工具派生子 Agent，子 Agent 在**独立的上下文窗口**中执行任务，完成后只把结果（而非过程）返回给主 Agent。

### 6.2 隔离模型

Sub-Agent 的隔离是严格的：

- 每个 Sub-Agent 有独立的上下文窗口，不共享主 Agent 的对话历史
- Sub-Agent 有独立的权限范围，不能超越主 Agent 的权限
- Sub-Agent 的嵌套深度限制为 1（Sub-Agent 不能再派生 Sub-Agent）

**为什么深度限制为 1？** 这是一个有意识的工程决策。更深的嵌套会导致权限传播难以追踪、调试困难、以及指数级的 token 消耗。深度 1 的限制在保留并发能力的同时，维持了系统的可控性。

### 6.3 Sub-Agent 的适用场景

Sub-Agent 最适合以下场景：

- **并行化**：多个独立的子任务可以同时派发给多个 Sub-Agent 并行执行
- **上下文隔离**：某个子任务需要大量中间信息，但这些信息对主任务没有价值
- **文件搜索**：在不确定能否快速找到目标文件时，用 Sub-Agent 执行搜索，避免污染主上下文

---

## 七、权限与安全模型

### 7.1 六层安全架构

每次工具调用都要经过多层安全检查，从外到内依次是：

1. **应用层权限规则**：`settings.json` 中配置的 allow/deny/ask 规则
2. **Hooks 系统**：PreToolUse 钩子可以拦截、修改或阻止工具调用
3. **权限对话框**：对于未匹配规则的操作，弹出交互式确认
4. **沙箱执行环境**：Bash 命令在受限的 shell 中执行（macOS 用 seatbelt，Linux 用 bubblewrap）
5. **PostToolUse Hooks**：可以修改工具输出
6. **Checkpoint 机制**：文件修改前自动快照，支持撤销

### 7.2 权限规则语法

```json
{
  "permissions": {
    "allow": ["Bash(npm test)", "Bash(git status)", "Edit(src/**/*.ts)"],
    "deny": ["Bash(rm -rf *)", "Write(.env)"],
    "ask": ["Bash(*)", "Edit(*)"]
  }
}
```

规则按 allow → deny → ask 的优先级匹配，支持通配符。

### 7.3 危险模式检测

Claude Code 内置了对危险命令模式的检测，例如 `rm -rf`、`sudo`、涉及 `.env` 文件的写操作等。这些检测在权限规则之外独立运行，作为最后一道防线。

---

## 八、会话持久化

### 8.1 存储内容

每个会话的以下内容会被持久化到本地：

- 完整的对话历史（每条消息、每次工具调用及其结果）
- 文件修改前的 Checkpoint 快照
- 会话元数据（时间戳、目录、模型版本）

存储位置：`~/.claude/*/sessions/`，格式为 JSONL。

### 8.2 会话恢复与分叉

`claude --continue` 恢复上次会话，追加新消息到同一会话 ID。

`claude --continue --fork-session` 创建新的会话 ID，但保留到分叉点为止的完整历史。原会话不受影响。这个功能类似 git branch，允许从同一个起点尝试不同的解决方案。

### 8.3 跨会话记忆

单个会话结束后，对话历史不会自动带入下一个会话。跨会话的知识传递通过两种机制实现：

**Auto Memory**：Claude 在工作过程中自动将重要发现（项目约定、用户偏好、架构决策）写入 `MEMORY.md`，下次会话开始时自动加载前 200 行。

**CLAUDE.md**：用户手动维护的项目级指令文件，每次会话都会加载。

---

## 九、设计哲学：Less Scaffolding, More Model

理解 Claude Code 架构的关键是理解 Anthropic 的核心设计哲学：**把复杂性交给模型，而不是框架**。

很多 Agent 框架（如 LangChain 早期版本）走的是相反的路：用复杂的 DAG、分类器、路由逻辑来控制 Agent 的行为。Claude Code 几乎没有这些东西。它的 Agent Loop 是一个简单的 while 循环，工具选择完全由模型决定，任务规划通过 TodoWrite 工具由模型自己管理。

这个选择的前提是：模型足够强大，能够在没有外部约束的情况下做出正确决策。当模型能力达到这个水平时，减少框架层的干预反而能让模型发挥出更好的效果——因为框架的每一层抽象都是一种约束，也是一种潜在的错误来源。

代价是：系统的行为更难预测，调试更依赖观察模型的推理过程，而不是检查框架的状态机。

---

## 十、与其他 Agent 框架的对比

| 维度 | Claude Code | LangGraph | AutoGPT |
|------|------------|-----------|---------|
| 循环控制 | while(tool_call)，模型决定 | DAG，开发者定义 | 固定循环 + 分类器 |
| 工具选择 | 模型自主选择 | 节点路由 | 规则 + 模型 |
| 上下文管理 | 自动压缩，92% 阈值 | 开发者控制 | 固定窗口 |
| 并发 | 并行工具调用 + Sub-Agent | 并行节点 | 有限并发 |
| 可观测性 | 流式输出，Hooks | 图可视化 | 日志 |
| 适用场景 | 编程任务，开放式探索 | 结构化工作流 | 通用任务 |

---

## 参考来源

- [How Claude Code Works - 官方文档](https://code.claude.com/docs/en/how-claude-code-works)（Tier 1，最权威）
- [How Claude Code Works: Architecture & Internals](https://cc.bruniaux.com/guide/architecture/)（Tier 2，基于 v2.1.34 的综合分析，2026-02 验证）
- [Agentic Loop and Tool Execution - DeepWiki](https://deepwiki.com/victor-software-house/claude-code-docs/3.2.1-agentic-loop-and-tool-execution)（Tier 2，基于官方文档的结构化解析）
- [Claude Code 逆向工程研究仓库](https://github.com/yuekcc/analysis_claude_code-fork)（Tier 3，v1.0.33 源码逆向，部分结论需交叉验证）
- [How the agent loop works - Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/agent-loop)（Tier 1，SDK 层面的官方说明）
