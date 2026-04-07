---
title: 'OpenClaw Channel 开发指南：从零打造 WebSocket 通道'
---

# OpenClaw Channel 开发指南：从零打造 WebSocket 通道

> 来源：OpenClaw 官方文档（docs.openclaw.ai）、Taichi-Labs/openclaw-websocket、掘金 Channel 插件开发实战指南、zeeklog.com 实战案例
> 整理日期：2026-04-07

---

## 为什么要开发自定义 Channel

OpenClaw 内置了 20+ 个消息渠道（Telegram、Discord、飞书、QQ Bot 等），但有时你需要接入自己的系统——比如内部 IM、自建 Web 聊天界面、或者任何通过 WebSocket 通信的服务。这时就需要开发一个自定义 Channel Plugin。

Channel Plugin 是 OpenClaw 插件系统中的一类，它的职责很明确：与外部消息平台建立连接，接收用户消息，将消息传递给 OpenClaw 进行 AI 处理，再把 AI 回复发送回用户。

---

## 核心概念：三个对象的关系

开发 Channel Plugin 前，必须先理解三个核心对象的关系，否则很容易在配置时搞混。

**Plugin 对象**（如 `myPlugin`）是插件的入口，负责向 OpenClaw 注册 Channel。它的 id 用于 `plugins.installs` 和 `plugins.allow` 配置层级。

**Channel 对象**（如 `myChannel`）是 Channel 的完整功能实现，包含消息收发逻辑、账户管理、状态管理等。它的 id 用于 `channels` 和 `bindings` 配置层级。

**ChannelDock 对象**（如 `myDock`）是轻量级的能力声明，告诉 OpenClaw 这个 Channel 支持哪些聊天类型、是否支持流式响应等。

用一个类比来理解：Plugin 是公司（整体注册认证），Channel 是销售部（具体业务处理），ChannelDock 是资质证书（能力声明）。

---

## 整体架构

一个典型的 WebSocket Channel 项目由三层组成：

```
用户浏览器（前端 UI）
    ↕ WebSocket
后端服务（消息中转，可选）
    ↕ WebSocket
OpenClaw Channel Plugin（Node.js）
    ↕ Plugin SDK API
OpenClaw Gateway
    ↕
AI Provider（LLM）
```

如果你的场景比较简单，可以省略后端服务，让前端直接连接 Channel Plugin 暴露的 WebSocket 端口。

---

## 开发环境准备

```bash
# 环境要求
# Node.js >= 18.0.0
# OpenClaw >= 2026.3.12

# 创建插件目录
mkdir my-ws-channel
cd my-ws-channel

# 初始化项目
npm init -y

# 安装依赖
npm install openclaw
npm install ws
npm install -D typescript @types/node @types/ws
```

配置 `tsconfig.json`：

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## 项目结构

```
my-ws-channel/
├── src/
│   ├── channel.ts          # Channel Plugin 核心实现
│   ├── runtime.ts          # 运行时存储（单例）
│   ├── types.ts            # 类型定义
│   └── websocket-client.ts # WebSocket 客户端封装（可选）
├── index.ts                # 插件入口（register 函数）
├── package.json
├── tsconfig.json
└── openclaw.plugin.json    # 插件清单（必须）
```

---

## 第一步：定义插件清单

`openclaw.plugin.json` 是 OpenClaw 在不执行代码的情况下验证插件的依据，必须提供。

```json
{
  "id": "my-ws-channel",
  "name": "My WebSocket Channel",
  "description": "Custom WebSocket messaging channel for OpenClaw",
  "channels": ["my-ws-channel"],
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "enabled": { "type": "boolean" },
      "config": {
        "type": "object",
        "properties": {
          "wsUrl": { "type": "string" },
          "enabled": { "type": "boolean" }
        }
      }
    }
  }
}
```

关键点：`channels` 字段必须声明这个插件会注册的渠道 id，否则 OpenClaw 会把未知的 `channels.*` 键视为错误。

---

## 第二步：定义类型

`src/types.ts`：

