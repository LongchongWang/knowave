# Github 一周热点 110 期：Github 历史增长最快项目

**来源：** 抖音 @IT咖啡馆（合集「GitHub 每周热点汇总」第 88 集）
**发布日期：** 2026-04-12
**视频时长：** 9 分 20 秒
**互动数据：** 点赞 3097 | 评论 55 | 收藏 1855 | 分享 281
**视频链接：** https://www.douyin.com/video/7627803481935465779
**标签：** #AI新星计划 #ClaudeCode #Github #IT咖啡馆 #智能体

---

## 内容概要

本期介绍了 5 个 GitHub 热点项目：用 Rust/Python 重写 Claude Code 并在数小时内获得数万 Star 的 claw-code（配合 oh-my-codex 工作流管理）、谷歌端侧 AI 体验 APP Google AI Edge Gallery、采用记忆宫殿架构的 AI 记忆系统 MemPalace、具备自我成长能力的开源智能体 Hermes Agent，以及开源免费录屏神器 Open Screen。此外还提到阿里内测视频模型 Happy Horse 登顶视频竞技场排行榜，并分享了两份行业报告。

---

## 项目深度解析

### 1. claw-code + oh-my-codex

#### 起源：一次意外泄露引发的开源运动

2026 年 3 月 31 日凌晨 4 点 23 分，Anthropic 在发布 npm 包时意外将 Claude Code 的 512,000 行 TypeScript 源代码一并打包上传。互联网在几分钟内就注意到了这件事。Anthropic 随即发出 DMCA 下架通知，GitHub 关闭了 8,100 个相关仓库——包括一些只是 fork 了 Anthropic 公开代码的无辜仓库。

韩国开发者 Sigrid Jin（GitHub: instructkr）在同一天凌晨醒来，用「清洁室重写」（clean-room rewrite）的方式，在不直接使用泄露代码的前提下，从零用 Python 重新实现了 Claude Code 的核心架构。这个项目就是 **claw-code**，后来核心模块又用 Rust 重写以提升性能。

#### 什么是「清洁室重写」

清洁室重写是一种规避版权的工程方法：开发者研究目标软件的行为和架构设计，但不直接复制任何源代码，而是从零独立实现相同的功能。这种方法在法律上被认为不构成版权侵权，因为版权保护的是具体的代码表达，而不是思想和架构本身。

claw-code 的 README 明确声明：「The result is a clean-room Python rewrite that captures the architectural patterns of Claw Code's agent harness without copying any proprietary source.」

#### claw-code 的技术架构

claw-code 的架构分为两层：Python 负责上层编排（orchestration），Rust 负责核心执行（core）。整体结构如下：

```
┌──────────────────────────────────┐
│       ClawCode Agent Harness     │
├──────────────────────────────────┤
│  LLM Router · any model          │
│  Tool-Call Loop + Retry Logic    │
│  Multi-Agent Coordination        │
│  Permission + Execution Layer    │
│  MCP Integration Support         │
└──────────────────────────────────┘
     Python orchestration · Rust core
```

与 Claude Code 的关键区别在于：claw-code 是**模型无关的**（model-agnostic）。它不绑定 Claude，可以接入 GPT-4、Gemini、DeepSeek、Llama 等任何 LLM。这对于无法访问 Anthropic API 的用户来说是重要的替代选项。

安装方式：

```bash
pip install clawcode
# 或使用 Rust 版本
cargo install claw-code
```

#### 增长速度为何如此惊人

claw-code 在发布 2 小时内突破 5 万 Star，9 天内达到 17 万+ Star，创下 GitHub 历史上最快的 Star 增速纪录。这背后有几个因素叠加：

第一，时机。Claude Code 泄露事件本身就是热点，claw-code 作为「第一个公开的开源替代」，承接了所有关注这件事的开发者的注意力。

第二，需求真实存在。Claude Code 的订阅费用对很多开发者来说是门槛，一个免费的开源替代方案有真实的市场需求。

第三，DMCA 效应。Anthropic 的下架行动反而引发了「Streisand Effect」——越是试图压制，越是引发更多关注。

