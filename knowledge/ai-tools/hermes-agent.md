# Hermes Agent：自进化 AI 智能体深度解析

> 整理日期：2026-04-14  
> 来源：[GitHub - NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) · [官方文档](https://hermes-agent.nousresearch.com/docs/) · [johng.cn 深度解析](https://johng.cn/ai/hermes-agent-framework-introduction) · [AI Insight 研报](https://www.ai-insight.org/reports/hermes-agent-2026)

---

## 它解决了什么问题

当前 AI 助手有一个根本性的缺陷：**每次对话结束即遗忘**。你今天教会它你的代码风格，明天它又变回了陌生人。你用它完成了一个复杂任务，那套经验就此消失，下次遇到同类问题还得从头来。

Hermes Agent 的出发点是：AI 助手应该像一个真正的同事，越合作越默契，而不是每次都要重新介绍自己。

它的官方定位是 **"The agent that grows with you"**——一个与你共同成长的 Agent。核心主张是：这是目前唯一内置完整学习闭环（Closed Learning Loop）的开源 AI Agent。

---

## 背景：Nous Research 是谁

Nous Research 是美国一家开源 AI 研究机构，起源于 2023 年 Discord 社区中 AI 爱好者的草根协作，以开源 LLM 微调和 Agent 研究著称。他们此前推出了 Hermes、Nomos、Psyche 等系列模型。

Hermes Agent 于 2026 年 2 月 25 日在 GitHub 上线，短短一个多月收获超过 7 万 Star（截至 2026-04-14），是近年来开源 AI Agent 领域增速最快的项目之一。

---

## 核心架构：五层分层设计

Hermes Agent 采用分层模块化架构，从上到下依次是：

**用户界面层**：CLI（`hermes` 命令行）和 Gateway（Telegram/Discord/Slack 等消息平台）

**Agent 核心层**：AgentLoop（推理循环）、Memory（记忆系统）、Skills（技能系统）、Cron（定时调度）

**工具系统层**：47 个内置工具，覆盖终端执行、文件操作、网络搜索、浏览器自动化、图像生成、子 Agent 委托、MCP 扩展等

**执行后端层**：6 种终端后端——本地（local）、Docker、SSH、Modal（云 GPU）、Daytona、Singularity（HPC 集群）

**模型提供商层**：OpenRouter（200+ 模型）、Anthropic、OpenAI、Gemini、ZAI/Kimi/MiniMax，以及任意 OpenAI 兼容端点（Ollama/vLLM/LM Studio）

这个架构的关键设计思想是**模型无关**：底层模型是可替换的，工作流和记忆是你的。

---

## 最核心的创新：学习闭环

Hermes Agent 最重要的差异化能力是它的学习闭环系统，由三个相互配合的机制构成。

### 技能系统（Skills）——过程记忆

技能（Skill）是 Hermes 对"过程记忆"的实现。当 Agent 完成一个复杂任务后，它会自动将这次经验提炼为一个 Markdown 文件，存储在 `~/.hermes/skills/` 目录下。这个文件描述了完成某类任务的步骤、最佳实践和注意事项。

下次遇到类似任务时，相关 Skill 会被自动注入到系统提示词中，Agent 直接调用已有经验而不是从零摸索。更重要的是，Skills 在使用过程中会**自我优化**——如果某个步骤不够好，Agent 会在执行后更新这个 Skill。

技能的生命周期：复杂任务完成 → Agent 自动创建 Skill → 存储到 `~/.hermes/skills/` → 下次会话开始时注入 → Agent 在使用中改进 Skill → 循环进化。

Hermes 还提供了 **Skills Hub**（对接 [agentskills.io](https://agentskills.io) 开放标准），用户可以安装社区贡献的技能，也可以分享自己的技能。

### 记忆体系——陈述性记忆

Hermes 有五层记忆机制：

- **代理记忆**（`~/.hermes/memories/MEMORY.md`）：Agent 学到的环境、项目、工具信息
- **用户画像**（`~/.hermes/memories/USER.md`）：用户偏好、沟通风格、工作习惯
- **历史检索**（FTS5 全文索引）：搜索过去任意会话的内容，配合 LLM 摘要生成
- **用户建模**（Honcho 辩证系统）：多维度持续深化的用户认知模型
- **结构化记忆**（可选的 mem0 / RetainDB）：向量/图数据库记忆后端

会话开始时，MEMORY.md 和 USER.md 的快照会被冻结注入到系统提示词中（保留 prefix cache，不改变系统提示词）。会话过程中，`memory` 工具可以实时写入持久化记忆。会话结束后，历史会话被 FTS5 索引，Honcho 用户模型更新。

### 跨会话搜索

`session_search` 工具让 Agent 可以搜索所有历史会话内容：

```python
session_search(query="上次那个 Docker Compose 配置是怎么写的")
# => 返回历史对话中相关片段及 LLM 生成的摘要
```

这意味着 Agent 不只是"记住了"，而是能够**回忆**——在新的上下文中检索并应用过去的经验。

---

## 多平台与多执行环境

Hermes Agent 不绑定在本地机器上，这是它区别于 Claude Code 等工具的重要特点。

**消息平台**（15+）：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、Mattermost、飞书、企业微信、钉钉、Email、SMS、Home Assistant、Webhook 等。你可以在手机上发 Telegram 消息，让部署在服务器上的 Agent 执行任务。

**执行后端**（6 种）：

| 后端 | 适用场景 |
|------|---------|
| local | 开发调试、个人使用 |
| docker | 安全隔离、可复现环境 |
| ssh | 使用强力远程硬件 |
| modal | GPU 集群、按需付费（闲置时近乎零成本） |
| daytona | 团队协作、持久工作区 |
| singularity | HPC 集群场景 |

---

## 智能模型路由

Hermes 支持根据请求复杂度自动选择模型：

```yaml
smart_model_routing:
  enabled: true
  max_simple_chars: 160
  max_simple_words: 28
  cheap_model:
    provider: openrouter
    model: google/gemini-2.5-flash
```

简单请求用廉价模型，复杂请求用主模型，在保证质量的同时控制成本。

---

## 子 Agent 并行与 Cron 调度

`delegate_task` 工具可以生成隔离的子 Agent 并行执行多个工作流，适合需要同时处理多个独立任务的场景。

内置 Cron 调度系统支持自然语言描述定时任务，执行结果自动推送到指定平台（Telegram、Discord 等）。这让 Hermes 可以作为 7×24 在线的自动化助手运行，而不只是一个交互式工具。

---

## RL 训练轨迹导出

这是一个容易被忽视但很有价值的功能：Hermes 的执行轨迹可以通过 `tinker-atropos` 子模块导出为强化学习训练数据。

实际意义：用大模型（如 Claude）驱动 Hermes 完成任务，把执行轨迹用来微调小模型，逐步降低 API 成本。这是一个真正的数据飞轮——Agent 的每次工作都在为未来的模型优化积累素材。

---

## 与 OpenClaw 的对比

Hermes Agent 和 OpenClaw 面向相同的用户群体，Hermes 甚至内置了 `hermes claw migrate` 命令，可以一键导入 OpenClaw 的记忆、技能、API Key 等配置。

在对比之前，有一点需要先说清楚：两者在某些维度上根本不是同一个设计层次，直接对比数字会产生误导。

**模型支持**：两者都是模型无关的，都支持大量提供商。OpenClaw 官方文档列出了 45+ 个 Provider（Anthropic、OpenAI、Google、DeepSeek、Qwen、GLM、Kimi、MiniMax、Ollama、vLLM、LM Studio、OpenRouter、Groq、Mistral、xAI、NVIDIA、Volcengine、Alibaba、Bedrock、HuggingFace 等），Hermes 通过 OpenRouter 可以接入 200+ 模型。两者在这个维度上旗鼓相当，都不存在"绑定单一提供商"的问题。

**消息平台**：OpenClaw 在这个维度上实际上比 Hermes 更强。OpenClaw 官方文档列出了 25+ 个渠道（Telegram、Discord、WhatsApp、Slack、飞书、Signal、Matrix、Mattermost、Microsoft Teams、QQ Bot、LINE、Google Chat、IRC、iMessage/BlueBubbles、WeChat、Zalo 等），Hermes 支持 15+ 个平台。

**执行环境**：这是两者真正的差异所在，但不是同一个维度的比较。Hermes 的 6 种执行后端（local/Docker/SSH/Modal/Daytona/Singularity）解决的是"在哪里运行代码"的问题，让 Agent 可以在云端 GPU 集群上执行任务。OpenClaw 本身是本地优先运行时，不提供这类多后端切换能力，但它的 Docker 部署方案同样支持云服务器部署。

| 维度 | Hermes Agent | OpenClaw |
|------|-------------|---------|
| 开源协议 | MIT ✅ | MIT ✅ |
| 模型提供商 | OpenRouter 等，200+ 模型 | 45+ 原生 Provider |
| 自进化 Skills | ✅ 自动创建 + 自我优化 | Skills（手动创建维护） |
| 跨会话记忆 | FTS5 全文检索 + LLM 摘要 | 向量 + BM25 混合检索 |
| 消息平台 | 15+ 平台 | 25+ 渠道 |
| 代码执行后端 | 6 种（含云 GPU） | 本地优先，无多后端切换 |
| RL 训练数据 | ✅ 轨迹导出（tinker-atropos） | ❌ |
| 定位 | 自进化个人 AI 助理 | 本地优先多通道 AI 助手运行时 |

两者的核心差异在于设计哲学：OpenClaw 更强调多渠道路由、本地数据主权和插件化扩展；Hermes 更强调 Skills 自进化学习循环和多种云端执行后端。如果你的核心需求是"AI 越用越聪明、自动积累经验"，Hermes 的学习闭环是真正的差异化；如果你的核心需求是"接入更多消息平台、本地数据完全自控"，OpenClaw 的渠道生态和本地优先架构更成熟。

---

## 安装与快速上手

```bash
# 一行安装（Linux / macOS / WSL2）
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

source ~/.zshrc  # 或 ~/.bashrc

hermes           # 启动交互式 CLI
hermes setup     # 完整配置向导
hermes model     # 选择 LLM 提供商/模型
hermes gateway   # 启动消息平台网关
hermes doctor    # 诊断配置问题
```

使用本地模型（Ollama）：

```yaml
# ~/.hermes/config.yaml
model:
  provider: "ollama"
  base_url: "http://localhost:11434/v1"
  default: "qwen2.5-coder:32b"
```

---

## 局限性与注意事项

**编程能力取决于底层模型**。Hermes 本身不提供模型，用 Claude Opus 驱动和用开源小模型驱动，体验天差地别。

**仍是早期版本**。截至 v0.7.0，GitHub 上有 780+ open issues，稳定性仍有优化空间。

**Skills 自进化质量尚未大规模验证**。自动创建的 Skills 是否真的比手动创建的更好，社区还在验证中。

**生态体量远小于 Claude Code**。agentskills.io 的 Skills Hub 规模与 ClawHub 相比仍有差距。

---

## 为什么值得关注

Hermes Agent 代表了一种不同的 AI 助手设计哲学：**从工具到同事**。

Claude Code 和 OpenClaw 的 Skills 需要人工创建和维护。Hermes 的 Skills 是 Agent 自己在工作中创建的，而且会在使用中自我优化。这是从"工具"到"同事"的质变——不是你在管理 AI，而是 AI 在学习如何更好地帮助你。

模型无关的架构意味着：当更好的模型出现时，你的工作流、记忆和技能都可以无缝迁移，不存在供应商锁定。

---

## 参考来源

- [GitHub - NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（78.7k Stars，MIT 协议）
- [官方文档 hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)
- [johng.cn：Hermes Agent 框架深度介绍](https://johng.cn/ai/hermes-agent-framework-introduction)
- [AI Insight：Hermes Agent 深度解读](https://www.ai-insight.org/reports/hermes-agent-2026)
