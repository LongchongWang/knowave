# AI-DLC：AI 驱动的软件开发生命周期

> 整理日期：2026-03-25  
> 来源：[AWS DevOps Blog](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/)、[AI-DLC 官网](https://ai-dlc.dev/)、[GitHub awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)

---

## 它解决了什么问题

在 AI 编程工具普及之前，软件开发的瓶颈是人的执行速度——写代码、写文档、写测试，每一步都需要人来完成。AI 出现后，大多数团队的应对方式分为两种极端：

**AI 辅助（AI-Assisted）**：把 AI 当成高级自动补全，只用来做代码补全、文档生成、单元测试等局部任务。AI 的能力被严重低估，团队的整体流程没有改变。

**AI 自主（AI-Autonomous）**：把需求扔给 AI，期望它自动生成完整系统。结果往往是 AI 产出的代码质量参差不齐，人类失去了对关键决策的控制，最终需要大量返工。

这两种方式都没有真正发挥 AI 的价值。AI-DLC（AI-Driven Development Lifecycle，AI 驱动的开发生命周期）就是为了解决这个问题而提出的——它把 AI 定位为**核心协作者**，而不是工具或替代者。

---

## 什么是 AI-DLC

AI-DLC 是 AWS 首席解决方案架构师 Raja SP 于 2025 年 7 月提出并开源的软件开发方法论。它的核心思想可以用一句话概括：

> **AI 负责执行，人类负责决策。**

具体来说，AI-DLC 建立在两个维度上：

**AI 驱动执行 + 人类监督（AI Powered Execution with Human Oversight）**：AI 主动制定详细工作计划，主动提问寻求澄清，在关键决策点等待人类确认后再继续。这个设计的出发点是：只有人类才真正理解业务背景和需求意图。

**动态团队协作（Dynamic Team Collaboration）**：当 AI 承担了大量例行工作后，团队成员从各自孤立地写代码，转变为在协作空间中实时解决问题、做创造性思考和快速决策。

---

## 三个阶段

AI-DLC 把软件开发分为三个顺序推进的阶段，每个阶段的产出都为下一个阶段提供更丰富的上下文。

### 阶段一：Inception（启动）

AI 将业务意图转化为详细的需求、用户故事和工作单元（Units of Work）。这个过程通过"Mob Elaboration"（集体细化）完成——整个团队实时验证 AI 提出的问题和方案。

这个阶段的关键产出是**规格文档**，它会被持久化存储到代码仓库，成为后续阶段的上下文基础。

### 阶段二：Construction（构建）

基于 Inception 阶段验证过的上下文，AI 提出架构方案、领域模型、代码实现和测试。这个过程通过"Mob Construction"（集体构建）完成——团队实时对技术决策和架构选择提供澄清。

### 阶段三：Operations（运维）

AI 利用前两个阶段积累的完整上下文，管理基础设施即代码（IaC）和部署流程，团队进行监督。

---

## 新术语体系

AI-DLC 刻意替换了 Agile/Scrum 的术语，以强调速度和 AI 协作的本质：

| 传统 Agile 术语 | AI-DLC 术语 | 含义变化 |
|---|---|---|
| Sprint（冲刺，以周计） | **Bolt**（闪电，以小时/天计） | 更短、更高强度的工作周期 |
| Epic（史诗） | **Unit of Work**（工作单元） | 内聚、可独立部署的工作块 |
| Story（用户故事） | **Intent**（意图） | 包含完成标准的高层目标声明 |

**Intent** 是 AI-DLC 中最核心的概念。一个 Intent 包含三个要素：描述（要构建什么、为什么）、完成标准（可验证的成功条件）、上下文（业务背景和约束）。

**Unit** 是从 Intent 派生出的内聚工作块，特点是：高内聚、低耦合、可独立部署、边界清晰。

---

## Hat 系统（帽子系统）

这是 AI-DLC 社区实现（ai-dlc.dev）中最有特色的设计。"帽子"是一种**关注点分离**的隐喻——每顶帽子代表一种特定的思维模式和职责范围。

核心工作流使用三顶帽子，按顺序切换：

**Planner（规划者）**：制定战术执行计划。审查当前工作单元，识别剩余完成标准，创建具体可操作的计划，标记潜在阻塞点。

**Builder（构建者）**：按照 Planner 的计划实现代码。以小的可验证增量工作，每次修改后运行测试/lint/类型检查（称为"backpressure"，反压），把测试失败当作实现指导而非障碍。

**Reviewer（审查者）**：验证实现是否满足完成标准。逐条检查每个完成标准，运行完整测试套件，做出明确的 APPROVE 或 REQUEST CHANGES 决定。

除了核心三帽，还有针对特定场景的专用帽子组合：

- **调试工作流**：Observer → Hypothesizer → Experimenter → Analyst（用科学方法系统排查 Bug）
- **TDD 工作流**：Test Writer → Implementer → Refactorer（经典红绿重构循环）
- **安全工作流**：Planner → Builder → Red Team → Blue Team → Reviewer（攻防循环）
- **设计工作流**：Planner → Designer → Reviewer

帽子系统的价值在于防止"上下文漂移"——AI 在规划时不会偷偷开始构建，在构建时不会跳过测试直接交付，在审查时不会因为"差不多了"而放水。

---

## 与传统 SDLC 的本质区别

传统 SDLC 的各个阶段（需求、设计、开发、测试）之间存在明显的交接成本，因为迭代代价高昂。AI-DLC 的核心洞察是：**当 AI 把迭代成本压缩到接近零时，顺序阶段就可以坍缩为连续流动（continuous flow）**。

另一个关键区别是**上下文的持久化**。AI-DLC 要求 AI 把计划、需求、设计产物全部存储到代码仓库，确保跨会话的工作连续性。这意味着即使删除所有代码，关于"构建了什么、为什么这样构建"的完整记录依然存在。

---

## 两个版本的关系

目前 AI-DLC 有两个主要版本，定位不同：

**AWS 官方版本**（awslabs/aidlc-workflows）：由 Raja SP 提出，强调大型团队的协作模式（Mob Elaboration、Mob Construction），配套工具是 Amazon Q Developer 和 Kiro IDE。适合企业级团队落地。

**社区版本**（ai-dlc.dev，The Bushido Collective）：基于 H•AI•K•U Method，强调 Hat 系统和工作流自动化，配套工具是 Claude Code 插件。更适合个人开发者和小团队快速上手。两者的核心理念一致，但实现路径不同。

---

## 实际价值

根据 AWS 的描述，AI-DLC 带来的核心收益是：

**速度**：AI 快速生成和迭代产物（需求、设计、代码、测试），让原本需要数周的工作在数小时或数天内完成。

**质量**：通过持续澄清，团队构建的是他们真正想要的东西，而不是 AI 对意图的抽象解读。AI 一致地应用组织特定的编码规范、设计模式和安全要求。

**开发者体验**：开发者从重复性编码任务转向关键问题解决，认知负担降低，同时因为能看到工作对业务价值的直接影响而获得更高的满足感。

---

## 参考资料

- [AWS DevOps Blog: AI-Driven Development Life Cycle](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/)（Raja SP，2025-07-31）
- [GitHub: awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows)
- [AI-DLC 官网（社区版）](https://ai-dlc.dev/)
- [The AI-DLC Handbook](https://aidlcbook.com/)
- [AWS re:Invent 2025 演讲](https://dev.to/kazuya_dev/aws-reinvent-2025-introducing-ai-driven-development-lifecycle-ai-dlc-dvt214-32b)
