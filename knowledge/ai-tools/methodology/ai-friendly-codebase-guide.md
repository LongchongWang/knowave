# AI 友好型代码库：终端研发实践指南

> 综述整理日期：2026-03-26

---

## 为什么这件事比你想的更重要

你可能已经在用 Cursor、Claude Code 或 Copilot 写代码了。但如果你只是把 AI 当成一个"更快的搜索引擎"或"自动补全工具"，你可能只用到了它 20% 的价值。

AI 辅助编程真正的潜力，在于让它承担完整的功能开发任务——你描述需求，它生成实现，你审查验收。这个工作流一旦跑通，开发效率的提升不是 20%，而是数倍。但这个工作流能否跑通，几乎完全取决于你的代码库是否给了 AI 足够的信息。

**代码库的质量，是 AI 辅助开发的天花板。**

一个结构混乱、约定隐式、文件臃肿的代码库，AI 在里面的表现会让你怀疑这个工具是否有用。而一个结构清晰、约定显式、模块自包含的代码库，AI 能做到的事情会让你重新定义"开发效率"这个词。

更深层的影响在于：随着 AI Agent 能力的提升，未来的开发模式很可能是"人负责架构决策和代码审查，AI 负责大部分实现"。在这个模式下，代码库的可读性和可预测性，直接决定了 AI 能否独立完成任务，还是每一步都需要人工干预和纠错。现在投入时间改造代码库，是在为这个未来做准备。

AI 在处理你的项目时，本质上是一个**刚入职的新员工**：不知道代码在哪里、不知道为什么这样写、不知道该遵循什么规范，只能靠猜。猜测就会出错。而且这个"新员工"每次对话结束后记忆清零，下次又要重新理解一遍。

这篇文章的目标是：告诉你如何把代码库改造成一个让 AI 能高效工作的环境——同时，这些改造对你的人类同事同样有益。

---

## 一、核心原则

### 原则 1：上下文质量决定生成质量

AI 生成代码的质量上限，由它能获取到的上下文质量决定。即便 Claude 拥有 200k token 的上下文，一个中等规模项目（67,000 行代码）展开后约 250 万 token，AI 一次只能看到不到 10% 的代码库。

这意味着：**你不能指望 AI 自己去理解你的项目，你必须主动把关键信息喂给它。**

好的代码会让 AI 生成更好的代码，屎山则更容易让 AI 生成屎山。这不是比喻，是字面意义上的模式复现。

### 原则 2：一致性比"最佳"更重要

命名规范选 snake_case 还是 camelCase 不重要，重要的是整个代码库保持一致。AI 是模式匹配机器——如果项目里有 10 个 Screen 都遵循同样的结构，AI 写第 11 个时会自然复现这个模式。反之，风格各异的代码库只能让 AI 猜测。

**一致性是 AI 友好型代码库最重要的单一属性。**

### 原则 3：显式优于隐式

代码里充满了"大家都知道"的潜规则，但没有任何文档记录，AI 无从得知。所有重要的约定——技术栈选型、禁止事项、命名规则、目录结构——都必须显式写出来，放在 AI 能自动加载的地方。

### 原则 4：自动化护栏是规范落地的唯一可靠方式

依赖 Code Review 来执行规范，在截止日期压力下必然失效。AI 编程 Agent 会把构建失败当作反馈信号——lint 报错，它会自动修复再重试。**把代码规范写进 lint 规则，比写进文档有效 10 倍。**

### 原则 5：验证是 AI 辅助开发的必要环节，不是可选项

AI 会产生幻觉，生成看似合理但实际错误的代码——不存在的 API 调用、虚构的库函数、只在一个平台上能跑的代码。"生成 → 审查 → 测试 → 优化"的循环必须建立。

### 原则 6：AI 友好 = 人类友好

这是最重要的认知：AI 友好型项目和人类友好型项目，在绝大多数标准上是重合的。改造历史项目的最好心态不是"为了 AI 而改造"，而是**借 AI 的压力，把项目变成一个对任何人都友好的代码库**。

---

## 二、常见反模式速查

