# Claude Code Dynamic Workflows 深度学习笔记

> 基于 Anthropic 官方博客、官方文档及多篇深度解析整理，写于 2026-05-30

---

## 背景：这是什么，为什么现在出现

2026 年 5 月 28 日，Anthropic 在发布 Claude Opus 4.8 的同时，向所有付费 Claude Code 用户开放了一项研究预览特性：**Dynamic Workflows（动态工作流）**。

要理解这个功能，先要理解它解决的问题。

传统的 Claude Code 会话里，模型本身就是编排者：每一轮决定下一步派谁去做、把上一步的结果消化进上下文、再据此规划。这种模式有两个先天缺陷：

1. **上下文窗口会被塞满**：每一个中间结果都回流到对话上下文，长任务必然撑爆窗口
2. **编排逻辑无法复用**：每次都是"即兴演奏"，同一套审计流程无法保存和重跑

Dynamic Workflows 的核心思路是：**把编排逻辑从模型的上下文里搬出来，落成一段可执行的 JavaScript 脚本，由独立运行时执行**。Claude 的上下文只剩下最终答案，中间状态全部活在脚本变量里。

---

## 技术本质：编排代码化

这个设计不是凭空出现的，它是过去四年 AI Agent 研究的一条清晰演进线的终点。

**2022 年**，PAL/PoT 论文证明了把数值计算从 LLM 的 token 采样里抽出来交给 Python 解释器，可以在数学基准上提升 8-40%。原理很简单：每生成一个 token 都是一次概率采样，N 步推理链整链正确的概率约为 `(1-ε)^N`，随长度指数衰减；把确定性计算交给解释器，就是把不确定性锁在了入口前。

**2022-2023 年**，Code as Policies（Google 机器人团队）让代码成为"行动"的载体：自然语言指令被翻译成调用 API 的策略代码。这个写法几乎可以一字不改地映射到今天 Claude Code 里"让 Claude 现场写脚本调度 subagent"的形态。

**2024 年**，CodeAct 论文（ICML 2024）做了理论归纳：把所有动作统一为可执行 Python 代码，让 Agent 自由组合 if/else、循环、错误处理，比传统 JSON Tool Call 方案在 17 个基准上高出 20% 成功率。JSON Tool Call 把动作空间约束成"单次调用+单次返回"，所有控制流都要被逆向拆回 LLM 的下一轮 forward 重新决策；CodeAct 让动作空间等于代码 AST，一次 forward 就能输出完整控制流。

**2025 年**，Anthropic 自己做了两次准备：Agent Skills（把专家知识打包成可检索的技能库）和 Code Execution with MCP（把 MCP 工具改造为基于文件系统的代码 API，避免上千个工具定义提前塞进上下文）。

Dynamic Workflows 是这条线的最新一步：**把编排（Orchestration）本身也代码化**。

---

## 核心机制

### 工作流是什么

一个 Dynamic Workflow 是一段 **JavaScript 脚本**，由 Claude 根据你描述的任务现场生成。脚本内部决定：
- 要派发哪些子 Agent
- 按何种顺序、走怎样的分支与循环
- 哪些子任务可以并行

运行时在独立沙盒中执行该脚本，当前规格：
- 最多协调 **1,000 个子 Agent**
- 最高 **16 个并行**
- 脚本本体没有文件系统与 shell 权限，只有被它派发的子 Agent 可以读写文件、运行命令、调用 MCP 工具

### 三个执行单元的区别

Claude Code 现在有三个互不替代但可组合的执行单元，理解它们的区别是用对这套体系的前提：

| 维度 | Subagents（子 Agent） | Skills（技能） | Workflows（工作流） |
|------|---------------------|--------------|------------------|
| 本质 | Claude 现场派生的工作进程 | Claude 跟随的一份说明书 | 运行时执行的一段脚本 |
| 谁决定下一步 | Claude，按轮决策 | Claude，按提示词决策 | 脚本 |
| 中间结果存在哪 | Claude 上下文窗口 | Claude 上下文窗口 | 脚本变量 |
| 可复用的是 | 工作进程的定义 | 说明书本身 | 整套编排 |
| 规模 | 每轮少量委派 | 与子 Agent 类似 | 每次几十到上千个 Agent |
| 中断恢复 | 重启当前轮 | 重启当前轮 | 同会话内可断点续跑 |

三者最大的区别在于**谁拿着计划**。Subagents 和 Skills 把计划交给 Claude 的当下推理；Workflows 把计划落成代码，由运行时执行。Workflows 内部仍然可以再派发 Subagents、再调用 Skills，它们是组合关系而非互斥关系。

### 对抗式验证（Adversarial Verification）

这是 Dynamic Workflows 里最有意思的设计。

一次工作流的执行通常分阶段：
1. Claude 先根据提示词制定计划，把工作切成子任务并行派发（fan-out）
2. 另一组"评审" Agent 被独立启动，专门尝试**反驳**第一组的结论
3. 如果两组结果不收敛，工作流继续迭代，直到答案稳定才进入下一阶段

这个设计的原型是 Reflexion/Self-Refine 论文，但有一个关键升级：从"同一个模型自我批评"升级为"独立的另一组 Agent 来反驳"。这避开了"自我评估者总倾向于证实自己"的失败模式——在没有人类参与的长任务中，风险通常来自"模型说服了自己"。

---

## 使用方式