```typescript
// WebSocket 消息格式（与你的服务端约定）
export interface WebSocketMessage {
  type: string;
  text?: string;
  to?: string;
  from?: string;
  messageId?: string;
  payload?: {
    content?: string;
    messageId?: string;
    to?: string;
  };
}

// Channel 账户配置
export interface WsChannelAccount {
  accountId: string;
  wsUrl: string;
  enabled?: boolean;
  configured?: boolean;
}
```

---

## 第三步：运行时存储

`src/runtime.ts`：

```typescript
import type { PluginRuntime } from "openclaw/plugin-sdk";

let runtime: PluginRuntime | null = null;

export function setRuntime(next: PluginRuntime) {
  runtime = next;
}

export function getRuntime(): PluginRuntime {
  if (!runtime) {
    throw new Error("Plugin runtime not initialized");
  }
  return runtime;
}
```

这个模块用于在插件 `register` 时保存 `api.runtime`，供 Channel 的 `startAccount` 方法使用。

---

## 第四步：实现 Channel Plugin（核心）

`src/channel.ts`：

```typescript
import type { ReplyPayload } from "openclaw/auto-reply/types";
import type { ChannelPlugin, OpenClawConfig } from "openclaw/plugin-sdk";
import { createDefaultChannelRuntimeState } from "openclaw/plugin-sdk";
import type { WsChannelAccount } from "./types.js";
import { getRuntime } from "./runtime.js";

// 存储活跃的 WebSocket 连接
const connections = new Map<string, { ws: any; accountId: string }>();

export const myWsChannel: ChannelPlugin<WsChannelAccount> = {
  // ── 1. 基础元数据 ──────────────────────────────────────────────
  id: "my-ws-channel",
  meta: {
    id: "my-ws-channel",
    label: "My WebSocket Channel",
    selectionLabel: "My WebSocket Channel (Custom)",
    docsPath: "/channels/my-ws-channel",
    blurb: "Custom WebSocket messaging channel.",
    aliases: ["ws-channel"],
  },

  // ── 2. 能力声明 ────────────────────────────────────────────────
  capabilities: {
    chatTypes: ["direct"],   // 支持私聊
    blockStreaming: true,     // 支持流式响应
  },

  // ── 3. 账户配置适配器 ──────────────────────────────────────────
  config: {
    // 列出所有账户 ID（简单场景固定返回 ["default"]）
    listAccountIds: (cfg: OpenClawConfig) => {
      return ["default"];
    },

    // 从 openclaw.json 中解析账户配置
    resolveAccount: (cfg: OpenClawConfig, accountId: string) => {
      const channelCfg = cfg.channels?.["my-ws-channel"];
      if (!channelCfg || !channelCfg.config) {
        return undefined;
      }
      const config = channelCfg.config as any;
      return {
        accountId: "default",
        wsUrl: config.wsUrl || "ws://localhost:8765/openclaw",
        enabled: config.enabled !== false,
      };
    },

    // 判断账户是否已配置（wsUrl 非空即视为已配置）
    isConfigured: async (account, cfg) => {
      return Boolean(account.wsUrl && account.wsUrl.trim() !== "");
    },
  },

  // ── 4. 状态管理适配器 ──────────────────────────────────────────
  // ⚠️ 必须实现 defaultRuntime，否则 UI 会显示 "0/1 connected"
  status: {
    defaultRuntime: createDefaultChannelRuntimeState("default", {
      wsUrl: null,
      connected: false,
      groupPolicy: null,
    }),

    buildChannelSummary: ({ snapshot }) => ({
      wsUrl: snapshot.wsUrl ?? null,
      connected: snapshot.connected ?? null,
      groupPolicy: snapshot.groupPolicy ?? null,
    }),

    buildAccountSnapshot: ({ account, runtime }) => ({
      accountId: account.accountId,
      enabled: account.enabled,
      configured: account.configured,
      wsUrl: account.wsUrl,
      running: runtime?.running ?? false,
      connected: runtime?.connected ?? false,
      groupPolicy: runtime?.groupPolicy ?? null,
      lastStartAt: runtime?.lastStartAt ?? null,
      lastStopAt: runtime?.lastStopAt ?? null,
      lastError: runtime?.lastError ?? null,
    }),
  },

  // ── 5. 出站消息处理 ────────────────────────────────────────────
  outbound: {
    sendText: async ({ accountId, to, text }) => {
      const conn = connections.get(accountId);
      if (!conn || conn.ws.readyState !== 1) {
        throw new Error(`No active WebSocket connection for account ${accountId}`);
      }
      conn.ws.send(JSON.stringify({
        type: "message",
        to,
        content: text,
      }));
    },
  },

  // ── 6. 网关适配器（核心：启动连接、处理消息）─────────────────
  gateway: {
    startAccount: async (ctx) => {
      const { log, account, abortSignal, cfg } = ctx;
      const runtime = getRuntime();

      log?.info(`[my-ws-channel] Starting for account: ${account.accountId}`);

      // ⭐ 关键：先设置状态为已连接，UI 才能正确显示
      ctx.setStatus({
        accountId: account.accountId,
        wsUrl: account.wsUrl,
        running: true,
        connected: true,
      });

      // 动态导入 ws 库（避免顶层 import 在某些环境下的问题）
      const WebSocketLib = await import("ws");
      const ws = new (WebSocketLib.default as any)(account.wsUrl);

      // 存储连接
      connections.set(account.accountId, { ws, accountId: account.accountId });

      // 用 Promise 控制生命周期
      let resolveLifecycle: () => void;
      let rejectLifecycle: (err: Error) => void;
      const lifecyclePromise = new Promise<void>((resolve, reject) => {
        resolveLifecycle = resolve;
        rejectLifecycle = reject;
      });

      // ── 监听入站消息 ──────────────────────────────────────────
      ws.on("message", async (data: Buffer) => {
        try {
          const rawData = data.toString();
          const eventData = JSON.parse(rawData);
          const innerData = eventData.data || {};

          // 标准化消息格式
          const normalizedMessage = {
            id: `${eventData.source || "ws"}-${Date.now()}`,
            channel: "my-ws-channel",
            accountId: account.accountId,
            senderId: innerData.source || eventData.source || "unknown",
            senderName: innerData.source || eventData.source || "Unknown",
            text: innerData.content || innerData.text || "",
            timestamp: innerData.timestamp || new Date().toISOString(),
            isGroup: false,
            groupId: undefined,
            attachments: [],
            metadata: {},
          };

          log?.info(`[my-ws-channel] Received: "${normalizedMessage.text}" from ${normalizedMessage.senderId}`);

          // 解析路由（确定消息应该发给哪个 Agent）
          const route = runtime.channel.routing.resolveAgentRoute({
            cfg,
            channel: "my-ws-channel",
            accountId: account.accountId,
            peer: {
              kind: "direct",
              id: normalizedMessage.senderId,
            },
          });

          // 构建消息上下文
          const ctxPayload = runtime.channel.reply.finalizeInboundContext({
            Body: normalizedMessage.text,
            BodyForAgent: normalizedMessage.text,
            From: normalizedMessage.senderId,
            To: undefined,
            SessionKey: route.sessionKey,
            AccountId: route.accountId,
            ChatType: "direct",
            SenderName: normalizedMessage.senderName,
            SenderId: normalizedMessage.senderId,
            Provider: "my-ws-channel",
            Surface: "my-ws-channel",
            MessageSid: normalizedMessage.id,
            Timestamp: Date.now(),
          });

          // 调度 AI 处理并回复
          await runtime.channel.reply.dispatchReplyWithBufferedBlockDispatcher({
            ctx: ctxPayload,
            cfg: cfg,
            dispatcherOptions: {
              deliver: async (payload: ReplyPayload, { kind }) => {
                log?.info(`[my-ws-channel] Delivering ${kind} reply...`);
                const currentConn = connections.get(account.accountId);
                if (!currentConn || currentConn.ws.readyState !== 1) {
                  throw new Error("No WebSocket connection available");
                }
                // 将 AI 回复发送回 WebSocket 客户端
                currentConn.ws.send(JSON.stringify({
                  type: "reply",
                  content: payload.text || "",
                  kind,
                }));
              },
              onError: (err, { kind }) => {
                log?.error(`[my-ws-channel] Delivery error for ${kind}: ${err.message}`);
              },
            },
          });

          log?.info(`[my-ws-channel] Message dispatched successfully`);
        } catch (err: any) {
          log?.error(`[my-ws-channel] Failed to process message: ${err.message}`);
        }
      });

      // ── 错误与关闭处理 ────────────────────────────────────────
      ws.on("error", (err: Error) => {
        log?.error(`[my-ws-channel] WebSocket error: ${err.message}`);
        connections.delete(account.accountId);
        ctx.setStatus({ connected: false, running: false });
        rejectLifecycle(err);
      });

      ws.on("close", () => {
        log?.info(`[my-ws-channel] Connection closed`);
        connections.delete(account.accountId);
        ctx.setStatus({ connected: false, running: false });
        resolveLifecycle();
      });

      // ── 中止信号处理 ──────────────────────────────────────────
      abortSignal.addEventListener("abort", () => {
        log?.info(`[my-ws-channel] Abort requested, closing connection`);
        ws.close();
        resolveLifecycle();
      });

      // 保持 startAccount 挂起，直到连接关闭或被中止
      await lifecyclePromise;
      connections.delete(account.accountId);
    },
  },
};
```

