# AI 驱动 UI 开发方法论：让 Agent 产出精美网站

> 整理日期：2026-04-16  
> 来源：GitHub 项目 [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)（55k+ Stars）、Google Stitch DESIGN.md 规范、社区实践综合整理

---

## 核心问题：为什么 AI 生成的 UI 总是"差那么一口气"

用过 AI 写前端代码的人都有过这种体验：同一个页面，让 AI 多生成几次，每次风格都不一样。有时圆角有时方角，有时间距 8px 有时 16px，甚至同一个按钮在不同对话里长得都不一样。

问题的根源很简单：**AI 没有视觉真理源（Source of Truth）**。它不知道你的品牌主色是什么，不知道你偏好什么圆角，不知道你的按钮永远是 8px 圆角。每次生成，它都在从零猜测你的审美。

解决这个问题的关键，是给 AI 一份**可执行的设计约束文档**。

---

## 第一层：DESIGN.md —— 给 AI 的设计系统说明书

### 什么是 DESIGN.md

DESIGN.md 是 Google Stitch 团队在 2026 年 3 月提出的概念。它是一份纯 Markdown 格式的设计系统文件，专为 AI 编码代理设计。

逻辑很简单：把你的设计系统写成纯文本，让 Agent 能读。类比关系如下：

| 文件 | 读取者 | 定义内容 |
|------|--------|----------|
| `AGENTS.md` | 编码 Agent | 如何构建项目 |
| `DESIGN.md` | 设计 Agent | 项目应该长什么样 |

把 DESIGN.md 放进项目根目录，任何 AI 编码 Agent（Claude Code、Cursor、Codex 等）或 Google Stitch 就能即时理解你的 UI 应该如何呈现。Markdown 是 LLM 最擅长读取的格式，没有额外解析和配置成本。

### DESIGN.md 的标准结构

一份完整的 DESIGN.md 通常包含以下章节：

**1. Visual Theme & Atmosphere**  
整体风格描述和设计哲学，例如"极简主义、深色优先、终端美学"或"温暖、编辑风格、留白充足"。

**2. Color Palette & Roles**  
精确的颜色定义，包括主色、辅助色、语义色（success/warning/error），以及 CSS Variables 定义。例如：
```
Primary: #5E6AD2 (Linear 紫)
Background: #0A0A0A
Text Primary: #FFFFFF
Text Secondary: rgba(255,255,255,0.6)
```

**3. Typography Rules**  
字体家族、字号层级（h1-h6、body、small）、行高和字重的完整规范。

**4. Component Stylings**  
按钮、表单、卡片、导航等核心组件的样式规范，包括状态（hover/active/disabled）。

**5. Layout Principles**  
间距系统（通常基于 4px 或 8px 网格）、网格断点、对齐原则。

**6. Depth & Elevation**  
阴影层级和 z-index 规范，定义视觉层次感。

**7. Do's and Don'ts**  
明确列出常见错误和正确做法，防止 AI 走弯路。

**8. Responsive Behavior**  
断点定义和响应式适配规则。

**9. Agent Prompt Guide**  
如何将本文档用于 AI 提示词，以及示例提示词模板。

### awesome-design-md：现成的 DESIGN.md 资源库

[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) 是一个开源项目，收录了 68 个知名品牌网站的 DESIGN.md 文件，包括 Apple、Claude、Linear、Airbnb、Vercel、Stripe、Spotify 等。

使用方式极其简单：
1. 从仓库中找到你想模仿的品牌风格（例如 Linear 的极简深色风）
2. 把对应的 DESIGN.md 复制到你的项目根目录
3. 告诉 AI Agent："参考 DESIGN.md 构建这个页面"

这个项目 4 天内获得 20k+ Stars，核心价值在于：它把成熟的设计经验转译为 AI 可执行的规范原则，让开发者不需要懂设计也能产出高质量 UI。

---

## 第二层：Prompt 工程 —— 如何精准指挥 Agent

有了 DESIGN.md 之后，Prompt 的质量决定了最终产出的精度。

### 原则一：明确引用设计规范

不要只说"做一个好看的按钮"，而是：

```
参考项目根目录的 DESIGN.md，使用其中定义的设计规范实现一个主要按钮：
- 背景色使用 --color-primary
- 圆角 8px
- 内边距 12px 24px
- hover 状态亮度提升 10%
```

### 原则二：要求 AI 引用具体的 CSS 变量

```
实现一个导航栏，要求：
- 背景色使用 --color-bg-primary
- 边框使用 --color-border-subtle  
- 文字使用 --text-color-primary
- 高度 64px，内容区最大宽度 1200px
```

### 原则三：提供视觉参考（截图）

截图是价值被严重低估的上下文。Cursor、Claude Code 等工具都支持多模态输入。典型工作流：

