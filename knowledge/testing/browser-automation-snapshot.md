# Browser Snapshot：AI Agent 操作网页的核心机制

## 什么是 Snapshot

Snapshot（快照）是 AI Agent 操作浏览器时的**核心抽象层**。它本质上是将网页的 DOM 结构转化为 AI 可理解的结构化表示，让 Agent 能够"看懂"网页并与之交互。

传统浏览器自动化（如 Selenium、Playwright 的原始 API）需要开发者编写精确的选择器（CSS Selector 或 XPath）来定位元素。但 AI Agent 无法直接"看到"网页，Snapshot 就是解决这个问题：它把网页内容转换成一种结构化的、带索引的文本表示，让 LLM 能够理解和操作。

---

## Snapshot 的工作原理

### 1. 从 DOM 到 Accessibility Tree

Snapshot 的底层基于浏览器的 **Accessibility Tree**（无障碍树）。这是浏览器为辅助技术（如屏幕阅读器）构建的一棵简化树，只包含对用户有意义的交互元素和内容。

```
原始 DOM（复杂、包含样式/脚本）
    ↓
Accessibility Tree（语义化、去噪）
    ↓
Snapshot（带索引的结构化文本）
```

### 2. Snapshot 的典型输出格式

```
[1] @e1 button "Submit"
[2] @e2 link "Home"
[3] @e3 textbox "Email"
[4] @e4 textbox "Password"
[5] @e5 checkbox "Remember me"
```

每个元素都有：
- **索引** `[N]`：人类可读的序号
- **引用 ID** `@eN` 或 `@cN`：机器可操作的引用
  - `@eN`（element）：可交互元素（按钮、链接、输入框）
  - `@cN`（content）：纯内容元素（标题、段落）
- **元素类型**：button、link、textbox、checkbox 等
- **文本内容**：元素的可见文本或标签

### 3. 为什么需要分层引用系统

```
Interactive elements: @e1, @e2, @e3... (buttons, links, inputs)
Content elements:     @c1, @c2, @c3... (headings, paragraphs, cells)
```

这种分离设计的好处：
- **减少噪音**：AI 只需要关注可交互元素来执行操作
- **节省 Token**：只输出交互元素时，Token 消耗可降低 90%+
- **语义清晰**：一眼区分"能点的"和"只能看的"

---

## Snapshot 的核心使用场景

### 场景一：表单自动化

```bash
# 1. 导航到页面
agent-browser open "https://example.com/form"

# 2. 获取 Snapshot，识别可交互元素
agent-browser snapshot -i
# 输出: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Submit"

# 3. 使用 @refs 执行操作
agent-browser fill @e1 "user@example.com"
agent-browser fill @e2 "password123"
agent-browser click @e3
```

### 场景二：数据提取

```bash
# 获取完整 Snapshot（包含内容元素）
agent-browser snapshot
# 输出包含 @c1, @c2 等文本内容引用

# 提取特定内容
agent-browser get text @c5
```

### 场景三：Diff 验证

```bash
# 基线 Snapshot
agent-browser snapshot

# 执行操作（如点击展开）
agent-browser click @e2

# 对比变化，只输出变更的部分
agent-browser diff snapshot
```

### 场景四：视觉辅助（Annotated Screenshot）

当页面有无标签的图标按钮或需要空间推理时：

```bash
agent-browser screenshot --annotate
# 输出截图 + 图例：[1] @e1 button, [2] @e2 link...
```

---

## Snapshot 模式对比

| 模式 | 命令 | Token 消耗 | 适用场景 |
|------|------|-----------|---------|
| **Interactive Only** | `-i` | ~330 | 只需要操作按钮/输入框 |
| **Compact**（默认） | `-c` | ~800-1500 | 平衡信息量与 Token |
| **Full** | `--full` | ~3750+ | 需要完整页面结构 |
| **Scoped** | `-s "#main"` | 视范围而定 | 只关注特定区域 |

### Compact 模式的智能裁剪

