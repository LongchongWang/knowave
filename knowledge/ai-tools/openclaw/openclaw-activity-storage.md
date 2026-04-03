# OpenClaw 各类活动信息的存储位置

> 整理日期：2026-03-25  
> 来源：[OpenClaw 中文文档 - Cron 定时任务](https://openclaw-docs.dx3n.cn/tutorials/automation/cron-jobs)、[Hooks 事件系统](https://openclaw-docs.dx3n.cn/tutorials/automation/hooks)、[智能体循环](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-loop)、[在线状态](https://openclaw-docs.dx3n.cn/tutorials/concepts/presence)、[技能系统](https://openclaw-docs.dx3n.cn/tutorials/tools/skills)、[插件系统](https://openclaw-docs.dx3n.cn/tutorials/tools/plugin)、[智能体工作区](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-workspace)

---

## 一、Cron 定时任务

### 配置存储

Cron 任务的定义写在全局配置文件中，不是独立文件：

```
~/.openclaw/openclaw.json   # cron.jobs 数组，定义所有定时任务
```

配置结构示例：

```json5
{
  cron: {
    timezone: "Asia/Shanghai",
    jobs: [
      {
        schedule: "0 9 * * 1-5",
        agent: "daily-summary",
        message: "生成今日工作总结",
        isolated: false,          // false=复用主会话，true=每次新建会话
        model: "claude-opus-4-6", // 可选：覆盖默认模型
        delivery: {               // 可选：执行结果投递目标
          channel: "slack",
          target: "#daily-reports"
        }
      }
    ]
  }
}
```

### 运行时状态存储

Cron 的执行历史和当前状态保存在本地：

```
~/.openclaw/cron/
├── history.json    # 执行历史记录（每次触发的时间、结果）
└── state.json      # 当前任务状态（下次执行时间、暂停/运行状态）
```

### 常用 CLI

```bash
openclaw cron list              # 查看所有任务及下次执行时间
openclaw cron history --limit 20  # 查看执行历史
openclaw cron run <job-name>    # 手动触发
openclaw cron pause <job-name>  # 暂停
openclaw cron resume <job-name> # 恢复
```

**注意**：2026.3.8 版本后，Cron 任务不再支持通过"即时 Agent"发送通知。如果从旧版迁移，需运行 `openclaw doctor --fix`。

---

## 二、Agent 活动信息

### 2.1 工具调用记录

工具调用不单独存储，而是作为对话轮次的一部分写入会话 JSONL 文件：

```
~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl
```

每个 `.jsonl` 文件记录完整的对话历史，包括用户消息、AI 回复、工具调用请求和工具返回结果。工具调用在写入前会对大小和图像负载进行清理。

### 2.2 任务执行状态（实时）

Agent 执行过程中的实时状态**不持久化到磁盘**，而是通过 Gateway 的事件流（WebSocket）实时广播：

- `lifecycle` 流：`phase: "start" | "end" | "error"`，标记一次 Agent 运行的开始和结束
- `assistant` 流：模型输出的流式增量
- `tool` 流：工具调用的 start/update/end 事件

这意味着：**如果没有客户端订阅，这些实时事件不会被保留**。要持久化工具调用审计日志，需要通过 Hooks 机制自行实现（见下文）。

### 2.3 当前活跃状态（Presence）

Agent 的在线状态存储在 **Gateway 内存**中，不写入磁盘：

```
内存映射（presence key → 条目）
TTL: 5 分钟后自动清除
最大条目数: 200
```

在线状态条目包含：`instanceId`、`host`、`ip`、`version`、`mode`（ui/webchat/cli/backend 等）、`lastInputSeconds`、`ts`（最后更新时间戳）。

查询方式：对 Gateway 调用 `system-presence` RPC，或在 macOS 应用的 Instances 标签页查看。

### 2.4 用量跟踪

Token 用量和成本信息通过以下方式查看，但**不单独存储为独立文件**：

- 会话 JSONL 文件中包含每轮的用量元数据
- `/usage cost` 命令从会话日志聚合本地成本摘要
- `/status` 命令显示当前会话 Token 和估算成本

### 2.5 通过 Hooks 实现工具调用审计

如果需要持久化工具调用日志，可以在 `~/.openclaw/hooks/` 下创建 Hook 脚本：

```bash
# ~/.openclaw/hooks/tool-called
#!/bin/bash
TOOL_NAME="${OPENCLAW_TOOL_NAME}"
AGENT_ID="${OPENCLAW_AGENT_ID}"
SESSION_ID="${OPENCLAW_SESSION_ID}"
echo "[$(date)] Agent=$AGENT_ID Tool=$TOOL_NAME Session=$SESSION_ID" \
  >> ~/.openclaw/logs/tool-audit.log
```

---

## 三、Skills（技能）

### 技能文件存储

技能以目录形式存储，按优先级从低到高：

```
~/.openclaw/skills/                    # 全局技能（对所有 Agent 生效）
├── code-review/
│   └── SKILL.md                       # 技能定义（唯一必需文件）
└── git-workflow/
    └── SKILL.md

{工作区}/.openclaw/skills/             # 工作区技能（覆盖全局同名技能）
└── project-specific/
    └── SKILL.md

{工作区}/skills/                       # 工作区根目录下的 skills 目录（同上）
```

每个技能是一个独立目录，目录名即为技能的唯一标识符，`SKILL.md` 是唯一必需的文件。

### 技能配置

技能的启用/禁用、Gate 规则、Agent 绑定等配置写在全局配置文件中：

```
~/.openclaw/openclaw.json   # skills 字段
```

```json5
{
  skills: {
    "code-review": {
      enabled: true,
      agents: ["dev-assistant"],  // 不填则对所有 Agent 生效
      gate: {
        keywords: ["review", "检查代码"]  // 按需激活，节省 Token
      }
    }
  }
}
```

### 技能生命周期

技能在 Agent 启动时扫描加载，注入到系统提示词中。运行时不单独存储状态，技能是否激活由 Gate 规则在每次请求时判断。

```bash
openclaw skills list                    # 查看已加载的技能
openclaw skills show <skill-name>       # 查看技能内容
openclaw skills validate <path>         # 验证技能文件格式
openclaw skills install clawhub/<name>  # 从 ClawHub 安装
```

---

## 四、插件（Plugins）

### 插件文件存储

插件按优先级从高到低存储在以下位置：

```
.openclaw/plugins/          # 项目级插件（最高优先级）
~/.openclaw/plugins/        # 用户级插件
/etc/openclaw/plugins/      # 系统级插件
ClawHub 注册表              # 官方插件（最低优先级）
```

插件 ID 格式：`<作者>/<插件名>[@版本]`，例如 `openclaw/firecrawl@2.1.0`。

### 插件配置

插件配置写在全局配置文件中：

```
~/.openclaw/openclaw.json   # plugins 字段
```

```json5
{
  plugins: {
    "firecrawl": {
      apiKey: "${FIRECRAWL_API_KEY}",
      stealth: true
    },
    "lobster": {
      maxParallelSteps: 5
    }
  }
}
```

### 官方内置插件

| 插件名 | 功能 |
|--------|------|
| `lobster` | 工作流运行时 |
| `firecrawl` | 高级网页抓取 |
| `clawhub` | 技能包市场客户端 |
| `reactions` | 消息表情回应 |
| `thinking` | 扩展思考模式 |

### 插件管理 CLI

```bash
openclaw plugins list                    # 查看已安装插件
openclaw plugins install <插件名>        # 安装插件
openclaw plugins enable/disable <插件名> # 启用/禁用
openclaw plugins uninstall <插件名>      # 卸载
```

---

## 五、Hooks（事件钩子）

Hooks 是连接各类活动信息的桥梁，可以在关键事件发生时执行自定义脚本。

### Hook 脚本存储

```
~/.openclaw/hooks/          # 全局 Hook（对所有项目生效）
.openclaw/hooks/            # 项目级 Hook（优先级更高）
```

文件名即事件名，例如文件名 `tool-called` 对应工具调用事件。

### 支持的事件

| 事件名 | 触发时机 |
|--------|----------|
| `session-started` / `session-ended` | 会话开始/结束 |
| `message-received` / `model-response` | 消息收发 |
| `agent-started` / `agent-finished` | Agent 执行开始/完成 |
| `tool-called` / `tool-result` | 工具调用前/后 |
| `cron-started` | Cron 任务开始 |
| `heartbeat` | 每个心跳间隔 |

Hook 脚本通过环境变量接收上下文（`OPENCLAW_TOOL_NAME`、`OPENCLAW_AGENT_ID`、`OPENCLAW_SESSION_ID` 等）。

---

## 六、全局存储路径汇总

| 活动类型 | 存储路径 | 格式 | 持久化 |
|----------|----------|------|--------|
| Cron 任务定义 | `~/.openclaw/openclaw.json` (cron.jobs) | JSON5 | ✅ |
| Cron 执行历史 | `~/.openclaw/cron/history.json` | JSON | ✅ |
| Cron 任务状态 | `~/.openclaw/cron/state.json` | JSON | ✅ |
| Agent 对话记录（含工具调用） | `~/.openclaw/agents/<agentId>/sessions/<SessionId>.jsonl` | JSONL | ✅ |
| Agent 实时执行状态 | Gateway 内存（WebSocket 事件流） | 内存 | ❌ |
| Agent 在线状态（Presence） | Gateway 内存（TTL 5 分钟） | 内存 | ❌ |
| Skills 文件 | `~/.openclaw/skills/<skill-name>/SKILL.md` | Markdown | ✅ |
| Skills 配置 | `~/.openclaw/openclaw.json` (skills) | JSON5 | ✅ |
| 插件文件 | `~/.openclaw/plugins/` | 各异 | ✅ |
| 插件配置 | `~/.openclaw/openclaw.json` (plugins) | JSON5 | ✅ |
| Hooks 脚本 | `~/.openclaw/hooks/` | 可执行脚本 | ✅ |
| 工具调用审计日志 | 需自行通过 Hook 写入（如 `~/.openclaw/logs/`） | 自定义 | 可选 |

---

## 七、关键设计理解

**实时活动 vs 持久化活动**：OpenClaw 的设计哲学是"Gateway 是事实来源"。Agent 的实时执行状态（当前在跑什么工具、当前活跃状态）存在 Gateway 内存中，通过 WebSocket 事件流实时广播，不写磁盘。只有对话历史（JSONL）和 Cron 历史（JSON）才持久化到磁盘。

**想要持久化实时活动**：必须通过 Hooks 机制自行实现。在 `~/.openclaw/hooks/tool-called` 等脚本中，将环境变量里的上下文信息写入自定义日志文件。

**配置的统一入口**：Cron、Skills、Plugins、Hooks 的配置都集中在 `~/.openclaw/openclaw.json` 这一个文件中，热重载支持（修改后无需重启 Gateway）。

---

## 参考资料

- [Cron 定时任务](https://openclaw-docs.dx3n.cn/tutorials/automation/cron-jobs)
- [Hooks 事件系统](https://openclaw-docs.dx3n.cn/tutorials/automation/hooks)
- [智能体循环（Agent Loop）](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-loop)
- [在线状态（Presence）](https://openclaw-docs.dx3n.cn/tutorials/concepts/presence)
- [技能系统（Skills）](https://openclaw-docs.dx3n.cn/tutorials/tools/skills)
- [创建自定义技能](https://openclaw-docs.dx3n.cn/tutorials/tools/creating-skills)
- [插件系统（Plugin System）](https://openclaw-docs.dx3n.cn/tutorials/tools/plugin)
- [智能体工作区（Agent Workspace）](https://openclaw-docs.dx3n.cn/tutorials/concepts/agent-workspace)
- [用量跟踪（Usage Tracking）](https://openclaw-docs.dx3n.cn/tutorials/concepts/usage-tracking)