需要注意的是，高 Star 数并不等于功能完整。claw-code 的 README 中有明确的 Porting Status 说明，部分 Claude Code 功能尚未实现（PARITY 缺口）。视频中提到的「18 万 Star」是早期数据，截至调研时已超过 17 万。

#### oh-my-codex：给 Codex CLI 加一层工作流

oh-my-codex（简称 OMX）是韩国开发者 Yeachan Heo 开发的工具，定位是 **OpenAI Codex CLI 的工作流增强层**。它不替换 Codex 作为执行引擎，而是在外面包了一层标准化的工作流和运行时。

视频中将 oh-my-codex 与 claw-code 并列介绍，但两者实际上是独立的项目，服务于不同的底层工具（claw-code 对应 Claude Code，oh-my-codex 对应 OpenAI Codex CLI）。它们的共同点是都属于「AI 编程工作流增强」这个方向，且都来自 UltraWorkers 社区生态。

oh-my-codex 的核心能力：

**标准化工作流阶段**：OMX 把 AI 编程拆解为 `deep-interview → ralplan → team/ralph` 的标准流程，强制 AI 先澄清需求、再制定方案、再执行，而不是直接开始写代码。这解决了 AI 编程中「理解不清就动手」的常见问题。

**36 个工作流技能（Skills）**：通过 `$name` 语法触发，覆盖 autopilot（全自动执行）、team（多 Agent 并行）、tdd（测试驱动开发）、code-review、security-review 等场景。

**团队并行执行（Team Mode）**：每个 worker 自动获得独立的 git worktree，零合并冲突，支持混合 provider（Codex + Claude + Gemini 并行工作）。

**5 个 MCP 服务器**：提供状态、记忆、代码智能、追踪等持久化能力，支持跨会话学习。

```bash
# 安装
npm install -g oh-my-codex

# 典型用法
omx autoresearch "how does the auth middleware work?"
omx team 3 "refactor auth module with full test coverage"
omx exec npm test -- --coverage
```

截至调研时，oh-my-codex 已有 22,200+ Star，每月下载量 48,500+，最新版本 v0.12.1（2026-04-07 发布）。

