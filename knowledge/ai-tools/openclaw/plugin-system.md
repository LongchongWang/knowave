---
title: 'OpenClaw 插件系统深度指南'
---

# OpenClaw 插件系统深度指南

> 来源：OpenClaw 官方文档（docs.openclaw.ai）、jetems.com 终极指南、腾讯云开发者社区、openclaw-hub.com 发布日志
> 整理日期：2026-03-29

---

## 为什么要理解插件系统

OpenClaw 有三种扩展方式：Skill、Tool、Plugin。很多人一开始会把 Plugin 理解成"更高级一点的 Tool"，但这是错的。

**Plugin 不是某个功能点的增强版，而是系统级扩展机制。**

理解这三者的边界，是用好 OpenClaw 的关键分水岭：

- **Skill**：给 AI 一份操作手册，解决"它应该怎么做"的问题。本质是向模型注入规则和上下文，不增加系统代码能力。
- **Tool**：给 AI 一个可调用的函数，解决"它能做什么动作"的问题。Tool 是被动的，必须等 Agent 主动调用。
- **Plugin**：扩展系统本身，解决"系统能提供什么能力"的问题。Plugin 可以主动介入生命周期，注册渠道、Provider、后台服务等。

一句话总结：Skill 教它怎么做，Tool 给它一个动作，Plugin 给整个系统增加能力并控制系统流程。

---

## 插件系统的四层架构

OpenClaw 插件系统分四层运作：

**第一层：清单 + 发现（Manifest + Discovery）**
OpenClaw 从已配置路径、工作区根目录、全局扩展根目录以及随附扩展中查找候选插件。发现过程先读取原生 `openclaw.plugin.json` 清单以及受支持的 bundle 清单。关键设计：发现和配置验证基于 manifest/schema 元数据运行，不执行插件代码。

**第二层：启用 + 验证（Enable + Validate）**
核心决定某个已发现插件是启用、禁用、阻止，还是被选用于某个独占插槽（Slot，例如 memory）。

**第三层：运行时加载（Runtime Load）**
原生 OpenClaw 插件通过 jiti 在进程内加载，并将功能注册到中央注册表。兼容的 bundle 会被规范化为注册表记录，不导入运行时代码。

**第四层：表面消费（Surface Consumption）**
OpenClaw 的其余部分读取注册表，以公开工具、渠道、Provider 设置、Hooks、HTTP 路由、CLI 命令和服务。

这种拆分让 OpenClaw 能在完整运行时激活之前，就验证配置、解释缺失/被禁用的插件，并构建 UI/schema 提示。

---

## 插件的两种形态

### 原生 OpenClaw 插件

原生插件由 `openclaw.plugin.json`（清单）+ TypeScript 运行时模块组成，通过 jiti 在进程内加载，与 Gateway 网关运行在同一进程。这意味着：

- 原生插件可以注册工具、网络处理器、Hooks 和服务
- 原生插件中的 bug 可能导致 Gateway 崩溃
- 恶意原生插件等同于在 OpenClaw 进程内执行任意代码

**安全提示**：将原生插件视为受信任代码，优先使用固定版本安装。

### 兼容 Bundle

OpenClaw 还识别三种兼容的外部 bundle 布局：

- Codex 风格：`.codex-plugin/plugin.json`
- Claude 风格：`.claude-plugin/plugin.json`
- Cursor 风格：`.cursor-plugin/plugin.json`

Bundle 默认更安全，因为 OpenClaw 目前将它们视为元数据/内容包，不执行运行时代码。当前支持：捆绑的 Skills、Claude `commands/` markdown 映射为 Skills、Cursor `.cursor/commands/*.md` 映射为 Skills、兼容的 Codex hook 目录。

---

## 插件清单（openclaw.plugin.json）

每个插件都必须在插件根目录下提供 `openclaw.plugin.json`。OpenClaw 使用此清单在不执行插件代码的情况下验证配置。

**必填字段：**

```json
{
  "id": "my-plugin",
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {}
  }
}
```

**可选字段：**

- `kind`：插件类型（如 `"memory"`）
- `channels`：此插件注册的渠道 id 数组
- `providers`：此插件注册的 Provider id 数组
- `skills`：要加载的 Skills 目录（相对于插件根目录）
- `name`：显示名称
- `description`：简短描述
- `uiHints`：用于 UI 渲染的配置字段标签/占位符/敏感标志
- `version`：版本（仅供参考）