---

## 第五步：插件入口

`index.ts`：

```typescript
import { myWsChannel } from "./src/channel.js";
import { setRuntime } from "./src/runtime.js";

export default function register(api: any) {
  console.log("[my-ws-channel] Registering WebSocket Channel plugin");

  // 保存 runtime 供 channel 使用
  setRuntime(api.runtime);

  // 注册 Channel
  api.registerChannel({
    plugin: myWsChannel,
  });
}
```

---

## 第六步：配置 OpenClaw

编辑 `~/.openclaw/config.json`（或通过 Web UI 配置）：

```json
{
  "plugins": {
    "allow": ["my-ws-channel"],
    "installs": {
      "my-ws-channel": {
        "source": "path",
        "path": "/absolute/path/to/my-ws-channel"
      }
    }
  },
  "channels": {
    "my-ws-channel": {
      "enabled": true,
      "config": {
        "enabled": true,
        "wsUrl": "ws://localhost:8765/openclaw"
      }
    }
  },
  "bindings": [
    {
      "agentId": "main",
      "match": {
        "channel": "my-ws-channel"
      }
    }
  ]
}
```

---

## 第七步：安装与启动

```bash
# 进入插件目录
cd my-ws-channel

# 安装到 OpenClaw（本地开发用 -l 做 link，不复制文件）
openclaw plugins install -l .

# 验证安装
openclaw plugins list

# 启用插件
openclaw plugins enable my-ws-channel

# 重启 Gateway（配置变更必须重启）
openclaw gateway restart

# 验证 Channel 状态
openclaw channels status
```

