# OpenClaw 队列模式（Queue Mode）

> 整理日期：2026-03-29  
> 来源：[OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)

---

## 队列模式是什么

当多条消息同时到达同一会话时，OpenClaw 需要决定：是等 AI 跑完当前轮次再处理新消息，还是立刻打断它？是把多条消息合并成一个提示，还是逐条处理？这就是队列模式（Queue Mode）要解决的问题。

队列模式只作用于 `main` Lane（入站消息），通过 `messages.queue.mode` 配置。

---

## 五种模式

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `collect`（默认） | 将所有排队消息合并为**单个**后续轮次 | 防止"继续、继续"式刷屏 |
| `followup` | 在当前运行结束后为下一个轮次入队，逐条处理 | 保证每条消息都被单独响应 |
| `steer` | 立即注入当前运行（在下一个工具边界后取消待处理的工具调用） | 需要实时打断 AI 的场景 |
| `steer-backlog` | 现在引导**并**保留消息用于后续轮次 | 既要打断又不想丢失后续消息 |
| `interrupt`（旧版） | 中止该会话的活动运行，然后运行最新消息 | 强制重置，已不推荐 |

`queue` 是 `steer` 的旧版别名，两者等价。

**关于 `steer-backlog` 的注意**：它会在被引导的运行之后产生一个后续响应，流式传输界面可能看起来像重复输出。如果希望每条消息只有一个响应，优先用 `collect` 或 `steer`。

**关于 `steer` 的回退**：`steer` 要求 AI 正处于流式输出状态才能生效。如果 AI 当前没有在流式传输，`steer` 会自动降级为 `followup` 行为，这个回退与渠道无关。

---

## 队列选项

`followup`、`collect`、`steer-backlog` 三种模式（以及 `steer` 回退到 followup 时）支持以下附加选项：

| 选项 | 含义 | 默认值 |
|------|------|--------|
| `debounceMs` | 开始后续轮次前等待静默的毫秒数，防止"继续继续"连发 | `1000` |
| `cap` | 每个会话最多缓存的消息条数 | `20` |
| `drop` | 超出 `cap` 时的溢出策略 | `summarize` |

`drop` 的三种策略：
- `old`：丢弃最早的消息
- `new`：丢弃最新的消息
- `summarize`：把被丢弃的消息提炼成简短要点，作为合成提示注入到下一轮次

---

## 三级配置优先级

队列模式支持三个粒度的配置，优先级从高到低：

```
会话级覆盖（/queue 命令，持久化到该 session）
    ↓
byChannel 渠道级配置（配置文件静态设置）
    ↓
全局 mode（配置文件静态设置）
    ↓
默认值（collect）
```

### 全局 + 按渠道配置

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

`byChannel` 中的渠道级配置会覆盖全局 `mode`，未列出的渠道使用全局值。

### 按渠道特性选择模式

| 渠道特性 | 推荐模式 | 原因 |
|----------|----------|------|
| 群聊/频道（Discord、Slack 频道） | `collect` | 多人快速发言，合并处理避免刷屏 |
| 私聊（Telegram DM、WhatsApp） | `followup` 或 `collect` | 一问一答节奏，`followup` 保证每条都被处理 |
| 实时协作场景 | `steer` | 需要随时打断 AI 调整方向 |
| 自动化/Bot 推送 | `collect` | 防止重复触发，合并批量事件 |

---

## 同渠道不同 Session 设置不同模式

`byChannel` 只能做到渠道粒度，无法为同一渠道下的不同群/频道/私聊单独预配置。但可以在对话中发送 `/queue` 命令，设置会被持久化到当前 session，只影响这一个 session，同渠道的其他 session 完全不受影响。

**`/queue` 命令真实场景举例**：

场景一：Telegram 某个群聊需要逐条处理，不合并消息（全局是 `collect`）

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

场景四：某个 WhatsApp 私聊临时切换为打断模式，用完后恢复默认

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

## `collect` 模式的跨渠道路由保留

`collect` 模式有一个重要细节：当排队的消息来自**不同渠道或不同线程**时，它们不会被合并成一个轮次，而是**分别单独排空**，以保留各自的路由信息。

举个例子：同一个 Agent 同时收到来自 Telegram 私聊和 Discord 频道的消息，即使都在 `collect` 模式下，这两条消息也会分开处理，回复分别发回各自的来源渠道，不会混淆。只有来自**同一渠道同一会话**的多条消息才会被合并。

---

## 常见误区

**误区：以为 `steer` 模式总是最好的**。`steer` 会取消正在进行的工具调用，可能导致任务中断。对于大多数场景，`collect`（默认）更安全。

---

## 参考来源

- [OpenClaw 官方文档 - 命令队列](https://docs.openclaw.ai/zh-CN/concepts/queue)