1. 截取当前页面的截图
2. 截取目标设计稿或参考网站的截图
3. 在 Prompt 中说明具体差异："让这个页面更像第二张图。把表单头部压扁，输入框移到左侧，背景色改用品牌色。"

### 原则四：一次只改一件事

AI 在处理多个并发变更时容易出错。把大改动拆成小步骤，每步验证后再继续。可以用编号列表，但每个列表项应该是独立可验证的变更。

### 原则五：在系统提示词中注入设计规范

如果你的工具支持自定义系统提示词（如 Cursor Rules、CLAUDE.md），可以把 DESIGN.md 的核心内容直接注入：

```markdown
# 设计规范
本项目使用以下设计系统，所有 UI 代码必须严格遵守：

## 颜色
- 主色：#5E6AD2
- 背景：#0A0A0A
...（DESIGN.md 核心内容）
```

---

## 第三层：迭代反馈循环 —— 截图驱动的精修

初版生成后，进入截图驱动的迭代循环是提升 UI 质量的关键。

### 标准迭代流程

1. 让 AI 生成初版代码
2. 在浏览器中渲染，截图
3. 对比目标设计，找出差异
4. 把截图和具体差异描述发给 AI："第一张是当前效果，第二张是目标效果。主要差异：间距太紧、字体偏小、按钮颜色不对"
5. AI 修改，重复循环

### 何时停止迭代

有一个重要的判断原则：**当你的解释比改动本身还长时，停下来自己改**。

AI 在处理大范围、模糊的 UI 改动时效率高；在处理小范围、精确的像素级调整时，手动改反而更快。

---

## 第四层：项目级设计约束 —— 让规范持久生效

### 在 CLAUDE.md / AGENTS.md 中注入设计规则

把设计约束写入项目的 AI 指令文件，让每次对话都自动遵守：

```markdown
# UI 开发规范

## 设计系统
本项目使用 Linear 风格设计系统，详见 DESIGN.md。

## 强制规则
- 所有颜色必须使用 CSS Variables，禁止硬编码颜色值
- 间距基于 8px 网格系统（8/16/24/32/48/64px）
- 圆角统一使用 8px（小组件）或 12px（卡片/容器）
- 禁止使用 box-shadow 超过两层
- 所有交互元素必须有 hover 和 focus 状态

## 参考品牌
风格参考 Linear（极简、深色、高密度信息展示）
```

### 维护设计 Token 的一致性

建议在 CI 中添加检查，确保 CSS 变量在 DESIGN.md 和代码实现中保持一致。这防止了"文档说一套、代码做一套"的漂移问题。

---

## 实战工具链推荐

**设计规范来源**
- [getdesign.md](https://getdesign.md) —— awesome-design-md 的配套网站，可视化浏览 68 个品牌的 DESIGN.md
- [Google Stitch](https://stitch.withgoogle.com) —— 从截图/草图直接生成 DESIGN.md 和 UI 代码

**AI 编码工具**
- Claude Code —— 最强的 Agentic 编码能力，支持多模态，可读取 DESIGN.md
- Cursor —— 内置截图对比功能，UI 迭代体验最好
- GitHub Copilot —— 适合轻量 UI 修改

**设计参考**
- [Dribbble](https://dribbble.com) / [Behance](https://behance.net) —— 找视觉灵感
- [shadcn/ui](https://ui.shadcn.com) —— 高质量 React 组件库，AI 友好
- [Tailwind UI](https://tailwindui.com) —— 现成的高质量 UI 组件

---

## 方法论总结

让 Agent 产出精美 UI 的核心是**给 AI 足够的约束**，而不是给它更多自由。

四层约束体系：

1. **DESIGN.md**：定义视觉真理源，解决"AI 不知道你想要什么风格"的问题
2. **精准 Prompt**：引用具体变量和规范，解决"AI 理解偏差"的问题  
3. **截图迭代**：视觉反馈驱动精修，解决"文字描述不如图片直观"的问题
4. **项目级规则**：CLAUDE.md/AGENTS.md 注入设计约束，解决"跨对话规范漂移"的问题

核心认知转变：**设计师的价值不是被 AI 替代，而是把自己的审美经验结构化为 AI 可执行的规则集**。谁先完成这一步，谁就能把个人能力放大为团队和产品的长期资产。

---

## 参考来源

- [VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) — 68 个品牌 DESIGN.md 资源库
- [Google Stitch DESIGN.md 文档](https://stitch.withgoogle.com/docs/design-md/overview) — 官方规范
- [GitHub 爆火的 Awesome-Design-md，彻底重塑了 AI 设计工作流](https://www.uisdc.com/awesome-design-md) — 优设网深度解析
- [Design.md：让 AI 一致性进行前端 UI 设计的解决方案](https://juejin.cn/post/7625921944858427444) — 掘金实践案例
- [Iterate and refine with the Cursor Agent](https://sylverstudios.dev/blog/2025/04/30/ai-for-refinement.html) — Cursor 截图迭代工作流