### 启动工作流

```bash
# 方式一：在 prompt 中显式描述，单次触发
Run a workflow to audit every API endpoint under src/routes/ for missing auth checks,
missing rate limiting, and unsafe input handling. Output a per-file report with severity.

# 方式二：开启 ultracode，整段会话由 Claude 自主决定是否开工作流
/effort ultracode

# 方式三：使用内置工作流（研究类问题首选）
/deep-research What changed in the Node.js permission model between v20 and v22?
```

### 内置工作流：/deep-research

研究预览阶段内置了 `/deep-research`。它对一个研究问题从多个独立角度并行搜索，对抓取到的来源相互交叉验证，对每条声明做内部投票，最终输出一份带引用、且自动过滤未通过交叉检验声明的报告。

### 保存和复用工作流

如果某次跑出的工作流符合预期，可以将其脚本保存为一条 `/` 命令：

```bash
# 项目级，随仓库共享给团队
.claude/workflows/security-audit.js

# 用户级，跨项目可用、仅自己可见
~/.claude/workflows/security-audit.js

# 之后在任何会话里都可以这样调用
/security-audit src/routes/
```

### 脚本结构示意

```javascript
// 伪代码：审计 src/routes/ 下的认证缺陷
const files = await agent.list('src/routes/**/*.ts');

// 阶段 1：fan-out，每个文件由独立 Agent 审查
const findings = await parallel(files, 16, async (file) => {
  return await agent.spawn('explore', {
    prompt: `Audit ${file} for missing auth checks.`,
    tools: ['Read', 'Grep']
  });
});

// 阶段 2：对抗式评审，反驳每条 finding
const verified = await parallel(findings, 16, async (f) => {
  const challenger = await agent.spawn('plan', {
    prompt: `Refute or confirm: ${f.summary}`,
    tools: ['Read', 'Grep']
  });
  return challenger.confirmed ? f : null;
});

// 阶段 3：合并并输出
return reportBuilder.fromFindings(verified.filter(Boolean));
```

---

## 适用场景

Dynamic Workflows 适合的任务有一个共同特征：**任务可以被分解为大量独立的子任务，且子任务之间的依赖关系可以被明确表达**。

典型场景：
- **大规模代码审计**：对整个仓库的每个文件并行检查安全漏洞、代码规范、性能问题
- **跨文件重构**：把一个 API 的所有调用点并行迁移到新接口
- **大规模迁移**：如把 Bun 从 Zig 迁移到 Rust（Anthropic 官方案例，11 天完成）
- **多维度文档审计**：对大量文档并行检查准确性、一致性、完整性
- **深度研究**：对一个问题从多个角度并行搜索并交叉验证

不适合的场景：
- 任务本身是串行的、强依赖上下文的（如写一篇需要前后呼应的文章）
- 任务规模小，单个 Agent 就能搞定的

---

## 与 Claude Opus 4.8 的关系

Dynamic Workflows 是随 Opus 4.8 同步发布的，但它是 Claude Code 的功能，不是模型本身的能力。两者的关系是：

- **Opus 4.8** 提升了 Agent 任务的判断力和长程执行能力，让它在复杂多步任务中更可靠
- **Dynamic Workflows** 是 Claude Code 的编排层，让 Opus 4.8 的能力可以被放大到数百个并行 Agent 的规模

Opus 4.8 的核心改进集中在三个方向：编程和 Agent 能力的全面提升、honesty（诚实度）的历史性改善，以及配合 Dynamic Workflows 的长程任务执行能力。在 SWE-bench Pro 上达到 69.2%，是目前最强的编程模型之一。

---

## 可用性

- **当前状态**：Research Preview（研究预览）
- **可用用户**：Enterprise、Team、Max 方案的付费用户
- **价格**：与 Opus 4.7 相同（常规模式 $5/$25 每百万 tokens 输入/输出）；Fast Mode 速度 2.5×，价格比上一代便宜 3 倍

---

## 一个值得记住的底层逻辑

Dynamic Workflows 背后有一个反直觉的洞察：**大模型这两年在产品形态上的所有重要突破，本质上都不是"模型能力升级"，而是"token IO 架构的设计游戏"**。

- CoT/PAL 在玩"不确定性放在哪里"
- ReAct/CodeAct 在玩"一次 forward 写多少"
- Voyager/Skills 在玩"跑过一次的东西如何复用"
- Code Execution with MCP 在玩"上下文按需加载"
- Dynamic Workflows 在玩"编排逻辑是否需要经过模型"

把 LLM 当 Reasoner 用（每一步都问它"下一步做什么"）是 2023 年的主流范式，到 2026 年应该被认为是落后的。把 LLM 当 Code Composer 用，一次 forward 输出完整控制流，才是这代 Coding Agent 的正确打开方式。

---

## 参考来源

- [Anthropic 官方博客：Introducing Claude Opus 4.8](https://www.anthropic.com/news/claude-opus-4-8)（2026-05-28）
- [Claude Code 官方文档：Dynamic Workflows](https://code.claude.com/docs/en/workflows)
- [SimonAKing：Claude Code Dynamic Workflows 深度解析](https://simonaking.com/blog/claude-code-dynamic-workflows/)（2026-05-30）
- [liuqi.dev：Claude Code Dynamic Workflows 指南](https://www.liuqi.dev/blog/claude-code-dynamic-workflows-guide)