**验证规则：**
- 每个插件都必须提供 JSON Schema，即使不接受任何配置（空 Schema 可接受）
- 未知的 `channels.*` 键会被视为错误，除非该渠道 id 已在清单中声明
- `plugins.entries.<id>`、`plugins.allow`、`plugins.deny` 和 `plugins.slots.*` 必须引用可发现的插件 id

---

## 插件能注册什么

一个原生 OpenClaw 插件可以注册以下能力：

- **Agent Tools**：给 LLM 可调用的工具函数
- **Gateway RPC Methods**：Gateway 远程调用方法
- **Gateway HTTP Routes**：HTTP 路由（适合接 webhook、第三方回调）
- **CLI Commands**：新的 `openclaw <cmd>` 命令
- **Background Services**：后台服务
- **Context Engines**：上下文引擎（v2026.3.7 新增，可插拔）
- **Provider Auth**：模型供应商的登录授权流程（OAuth/API Key/Device Code）
- **Messaging Channels**：新的消息渠道（飞书、钉钉、Matrix 等）
- **Skills**：通过在清单中列出 `skills` 目录
- **Auto-reply Commands**：不经过 AI Agent 直接执行的命令
- **Lifecycle Hooks**：在 Agent 生命周期关键节点主动介入

---

## 插件 API 详解

### 最小骨架

```typescript
export default {
  id: "my-plugin",
  register(api) {
    api.logger.info("plugin loaded");
  },
};
```

或函数形式：

```typescript
export default function (api) {
  api.logger.info("plugin loaded");
}
```

### 注册 Agent Tool

```typescript
import { Type } from "@sinclair/typebox";

export default function (api) {
  api.registerTool({
    name: "my_tool",
    description: "Do a thing",
    parameters: Type.Object({
      input: Type.String(),
    }),
    async execute(_id, params) {
      return { content: [{ type: "text", text: params.input }] };
    },
  });
}
```

**可选工具**（需要用户显式启用）：

```typescript
api.registerTool(
  {
    name: "workflow_tool",
    description: "Run a local workflow",
    parameters: { /* ... */ },
    async execute(_id, params) { /* ... */ },
  },
  { optional: true }
);
```

在配置中启用可选工具：

```json
{
  "agents": {
    "list": [{
      "id": "main",
      "tools": {
        "allow": [
          "workflow_tool",   // 特定工具名称
          "workflow",        // 插件 id（启用该插件的所有工具）
          "group:plugins"    // 所有插件工具
        ]
      }
    }]
  }
}
```

**注意**：工具名称不能与核心工具名称冲突，冲突的工具会被跳过。

### 注册 Lifecycle Hook（生命周期钩子）

Hook 是 Plugin 与 Tool 最根本的区别：Tool 等 Agent 主动调用，Hook 在系统关键节点主动介入。

```typescript
export default function register(api) {
  api.registerHook(
    "command:new",
    async () => {
      // 每次 /new 命令时自动执行
    },
    {
      name: "my-plugin.command-new",
      description: "Runs when /new is invoked",
    }
  );
}
```

**推荐使用 `api.on(...)` 做类型化生命周期 Hook：**

```typescript
export default function register(api) {
  // Prompt 构建前注入上下文
  api.on("before_prompt_build", () => {
    return {
      prependSystemContext: "Follow company style guide.",
    };
  });
}
```

**三个关键生命周期节点：**

- `before_model_resolve`：模型选择前，适合做 `modelOverride` / `providerOverride`
- `before_prompt_build`：Prompt 构建前，适合注入上下文，可返回 `prependContext`、`systemPrompt`、`prependSystemContext`、`appendSystemContext`
- `before_agent_start`：官方标记为 legacy compatibility hook，优先使用前两个

**v2026.2.15 新增**：`llm_input` 和 `llm_output` hook，可观察进出模型的内容，用于自定义日志、Prompt 审计、成本追踪或构建拦截器。

**v2026.3.7 新增**：ContextEngine 插件 Slot，含 `bootstrap`、`ingest`、`assemble`、`compact`、sub-agent hooks 等 7 个生命周期节点，可完全自定义上下文管理行为。

**安全限制**：运营者可以限制插件的 Prompt 注入能力：

```json
{
  "plugins": {
    "entries": {
      "some-plugin": {
        "hooks": {
          "allowPromptInjection": false
        }
      }
    }
  }
}
```

