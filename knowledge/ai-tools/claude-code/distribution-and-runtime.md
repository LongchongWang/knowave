# Claude Code 的分发与运行时架构

> 整理自 2026-06-23 的探索对话

## 基本信息

- 当前版本：`2.1.186`（可通过 `claude --version` 或 `npm view @anthropic-ai/claude-code version` 查询）
- 分发渠道：npm（`@anthropic-ai/claude-code`）
- 授权类型：**闭源私有软件**，npm 分发 ≠ 开源

## 技术栈：TypeScript + Bun 编译

Claude Code 用 TypeScript/JavaScript 编写，通过 **[Bun](https://bun.sh)** 编译成原生可执行二进制文件。

二进制文件位置：`~/.local/share/claude/versions/<version>`（`~/.local/bin/claude` 是软链接）

**文件大小：约 207MB**（主要是 JavaScriptCore 运行时引擎的体积）

## Bun 编译的工作原理

编译后的二进制结构：

```
claude 二进制文件
├── JavaScriptCore 运行时引擎   ← 原本需要 Node/Bun 提供的
├── 编译后的 JS/TS 字节码       ← 业务逻辑
├── 依赖库（npm packages）      ← 全部打包进来
└── 原生入口（C 层 bootstrap）  ← 操作系统从这里开始执行
```

执行引导流程：

```
OS 执行 claude
    ↓
原生入口初始化（设置内存/信号等）
    ↓
启动内嵌的 JavaScriptCore 引擎
    ↓
从二进制自身读取内嵌的 JS 字节码
    ↓
执行业务逻辑
```

**关键点**：运行时引擎被直接嵌进二进制，用户无需安装 Node.js，操作系统视其为普通原生可执行文件。

## 与传统 Node.js 方式对比

| | 传统 Node 方式 | Bun 编译后 |
|--|--|--|
| 依赖 | 需要安装 Node.js | 无外部依赖 |
| 分发 | 发代码 + 让用户装 Node | 发一个二进制文件 |
| 启动速度 | 较慢 | 更快 |
| 体积 | 小（代码本身） | 大（含运行时，通常 100-200MB） |

## 类似方案横向对比

| 工具 | 语言 | 打包内容 | 典型体积 |
|--|--|--|--|
| Bun compile | JS/TS | JavaScriptCore + 代码 | ~100-200MB |
| Electron | JS/TS | **Chromium + Node.js** + 代码 | ~300-500MB |
| Deno compile | JS/TS | V8 + 代码 | ~60-100MB |
| PyInstaller | Python | CPython 解释器 + 代码 | ~30-100MB |
| Go | Go | 无运行时（静态编译） | ~5-20MB |

## Electron 补充说明

Electron 与 Bun compile 思路相同（把运行时打进包），但更重：

- 额外内嵌了完整 **Chromium 浏览器内核**（用于渲染 HTML/CSS UI）
- 每个 Electron 应用运行时都开着一个 Chromium 实例，这是"吃内存"的根本原因
- 适用于桌面 GUI 应用（VS Code、Slack、Discord 等）

## `/recap` 功能

Claude Code 的会话摘要功能：

| | `/recap` | `/compact` |
|--|--|--|
| 替换历史记录 | 否 | 是 |
| 影响 prompt cache | **无**（cache-safe） | 使缓存失效 |
| 消耗 token | 极少 | 较多 |
| 用途 | 随时看进度 | 清理上下文 |

触发方式：
- **手动**：输入 `/recap`
- **自动**：离开终端 3 分钟后返回，且对话已有 3 轮以上时自动触发

可在 `/config` → Session recap 中开关。
