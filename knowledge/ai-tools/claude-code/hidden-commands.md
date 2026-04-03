# Claude Code 隐藏命令与快捷键指南

> 来源：[抖音文章](https://www.douyin.com/article/7619211968238472482)  
> 整理日期：2026-03-21

---

## 背景

Claude Code 更新速度极快，很多实用功能藏在更新日志甚至开发团队的 Twitter 动态里，官方文档都来不及同步。这篇文章整理了其中最值得掌握的隐藏命令和快捷键。

官方更新日志：[https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

---

## 核心命令

### 一、`/rename` — 给当前 session 起名

**用法**：`/rename <名称>`

**解决的问题**：session 默认只有一个 UUID，没有可读的名字，时间久了根本不知道哪个 session 是干什么的。

**效果**：
- 名称会显示在终端底部的 **prompt bar** 上
- 可以用 `claude -r "名称"` 随时恢复这个 session
- 搭配 `/branch` 使用效果最佳（`/branch` 后再 `/rename`，名字才会显示在 prompt bar）

**官方推荐工作流**：`/rename` + `/clear` 组合，用于切换任务时省 token，同时保留通过名字找回 session 的能力：

```bash
/rename A任务           # 先给 session 起名
/clear                  # 清空上下文，省 token，开始做 B 任务
# ... 做 B 任务
（退出）

claude -r "A任务"       # 找回这个 session
```

**注意**：resume 回来后，Claude 会重新加载**完整历史**（A任务 + `/clear` + B任务都在），并停在 session 最末尾，而不是回到 A 任务的节点。所以这个工作流的核心价值只是**"用名字标记 session，方便之后找回"**，并不是真正意义上的"切换任务后回到 A"。

如果你想从某个节点分叉出两条完全独立的路线，应该用 `/branch`，而不是 `/clear`：

```bash
# 想保留当前进度，同时开一条新路线
/branch A任务备份       # 原 session 定格在此，新 session 继续
```

---

### 二、`/resume` — 交互式恢复历史 session

**两种触发方式，行为不同**：

| 输入方式 | 行为 |
|----------|------|
| `/resume` + 空格 | 弹出**有名字或 branch 的候选 session**（过滤后的精简列表） |
| `/resume` + 回车 | 进入**所有 session 的完整选择列表** |

**效果**：
- 显示 session 名称、时间、分支、大小等信息
- 只显示**当前目录**关联的 session（不是全局所有 session）
- 命令行也可以用 `claude --resume` 启动时选择

```bash
❯ /resume  
─────────────────────────────────────────────────────────────────────────────────────────────────────
  new-branch                 5 seconds ago · master · 17.5KB
  branch-learning (Branch)   1 minute ago · master · 17.3KB
```

> 技巧：平时用 `/resume` + 空格快速找有名字的 session；找不到时再用 `/resume` + 回车翻全部历史。

---

### 三、`/btw` — 不污染上下文的插队提问

**发布时间**：2025年3月11日

**解决的问题**：以前在 Claude 执行长任务时，如果临时插一个问题（比如"那个测试文件在哪个目录"），Claude 会停下来回答，上下文窗口里就多了一段无关对话，导致后续任务跑偏——这就是"上下文污染"。

**用法**：在 Claude 执行任务过程中，输入 `/btw` 加空格，然后写问题发送。

**效果**：
- 回答与正在执行的任务完全并行，互不干扰
- 看完回答后按空格或回车可直接消除这段对话
- 原任务继续执行，对话历史干干净净
- 几乎不消耗额外 token（复用当前提示缓存）

---

### 四、`/rewind`（或按两下 Esc）— 分别回退代码和对话

**升级时间**：2025年2月

**解决的问题**：以前只能整段对话一起回退，连之前的讨论也会丢失。

**用法**：输入 `/rewind`，弹出菜单选择回退方式：

| 选项 | 说明 |
|------|------|
| 回退代码和对话 | 完全撤销 |
| 回退对话，保留代码 | 保留代码改动，清除对话记录 |
| 回退代码，保留对话 | Claude 还记得刚才聊了什么，知道这条路不通，可以直接换方向 |
| 从该点压缩上下文 | 释放上下文窗口空间 |

**推荐场景**：让 Claude 试一种新方案，不行的话，代码回退、对话留着，Claude 知道这条路不通，可以直接换方向，不用重新解释需求。

---

### 五、`/insights` — 分析你的使用习惯

**解决的问题**：帮你发现自己的重复性操作模式，推荐更高效的工作方式。

**用法**：直接输入 `/insights`，Claude Code 会生成一份本地 HTML 报告，分析你过去一个月的使用习惯，包括：
- 最常用的命令
- 重复性操作模式
- 推荐的自定义命令和 Skills

**建议**：每个月跑一次，让 Claude Code 反向观察你，帮你重新认识自己的使用习惯。

---

### 六、`/model opusplan` — Pro 用户的省钱神器

**适用人群**：每月 $20 Pro 订阅用户

**解决的问题**：Pro 用户的 Opus 额度有限，全程用 Opus 写代码很快就会被限速。

**原理**：在需要复杂推理时自动以 plan 模式使用 Claude Opus，然后切换到 Claude Sonnet 进行执行。

**逻辑**：
- **规划阶段**：需要深度思考、理解整个项目架构和依赖关系 → 用 Opus
- **执行阶段**：具体写代码，小项目 Sonnet 完全够用，而且更快 → 用 Sonnet

> 注意：这是隐藏命令，直接 `/model` 切换模型的菜单里没有这个选项。

```bash
/model opusplan
  ⎿  Set model to Opus 4.6 in plan mode, else Sonnet 4.6
```

---

### 七、`/simplify` — 三合一代码审查

**发布时间**：2025年2月底（1月已开源，2月底集成到 Claude Code）

**用法**：输入 `/simplify` 后，Claude Code 会同时启动三个并行 Agent，分别从以下角度审查代码：
1. **代码复用**
2. **代码质量**
3. **运行效率**

**推荐用法**：每次跟 Claude Code 对话多轮、写了几个大功能更新之后，顺手跑一遍。AI 写的代码经常有微妙的冗余——多余的 import、重复的逻辑、可以更简洁的写法，`/simplify` 基本都能挑出来。

> 相当于找了三个同事同时帮你 review。`/review` 命令基本可以退休了。

---

### 八、`/branch`（原 `/fork`）— 对话分叉

**用法**：把当前对话分叉出一个新会话，原来的会话不受影响。起一个好记的名字，一般需要搭配 /resume 一起使用。

**适用场景**：聊到一半，想试另一个方向，但不想丢掉当前进度。比如 Claude 刚帮你梳理完一个方案思路，想沿着这个思路试两种不同的实现方式，`/branch` 一下，两个会话各走一边，最后挑效果好的。

**与 `/rewind` 的区别**：
- `/rewind` = 后悔药（回退）
- `/branch` = 平行宇宙（分叉）

> 打 `/fork` 还是能用，会自动跳转到 `/branch`。

```bash
❯ /branch new-branch                                                                                 
  ⎿  Branched conversation "new-branch". You are now in the branch.
     To resume the original: claude -r 46ff018a-de20-4a13-8249-d879b5be0c36

❯ /rename new-branch                                                                                 
  ⎿  Session renamed to: new-branch

─────────────────────────────────────────────────────────────────────────────────────── new-branch ──
❯ /resume  
─────────────────────────────────────────────────────────────────────────────────────────────────────
  new-branch                 5 seconds ago · master · 17.5KB
  branch-learning (Branch)   1 minute ago · master · 17.3KB
```

---

### 九、`/loop` — 定时重复执行任务

**用法**：`/loop [时间间隔] [任务描述]`

**示例**：`/loop 5m 检查一下部署状态` → 每5分钟自动执行一次，默认间隔10分钟。

**特点**：
- 结果直接在对话上下文里，Claude 可以基于结果做判断和后续操作
- 定期任务在创建 3 天后自动过期（最后触发一次后自我删除）
- 如需一直运行，使用桌面版

---

### 十、`/remote-control`（或 `/rc`）— 手机遥控

**发布时间**：2025年2月底

**用法**：在终端输入 `/rc` 或 `/remote-control`，会生成一个 URL，用手机打开即可远程操控。

**特点**：
- 手机和终端完全同步，对话历史一致
- 代码始终在电脑上跑，手机只是遥控器
- 文件系统、MCP 服务器、项目配置全部保留在本地，安全可靠

---

### 十一、`/export` — 导出对话为 Markdown

**用法**：直接输入 `/export`，当前整段对话导出为 Markdown 文件。

**推荐场景**：
- 与 Claude 讨论了半小时架构方案，有大量来回推敲，导出保存作为未来的详细 context
- 导出后扔给其他 AI（如 Codex）进行交叉验证

---

## 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+V` | 直接粘贴截图（无需先保存文件）。Debug 时截屏直接粘贴，Claude 看图说话。**Mac 用户注意是 Ctrl+V，不是 Cmd+V** |
| `Ctrl+J` 或 `Option+回车`（Mac） | 换行输入 |
| `Ctrl+R` | 搜索历史 prompt |
| `Ctrl+U` | 删除整行输入 |
| `Esc Esc`（按两下） | 等同于 `/rewind`，回退操作 |

---

## 总结

Claude Code 的更新速度已经快到让人焦虑的程度。建议：

1. 定期查看官方更新日志：[CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
2. 关注 Claude Code 开发团队在 Twitter 上的动态（经常比官方文档更早透露新功能）
3. 每月跑一次 `/insights`，发现自己的使用盲区
