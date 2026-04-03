# OpenClaw 技术架构与跨 Session 共享机制

> 整理日期：2026-03-24  
> 来源：[OpenClaw 中文文档 - 系统架构详解](https://openclaw-docs.dx3n.cn/tutorials/concepts/system-architecture)、[会话管理](https://openclaw-docs.dx3n.cn/tutorials/concepts/session)、[记忆](https://openclaw-docs.dx3n.cn/tutorials/concepts/memory)、[智能体工作区](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-workspace)、[多智能体路由](https://openclaw-docs.dx3n.cn/tutorials/concepts/multi-agent)

---

## 一、OpenClaw 是什么

OpenClaw 是一个**本地优先的多通道 AI 助手运行时**，跑在用户自己的设备上（笔记本、云服务器、Mac Mini 等）。它把 AI 模型（Claude、GPT、Ollama 等）和各种工具连接到日常聊天 App（Telegram、WhatsApp、Discord、飞书等），核心设计哲学是"把 AI 助手当作基础设施来构建"，而不只是优化提示词。

2025 年 11 月创建，4 个月内 GitHub Star 数突破 26 万，是 GitHub 历史上增长最快的非聚合类软件项目之一。

---

## 二、整体架构分层

OpenClaw 采用六层架构，从上到下依次是：

```
┌─────────────────────────────────────────────────────┐
│ CLI 层                                               │
│ entry.ts → run-main.ts → command-registry            │
├─────────────────────────────────────────────────────┤
│ Gateway 层（控制平面）                                │
│ WebSocket 服务 · HTTP 服务 · 通道管理 · 热重载        │
├──────────────┬──────────────┬────────────────────────┤
│ Channel 层   │ Routing 层   │ Plugin 层               │
│ 多通道适配   │ 路由 + 会话键 │ 工具/通道/Provider 注册  │
├──────────────┴──────────────┴────────────────────────┤
│ Auto-Reply / Agent 执行层                             │
│ dispatch → get-reply → agent-runner → embedded PI    │
├─────────────────────────────────────────────────────┤
│ AI Provider 层                                       │
│ Anthropic · OpenAI · Ollama · Bedrock · ...          │
├─────────────────────────────────────────────────────┤
│ 持久化 / 基础设施层                                   │
│ Config · Sessions · Media · Security · Cron          │
└─────────────────────────────────────────────────────┘
```

**Gateway 是整个系统的核心，必须常驻运行。** 它暴露两个接口：WebSocket（默认 `127.0.0.1:18789`，主控制协议）和 HTTP（同端口，用于 Hooks 回调、工具调用、Slack 等）。

---

## 三、Session（会话）机制

### 3.1 Session Key 是什么

Session Key 是 OpenClaw 中**并发隔离和持久化分区的核心**。每条入站消息都会被路由层计算出一个唯一的 Session Key，格式如下：

```
私聊（DM）：agent:{agentId}:{channel}:{accountId}:direct:{peerId}
群聊/频道：agent:{agentId}:{channel}:{accountId}:{peerKind}:{peerId}
```

Session Key 的作用有三个：同一会话消息串联（历史上下文）、并发队列按 session 隔离（Lane 机制）、存储文件按 session 定位。

### 3.2 Session 存储在哪里

会话记录存储在 Gateway 主机的本地文件系统上：

```
~/.openclaw/agents/<agentId>/sessions/sessions.json   # 索引（sessionKey → sessionId 映射）
~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl  # 每个会话的完整对话记录
```

每个 `.jsonl` 文件记录了所有对话轮次（用户消息 + AI 回复）。**网关是会话状态的唯一事实来源**，UI 客户端必须查询网关获取会话列表，而不是直接读取本地文件。

### 3.3 dmScope：控制 DM 会话如何分组

`session.dmScope` 是控制直接消息（DM）如何分组的关键配置，有四个选项：

- `main`（默认）：所有 DM 共享主会话，保持连续性。适合单用户场景。
- `per-peer`：按发送者 ID 跨通道隔离。
- `per-channel-peer`：按通道 + 发送者隔离。**推荐用于多用户收件箱。**
- `per-account-channel-peer`：按账户 + 通道 + 发送者隔离。**推荐用于多账户收件箱。**

**安全警告**：如果 Agent 可以接收来自多人的 DM，必须启用安全 DM 模式，否则所有用户共享同一对话上下文，可能导致私人信息泄露（Alice 说的话，Bob 能看到）。

```json5
// ~/.openclaw/openclaw.json
{
  session: {
    dmScope: "per-channel-peer",  // 安全 DM 模式
  },
}
```

### 3.4 Session 生命周期

- **每日重置**：默认网关主机本地时间凌晨 4:00 重置。
- **空闲重置**：可配置 `idleMinutes`，滑动空闲窗口。
- **手动重置**：发送 `/new` 或 `/reset` 命令，或直接删除 JSONL 文件。
- **会话修剪**：LLM 调用前自动修剪旧的工具结果（不重写 JSONL 历史）。
- **上下文压缩（Compaction）**：对话太长时自动压缩旧内容节省 Token。

---

## 四、跨 Session 共享能力的三种机制

这是 OpenClaw 架构中最关键的设计问题：**不同 session 之间如何共享信息和能力？**

### 4.1 Memory（记忆）：跨 Session 的持久化知识

Memory 是 OpenClaw 跨 session 共享信息的核心机制。**记忆的本质是智能体工作区中的纯 Markdown 文件**，这些文件是事实的来源，模型只"记得"写入磁盘的内容。

默认工作区布局使用两个记忆层：

```
~/.openclaw/workspace/
├── MEMORY.md              # 精选的长期记忆（仅在主私人会话中加载）
└── memory/
    ├── 2026-03-23.md      # 每日日志（仅追加）
    └── 2026-03-24.md
```

**写入时机**：
- 决策、偏好、持久性事实 → 写入 `MEMORY.md`
- 日常笔记、运行上下文 → 写入 `memory/YYYY-MM-DD.md`
- 用户说"记住这个" → 立即写入（不只保留在内存中）

**自动记忆刷新**：当会话接近自动压缩时，OpenClaw 会触发一个静默的 Agent 轮次，提醒模型在上下文被压缩之前把重要信息写入磁盘。

### 4.2 向量记忆搜索：语义检索跨 Session 知识

OpenClaw 在 `MEMORY.md` 和 `memory/*.md` 上构建向量索引，支持语义查询，即使措辞不同也能找到相关笔记。

**索引存储**：每 Agent 独立的 SQLite 数据库，位于：
```
~/.openclaw/memory/<agentId>.sqlite
```

**混合搜索（BM25 + 向量）**：
- 向量搜索：擅长语义匹配（"Mac Studio gateway host" vs "the machine running the gateway"）
- BM25 关键词搜索：擅长精确 Token（ID、代码符号、错误字符串）
- 两者结合，加权融合：`finalScore = vectorWeight * vectorScore + textWeight * textScore`

**高级后端 QMD**：可选启用 `memory.backend = "qmd"`，使用 BM25 + 向量 + 重排序的本地优先搜索，完全离线运行。

**会话记忆搜索（实验性）**：可选索引会话 JSONL 记录，让 `memory_search` 能召回最近的对话历史：
```json5
agents: {
  defaults: {
    memorySearch: {
      experimental: { sessionMemory: true },
      sources: ["memory", "sessions"]
    }
  }
}
```

### 4.3 Agent Workspace（工作区）：跨 Session 的共享上下文

工作区是 Agent 的主目录，每次会话开始时都会加载工作区中的标准文件，这是跨 session 共享"人设"和"规则"的机制：

| 文件 | 作用 | 加载时机 |
|------|------|----------|
| `AGENTS.md` | 操作指令、行为规则 | 每次会话开始 |
| `SOUL.md` | 人设、语调、边界 | 每次会话开始 |
| `USER.md` | 用户信息、称呼方式 | 每次会话开始 |
| `MEMORY.md` | 精选长期记忆 | 仅主私人会话 |
| `memory/YYYY-MM-DD.md` | 每日日志 | 今天 + 昨天 |

---

## 五、多 Agent 架构：跨 Session 的能力隔离与共享

### 5.1 Agent 是什么

一个 Agent 是一个完全作用域化的"大脑"，拥有自己的：
- **工作区**（文件、人设规则、本地笔记）
- **状态目录**（`~/.openclaw/agents/<agentId>/agent`，存放认证配置文件、模型注册表）
- **会话存储**（`~/.openclaw/agents/<agentId>/sessions`，聊天历史 + 路由状态）

**认证配置文件是每 Agent 独立的**，主 Agent 凭证不会自动共享。如果想共享凭证，需要手动复制 `auth-profiles.json`。

### 5.2 多 Agent 路由

一个 Gateway 可以托管多个 Agent 并行运行，通过 `bindings` 配置将入站消息路由到不同 Agent：

```json5
{
  agents: {
    list: [
      { id: "home", workspace: "~/.openclaw/workspace-home" },
      { id: "work", workspace: "~/.openclaw/workspace-work" },
    ],
  },
  bindings: [
    { agentId: "home", match: { channel: "whatsapp", peer: { kind: "direct", id: "+15551230001" } } },
    { agentId: "work", match: { channel: "telegram", peer: { kind: "direct", id: "123456" } } },
  ],
}
```

路由匹配优先级（从高到低）：peer 精确匹配 → parentPeer 继承 → guild + roles → guild → team → account → channel → 默认 Agent。

### 5.3 跨 Agent 共享技能（Skills）

技能（Skills）通过两个层级管理：
- **共享技能**：`~/.openclaw/skills/`，所有 Agent 共享
- **每 Agent 技能**：`~/.openclaw/workspace-<agentId>/skills/`，覆盖共享技能

### 5.4 identityLinks：跨通道合并同一用户的 Session

如果同一个人通过多个通道联系 Agent，可以用 `session.identityLinks` 将他们的 DM 会话合并到一个规范身份：

```json5
{
  session: {
    dmScope: "per-peer",
    identityLinks: {
      alice: ["telegram:123456789", "discord:987654321012345678"],
    },
  },
}
```

这样 Alice 无论从 Telegram 还是 Discord 发消息，都会进入同一个 session，AI 能记住跨通道的对话历史。

---

## 六、Lane 并发模型

Lane 是 OpenClaw 控制并发执行的机制，与 session 隔离直接相关：

```
每个 Session 独占一个 Session Lane（队列）
所有 Session 共享一个 Global Lane（全局并发控制）
```

当新消息到来时，有六种队列策略（QueueMode）：
- `interrupt`：中断当前 run，立即执行新消息
- `steer`：把新消息追加到当前 run 的上下文中继续执行
- `steer-backlog`：steer 的变体，同时保留待处理消息
- `followup`：等当前 run 结束后再执行
- `collect`：收集多条消息合并后再执行（防抖批处理）
- `queue`：普通排队，依序执行

---

## 七、持久化层总结

| 子系统 | 存储路径 | 格式 | 说明 |
|--------|----------|------|------|
| 配置 | `~/.openclaw/openclaw.json` | JSON5/TOML | 热重载支持 |
| 会话索引 | `~/.openclaw/agents/<agentId>/sessions/sessions.json` | JSON | sessionKey → sessionId 映射 |
| 会话记录 | `~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl` | JSONL | 完整对话轮次 |
| 记忆文件 | `~/.openclaw/workspace/MEMORY.md` + `memory/*.md` | Markdown | 纯文本，事实来源 |
| 向量索引 | `~/.openclaw/memory/<agentId>.sqlite` | SQLite | 嵌入向量 + BM25 索引 |
| 认证配置 | `~/.openclaw/agents/<agentId>/agent/auth-profiles.json` | JSON | 每 Agent 独立 |
| 媒体文件 | `~/.openclaw/media/` | 二进制 | 有 TTL 和安全校验 |

---

## 八、关键设计哲学

**纯文本存储革命**：记忆和配置都是纯文本文件（Markdown + JSON5），没有私有数据库格式，用户完全掌控数据，可以用 Git 备份、用任何编辑器修改。

**Gateway 是事实来源**：所有状态由 Gateway 拥有，UI 客户端只是视图层，这使得远程部署和多客户端访问成为可能。

**插件化扩展**：通道、工具、Provider、Hooks 均可通过插件注入，5 种注入点（channel / tool / provider / hook / http-route）覆盖了几乎所有扩展场景。

**本地优先**：数据存在用户自己的机器上，不依赖云服务，支持完全离线的 Ollama 模型。

---

## 参考资料

- [OpenClaw 系统架构详解](https://openclaw-docs.dx3n.cn/tutorials/concepts/system-architecture)
- [会话管理（Session Management）](https://openclaw-docs.dx3n.cn/tutorials/concepts/session)
- [会话（Sessions）](https://openclaw-docs.dx3n.cn/tutorials/concepts/sessions)
- [记忆（Memory）](https://openclaw-docs.dx3n.cn/tutorials/concepts/memory)
- [智能体工作区（Agent Workspace）](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-workspace)
- [多智能体路由](https://openclaw-docs.dx3n.cn/tutorials/concepts/multi-agent)
- [OpenClaw GitHub 组织](https://github.com/openclaw)