---

## 关键细节与常见坑

### defaultRuntime 不能省略

这是最容易踩的坑。OpenClaw 的 UI 通过读取 `defaultRuntime` 来知道要跟踪哪些状态字段。如果省略这个配置，即使你在 `startAccount` 中调用了 `ctx.setStatus({ connected: true })`，UI 也只会显示 "0/1 connected"。

正确做法是：在 `defaultRuntime` 中声明所有要跟踪的字段（包括 `connected: false`），然后在 `startAccount` 开始时调用 `ctx.setStatus({ connected: true })`。

### startAccount 必须保持挂起

`startAccount` 是一个异步函数，OpenClaw 会等待它 resolve 才认为账户已停止。如果你的函数立即 return，Gateway 会认为账户已关闭。

正确做法是用一个 Promise 控制生命周期，在 WebSocket 关闭或收到 `abortSignal` 时才 resolve。

### channels 字段必须在清单中声明

`openclaw.plugin.json` 的 `channels` 字段必须列出这个插件会注册的所有渠道 id。如果 `openclaw.json` 的 `channels` 层级出现了清单中未声明的 id，OpenClaw 会报错。

### 配置变更必须重启

这是最常见的"为什么没反应"根因。任何配置变更（包括 `channels.*` 配置）都必须重启 Gateway 才生效。