### 注册 Provider Auth（模型供应商授权）

```typescript
api.registerProvider({
  id: "acme",
  label: "AcmeAI",
  auth: [{
    id: "oauth",
    label: "OAuth",
    kind: "oauth",
    run: async () => {
      return {
        profiles: [{
          profileId: "acme:default",
          credential: {
            type: "oauth",
            provider: "acme",
            access: "...",
            refresh: "...",
            expires: Date.now() + 3600 * 1000,
          },
        }],
        defaultModel: "acme/opus-1",
      };
    },
  }],
});
```

用户侧使用：

```bash
openclaw models auth login --provider acme --method oauth
```

### 注册 Channel（消息渠道）

Channel 配置不放在 `plugins.entries`，而是放在 `channels.<id>`：

```json
{
  "channels": {
    "acmechat": {
      "accounts": {
        "default": {
          "token": "ACME_TOKEN",
          "enabled": true
        }
      }
    }
  }
}
```

最小 Channel 实现需要：`config.listAccountIds`、`config.resolveAccount`、`outbound.sendText`。

Channel 还可以扩展：onboarding、security、status、gateway、mentions、threading、streaming、actions、commands。

### 注册 CLI 命令

```typescript
export default function (api) {
  api.registerCli(
    ({ program }) => {
      program.command("mycmd").action(() => {
        console.log("Hello");
      });
    },
    { commands: ["mycmd"] }
  );
}
```

### 注册 Auto-reply Command（不经过 AI 直接执行）

```typescript
api.registerCommand({
  name: "mystatus",
  description: "Show plugin status",
  handler: () => ({ text: "Plugin is running!" }),
});
```

### 注册 HTTP Route

```typescript
api.registerHttpRoute({
  path: "/acme/webhook",
  auth: "plugin",
  match: "exact",
  handler: async (_req, res) => {
    res.statusCode = 200;
    res.end("ok");
    return true;
  },
});
```

---

## Plugin Slots（独占插槽）

有些插件不是"并排增加一个能力"，而是独占接管某个系统模块。目前官方明确的 Slot：

- `memory`：记忆系统（默认 `memory-core`，可替换为 `memory-lancedb` 等）
- `contextEngine`：上下文引擎（v2026.3.7 新增）

配置方式：

```json
{
  "plugins": {
    "slots": {
      "memory": "memory-lancedb",
      "contextEngine": "legacy"
    }
  }
}
```

关闭某个 Slot：

```json
{
  "plugins": {
    "slots": {
      "memory": "none"
    }
  }
}
```

**关键约束**：同一个 Slot，同时只能由一个插件接管。开发 memory plugin 或 context engine plugin 本质上是"替换当前 owner"，而不是"再加一个"。

---

## 插件目录结构

```
my-plugin/
├── package.json          # npm 包信息 + openclaw.extensions 声明
├── openclaw.plugin.json  # 插件清单（必须）
├── index.ts              # 插件入口
└── skills/               # 可选：捆绑的 Skills 目录
    └── my-skill/
        └── SKILL.md
```

`package.json` 中声明 extension entry：

```json
{
  "name": "my-plugin",
  "openclaw": {
    "extensions": ["./index.ts"]
  }
}
```

---

## 使用现成插件的完整流程

```bash
# 1. 查看当前已加载的插件
openclaw plugins list

# 2. 安装 npm 插件（只接受 registry-only，不接受 Git/URL/file/semver range）
openclaw plugins install @openclaw/voice-call

# 3. 安装本地插件
openclaw plugins install ./extensions/my-plugin

# 4. 开发调试时 link 本地插件（不复制，添加到 plugins.load.paths）
openclaw plugins install -l ./extensions/my-plugin

# 5. 启用插件（安装 ≠ 启用，必须显式启用）
openclaw plugins enable voice-call

# 6. 在配置中设置插件参数
# plugins.entries.<id>.config 下配置，支持 ${ENV_VAR} 环境变量

# 7. 重启 Gateway（配置变更必须重启才生效）
openclaw gateway restart

# 8. 验证与诊断
openclaw plugins info <id>
openclaw plugins doctor
openclaw config validate
```

**更新插件：**

```bash
openclaw plugins update <id>
openclaw plugins update --all
openclaw plugins update <id> --dry-run  # 预览更新
```

---

## 官方内置插件清单

