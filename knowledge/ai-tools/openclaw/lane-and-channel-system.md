# OpenClaw Lane 任务通道与 Channel 管理机制

> 整理日期：2026-03-29  
> 来源：[OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)、[OpenClaw 官方文档 - 定时任务](https://docs.openclaw.ai/zh-CN/automation/cron-jobs)、[OpenClaw 官方文档 - Channel Routing](https://docs.openclaw.ai/channels/channel-routing)、[OpenClaw 中文文档 - 并发队列与 Session-Lane 模型](https://openclaw-docs.dx3n.cn/beginner-openclaw-guide/15-%E5%B9%B6%E5%8F%91%E9%98%9F%E5%88%97%E4%B8%8ESession-Lane%E6%A8%A1%E5%9E%8B)

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

## Lane 名称解析规则

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

## 队列模式（消息如何排队）

当多条消息同时到达同一会话时，OpenClaw 提供多种排队策略，通过 `messages.queue.mode` 配置：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `collect`（默认） | 将所有排队消息合并为**单个**后续轮次 | 防止"继续、继续"式刷屏 |
| `steer` | 立即注入当前运行（在下一个工具边界后取消待处理的工具调用） | 需要实时打断 AI 的场景 |
| `followup` | 在当前运行结束后为下一个轮次入队 | 顺序处理每条消息 |
| `steer-backlog` | 现在引导**并**保留消息用于后续轮次 | 既要打断又要保留上下文 |
| `interrupt`（旧版） | 中止该会话的活动运行，然后运行最新消息 | 强制重置 |

### 队列模式与 Channel 的关系

队列模式和 Channel 在两个维度上产生交叉：**按渠道差异化配置**，以及**跨渠道消息的路由保留**。

**一、`byChannel`：为不同渠道设置不同的队列模式**

队列模式可以全局设置，也可以针对特定渠道单独覆盖。这是因为不同渠道的使用场景差异很大——Discord 频道里用户可能快速连发多条消息，而 Telegram 私聊则更像一问一答。

```json
{
  "messages": {
    "queue": {
      "mode": "collect",
      "debounceMs": 1000,
      "cap": 20,
      "drop": "summarize",
      "byChannel": {
        "discord": "collect",
        "telegram": "followup",
        "slack": "steer"
      }
    }
  }
}
```

优先级规则：`byChannel` 中的渠道级配置 > 全局 `mode`。也就是说，上面的配置里，Discord 用 `collect`，Telegram 用 `followup`，Slack 用 `steer`，其余渠道都用全局的 `collect`。

**二、`collect` 模式的跨渠道路由保留**

`collect` 模式有一个重要的细节：当排队的消息来自**不同渠道或不同线程**时，它们不会被合并成一个轮次，而是**分别单独排空**，以保留各自的路由信息。

举个例子：同一个 Agent 同时收到来自 Telegram 私聊和 Discord 频道的消息，即使都在 `collect` 模式下，这两条消息也会分开处理，回复分别发回各自的来源渠道，不会混淆。只有来自**同一渠道同一会话**的多条消息才会被合并。

**三、`steer` 模式的渠道感知回退**

`steer` 模式在 AI 当前没有处于流式输出状态时，会自动回退到 `followup` 行为。这个回退是渠道无关的——无论消息来自哪个渠道，只要 AI 不在流式传输，`steer` 就等同于 `followup`。

**四、按渠道特性选择队列模式的建议**

| 渠道特性 | 推荐模式 | 原因 |
|----------|----------|------|
| 群聊/频道（Discord、Slack 频道） | `collect` | 多人快速发言，合并处理避免刷屏 |
| 私聊（Telegram DM、WhatsApp） | `followup` 或 `collect` | 一问一答节奏，`followup` 保证每条都被处理 |
| 实时协作场景 | `steer` | 需要随时打断 AI 调整方向 |
| 自动化/Bot 场景 | `collect` | 防止重复触发，合并批量事件 |

**五、同渠道不同 Session 设置不同队列模式**

配置文件（`byChannel`）只能做到渠道粒度，无法为同一渠道下的不同群/频道/私聊单独预配置。但 OpenClaw 提供了运行时的**会话级覆盖**机制来弥补这个缺口：在对话中发送 `/queue` 命令，设置会被持久化到当前 session，只影响这一个 session，同渠道的其他 session 完全不受影响。

完整优先级从高到低：

```
会话级覆盖（/queue 命令，持久化到该 session）
    ↓
byChannel 渠道级配置（配置文件静态设置）
    ↓
全局 mode（配置文件静态设置）
    ↓
默认值（collect）
```

**`/queue` 命令真实场景举例**：

场景一：Telegram 群聊 A 需要逐条处理，不合并消息（全局是 `collect`）

```
/queue followup
```

发送后，这个群聊的所有后续消息都会逐条排队处理，不再合并。其他 Telegram 群聊不受影响。

---

场景二：Discord 某个频道正在进行实时代码 Review，需要随时打断 AI

```
/queue steer
```

AI 正在输出时，新消息会在下一个工具边界处注入并取消当前工具调用，立即响应新指令。

---

场景三：某个 Slack 频道是自动化 Bot 推送，消息量大，希望合并处理并延迟 3 秒等待批量到达

```
/queue collect debounce:3s cap:50 drop:summarize
```

等待 3 秒静默后才开始处理，最多缓存 50 条，超出时把被丢弃的消息摘要注入到提示词里。

---

场景四：某个 WhatsApp 私聊临时需要打断模式，用完后恢复默认

```
/queue steer
# ... 用完后 ...
/queue default
```

`/queue default` 或 `/queue reset` 会清除该 session 的覆盖，回退到 `byChannel` 或全局配置。

---

场景五：查看当前 session 的队列模式（确认是否生效）

```
/queue
```

不带参数发送 `/queue`，会显示当前 session 的队列模式及来源（session 覆盖 / 渠道配置 / 全局默认）。

---

**注意**：`/queue` 命令只能在对话中手动触发，无法在配置文件里预先为某个特定 session 静态设置。如果需要在部署时就为某个特定群/频道设置不同模式，只能用 `byChannel` 在渠道粒度上配置。

---

## Channel（渠道）与 Lane 的关系

Channel 和 Lane 是两个不同层次的概念，容易混淆：

- **Channel（渠道）**：消息的来源平台，如 `telegram`、`discord`、`slack`、`whatsapp` 等。Channel 决定消息从哪里来、回复发到哪里去。
- **Lane（通道）**：任务的执行队列类型，决定任务在哪个并发池里运行。

一条来自 Telegram 的消息，会经过 Channel 路由找到对应的 Agent，然后进入 `main` Lane 的队列等待执行。

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

## 常见误区

**误区一：以为 Channel 就是 Lane**。Channel 是消息来源（Telegram/Discord），Lane 是执行队列（main/cron/subagent）。一条 Telegram 消息进入的是 `main` Lane，而不是 `telegram` Lane。

**误区二：以为 Cron 任务会阻塞用户对话**。Cron 任务运行在独立的 `cron` Lane，与 `main` Lane 完全隔离，不会影响用户的正常对话响应速度。

**误区三：以为子 Agent 和主 Agent 共享会话**。子 Agent 默认在独立 session 中运行，不会污染主会话的对话历史。

**误区四：以为 `steer` 模式总是最好的**。`steer` 会取消正在进行的工具调用，可能导致任务中断。对于大多数场景，`collect`（默认）更安全。

---

## 参考来源

- [OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)
- [OpenClaw 官方文档 - 定时任务](https://docs.openclaw.ai/zh-CN/automation/cron-jobs)
- [OpenClaw 官方文档 - Channel Routing](https://docs.openclaw.ai/channels/channel-routing)
- [OpenClaw 中文文档 - 并发队列与 Session-Lane 模型（源码级）](https://openclaw-docs.dx3n.cn/beginner-openclaw-guide/15-%E5%B9%B6%E5%8F%91%E9%98%9F%E5%88%97%E4%B8%8ESession-Lane%E6%A8%A1%E5%9E%8B)
