# OpenClaw `flows` 命令与 TaskFlow 底层实现

> 整理日期：2026-04-03  
> 参考来源：[官方文档 docs.openclaw.ai/automation/taskflow](https://docs.openclaw.ai/automation/taskflow)、[GitHub openclaw/openclaw](https://github.com/openclaw/openclaw)、[源码分析文章 shuwoom.com](https://shuwoom.com/post/openclaw-任务编排与调度系统架构深度解析/)

---

## 一、先搞清楚命名混乱

`openclaw flows` 这个命令在不同版本的文档里有两种形态，容易让人困惑：

**旧形态（v2026.3.31 之前的某些 fork/镜像文档）**：`openclaw flows` 是一个独立的顶级命令，直接操作 ClawFlow 作业。

**当前官方形态（v2026.3.31 起）**：`openclaw flows` 作为独立命令已被重定向，官方文档 `docs/cli/flows.md` 的 frontmatter 明确写着：

```
summary: "Redirect: flow commands live under `openclaw tasks flow`"
```

也就是说，**现在正确的命令是 `openclaw tasks flow`**，它是 `openclaw tasks` 的子命令组，而不是独立命令。

不过在 v2026.4.2 的 Release Notes 里，又出现了 `openclaw flows` 的表述（"restore the core Task Flow substrate with `openclaw flows` inspection/recovery primitives"），说明这个命令面在最新版本里可能以某种形式并存。实际使用时以 `openclaw tasks flow` 为准，`openclaw flows` 可能是别名或兼容入口。

---

## 二、`openclaw tasks flow` 命令参考

```bash
# 列出所有活跃和近期的 flow
openclaw tasks flow list

# 查看某个 flow 的详情（支持 flow id 或 owner session key 作为 lookup）
openclaw tasks flow show <lookup>

# 取消一个 flow 及其所有活跃子任务
openclaw tasks flow cancel <lookup>
```

### `tasks flow list`

列出被追踪的 flow，显示状态和同步模式。支持 `--json` 输出。

### `tasks flow show <lookup>`

`<lookup>` 接受 flow id 或 owner session key。输出包含：

- flow 状态（active / waiting / blocked / finished / failed / cancelled）
- 当前步骤（currentStep）
- 等待目标（waitTarget）——如果处于等待状态
- 阻塞摘要（blockedSummary）——如果处于阻塞状态
- 已存储的输出键（stored output keys）
- 关联的 task 列表

### `tasks flow cancel <lookup>`

取消 flow 本身，同时终止所有活跃的子任务（对于 ACP/subagent 类型的任务，会 kill 对应的子 session）。

---

## 三、TaskFlow 是什么，解决了什么问题

TaskFlow（在源码和部分文档里也叫 ClawFlow）是 OpenClaw 在 **v2026.3.31** 引入的**流程编排基底（Runtime Substrate）**，位于 Background Tasks 之上。

### 它解决的四个核心问题

**问题 1：所有者上下文丢失**

任务被分离到后台运行后，完成时不知道把结果发回哪个 session。ClawFlow 通过 `ownerSessionKey` 保持返回通道，任务完成后自动路由回正确的会话。

**问题 2：多步骤任务缺乏关联**

复杂任务往往需要多个步骤，但这些步骤看起来是孤立的 Task 记录，无法知道它们属于同一个"作业"，也无法整体取消或查看整体进度。ClawFlow 把相关任务组织成一个 Flow，支持输出传递和整体控制。

**问题 3：等待状态不透明**

长时间运行的任务在等待子任务或外部事件时，系统只显示"运行中"，运维人员无法判断是卡住了还是正常等待。ClawFlow 引入显式的 `waitTarget` 字段，清晰记录在等待什么。

**问题 4：阻塞状态无法持久化**

任务因权限、配额等原因被阻塞时，重启后阻塞原因丢失。ClawFlow 将 `blocked` 状态和 `blockedSummary` 持久化到 SQLite，支持干净重试。

---

## 四、核心数据结构

```typescript
type Flow = {
  flowId: string;                    // 流程唯一标识
  ownerSessionKey: string;           // 所有者会话键（返回上下文）
  goal?: string;                     // 流程目标描述
  currentStep?: string;              // 当前步骤
  status: FlowStatus;                // 流程状态
  waitTarget?: string;               // 等待目标（等待中的任务或事件）
  outputs?: Record<string, unknown>; // 步骤间传递的小型输出
  blockedSummary?: string;           // 阻塞原因（如有）
  createdAt: number;
  updatedAt: number;
};

type FlowStatus =
  | "active"     // 活跃中
  | "waiting"    // 等待中（等待子任务或外部事件）
  | "blocked"    // 阻塞（需要人工干预）
  | "finished"   // 已完成
  | "failed"     // 失败
  | "cancelled"; // 已取消
```

---

## 五、两种同步模式

TaskFlow 支持两种 sync mode，这是理解它的关键：

**Managed（托管模式）**：TaskFlow 端到端拥有生命周期，自己创建并驱动子任务。适合由 OpenClaw 内部编排层（Lobster、ACPX、TypeScript Helpers）发起的多步骤工作流。

**Mirrored（镜像模式）**：TaskFlow 观察外部创建的任务，保持 flow 状态同步，但不接管任务创建权。适合外部系统已经在创建任务，只需要 OpenClaw 追踪整体进度的场景。

---

## 六、运行时 API（供编排层调用）

这些 API 是上层编排层（Lobster DSL、ACPX、TypeScript 代码）用来操作 Flow 的接口：

```typescript
// 创建新流程
createFlow({ ownerSessionKey, goal? }): Flow

// 在流程中运行任务（Managed 模式）
runTaskInFlow({ flowId, runtime, task, currentStep? }): TaskRecord

// 设置流程为等待状态
setFlowWaiting({ flowId, waitTarget }): void

// 设置/追加步骤间传递的输出
setFlowOutput({ flowId, key, value }): void
appendFlowOutput({ flowId, key, value }): void

// 向所有者发送流程更新消息
emitFlowUpdate({ flowId, message }): void

// 恢复流程执行
resumeFlow({ flowId, currentStep? }): void

// 完成/失败流程
finishFlow({ flowId, summary? }): void
failFlow({ flowId, error }): void
```

v2026.4.2 还新增了 `api.runtime.taskFlow` seam，让插件和受信任的编排层可以通过 host-resolved 的 OpenClaw 上下文创建和驱动 Managed Flow，不需要在每次调用时传递 owner 标识符。

---

## 七、底层存储

Flow 状态和 Task 记录都持久化在同一个 SQLite 数据库：

```
$OPENCLAW_STATE_DIR/tasks/runs.sqlite
```

Gateway 启动时将注册表加载到内存，写操作同步到 SQLite 保证跨重启的持久性。

维护机制：每 60 秒运行一次 sweeper，负责：
1. **Reconciliation**：检查活跃任务的 backing session 是否还存在，消失超过 5 分钟则标记为 `lost`
2. **Cleanup stamping**：为终态任务设置 `cleanupAfter` 时间戳（endedAt + 7 天）
3. **Pruning**：删除超过 `cleanupAfter` 的记录

---

## 八、架构层次关系

```
┌─────────────────────────────────────────────────────────┐
│ 编排层（Authoring Layer）                                │
│  Lobster DSL  |  ACPX（AI 自主决策）  |  TypeScript     │
└────────────────────────┬────────────────────────────────┘
                         │ 调用 Runtime API
┌────────────────────────▼────────────────────────────────┐
│ TaskFlow / ClawFlow（流程编排基底）                      │
│  - Flow 身份与状态管理                                   │
│  - ownerSessionKey（返回上下文）                         │
│  - waitTarget / blockedSummary                          │
│  - 小型持久化输出（outputs）                             │
│  - CLI: openclaw tasks flow list|show|cancel            │
└────────────────────────┬────────────────────────────────┘
                         │ 协调
┌────────────────────────▼────────────────────────────────┐
│ Task Registry（后台任务注册表）                          │
│  - 单个任务记录与状态追踪                                │
│  - 通知投递（done_only / state_changes / silent）        │
│  - CLI: openclaw tasks list|show|cancel|notify|audit    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ SQLite Storage                                          │
│  $OPENCLAW_STATE_DIR/tasks/runs.sqlite                  │
└─────────────────────────────────────────────────────────┘
```

**Flow 和 Task 的关系**：Flow 协调 Task，不替代 Task。一个 Flow 在其生命周期内可以驱动多个 Task。用 `openclaw tasks` 查看单个任务记录，用 `openclaw tasks flow` 查看编排它们的 Flow。

---

## 九、与 Lobster 的关系

Lobster 是另一个编排层，但定位不同：

| 维度 | Lobster | TaskFlow |
|------|---------|----------|
| 定位 | 声明式工作流 DSL，单次调用执行多步骤管道 | 持久化流程状态基底，跨重启存活 |
| 适用场景 | 有明确开始/结束的管道（如邮件分拣）| 长时间运行、需要等待外部事件的流程 |
| 审批机制 | 内置 approve/resume token | 无内置审批，依赖上层编排层 |
| 持久化 | 轻量 resume token | 完整 flow 状态持久化到 SQLite |

官方文档的描述：Lobster 是"单次调用内的确定性管道"，TaskFlow 是"单次调用之上的流程编排"。两者可以配合使用：用 Lobster 执行单次管道，用 TaskFlow 追踪跨多次 Lobster 调用的整体进度。

---

## 十、实用操作速查

```bash
# 查看所有 flow（含状态）
openclaw tasks flow list

# 查看某个 flow 的详情（用 flow id 或 session key）
openclaw tasks flow show flow-inbox-triage-001

# 取消卡住的 flow
openclaw tasks flow cancel flow-inbox-triage-001

# 配合 tasks 命令查看 flow 下的具体任务
openclaw tasks list
openclaw tasks show <task-id>

# 健康检查（会显示 stale/lost flow 和 task）
openclaw tasks audit
openclaw doctor
```

---

## 十一、容易混淆的地方

**`openclaw flows` vs `openclaw tasks flow`**：前者是旧命令或别名，后者是当前官方路径。两者功能相同，优先用后者。

**Flow 和 Task 的区别**：Task 是"一次后台运行的记录"，Flow 是"把多个 Task 组织成一个作业的包装器"。简单的单任务分离运行会自动创建一个单任务 Flow（auto-sync 模式），复杂的多步骤工作流需要显式创建 Flow。

**Managed vs Mirrored**：Managed 是 OpenClaw 自己创建和驱动子任务，Mirrored 是外部系统创建任务、OpenClaw 只负责追踪。`openclaw tasks flow list` 的输出里会显示 sync mode。

**blockedSummary 的用途**：当 flow 进入 `blocked` 状态时，`blockedSummary` 字段记录阻塞原因（如 API 配额耗尽、权限不足），这个信息持久化在 SQLite 里，重启后不会丢失，方便运维人员排查。
