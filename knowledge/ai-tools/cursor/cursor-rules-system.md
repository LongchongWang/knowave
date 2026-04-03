# Cursor IDE AI 编码规则三级体系

> 整理自：[Cursor IDE AI编码规则深度优化：提升开发效率的实战指南](https://kirill-markin.com/zh/zhishi/cursor-ide-ai-bianma-guize-youhua/)（Kirill Markin，2025-05-08）
>
> 整理日期：2026-03-26

---

## 核心思路：三级规则体系

Cursor 的规则系统分三个层级，每一级的作用域和激活方式不同：

**全局规则**（Global Rules）：存放在 Cursor 设置界面（Cursor → 设置 → Cursor设置 → AI规则），对所有项目生效，始终启用。适合跨项目通用的编码标准，但 token 效率最低（始终占用上下文）。

**仓库级规则**（`.cursor/index.mdc`，Rule Type "Always"）：存放在项目仓库中，随仓库克隆自动获取，团队共享。替代了传统的 `.cursorrules` 文件（后者仍兼容但不再推荐）。适合项目架构规范、技术栈约定等项目特定内容。

**情景规则**（`.cursor/rules/*.mdc`）：按任务动态激活，只在相关任务时加载，token 效率最高。适合领域专业知识，如数据库查询规范、API 集成标准、React 组件规范等。

| 特性 | 全局设置 | 仓库级规则 | 情景规则 |
|------|----------|------------|----------|
| 适用范围 | 所有项目 | 特定仓库 | 专项任务 |
| 可见性 | 仅本地 | 团队共享 | 团队共享 |
| 激活方式 | 始终启用 | 仓库内始终有效 | 按任务动态激活 |
| Token 效率 | 低 | 中 | 高 |
| 设置位置 | Cursor 设置界面 | `.cursor/index.mdc` | `.cursor/rules/*.mdc` |
| 可移植性 | 每台设备手动设置 | 随仓库克隆自动获取 | 随仓库克隆自动获取 |

---

## 全局规则：经过验证的基础配置

以下是作者经过 3 个月迭代优化的全局规则配置，覆盖代码风格、错误处理、语言特性、依赖管理、终端使用、代码变更和文档七个维度：

```markdown
# Global Rules

## Code Style
- Comments in English only
- Prefer functional programming over OOP
- Use OOP classes only for connectors and interfaces to external systems
- Write pure functions - only modify return values, never input parameters or global state
- Follow DRY, KISS, and YAGNI principles
- Use strict typing everywhere - function returns, variables, collections
- Check if logic already exists before writing new code
- Avoid untyped variables and generic types
- Never use default parameter values - make all parameters explicit
- Create proper type definitions for complex data structures
- All imports at the top of the file
- Write simple single-purpose functions — no multi-mode behavior, no flag parameters that switch logic

## Error Handling
- Always raise errors explicitly, never silently ignore them
- Use specific error types that clearly indicate what went wrong
- Avoid catch-all exception handlers that hide the root cause
- Error messages should be clear and actionable
- NO FALLBACKS: Code should either succeed or fail with a clear error
- Transparent debugging: When something fails, show exactly what went wrong and why
- Fix root causes, not symptoms - fallbacks hide real problems that need solving
- External API/service calls: use retries with warnings, raise the last error if all attempts fail
- Error messages must include enough context to debug (request params, response body, status codes)
- Logging: no dynamic values interpolated into log message strings — pass them as structured data

## Language Specifics
- Prefer structured data models over loose dictionaries (Pydantic, interfaces)
- Avoid generic types like `Any`, `unknown`, or `List[Dict[str, Any]]`
- Use modern package management (pyproject.toml, package.json)
- Leverage language-specific type features (discriminated unions, enums)

## Libraries and Dependencies
- Install in virtual environments, not globally
- Add to project configs, not one-off installs
- When a dependency is installed locally, read its source code directly — best way to understand how it works
- Update project configuration files when adding dependencies

## Terminal Usage
- Always use non-interactive git diff: `git --no-pager diff` or `git diff | cat`
- Prefer non-interactive commands with flags over interactive ones

## Code Changes
- Matching the existing code style is more important than "correct" or "ideal" style
- Suggest only minimal changes related to current dialog
- Change as few lines as possible while solving the problem
- Focus only on what user is asking for - no extra improvements

## Documentation
- Code is the primary documentation — use clear naming, types, and docstrings
- Keep documentation in docstrings of the functions/classes they describe, not in separate files
- Separate docs files only when a concept cannot be expressed in code — and only one file per topic
- Never duplicate documentation across files — reference other sources instead
- Store knowledge as current state, not as a changelog of modifications
```

---

## 仓库级规则：项目专属规范

`.cursor/index.mdc` 文件（Rule Type "Always"）相当于为 AI 定制的 README.md，提供项目目标、架构说明和编码模式。

**推荐模板结构**（保持 < 100 行）：

```markdown
# 项目：[项目名称]

## 概述
- 目的：[简短描述]
- 技术栈：[关键技术]
- 架构：[关键模式 - MVC、微服务等]

## 代码模式
- [列出项目特定模式]

## 风格要求
- [项目特定风格指南]

## 错误处理
- [定义异常处理策略]

## 测试规范
- [描述测试方法和覆盖率要求]
```

---

## 情景规则：专项任务的精准指导

当仓库级规则变得过于庞大时，将其拆分为 `.cursor/rules/*.mdc` 文件，每个文件专注单一主题，只在相关任务时激活。

**常见情景规则示例**：

测试规则（`test-guidelines.mdc`）：命名模式、模拟策略、覆盖率要求、断言风格。

API 集成规则（`api-standards.mdc`）：错误处理与重试逻辑、认证流程、日志记录规范、API 版本策略。

状态管理规则（`state-patterns.mdc`）：action 和 reducer 命名约定、状态结构标准、异步操作处理、memoization 策略。

React 组件规则（`react-components.mdc`）：

```markdown
# React组件指南

## 组件结构
- 使用函数组件
- 定义清晰的TypeScript接口
- 复杂状态管理使用自定义hooks

## 样式设计
- 使用styled components
- 避免内联样式
- 遵循设计系统规范

## 命名约定
- 组件文件：PascalCase.tsx
- Hook文件：use[Name].ts
- 样式文件：[name].styles.ts
```

---

## 关键限制：对话中期规则激活

情景规则在**新对话开始时**效果最佳。如果在现有对话中途需要应用专门规则，AI 可能不会自动加载该规则文件——因为 Cursor 已经为对话建立了上下文，不会在对话中期重新评估需要哪些规则。

解决方案：明确提示（"请遵循我们的数据库查询指南完成此任务"），或者对关键任务启动新对话。

---

## Token 经济学：为什么规则要精简

所有基于 LLM 的工具都遵循同一原则：**最小化 token 使用对获取最佳结果至关重要**。

- 指令中的每个词都消耗 token
- 用于指令的 token 会减少用于代码理解的可用上下文
- 极度冗长的指导会导致收益递减

三级规则体系的设计本质上就是 token 优化策略：全局规则保持最小化，项目规范放仓库级，专项知识按需加载。

---

## 量化收益（作者实测数据）

代码质量方面：PR 评论减少 50%，类型错误下降 35%，代码重复率降低 42%，代码审查时间缩短 30%。

团队协作方面：新人培训时间减少 60%，跨团队沟通效率提升 40%。

开发效率方面：初始提交速度加快 35%，风格修复提交减少 40%，认知负荷降低 55%。

---

## 与其他 AI 编码工具的对比

Cursor 的三级规则体系在设计上最为精细，但其他工具也有类似机制：

- **GitHub Copilot**：`.github/copilot/settings.yml` 项目级配置
- **JetBrains AI Assistant**：项目级代码片段和模板（`.junie/guidelines.md`）
- **VS Code + AI 扩展**：工作区设置和自定义文件
- **百度 Comate**：`.comate/config.yaml`
- **阿里云 Cosy**：工作区预设模板

核心原则相同：在不让模型负担过重的情况下，提供恰到好处的上下文。

---

## 参考来源

- [Cursor IDE AI编码规则深度优化](https://kirill-markin.com/zh/zhishi/cursor-ide-ai-bianma-guize-youhua/)（Kirill Markin）
- [Cursor 官方文档：AI 规则](https://docs.cursor.com/context/rules-for-ai)