以下插件随 OpenClaw 捆绑，部分默认启用，部分需要手动启用：

**渠道类（需安装）：**
- `@openclaw/voice-call`：语音通话
- `@openclaw/matrix`：Matrix 协议
- `@openclaw/nostr`：Nostr 协议
- `@openclaw/zalo`：Zalo 渠道
- `@openclaw/msteams`：Microsoft Teams（v2026.1.15 起仅以插件形式提供）

**记忆类（捆绑）：**
- `memory-core`：默认内存搜索（通过 `plugins.slots.memory` 启用）
- `memory-lancedb`：长期记忆，支持自动召回/捕获

**Provider 类（捆绑，默认启用）：**
Anthropic、OpenAI、OpenRouter、Google、GitHub Copilot、Moonshot、MiniMax、Volcengine、Kimi Coding、BytePlus 等 20+ 个 Provider 插件。

---

## 什么时候该上 Plugin

**用 Skill 就够了：** 给 AI 增加规则、限制行为、补充知识、规范回答方式。

**用 Tool 更合适：** 增加一个明确功能，输入参数 → 执行 → 返回结果，不需要系统级接入。

**必须上 Plugin 的情况：**

1. 你想让某件事自动发生（每次 Prompt 构建前注入内容、每次工具调用前审计参数）
2. 你想接入一个新的消息渠道（飞书、钉钉、自建 IM）
3. 你想给模型做登录授权（OAuth、API Key、Device Code）
4. 你想替换默认系统能力（记忆系统、上下文引擎）
5. 你想给 OpenClaw 增加新的系统入口（CLI 命令、HTTP 路由、Gateway RPC、后台服务）

---

## 最佳实践

**开发顺序：** 先做最小骨架（让它加载起来）→ 注册一个 Tool → 加 Hook → 挑战更重的系统能力（Channel/Provider/Slot）。

**配置安全：** 永远不要硬编码密钥，使用 `${ENV_VAR}` 环境变量引用。

**版本管理：** 安装时优先使用固定版本，避免 `@latest` 在预发布版本上意外升级。

**Slot 设计：** 开发 memory 或 contextEngine 类插件时，明确告知用户这会替换现有系统，而不是并行添加。

**Hook 设计：** Prompt 注入类 Hook 要考虑运营者可能禁用 `allowPromptInjection`，做好降级处理。

**工具命名：** 工具名称不能与核心工具冲突，建议加插件 id 前缀（如 `myplugin_do_thing`）。

**可选工具：** 对触发副作用或需要额外凭证的工具，优先使用 `optional: true`，让用户显式选择启用。

**诊断三件套：**

```bash
openclaw plugins info <id>   # 查看插件详情和状态
openclaw plugins doctor      # 全局诊断
openclaw config validate     # 配置语法检查
```

---

## 常见误区

**误区一：安装了就能用。** 安装只是把插件放进系统，必须显式 `enable` 才会加载。

**误区二：配置了不重启。** 配置变更必须重启 Gateway 才生效，这是最常见的"为什么没反应"根因。

**误区三：Plugin 是更高级的 Tool。** Plugin 是系统级扩展，Tool 只是 Plugin 能注册的能力之一。

**误区四：Bundle 和原生插件一样强。** Bundle 目前主要支持 Skills 和部分 Hooks，不执行运行时代码，能力有限。

**误区五：同一 Slot 可以装多个插件。** Slot 是独占的，同时只能有一个插件接管。

---

## 参考来源

- [OpenClaw 官方文档 - 插件系统](https://docs.openclaw.ai/zh-CN/tools/plugin)
- [OpenClaw 官方文档 - 插件清单](https://docs.openclaw.ai/zh-CN/plugins/manifest)
- [OpenClaw 官方文档 - 插件智能体工具](https://docs.openclaw.ai/zh-CN/plugins/agent-tools)
- [OpenClaw 官方文档 - plugins CLI](https://docs.openclaw.ai/zh-CN/cli/plugins)
- [jetems.com - OpenClaw Plugin 终极指南](https://www.jetems.com/posts/openclaw-plugin-ultimate-guide/)
- [openclaw-hub.com - v2026.2.15 发布日志](https://openclaw-hub.com/releases/v2026.2.15/)
- [腾讯云开发者社区 - OpenClaw 插件系统终极指南](https://developer.cloud.tencent.com/article/2640909)