在开始建立规范之前，先认清楚哪些是最常见的"AI 杀手"。这些反模式在终端项目里极为普遍，每一个都会显著降低 AI 的工作质量。

| 反模式 | 对 AI 的影响 | 解决方案 |
|--------|-------------|----------|
| 上帝文件（500+ 行） | 无法在一个上下文里完整理解，容易生成与文件其他部分冲突的代码 | 按职责拆分，每个文件只做一件事 |
| 配置散落各处 | 需要加载大量文件才能理解系统配置，容易遗漏或覆盖 | 集中到一个或少数几个配置文件 |
| 深层组件继承链 | 必须加载整条链才能理解最末端的组件行为 | 用组合（Composition）替代继承 |
| 隐式约定 | 无从得知"大家都知道"的潜规则，生成不符合项目规范的代码 | 写进 `CLAUDE.md`，写进 lint 规则 |
| Barrel Imports | 不知道组件来自哪里，需要额外消耗上下文预算追踪 | 使用直接路径导入 |
| Props 类型散落 | 修改组件时需要打开另一个文件才能知道参数，消耗额外上下文 | Props 类型紧贴组件定义 |
| `ScrollView + map` 渲染列表 | 不知道项目的性能约定，生成低性能代码并在项目里扩散 | 写进 lint 规则，强制使用 FlashList |
| 内联样式对象 | 每次渲染创建新对象，AI 容易复现这个模式并在项目里扩散 | 写进 lint 规则，强制使用 StyleSheet.create |

---

## 三、黄金法则（10 条）

这 10 条是所有规范的浓缩，可以贴在工位上，也可以直接写进 Code Review Checklist：

1. 一个概念，一个文件
2. 自包含的实现（重要的东西内联，不要分散到 utils）
3. 在使用点处文档化（注释写在用到的地方，不要只写在定义处）
4. 扁平优于嵌套（目录层级、组件层级都是）
5. 显式优于隐式（约定写出来，不要靠"大家都知道"）
6. 单文件最多 300 行
7. 最多 2 层导入深度
8. 每个目录都有 README
9. 示例优于解释（参考文件比文字描述更有效）
10. 规范写进 lint，不要只写进文档

---

## 四、规范体系

### 4.1 上下文文件规范（最高优先级）

这是 AI 友好型项目最核心的基础设施，成本最低、收益最高。

**项目根目录必须有 `CLAUDE.md`（或 `AGENTS.md` / `.cursorrules`）**，内容包括：

- 项目是什么、技术栈是什么
- 目录结构如何（每个目录的职责）
- 关键约定是什么（命名规则、文件结构）
- 哪些地方不能动、哪些是禁止事项
- 常用命令是什么（构建、测试、lint）
- 参考文件指向（"写新组件请参考 `src/features/product/components/ProductCard.tsx`"）

500 字以内的精准描述比 5000 字的流水账有用得多。

**每个主要目录下必须有 `README.md`**，说明这个目录里有什么、命名规则、如何新增。AI 不用打开文件就能知道该去哪里找什么。

### 4.2 文件规范

| 指标 | 规范 |
|------|------|
| 文件行数 | 50–300 行为宜，超过 500 行必须拆分 |
| 文件职责 | 一个文件只做一件事，做完整 |
| 导入深度 | 最多 2 层，避免循环依赖 |
| 自包含性 | 重要的常量、类型、验证逻辑尽量内联，减少跨文件依赖 |

### 4.3 命名规范

命名要表达意图，而不是实现细节。`calculateOrderTotal()` 而非 `calc()`，`useProductData` 而非 `useFetchProductFromAPI`。目录名本身就应该是文档——`src/features/order/` 比 `src/utils/` 清晰得多。

规范的选择（snake_case vs camelCase）不如一致性重要。选定一种，全项目统一，用自动化工具强制执行。

### 4.4 错误处理规范

错误处理的关键是具体性，而非复杂性。捕获具体的错误类型（`NetworkError`、`ParseError`）而非通用异常，日志里包含关键上下文（`orderId`、`userId`、`screenName`）。AI 生成的错误处理代码往往过于宽泛，这条规范要写进 lint 规则。