**参考来源：** [claw-code GitHub](https://github.com/ultraworkers/claw-code) · [claw-code.io](https://claw-code.io/) · [oh-my-codex GitHub](https://github.com/Yeachan-Heo/oh-my-codex) · [oh-my-codex 官网](https://yeachan-heo.github.io/oh-my-codex-website/)

---

### 2. Google AI Edge Gallery

#### 它解决了什么问题

在 AI Edge Gallery 出现之前，在手机上体验大模型有两条路：要么用云端 API（需要网络、有隐私顾虑、有费用），要么自己折腾 Ollama 或 LM Studio（只支持桌面端，对普通用户门槛极高）。

Google AI Edge Gallery 的定位是：**让普通 Android/iOS 用户无需任何技术背景，就能在手机上本地运行大模型**。它是一个实验性应用，由 Google AI Edge 团队开源（Apache 2.0 协议），GitHub 仓库为 `google-ai-edge/gallery`。

#### 核心特点

**完全离线运行**：模型下载到本地后，所有推理在设备上完成，不向任何服务器发送数据。这对隐私敏感场景（医疗、法律、个人日记）有实际价值。

**Gemma 4 作为核心模型**：2026 年 4 月 2 日，Google DeepMind 发布了 Gemma 4 开源多模态模型系列，AI Edge Gallery 同步支持。Gemma 4 的 E2B 变体（约 1.5GB）可以在普通 Android 手机上运行，支持文本、图像、语音多模态输入。

**多功能模块**：Gallery 内置了多个 AI 使用场景，包括 AI Chat（对话）、Ask Image（图像问答）、Prompt Lab（提示词实验）、Mobile Actions（自然语言控制手机功能）、Tiny Garden（AI 小游戏，270M 模型驱动）等。

**Hugging Face 模型库直连**：用户可以直接从 Hugging Face 浏览和下载兼容的模型，不局限于 Gemma 系列。

**平台支持**：最初仅支持 Android（APK 从 GitHub Releases 下载），后来上架 Google Play，并在 Google I/O 期间推出 iOS 版本。

#### 与桌面端工具的本质区别

Ollama 和 LM Studio 是面向开发者的桌面工具，需要命令行或图形界面操作，运行在 PC/Mac 上。AI Edge Gallery 的目标用户是普通消费者，运行在手机上，界面是熟悉的聊天式 UI，安装方式是 APK 或 App Store。

这个定位差异决定了它的价值：不是给开发者用的，而是给「想体验本地 AI 但不懂技术」的普通用户用的。

#### 局限性

手机端运行大模型的硬件瓶颈是真实存在的。模型在 CPU 上运行，响应速度明显慢于云端；存储占用大（一个模型通常 1-4GB）；老款手机可能无法流畅运行。此外，手机端能运行的模型规模有限，能力上限远低于云端旗舰模型。

**参考来源：** [Google AI Edge Gallery GitHub](https://github.com/google-ai-edge/gallery) · [Google Developers Blog](https://developers.googleblog.com/google-ai-edge-gallery-now-with-audio-and-on-google-play/)

---

### 3. MemPalace

#### 一个好莱坞女演员参与开发的 AI 记忆系统

MemPalace 的联合创始人之一是 Milla Jovovich——《生化危机》系列的女主角 Alice、《第五元素》里的 Leeloo。她和开发者 Ben Sigman 用 Claude Code 花了数月时间共同构建了这个项目。

这个背景本身就是一个很好的传播素材，但更重要的是项目本身解决的问题是真实的。

#### AI 记忆系统的核心矛盾

现有 AI 记忆方案（如 Mem0、Zep）的通用做法是：让 AI 决定哪些内容值得记住，提取关键信息，丢弃其余内容。这个方案的问题在于：**AI 决定丢弃的，往往正是用户最需要的**——推理过程、考虑过的替代方案、改变主意的原因、细节上下文。

MemPalace 的核心思路是反其道而行之：**不让 AI 决定什么值得记，而是存储一切，然后让检索变得可行**。

#### 记忆宫殿架构

MemPalace 的名字来自古希腊演说家使用的「记忆宫殿法」（Method of Loci）——通过将信息与空间位置关联来增强记忆。MemPalace 将这个比喻转化为数据结构：

- **Palace（宫殿）**：包含所有知识的顶层容器
- **Wings（翼楼）**：按人物或项目划分的顶层分区
- **Halls（走廊）**：按记忆类型（事实、事件、发现）连接各房间的通道
- **Rooms（房间）**：特定主题的记忆空间
- **Drawers（抽屉）**：原始逐字记录文件，永不删除，是真相的来源
- **Closets（壁橱）**：用 AAAK 格式压缩 30 倍的摘要，供快速检索

检索时，系统像「在房间里行走，推开一扇扇门」一样，通过空间结构定位记忆，而不是在一个扁平的向量数据库里全局搜索。这种结构化检索比全局搜索效率提升约 34%。

#### 技术实现

MemPalace 完全本地运行，使用 ChromaDB 做向量存储，SQLite 做元数据管理，all-MiniLM-L6-v2 做 Embedding。零 API 调用，零云端依赖，零成本。

```bash
pip install mempalace
mempalace init
```

支持通过 MCP 协议接入 Claude Code、ChatGPT、Cursor 等主流工具。

#### 基准测试争议

MemPalace 声称在 LongMemEval 基准测试上取得了 100% 的满分（混合模式）和 96.6%（纯本地模式）。这是迄今为止免费 AI 记忆系统的最高分。

但这个数字引发了社区的质疑：

- 100% 的混合模式分数使用了 LLM 重排序（Haiku），并非纯本地
- 100% 是在针对失败问题做了 3 次定向修复后才达到的（99.4% → 100%）
- 部分测试的 top_k 参数设置可能超出了候选池大小
- AAAK 压缩实际上会将准确率从 96.6% 降至约 84.2%

独立评测机构 Penfield Labs 发文质疑基准测试的真实性。MemPalace 团队也承认了部分方法论问题。

综合来看：**96.6% 的纯本地分数是真实可信的，是免费工具中的最高水平**；100% 的混合分数有水分，营销成分大于技术成分。

视频评论区提到的「450GB 缓存」bug 和「分析没几个文件就报错」的问题，在 GitHub Issues 中也有记录（#47 UnicodeEncodeError、#29 基准测试方法论质疑），说明项目仍处于早期阶段，生产可用性有待验证。

**参考来源：** [MemPalace GitHub](https://github.com/milla-jovovich/mempalace) · [mempalace.tech](https://www.mempalace.tech/) · [LongMemEval 论文](https://arxiv.org/abs/2410.10813)

---

### 4. Hermes Agent

#### 定位：不是 IDE 插件，是住在服务器上的自主智能体

Hermes Agent 由 **Nous Research** 开发，于 2026 年 2 月发布，MIT 协议开源，GitHub 仓库为 `NousResearch/hermes-agent`。

Nous Research 是一家专注于开源 LLM 训练的研究机构，Hermes 系列模型（Hermes、Nomos、Psyche）是他们的代表作。Hermes Agent 是他们将模型训练经验延伸到 Agent 框架领域的产品。

与 Claude Code、Cursor 这类绑定在 IDE 里的编程助手不同，Hermes Agent 的定位是**自主智能体**：它运行在你的服务器上（或 $5/月的 VPS 上），你通过 Telegram/Discord/微信等消息平台与它交互，它在后台持续工作，记住它学到的一切，越用越强。

#### 核心差异：内置学习闭环

大多数 AI Agent 框架是无状态的——每次对话都从零开始，不记得上次做了什么，不会从经验中学习。Hermes Agent 的核心创新是**内置学习闭环（built-in learning loop）**：

**记忆系统（Memory）**：三层记忆架构。短期记忆保存当前会话上下文；长期记忆跨会话持久化，使用 FTS5 全文搜索 + LLM 摘要召回；用户模型（User Modeling）通过 Honcho 框架持续深化对用户的理解，记录用户的偏好、工作方式、项目背景。

**技能系统（Skills）**：当 Hermes 完成一个任务后，它会自动将解决方案提炼为可复用的技能（Skill），下次遇到类似问题时直接调用，而不是重新推理。技能在使用过程中持续改进。这套技能系统兼容 [agentskills.io](https://agentskills.io) 开放标准，技能可以在社区共享。

**自我提示（Self-Nudging）**：Hermes 会主动提醒自己持久化重要知识，而不是等用户告诉它「记住这个」。

#### 技术规格

- **47 个内置工具**：覆盖文件操作、代码执行、网络搜索、图像生成、语音合成等
- **6 种执行环境**：本地、Docker、SSH、Daytona（无服务器）、Singularity、Modal
- **15+ 消息平台**：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、微信、飞书、钉钉等
- **MCP 支持**：可接入任意 MCP 服务器扩展工具能力
- **语音模式**：支持 CLI、Telegram、Discord 的实时语音交互
- **定时任务**：内置 cron，用自然语言描述调度规则

```bash
# 安装
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes setup
```

#### 与 OpenClaw 的对比

Hermes Agent 和 OpenClaw 经常被拿来比较，两者都是「住在服务器上的 AI 助手」，但设计哲学不同：

OpenClaw 是**多通道路由架构**，强调多 Agent 并发、Channel 管理、Lane 调度，适合需要同时处理多个任务流的场景。

Hermes Agent 是**单体自进化架构**，强调记忆积累和技能沉淀，适合需要长期陪伴、越用越懂你的场景。

视频评论区有用户将 Hermes Agent 称为「完美取代 OpenClaw」，这个说法过于绝对——两者的设计目标有重叠但不完全相同。

**参考来源：** [Hermes Agent GitHub](https://github.com/NousResearch/hermes-agent) · [官方文档](https://hermes-agent.nousresearch.com/docs/)

---

### 5. Open Screen

#### 两个同名项目的澄清

搜索「OpenScreen」会找到两个不同的开源录屏项目，需要区分：

- **siddharthvaddem/openscreen**：基于 Electron + React，跨平台（macOS + Windows），功能相对基础，是 Screen Studio 的轻量替代
- **ghollbeck/openscreen**：基于 Swift，仅支持 macOS 14+，功能更完整，**内置 MCP 服务器**，是视频中介绍的版本

视频中提到的 Open Screen 应为后者（ghollbeck/openscreen），官网为 openscreen.io，定位是「Screen Studio + Loom + Glimpse 的开源替代」。

#### 它解决了什么问题

Screen Studio 是 macOS 上最受欢迎的录屏工具之一，以自动缩放、光标跟踪、精美的视觉效果著称，售价 $89 一次性买断（或 $29/月订阅）。对于需要制作产品演示、教程视频的开发者来说，这个价格不低。

Open Screen 的定位是：**免费、开源、永久可用，覆盖 Screen Studio 的核心功能**。MIT 协议，个人和商业均可免费使用，无水印，无订阅。

#### 核心功能

**智能自动缩放**：基于点击事件自动生成缩放动画，使用弹簧物理（spring physics）模拟自然运动感。支持四种动画风格，也支持手动在时间轴上放置缩放块（Cmd+I）。

**专业视觉效果**：7 种光标样式、GPU 加速的运动模糊（zoom 过渡时自动激活）、淡入淡出过渡、可调节的背景（纯色/渐变/壁纸/自定义图片）、内边距和圆角控制、阴影效果、Logo 水印。

**多格式导出**：MP4（H.264/HEVC，最高 4K 60fps）、GIF（优化的动态图）、Final Cut Pro（.fcpxml）、Premiere Pro（FCP 7 XML）。

**MCP 服务器（最独特的功能）**：Open Screen 内置了一个 MCP 服务器，提供 11 个工具和 4 个资源，允许 AI Agent 直接控制录屏——启动录制、停止录制、添加缩放标记、导出视频。这个功能类似 Cursor 的 Glimpse，但完全开源。

```bash
# 启动 MCP 服务器
open-screen mcp start
```

这意味着你可以让 Claude Code 或其他 AI Agent 在执行代码修改时自动录制操作过程，无需手动操作录屏软件。

#### 与竞品的对比

| 功能 | Open Screen | Screen Studio | Loom | OBS |
|------|-------------|---------------|------|-----|
| 开源 | ✅ | ❌ | ❌ | ✅ |
| 自动缩放 | ✅ | ✅ | ❌ | ❌ |
| AI 编辑（MCP）| ✅ | ❌ | ❌ | ❌ |
| 云端分享 | ❌ | ❌ | ✅ | ❌ |
| GIF 导出 | ✅ | ❌ | 付费 | ❌ |
| 价格 | 免费 | $89 | $15+/月 | 免费 |

Open Screen 的核心优势是 MCP 集成——这是其他录屏工具都没有的能力，让它在 AI Agent 工作流中有独特的位置。

**参考来源：** [Open Screen GitHub](https://github.com/ghollbeck/openscreen) · [openscreen.io](https://openscreen.io/)

---

## 相关项目速查

| 项目 | 类型 | GitHub | 亮点 |
|------|------|--------|------|
| claw-code | Claude Code 开源重写 | ultraworkers/claw-code | 清洁室重写，模型无关，历史最快 Star 增速 |
| oh-my-codex | Codex CLI 工作流增强 | Yeachan-Heo/oh-my-codex | 36 技能，团队并行，5 MCP 服务器 |
| Google AI Edge Gallery | 手机端本地 AI 应用 | google-ai-edge/gallery | 完全离线，Gemma 4，Android/iOS |
| MemPalace | AI 记忆系统 | milla-jovovich/mempalace | 记忆宫殿架构，96.6% LongMemEval，免费本地 |
| Hermes Agent | 自主 AI 智能体框架 | NousResearch/hermes-agent | 内置学习闭环，技能自动沉淀，15+ 消息平台 |
| Open Screen | 开源录屏软件 | ghollbeck/openscreen | macOS 原生 Swift，内置 MCP 服务器，免费 |
| Happy Horse | 视频生成模型 | — | 阿里内测，登顶视频竞技场排行榜，未上线 |
