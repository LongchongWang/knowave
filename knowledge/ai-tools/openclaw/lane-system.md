# OpenClaw Lane 任务通道系统

> 整理日期：2026-03-29  
> 来源：[OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)、[OpenClaw 官方文档 - 定时任务](https://docs.openclaw.ai/zh-CN/automation/cron-jobs)、[OpenClaw 官方文档 - Channel Routing](https://docs.openclaw.ai/channels/channel-routing)、[OpenClaw 中文文档 - 并发队列与 Session-Lane 模型（源码级）](https://openclaw-docs.dx3n.cn/beginner-openclaw-guide/15-%E5%B9%B6%E5%8F%91%E9%98%9F%E5%88%97%E4%B8%8ESession-Lane%E6%A8%A1%E5%9E%8B)

---

## 为什么需要 Lane？

OpenClaw 是一个多通道 AI 助手运行时，同一时刻可能有来自 Telegram、Discord、Slack 等多个渠道的消息同时到达。如果不加控制，多条消息并发写入同一个 AI 会话，会导致对话历史乱序，AI 的上下文损坏。

Lane（执行通道）就是解决这个问题的核心机制：**同一会话内的任务严格串行，不同会话之间可以安全并行**。

---

## 双层排队模型

每次 `runEmbeddedPiAgent(...)` 调用都会排**两次队**，而不是一次：

```
sessionLane = resolveSessionLane(sessionKey)  → "session:user-abc"（同会话串行）
globalLane  = resolveGlobalLane(params.lane)  → CommandLane.Main（全局限流）

执行：enqueue(sessionLane, () => enqueue(globalLane, task))
```

这就是"局部有序 + 全局限流"的本质。Session Lane 保证同一会话的消息不会并发处理，Global Lane 则控制整个进程的并发上限。

---

## 三种内置 Lane 类型

OpenClaw 源码中定义了三个 `CommandLane` 命名常量，对应三种任务类型：

### 1. `main` — 主通道（入站消息）

**用途**：处理所有来自用户的入站消息（WhatsApp、Telegram、Slack、Discord、Signal、iMessage 等）。

**默认并发数**：4（即最多同时处理 4 个不同会话的消息）。

**配置方式**：
```json
{
  "agents": {
    "defaults": {
      "maxConcurrent": 4
    }
  }
}
```

**触发条件**：用户在任意接入渠道发送消息时自动触发。

---

### 2. `cron` — 定时任务通道

**用途**：运行 Gateway 内置调度器触发的定时任务，与入站消息完全隔离，不会阻塞用户的正常对话。

**默认并发数**：1（定时任务默认串行执行）。

**配置方式**：
```json
{
  "cron": {
    "maxConcurrentRuns": 1
  }
}
```

**触发条件**：由 `openclaw cron add` 创建的定时任务在预定时间触发。

Cron 任务有两种执行模式：

- **主会话模式**（`sessionTarget: "main"`）：将系统事件入队，等待下一次心跳时在主会话上下文中运行。适合需要访问主会话记忆的任务。
- **隔离模式**（`sessionTarget: "isolated"`）：在独立的 `cron:<jobId>` 会话中运行，每次都是全新会话，不污染主聊天记录。适合"后台杂务"类任务。

```bash
# 创建一个每天早上 7 点运行的隔离定时任务
openclaw cron add \
  --name "Morning brief" \
  --cron "0 7 * * *" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --message "总结昨日未读消息和待办事项" \
  --announce \
  --channel telegram \
  --to "-1001234567890"
```

---

### 3. `subagent` — 子智能体通道

**用途**：运行由主 Agent 派生的子 Agent 任务，实现并行工作而不阻塞主会话的入站回复。

**默认并发数**：8（子 Agent 可以高度并行）。

**触发条件**：主 Agent 在处理任务时调用子 Agent 工具（如 `agent_send`、`subagent` 工具调用）时自动触发。

子 Agent 的核心价值在于：将"研究/长任务/慢工具"类工作并行化，同时保持会话隔离（独立 session + 可选沙箱）。

---

## 并发配置全景

三种 Lane 的并发数统一在 `applyGatewayLaneConcurrency` 中配置：

```json
{
  "agents": {
    "defaults": {
      "maxConcurrent": 4
    },
    "subagent": {
      "maxConcurrent": 8
    }
  },
  "cron": {
    "maxConcurrentRuns": 1
  }
}
```

| Lane | 默认并发 | 配置字段 |
|------|----------|----------|
| `main` | 4 | `agents.defaults.maxConcurrent` |
| `subagent` | 8 | `agents.subagent.maxConcurrent` |
| `cron` | 1 | `cron.maxConcurrentRuns` |

---

## Lane 名称解析规则（源码级）

Lane 名称由源码中的两个函数决定：

```typescript
// 会话级 Lane：保证同一会话串行
function resolveSessionLane(key: string) {
  const cleaned = key.trim() || CommandLane.Main;
  // 幂等：已有 "session:" 前缀则不再加
  return cleaned.startsWith("session:") ? cleaned : `session:${cleaned}`;
}

// 全局 Lane：控制整体并发
function resolveGlobalLane(lane?: string) {
  const cleaned = lane?.trim();
  // 空值默认走 Main lane
  return cleaned ? cleaned : CommandLane.Main;
}
```

**特殊情况 — Probe Lane**：以 `auth-probe:` 或 `session:probe-` 开头的 Lane 是探针通道，任务失败时不打错误日志，因为探针本来就是试错用的。

---

## Channel 与 Lane 的关系

Channel 和 Lane 是两个不同层次的概念，容易混淆：

- **Channel（渠道）**：消息的来源平台，如 `telegram`、`discord`、`slack`、`whatsapp` 等。Channel 决定消息从哪里来、回复发到哪里去。
- **Lane（通道）**：任务的执行队列类型，决定任务在哪个并发池里运行。

一条来自 Telegram 的消息，会经过 Channel 路由找到对应的 Agent，然后进入 `main` Lane 的队列等待执行。一条 Telegram 消息进入的是 `main` Lane，而不是 `telegram` Lane。

---

## Channel 路由机制

OpenClaw 的路由是**确定性的**，模型不参与路由决策，完全由配置控制。

**路由优先级**（从高到低）：

1. 精确 peer 匹配（`bindings` 中配置了 `peer.kind` + `peer.id`）
2. 父 peer 匹配（线程继承）
3. Guild + roles 匹配（Discord）
4. Guild 匹配（Discord）
5. Team 匹配（Slack）
6. Account 匹配（`accountId`）
7. Channel 匹配（该渠道的任意账号）
8. 默认 Agent（`agents.list[].default`，否则第一个，最终回退到 `main`）

**Session Key 的形状**：

```
# 私信（DM）→ 合并到 Agent 的主会话
agent:<agentId>:<mainKey>          # 例：agent:main:main

# 群组 → 每个群独立会话
agent:<agentId>:<channel>:group:<id>

# 频道/房间
agent:<agentId>:<channel>:channel:<id>

# 线程（Slack/Discord）
agent:<agentId>:<channel>:channel:<id>:thread:<threadId>

# Telegram 论坛话题
agent:<agentId>:telegram:group:-1001234567890:topic:42
```

**多 Agent 路由配置示例**：

```json
{
  "agents": {
    "list": [
      { "id": "support", "name": "客服 Agent", "workspace": "~/.openclaw/workspace-support" },
      { "id": "coder", "name": "编程 Agent", "workspace": "~/.openclaw/workspace-coder" }
    ]
  },
  "bindings": [
    { "match": { "channel": "slack", "teamId": "T123" }, "agentId": "support" },
    { "match": { "channel": "telegram", "peer": { "kind": "group", "id": "-100123" } }, "agentId": "coder" }
  ]
}
```

**广播组**（同一消息触发多个 Agent）：

```json
{
  "broadcast": {
    "strategy": "parallel",
    "-1001234567890@g.us": ["alfred", "logger"]
  }
}
```

---

## 常见误区

**误区一：以为 Channel 就是 Lane**。Channel 是消息来源（Telegram/Discord），Lane 是执行队列（main/cron/subagent）。

**误区二：以为 Cron 任务会阻塞用户对话**。Cron 任务运行在独立的 `cron` Lane，与 `main` Lane 完全隔离，不会影响用户的正常对话响应速度。

**误区三：以为子 Agent 和主 Agent 共享会话**。子 Agent 默认在独立 session 中运行，不会污染主会话的对话历史。

---

## 参考来源

- [OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)
- [OpenClaw 官方文档 - 定时任务](https://docs.openclaw.ai/zh-CN/automation/cron-jobs)
- [OpenClaw 官方文档 - Channel Routing](https://docs.openclaw.ai/channels/channel-routing)
- [OpenClaw 中文文档 - 并发队列与 Session-Lane 模型（源码级）](https://openclaw-docs.dx3n.cn/beginner-openclaw-guide/15-%E5%B9%B6%E5%8F%91%E9%98%9F%E5%88%97%E4%B8%8ESession-Lane%E6%A8%A1%E5%9E%8B)