### 4.5 测试规范

测试应该是自文档化的：不需要理解实现细节，只需要看测试本身就能理解被测行为。一个写得好的参考测试文件，AI 可以照着模式生成新测试。测试本身也是 AI 验证自己改动是否正确的反馈机制。

### 4.6 React Native 专项规范

对于终端研发（React Native 项目），以下规范对 AI 生成代码质量影响最大：

**组件结构规范：** Props 类型定义紧贴组件，不放全局 `types/` 目录。文件结构从上到下依次是：imports → 类型定义 → 组件实现 → StyleSheet。数据逻辑抽到 Custom Hook，组件只负责渲染。

```tsx
// ✅ 好：类型和组件在一起，AI 修改组件时无需打开其他文件
interface ProductCardProps {
  id: string;
  title: string;
  price: number;
  onAddToCart: (id: string) => void;
}

export const ProductCard = ({ id, title, price, onAddToCart }: ProductCardProps) => {
  // ...
};

const styles = StyleSheet.create({
  // 样式紧贴组件
});
```

**禁止 Barrel Imports：** 禁止用 `index.ts` 把整个目录重新导出（`import { Button, Card, Modal } from '../components'`）。AI 无法知道 `Button` 来自哪里，需要额外消耗上下文预算追踪。使用直接路径导入（`import { Button } from '../shared/components/Button'`）。

**性能禁忌写进 lint 规则：**

- 长列表禁止 `ScrollView + map`，必须使用 `FlashList`
- 禁止内联样式对象（`style={{ padding: 16 }}`），统一用 `StyleSheet.create()`
- 动画必须使用 Reanimated，不用 Animated API

**平台差异处理：** 平台特定代码使用 `.ios.tsx` / `.android.tsx` 后缀，不要用大量 `Platform.OS` 条件判断。在 `CLAUDE.md` 里明确写清楚 iOS/Android 的差异处理约定（阴影、键盘、安全区域等）。

**目录结构：** 按功能（Feature）组织，把同一个功能的所有文件（组件、Hook、页面、类型）放在一起，而不是按文件类型分散到不同目录。

```
src/
├── features/
│   ├── order/
│   │   ├── components/    # 订单相关 UI 组件
│   │   ├── hooks/         # 订单数据 Hook
│   │   ├── screens/       # 订单相关页面
│   │   └── index.ts       # 对外公开 API
│   └── product/
│       └── ...
├── shared/                # 真正跨功能共享的东西
└── navigation/
```

---

## 五、可量化的标准

### 5.1 上下文预算标准

把上下文当作预算来管理：

```
总预算：200k token
对话历史：-20k token
AI 响应缓冲：-20k token
可用工作空间：约 160k token（约可同时查看 30–40 个文件）
```

**设计目标：让 AI 完成一个典型任务所需加载的文件数控制在 30 个以内。**

如果实现一个功能需要 AI 跨越 15 个文件才能理解，这个功能的代码组织方式就需要改造。

### 5.2 文件健康度标准

| 状态 | 行数 |
|------|------|
| 最优 | 50–150 行（一个完整功能单元） |
| 可用 | 150–300 行 |
| 需关注 | 300–500 行 |
| 必须拆分 | 500+ 行 |

### 5.3 AI 友好度自检清单

在提交代码或做 Code Review 时，可以用这个清单快速自检：

- [ ] 这个文件超过 300 行了吗？如果是，能否按职责拆分？
- [ ] 这个文件的 Props 类型/接口定义是否和实现放在一起？
- [ ] 新增的约定是否更新到了 `CLAUDE.md`？
- [ ] 这个目录下有 `README.md` 吗？
- [ ] 有没有引入新的 barrel import？
- [ ] 错误处理是否足够具体（捕获了具体类型、日志包含关键上下文）？
- [ ] 新增的重要规范是否写进了 lint 规则？

### 5.4 CLAUDE.md 质量标准

一个合格的 `CLAUDE.md` 应该能回答以下问题：

