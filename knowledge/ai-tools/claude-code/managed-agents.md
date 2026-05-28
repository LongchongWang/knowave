# Claude Managed Agents

> 来源：[Anthropic Engineering Blog](https://www.anthropic.com/engineering/managed-agents) · [产品博客](https://claude.com/blog/new-in-claude-managed-agents) · [官方文档](https://platform.claude.com/docs/en/managed-agents/overview)
> 发布时间：2026年4月8日（Public Beta）

---

## 它解决的问题

自建一个生产级 Agent 系统的复杂度，来自三个层次的问题，层层递进。

**第一层：让 Agent 跑起来。** 你需要自己写 agent loop，驱动 Claude 在"调用工具 → 看结果 → 再决策"这个循环里不断迭代，直到任务完成。这只是最基础的起点。

**第二层：让 Agent 跑得稳。** 一旦任务变长、变复杂，问题就来了。工具调用会失败——网络抖动、外部 API 限流、文件权限不够，你需要在 agent loop 里写清楚：是重试、换策略、还是报错？容器可能宕机，如果 harness、沙箱、会话状态都在同一个容器里，容器一挂整个任务进度全丢，只能从头来，所以需要把会话状态持久化到容器外面，支持断点恢复。最后是上下文窗口被撑满的问题，任务跑得越久积累的中间输出越多，你需要设计裁剪策略——而裁剪是不可逆的，裁掉的内容找不回来，策略选错了会影响 Agent 后续的决策质量。

**第三层：让 Agent 跑得安全。** 核心威胁是提示注入（Prompt Injection）。Agent 在执行任务时会读取外部内容——网页、文件、API 返回——这些内容里可能藏着恶意指令，操控 Claude 做它不该做的事。如果 API Key 和其他凭据就在沙箱容器的环境变量里，提示注入只需要说服 Claude 执行一条 `printenv`，凭据就出去了。更危险的是，拿到凭据之后攻击者可以用这个 Key 启动新的 session，在你的账户里做任何事。所以安全沙箱的本质要求是：Claude 生成的代码和它的执行环境，永远不能接触到凭据。

这三层加起来，还需要自己部署、监控、扩容整套基础设施，而这些全部和你的业务本身无关。Claude Managed Agents 的定位是：**把这些基础设施全部托管到 Anthropic 云端**。开发者只需定义"Agent 做什么"，Anthropic 负责"Agent 怎么跑"。

---

## 与 Messages API 的核心区别

| 维度 | Messages API | Managed Agents |
|------|-------------|----------------|
| 定位 | 直接模型调用，细粒度控制 | 预构建 Agent 框架，长时自主任务 |
| 需自建 | 完整的 agent loop、沙箱、工具执行 | 几乎不需要 |
| 适用场景 | 自定义控制流、短对话 | 长时任务、异步工作流 |
| 会话持久 | 否（调用方管理状态） | 是（服务端持久化） |
| 执行环境 | 无 | 托管云容器 |

---

## 核心架构：Brain / Hands / Session 三层解耦

这是 Managed Agents 最重要的设计思想，也是它解决"容器即宠物"问题的根本方案。

```
+---------+  execute(name, input)  +-----------+
|  Brain  | ───────────────────>   |   Hands   |
| (Claude |                        | (Sandbox  |
| +harness)|  <── string result ── |   Tools)  |
+---------+                        +-----------+
     |
     | emitEvent / getEvents
     v
+---------+
| Session | (append-only durable event log)
+---------+
```

**Brain（大脑）**：Claude 模型 + harness（控制循环逻辑）。完全无状态，可以独立扩缩容。

**Hands（手）**：沙箱容器和工具。任何工具调用都抽象为统一接口 `execute(name, input) → string`。容器宕机只是工具调用返回一个错误，Brain 可以用 `provision({resources})` 启动新容器继续。

**Session（会话）**：所有事件的持久化追加日志，保存在 Brain 和 Hands 之外。任何一方崩溃都不丢失进度。harness 崩溃后通过 `wake(sessionId)` 恢复，读取事件日志从上次停止的地方继续。

### 为什么这样设计

Anthropic 最初把所有东西放在一个容器里，发现了一个经典的基础设施问题：容器变成了"宠物"——一旦出问题必须精心修复，调试时还无法进入容器（里面有用户数据）。

三层解耦之后：
- 容器故障不导致会话丢失
- harness 崩溃可以立刻重启
- 凭据不放在沙箱容器内，Claude 生成的代码无法直接拿到 API Key
- p50 首 Token 延迟（TTFT）降低约 60%，p95 降低超过 90%（因为容器可以按需启动，不必每次提前 provision）

### Session ≠ Context Window

这是一个容易混淆的地方。Session 是外部持久化的事件日志，Claude 的 context window 只是 Session 的一个"视窗"。通过 `getEvents()` 接口，harness 可以灵活地选择哪些历史事件放进上下文，实现各种 context engineering 策略（压缩、缓存命中率优化等），而不会导致历史数据不可恢复。

---

## 四个核心概念

| 概念 | 含义 |
|------|------|
| **Agent** | 模型、系统提示、工具集、MCP 服务器和 Skills 的组合配置。可复用，带版本管理 |
| **Environment** | 云容器模板（预安装包、网络访问规则等）。多个 Session 可共享同一 Environment，但每个 Session 有独立容器实例 |
| **Session** | 在指定 Environment 中运行的 Agent 实例，执行具体任务，拥有独立上下文和事件日志 |
| **Events** | 应用与 Agent 之间通过 SSE（Server-Sent Events）交换的消息 |

### Agent 配置字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✓ | 可读名称 |
| `model` | ✓ | Claude 模型（支持 Sonnet 4.6 及更新版本） |
| `system` | - | 系统提示，定义行为角色 |
| `tools` | - | 内置工具集、MCP 工具、自定义工具 |
| `mcp_servers` | - | 标准化第三方能力的 MCP 服务器 |
| `skills` | - | 特定领域的专属上下文 |
| `callable_agents` | - | 可调用的其他 Agent（多 Agent 编排） |

每次更新 Agent 都生成新版本（从 1 开始递增），旧版本 Session 继续正常运行。

### 内置工具集（agent_toolset_20260401）

| 工具名 | 功能 |
|--------|------|
| `bash` | 在容器内执行 Shell 命令 |
| `read` / `write` / `edit` | 文件读写和字符串替换 |
| `glob` / `grep` | 文件匹配和文本搜索 |
| `web_fetch` | 获取网页内容 |
| `web_search` | 互联网搜索 |

所有工具默认启用。可以按名称禁用，或用白名单模式只启用特定工具。

---

## 快速上手：四步流程

```bash
# Step 1: 创建 Agent
agent=$(curl -sS https://api.anthropic.com/v1/agents \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{
    "name": "Coding Assistant",
    "model": "claude-sonnet-4-6",
    "system": "You are a helpful coding assistant.",
    "tools": [{"type": "agent_toolset_20260401"}]
  }')
AGENT_ID=$(jq -r '.id' <<< "$agent")

# Step 2: 创建 Environment（定义容器配置）
env=$(curl -sS https://api.anthropic.com/v1/environments \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{"name": "my-env", "config": {"type": "cloud", "networking": {"type": "unrestricted"}}}')
ENV_ID=$(jq -r '.id' <<< "$env")

# Step 3: 启动 Session
session=$(curl -sS https://api.anthropic.com/v1/sessions \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d "{\"agent\": \"$AGENT_ID\", \"environment_id\": \"$ENV_ID\"}")
SESSION_ID=$(jq -r '.id' <<< "$session")

# Step 4: 发送消息 + 消费 SSE 事件流
curl -sS https://api.anthropic.com/v1/sessions/$SESSION_ID/events \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  ... -d '{"events": [{"type": "user.message", "content": [...]}]}'

# 建立 SSE 连接监听输出
curl -sS -N https://api.anthropic.com/v1/sessions/$SESSION_ID/stream \
  -H "Accept: text/event-stream" ...
```

注意：所有请求需携带 Beta 请求头 `anthropic-beta: managed-agents-2026-04-01`，SDK 会自动添加。

---

## 最新功能（2026年5月发布）

### Dreaming（梦境，研究预览）

Dreaming 是一个定时调度流程，它回顾历史 Session 和 memory store，提取模式，自动更新 Agent 的记忆，让 Agent 随时间自我提升。

类比：Memory 是 Agent "工作时"实时学习，Dreaming 是 Agent "休息时"消化整合。

它能发现单个 Agent 自身看不到的模式——跨多个用户/Session 的共性错误、高效工作流、团队偏好。Memory 粒度是单次 Session，Dreaming 粒度是跨 Session 的宏观规律。

开发者可以选择：自动应用 Dreaming 结果，或人工审核后再生效。

### Outcomes（结果导向）

让开发者写一个评分 Rubric，描述"好结果"的标准。Agent 工作完成后，一个独立的 Grader（在自己的 context window 里）对输出打分，找出不足，Agent 重新来过，循环直到达标。

Grader 独立运行很关键：它不受 Agent 推理过程影响，评估更客观。内部测试数据：Outcomes 在最难的任务上提升了约 10 个百分点的成功率，docx 文件生成 +8.4%，pptx +10.1%。

### Multiagent Orchestration（多 Agent 编排）

当任务量超过一个 Agent 的处理上限，Lead Agent 可以把工作拆分，委托给多个 Specialist Agent 并行处理。各 Specialist 拥有各自的模型、系统提示和工具。

共享 filesystem、持久化 events，Lead Agent 可以中途 check in 其他 Agent 的进展。在 Claude Console 可以完整追踪哪个 Agent 做了什么、按什么顺序、原因是什么。

Netflix 案例：分析来自数百个构建任务的日志，多 Agent 并行处理不同批次，最终汇总跨批次的共性问题。

### Webhooks

Session 完成后通过 webhook 通知，不需要长轮询，适合异步后台任务场景。

---

## 与 Claude Code SubAgents / AgentTeams 的区别

三者都涉及"多个 Agent 协作"，但定位完全不同：

| 特性 | SubAgents | AgentTeams | Managed Agents |
|------|-----------|------------|----------------|
| 运行环境 | Claude Code 本地 | Claude Code 本地 | 云端托管基础设施 |
| 使用方式 | `/agents` 命令或自动委托 | 实验性多实例协作 | REST API / SDK |
| 典型场景 | 主对话的子任务委托 | 多维度并行任务协作 | 长时自动化、异步后台任务 |
| 会话持久 | 否（随主对话生命周期） | 否 | 是（服务端持久化） |
| 执行沙箱 | 本地工作目录 | 本地工作目录 | 隔离的云容器 |
| 目标用户 | 用 Claude Code 的开发者 | 用 Claude Code 的开发者 | 构建 AI 产品的开发者 |
| 阶段 | GA | 实验性 | Beta |

简单记忆：SubAgents 和 AgentTeams 是开发者工具（Claude Code 内部），Managed Agents 是平台服务（用 API 调用，嵌入自己的产品）。

---

## 安全设计

凭据从不进入沙箱容器：

- **Git 仓库**：用 access token 在容器初始化时 clone，token 写入 git remote 配置，Agent 通过 `push`/`pull` 操作，永远不直接接触 token。
- **自定义工具（MCP）**：OAuth token 存放在独立 Vault，Claude 通过专属 Proxy 调用 MCP 工具，Proxy 持有 session 级 token 去 Vault 换取凭据，harness 对真实凭据完全不可见。

这种设计在结构上杜绝了提示注入攻击（即使攻击者控制了 Claude 生成的代码，沙箱内也没有凭据可以窃取）。

---

## 真实使用案例

- **Harvey**（法律 AI）：用 Managed Agents 处理长篇法律文件起草和多文档创作。接入 Dreaming 后，Agent 跨 Session 积累文件格式 workaround 和工具使用模式，完成率提升约 6x。
- **Netflix**（平台工程）：分析来自数百个构建任务的日志，用多 Agent 并行处理，只汇报跨批次的共性问题。
- **Spiral**（Every 旗下写作工具）：Lead Agent（Haiku）路由请求，Subagent（Opus）并行生成多个草稿，Outcomes 用 Every 编辑原则打分，只返回达标草稿。
- **Wisedocs**（文件核查）：文件质量审核流程，Outcomes 对照内部准则打分，速度提升 50%。

---

## 参考资料

- [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)（Anthropic Engineering Blog，2026-04-08）
- [New in Claude Managed Agents: dreaming, outcomes, and multiagent orchestration](https://claude.com/blog/new-in-claude-managed-agents)（2026-05-06）
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)（Anthropic Engineering Blog，2024-12-19）
- [官方文档](https://platform.claude.com/docs/en/managed-agents/overview)