Compact 模式会：
1. 移除不可见元素
2. 折叠深层嵌套的非交互容器
3. 保留语义结构的同时大幅压缩体积

---

## Snapshot 的生命周期与注意事项

### Ref 的失效规则

**关键原则**：`@eN` 引用在每次 Snapshot 后都会失效

```bash
# ❌ 错误：跨 Snapshot 使用旧 ref
agent-browser snapshot
# 得到 @e5 是 "Submit" 按钮
agent-browser click @e5      # 点击后页面跳转
agent-browser click @e6      # ❌ 危险！@e6 可能指向完全不同的元素

# ✅ 正确：每次导航后重新 Snapshot
agent-browser snapshot
agent-browser click @e5
agent-browser snapshot       # 重新获取
agent-browser click @e2      # ✅ 使用新的 ref
```

### 常见陷阱

| 陷阱 | 现象 | 解决方案 |
|------|------|---------|
| Ref 漂移 | 点击后 ref 指向错误元素 | 每次导航/DOM 变化后重新 snapshot |
| 动态加载 | 元素还没出现就操作 | 使用 `wait` 或 `waitforselector` |
| 多 Tab | 点击打开新标签页 | 检查 `_tabChanged` 提示，用 `tab_close` 返回 |
| 无限滚动 | 内容随滚动加载 | 先 `scroll` 再 `snapshot` |

---

## 主流工具对比

| 工具 | Snapshot 实现 | 特点 |
|------|--------------|------|
| **agent-browser** | Accessibility Tree + 自定义 Ref 系统 | 极速（150-300ms）、Token 省 90%、支持 Diff |
| **Playwright** | `page.accessibility.snapshot()` | 原生 API，功能完整 |
| **CatPaw Desk** | 内置 browser-action | 与 IDE 集成、支持截图预览、自动会话管理 |
| **MCP Browser** | 基于 Playwright 的 MCP Server | 标准化接口，任何 MCP Client 可用 |

### agent-browser 的性能优势

基于 Vercel Labs 的 agent-browser（v0.18.0 + 增强）：

| 操作 | 耗时 |
|------|------|
| Cold open | ~2800ms |
| Snapshot (compact+interactive) | ~260ms |
| Click/Fill by ref | ~200-350ms |
| Diff snapshot | ~175ms |

相比传统 browser tool：**速度快 3-10x，Token 省 90%**

---

## Snapshot 的安全设计

### Content Boundary Markers

Snapshot 输出被随机 nonce 包裹，防止 prompt injection：

```
---PAGE-CONTENT-BEGIN-a7f3e2d1---
(snapshot content)
---PAGE-CONTENT-END-a7f3e2d1---
```

### 默认安全策略

- 禁止 `eval` 执行
- 禁止文件下载/上传（除非显式授权）
- 路径遍历防护
- Socket 认证隔离

---

## 最佳实践

1. **优先使用 Interactive Snapshot**
   ```bash
   agent-browser snapshot -i  # 只获取可交互元素
   ```

2. **批量操作减少往返**
   ```bash
   # ✅ 一次发送多个操作
   agent-browser '[{"action":"fill","selector":"@e1","value":"text"},{"action":"click","selector":"@e2"}]'
   ```

3. **操作后必须重新 Snapshot**
   ```bash
   agent-browser click @e5
   agent-browser snapshot -i  # 获取新的 refs
   ```

4. **善用 Diff 验证变化**
   ```bash
   agent-browser diff snapshot  # 只显示变更的行
   ```

5. **复杂页面使用 Scoped Snapshot**
   ```bash
   agent-browser snapshot -s "#main-content"
   ```

---

## 参考来源

- [Vercel Labs agent-browser](https://github.com/vercel-labs/agent-browser)
- [Playwright Accessibility](https://playwright.dev/docs/api/class-accessibility)
- [CatPaw Desk Browser Skill](/Users/wanglongchong/.catpaw/skills/catdesk-browser/SKILL.md)
- [agent-browser Skill (Patched)](/Users/wanglongchong/.catpaw/skills/skills-market/agent-browser/SKILL.md)