### Plugin id 与 Channel id 的作用域不同

Plugin id（`plugins.installs`、`plugins.allow`）和 Channel id（`channels`、`bindings`）是两个不同的作用域。在简单场景下两者可以相同，但要清楚它们分别控制什么。

---

## 完整数据流

**入站（用户 → AI）：**

1. 外部服务通过 WebSocket 发送消息到 Channel Plugin
2. `ws.on("message")` 接收并解析消息
3. 调用 `runtime.channel.routing.resolveAgentRoute` 确定路由
4. 调用 `runtime.channel.reply.finalizeInboundContext` 构建消息上下文
5. 调用 `runtime.channel.reply.dispatchReplyWithBufferedBlockDispatcher` 触发 AI 处理

**出站（AI → 用户）：**

1. AI 生成回复
2. `dispatchReplyWithBufferedBlockDispatcher` 的 `deliver` 回调触发
3. Channel Plugin 通过 WebSocket 将回复发送回外部服务

---

## 多账户支持

如果需要支持多个 WebSocket 连接（例如连接多个不同的服务），可以扩展 `config.listAccountIds` 和 `config.resolveAccount`：

```typescript
config: {
  listAccountIds: (cfg: OpenClawConfig) => {
    const channelCfg = cfg.channels?.["my-ws-channel"];
    const accounts = channelCfg?.accounts || {};
    return ["default", ...Object.keys(accounts)];
  },

  resolveAccount: (cfg: OpenClawConfig, accountId: string) => {
    const channelCfg = cfg.channels?.["my-ws-channel"];
    if (accountId === "default") {
      return {
        accountId: "default",
        wsUrl: channelCfg?.config?.wsUrl || "ws://localhost:8765/openclaw",
        enabled: true,
      };
    }
    const accountCfg = channelCfg?.accounts?.[accountId];
    if (!accountCfg) return undefined;
    return {
      accountId,
      wsUrl: accountCfg.wsUrl,
      enabled: accountCfg.enabled !== false,
    };
  },
}
```

对应的 `openclaw.json` 配置：

```json
{
  "channels": {
    "my-ws-channel": {
      "enabled": true,
      "config": {
        "wsUrl": "ws://service-a:8765/openclaw"
      },
      "accounts": {
        "service-b": {
          "wsUrl": "ws://service-b:8766/openclaw",
          "enabled": true
        }
      }
    }
  }
}
```

---

## 调试技巧

```bash
# 查看 Gateway 日志（实时）
openclaw gateway logs --follow

# 查看插件详情和状态
openclaw plugins info my-ws-channel

# 全局诊断
openclaw plugins doctor

# 配置语法检查
openclaw config validate

# 查看 Channel 状态
openclaw channels status
```

在 `startAccount` 中大量使用 `log?.info(...)` 是最直接的调试方式，日志会出现在 Gateway 日志中。

---

## 参考资源

- [OpenClaw 官方文档 - 聊天渠道](https://docs.openclaw.ai/zh-CN/channels)
- [OpenClaw 官方文档 - 插件系统](https://docs.openclaw.ai/zh-CN/tools/plugin)
- [Taichi-Labs/openclaw-websocket（GitHub）](https://github.com/Taichi-Labs/openclaw-websocket)
- [chatu-ai/webhub - 官方 WebSocket Channel 插件](https://github.com/chatu-ai/webhub)
- [掘金 - Channel 插件开发实战指南](https://juejin.cn/post/7621392923704098851)
- [zeeklog.com - OpenClaw WebSocket Channel 开发实战](https://www.zeeklog.com/openclaw-websocket-channelkai-fa-shi-zhan-cong-ling-da-zao-zi-ding-yi-ai-tong-xin-tong-dao-23/)
