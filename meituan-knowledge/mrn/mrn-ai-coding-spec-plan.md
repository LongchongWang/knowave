---
title: 'MRN AI Coding SPEC 制定计划'
---

# MRN AI Coding SPEC 制定计划

> 整理日期：2026-03-26
> 背景：为辅助 AI 写出符合美团 MRN 规范的代码，需要产出一份结构化的 SPEC 文档

---

## 一、为什么需要 SPEC

AI 写 MRN 代码面临的核心问题是**私有知识缺失**：

- AI 训练数据里有标准 React Native，但没有 `@mrn/react-native`、`NativeModules.MRNNetwork` 这些美团私有包
- AI 不知道美团的包命名规范、版本区间机制、MSI 标准桥约束
- AI 不了解团队的代码风格、目录结构约定、埋点调用方式

SPEC 的本质是**上下文构建工程**——把 AI 不知道的私有知识系统化地注入给它。

内部实践验证：医药终端、门店业务等团队通过 SPEC + Skill 方式，整体提效 40%+，首次增量代码生成率 80%~90%。

---

## 二、SPEC 的最终形态

SPEC 最终会以以下形式落地，供 AI IDE 读取：

- **Cursor**：`.cursor/rules/mrn.mdc` 或 `.cursorrules`
- **Claude Code**：`CLAUDE.md`
- **CatPaw IDE**：知识库配置 / Project Rules

建议先产出一份完整的 Markdown 文档，再按需适配到各 IDE 格式。

---

## 三、行动计划

### 第一阶段：知识收集（1~2 天）

这是决定 SPEC 质量上限的关键阶段。

#### 1.1 读 MRN 官方文档

重点读以下内容，整理成结构化笔记：

- [ ] 组件 API 列表（哪些组件可用，哪些是 MRN 特有的）
  - 文档：`https://mrn.sankuai.com/docs/`
  - 文档：`https://km.sankuai.com/space/MRNDOCS`
- [ ] 网络请求规范（`MRNNetwork.request` 的参数格式、公参注入方式）
  - 文档：`https://km.sankuai.com/docs/mrn/page/293902581#id-request`
- [ ] 路由/导航规范（`@mrn/react-navigation` 的用法，页面跳转 scheme）
- [ ] 版本区间机制（如何选择，有哪些约束）
- [ ] 埋点规范（lxTrackMPT/lxTrackModuleView 的参数格式）

#### 1.2 分析团队业务代码

找 2~3 个典型页面的代码，提炼出：

- [ ] 项目目录结构的约定（pages/components/api 的组织方式）
- [ ] 网络请求的封装方式（BaseApi 的写法，公参如何注入）
- [ ] 埋点的调用方式（lxTrackMPT 的参数格式，模块曝光 vs 点击）
- [ ] 状态管理的方案（是否用 Redux/MobX，还是纯 hooks）
- [ ] 样式的写法（StyleSheet 的使用规范，是否有设计 token）
- [ ] 路由跳转的写法（scheme 格式，参数传递方式）

#### 1.3 收集常见"坑"

这是 SPEC 中 ROI 最高的部分，找团队老同学问：

- [ ] 哪些 Web/标准 RN 的写法在 MRN 里不能用？
- [ ] 哪些组件有 MRN 特有的替代品？（如 `react-native` → `@mrn/react-native`）
- [ ] 版本区间选择有什么注意事项？
- [ ] 新架构迁移有哪些 Breaking Change？
- [ ] 网络请求公参迁移有哪些坑？

---

### 第二阶段：SPEC 撰写（1~2 天）

SPEC 是一个结构化的 Markdown 文档，放在项目根目录供 AI IDE 读取。

#### SPEC 文档结构

```markdown
# MRN 项目开发规范（AI Coding SPEC）

## 1. 项目身份声明
## 2. 包引用规范（最关键）
## 3. 目录结构规范
## 4. 组件使用规范
## 5. 网络请求规范
## 6. 路由导航规范
## 7. 埋点规范
## 8. 样式规范
## 9. 性能规范
## 10. 禁止事项（Forbidden）
## 11. 典型代码示例（最有价值）
```

#### 各章节要点

**2. 包引用规范**（最关键，防止 AI 用错包名）

```markdown
### 基础组件
- 使用 `@mrn/react-native` 而非 `react-native`
- View、Text、Image、TouchableOpacity 等从 `@mrn/react-native` 引入

### 网络请求
- 使用 `NativeModules.MRNNetwork.request({})` 或团队封装的 BaseApi
- 禁止使用 fetch、axios 等 Web 网络库

### 路由导航
- 使用 `@mrn/react-navigation`
- 页面跳转使用 scheme：[具体 scheme 格式待补充]

### 视觉组件
- 使用 `@ss/mtd-react-native` 作为 UI 组件库
```

**10. 禁止事项**（防止 AI 犯常见错误）

```markdown
- 禁止使用 `react-native` 直接引入，必须使用 `@mrn/react-native`
- 禁止使用 `fetch`/`axios`，必须使用 MRNNetwork 或 BaseApi
- 禁止使用自定义 Native 桥，必须使用 MSI 标准桥
- 禁止使用 Web 专有 API（window、document、localStorage 等）
- 样式不支持 CSS 百分比宽高（除 width: '100%'），使用 Dimensions 获取屏幕尺寸
```

**11. 典型代码示例**（最有价值，AI 从示例中学习代码风格）

需要提供以下典型场景的完整示例：
- 一个带网络请求的列表页（含下拉刷新、分页加载）
- 一个表单提交页（含输入验证、Loading 状态）
- 一个带埋点的页面（含模块曝光和点击埋点）

---

### 第三阶段：验证与迭代（持续）

#### 3.1 用真实需求测试

拿一个中等复杂度的新需求，完全用 AI + SPEC 来写，记录：
- AI 第一次生成的代码有多少比例可以直接用？
- 哪些地方 AI 还是写错了？

#### 3.2 把错误补充进 SPEC

每次发现 AI 写错的地方，就在 SPEC 里加一条"禁止/注意"规则。SPEC 是活文档，随着使用不断完善。

#### 3.3 沉淀为团队共享资产

- 将 SPEC 提交到代码仓库，让团队所有人都能用
- 定期更新（尤其是 MRN 新架构升级后）

---

## 四、关键判断：MRN 还是 Max？

SPEC 的重心取决于团队当前的技术栈状态：

| 状态 | SPEC 重心 |
|------|-----------|
| 纯 MRN 技术栈 | 重点是 `@mrn/*` 包的用法规范 |
| 已迁移到 Max | 重点是 Max DSL 的写法，以及 Max 和 MRN 组件的混用规则 |
| 正在从 MRN 迁移到 Max | SPEC 里需要明确标注"旧写法 → 新写法"的对照 |

---

## 五、参考案例

内部已有团队的 AI Coding 手册可以参考：

- 医药终端 AICoding 手册：`https://km.sankuai.com/collabpage/2715085101`（含 Project Rules 配置示例）
- 服体前端 AI Coding 手册：`https://km.sankuai.com/collabpage/2710125687`（含 Rules & Prompt 模板）
- Skills + 云端 Agent 加速技术栈收敛：`https://km.sankuai.com/collabpage/2750906782`（含 Skill 固化流程的实测数据）
- Spec Coding 技术方案设计：`https://km.sankuai.com/collabpage/2724734018`（含 SPEC 文档结构设计）