1. 这个项目是什么？（一句话）
2. 技术栈是什么？（框架、状态管理、导航、样式方案）
3. 目录结构如何？（每个主要目录的职责）
4. 有哪些禁止事项？（明确列出，不要含糊）
5. 参考文件在哪里？（"写新组件请参考 X 文件"）
6. 常用命令是什么？（构建、测试、lint）

---

## 六、落地步骤

改造不需要一次性推倒重来，分三个阶段渐进推进，总体原则是**成本从低到高、收益从高到低**。

### 第一阶段：建立基础（1–2 周）

**目标：给 AI 一张地图。** 这一阶段不改一行业务代码，只做文档和配置。

**第 1 步：写 `CLAUDE.md`（1–2 天）**

在项目根目录创建 `CLAUDE.md`，按照上面的质量标准填写。如果不知道从哪里开始，可以让 AI 分析现有代码库，自动生成初稿，再由人工调整补充。

对于 React Native 项目，重点写清楚：技术栈版本、状态管理方案、导航方案、样式方案、性能禁忌（FlashList、StyleSheet.create、Reanimated）、平台差异处理约定。

**第 2 步：在主要目录下加 `README.md`（2–3 天）**

不需要全量覆盖，优先覆盖改动最频繁的目录。每个 README 只需要说明：这里有什么、命名规则、如何新增。

**第 3 步：标注参考文件（半天）**

识别项目里写得最好的那个组件/Hook/页面，在 `CLAUDE.md` 里明确指向它，作为 AI 生成新代码的参考模板。

**预期效果：** 完成这一阶段后，AI 生成的代码风格符合度会有显著提升，不再需要在每次 prompt 里重复说明项目约定。

---

### 第二阶段：建立护栏（3–4 周）

**目标：让 AI 难以犯错。** 这一阶段把重要规范从文档变成自动化约束。

**第 1 步：启用 Linter，把重要规则设为 error 级别（1 周）**

重要的规则要设置为 **error**（中断构建），而不是 warning（AI 会忽略 warning）。

对于 React Native 项目，优先把以下规则设为 error：

- 禁止 `ScrollView` 内直接 `map` 渲染列表
- 禁止内联样式对象
- 禁止 barrel imports（可用 `eslint-plugin-import` 的 `no-restricted-imports` 规则）
- 禁止 `Animated` API（统一用 Reanimated）

**如果某件事在 Code Review 时反复被提到，就把它写成 lint 规则。**

**第 2 步：建立快速验证构建（3–5 天）**

建立一个只跑 lint + 单元测试的轻量构建命令（区别于完整的 CI 构建），供 AI Agent 迭代时使用。AI 需要快速的反馈循环，完整构建太慢会降低 AI 的迭代效率。

**第 3 步：补充 TypeScript 类型覆盖（持续进行）**

TypeScript 的类型系统是防止 AI 生成错误代码的天然屏障。AI 在 TypeScript 代码库中的表现明显优于 JavaScript，因为类型系统提供了即时的错误反馈。优先为高频改动的模块补充完整的类型定义。

**预期效果：** AI 生成的代码不再需要人工纠正常见的规范违规，lint 会自动捕获并提示修复。

---

### 第三阶段：结构优化（持续进行）

**目标：从根本上降低 AI 理解代码的成本。** 这一阶段才涉及代码结构本身的改造。

**核心原则：每次修改一个模块时，顺手把它改造成 AI 友好的形式，而不是专门开一个"AI 友好化"的大项目。** 改造成本分摊到日常开发里，阻力最小。

**优先从改动最频繁的模块开始：**

对于超过 500 行的"上帝文件"，按职责拆分，每个文件只做一件事。对于深层组件继承链，考虑用组合替代继承。对于散落各处的配置，集中到一个或少数几个配置文件。

对于 React Native 项目，按功能（Feature）组织目录结构，把同一个功能的所有文件（组件、Hook、页面、类型）放在一起，而不是按文件类型分散到不同目录。每次新建功能模块时，直接按 Feature-Based 结构创建，不需要迁移旧代码。

**Props 类型迁移：** 每次修改组件时，顺手把 Props 类型从全局 `types/` 目录移到组件文件里。不需要专门开一个"重构"任务，改到哪里顺手改，积累下来效果显著。

---

## 七、React Native CLAUDE.md 模板

直接复制，按项目实际情况修改：

```markdown
# 项目：[项目名称]

## 技术栈
- React Native [版本] + TypeScript
- 状态管理：Zustand（全局）/ React Query（服务端状态）/ useState（本地）
- 导航：React Navigation v6
- 样式：StyleSheet.create（禁止内联样式对象）
- 列表：FlashList（禁止 ScrollView + map）
- 动画：Reanimated v3（禁止 Animated API）

## 目录结构
- `src/features/` - 按功能组织的业务代码，每个功能一个目录
- `src/shared/` - 跨功能共享的组件、Hook、工具函数
- `src/navigation/` - 导航配置
- 每个 feature 目录有 README.md 说明其内容

## 组件规范
- Props 类型定义紧贴组件，不放全局 types 目录
- 文件结构：imports → 类型定义 → 组件实现 → StyleSheet
- 数据逻辑抽到 Custom Hook，组件只负责渲染
- 禁止 barrel imports，使用直接路径导入

## 平台差异处理
- 平台特定代码使用 .ios.tsx / .android.tsx 后缀
- 阴影：iOS 用 shadow* 属性，Android 用 elevation，封装在 shared/styles/shadow.ts
- 键盘：KeyboardAvoidingView，iOS 用 'padding'，Android 用 'height'
- 安全区域：所有页面必须使用 SafeAreaView 或 useSafeAreaInsets

## 参考文件
- 标准组件：`src/features/product/components/ProductCard.tsx`
- 标准 Hook：`src/features/product/hooks/useProducts.ts`
- 标准页面：`src/features/product/screens/ProductDetailScreen.tsx`

## 禁止事项
- 禁止 ScrollView + map 渲染列表（使用 FlashList）
- 禁止内联样式对象（使用 StyleSheet.create）
- 禁止在组件文件外定义 Props 类型
- 禁止 barrel imports（components/index.ts 这类）
- 禁止直接使用 Animated API（统一用 Reanimated）

## 常用命令
- 启动：`yarn start`
- iOS：`yarn ios`
- Android：`yarn android`
- Lint：`yarn lint`
- 测试：`yarn test`
```

---

## 参考来源

- [Making Your Codebase LLM Friendly](https://srungta.github.io/blog/llm/llm-friendly-codebases) — Shaswat Rungta, 2026
- [Context Window Management: Building AI-Friendly Code at Scale](https://operationalsemantics.dev/posts/18-context-window-management.md/) — Myron Koch, 2025
- [AI-Ready Codebase Guide 2025](https://llmx.tech/blog/ai-ready-codebase-claude-cursor-integration-guide/) — llmx.tech
- [AI-Optimized React Development](https://zenreact.dev/blog/ai-optimized-react-development) — ZenReact
- [React Native Best Practices for AI Agents](https://www.callstack.com/blog/announcing-react-native-best-practices-for-ai-agents) — Callstack
- [Please Stop Using Barrel Files](https://tkdodo.eu/blog/please-stop-using-barrel-files) — TkDodo
- [Structuring Your Codebase for AI Tools](https://www.propelcode.ai/blog/structuring-codebases-for-ai-tools-2025-guide) — Propel, 2025
- [AI 友好架构：AI 编程最佳范式](https://cloud.tencent.com/developer/article/2517286) — Phodal / 腾讯云
- [Enterprise Coding Standards: 12 Rules for AI-Ready Teams](https://www.augmentcode.com/guides/enterprise-coding-standards-12-rules-for-ai-ready-teams) — Augment Code
- [Coding Guidelines for Your AI Agents](https://blog.jetbrains.com/idea/2025/05/coding-guidelines-for-your-ai-agents/) — JetBrains
- [How to Make Your Codebase AI Friendly](https://www.simplefrontend.dev/blog/how-to-make-your-codebase-ai-friendly/) — SimpleFrontend
