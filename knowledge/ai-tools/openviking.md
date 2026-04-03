---
title: 'OpenViking：专为 AI Agent 设计的上下文数据库'
---

# OpenViking：专为 AI Agent 设计的上下文数据库

> 整理日期：2026-03-25（基于官方文档更新，补充完整使用方法）
> 来源：[GitHub - volcengine/OpenViking](https://github.com/volcengine/OpenViking) · [DeepWiki 文档](https://deepwiki.com/volcengine/OpenViking) · [官网](https://www.openviking.ai/)

---

## 它解决了什么问题

构建 AI Agent 时，开发者面临一个根本性的困境：Agent 需要的上下文（记忆、资源、技能）散落在各处——记忆写在代码里，资源存在向量库，技能到处乱放。传统 RAG 方案用扁平的向量存储来管理这些内容，在长期、多步骤任务中暴露出几个核心问题：

**上下文碎片化**：没有统一的组织方式，Agent 无法感知内容之间的层级关系和语义结构。

**Token 消耗爆炸**：长任务产生的海量信息如果全部塞进 prompt，要么超出窗口，要么成本极高。简单截断又会丢失关键内容。

**检索质量差**：扁平向量搜索缺乏全局理解，无法利用内容的层级位置信息来提升相关性。

**不可观测**：检索链路是黑盒，难以调试和追踪 Agent 到底用了哪些上下文。

**记忆不会进化**：静态存储，没有学习循环，Agent 无法从历史对话中积累经验。

OpenViking 的核心洞察是：**把上下文管理做成一个数据库，用文件系统的范式来组织所有内容**。记忆、资源、技能，统一挂在 `viking://` 这棵虚拟目录树下。

---

## 核心设计：文件系统范式

OpenViking 的口号是 **"Memory, Resource, Skill. Everything is a File."**

所有上下文通过 `viking://` URI 协议访问，组织成一棵层级分明的虚拟目录树：

```
viking://
├── resources/          # 文档、代码、网页等外部资源
│   ├── user/
│   ├── agent/
│   └── session/
├── memories/           # 记忆（用户偏好、学习到的模式）
│   ├── preferences/
│   └── entities/
└── skills/             # 技能（能力描述、工具定义）
    ├── memories/
    └── instructions/
```

这个范式的好处是：Agent 可以用熟悉的文件操作（`ls`、`find`、`read`）来浏览和访问上下文，同时底层享有语义搜索和分层加载的能力。上下文不再是散落一地的拼图，而是一个层次分明、可导航的认知系统。

---

## 三层上下文模型（L0/L1/L2）

这是 OpenViking 最核心的技术创新，直接解决了 Token 消耗问题。

每个目录节点在写入时，会被自动处理成三个层级：

| 层级 | 名称 | 大小 | 用途 |
|------|------|------|------|
| **L0** | Abstract（摘要） | ~100 tokens | 向量搜索召回、目录列表展示 |
| **L1** | Overview（概览） | ~2000 tokens | 精排、内容导航、决策参考 |
| **L2** | Full Content（全文） | 无限制 | Agent 按需深度阅读 |

L0 和 L1 在资源写入时由 VLM（视觉语言模型）自动生成，以隐藏文件（`.abstract.md`、`.overview.md`）的形式存储在每个目录节点内。L2 就是原始内容文件本身。

**检索时的渐进式加载策略**：

1. 先用 L0 摘要做向量搜索，快速定位相关目录（成本极低）
2. 对高分目录加载 L1 概览，获取更详细的结构信息
3. 只有 Agent 明确需要时，才通过 `read()` 加载 L2 全文

这个设计让 Agent 在规划阶段只消耗少量 Token，执行阶段才按需加载细节，大幅降低了长任务的上下文成本。

---

## 安装

**系统要求**：Python 3.10+，支持 Linux（Ubuntu 20.04+）/ macOS 10.15+ / Windows 10+（推荐 WSL2）。

```bash
# 推荐方式：pip 安装（含预编译的 Go/Rust/C++ 组件，无需额外构建工具）
pip install openviking

# 或使用 uv（更快）
uv pip install openviking
```

安装包内已包含预编译的 `agfs-server`（Go）、`ov` CLI（Rust）和 C++ 向量引擎扩展，无需额外安装构建工具。

验证安装：

```bash
python -c "import openviking; print(openviking.__version__)"
ov --version
```

---

## 配置

OpenViking 使用两个 JSON 配置文件：

| 文件 | 用途 | 默认路径 |
|------|------|----------|
| `ov.conf` | SDK 嵌入模式 + 服务端配置 | `~/.openviking/ov.conf` |
| `ovcli.conf` | HTTP 客户端和 CLI 连接配置 | `~/.openviking/ovcli.conf` |

### ov.conf 基础配置

```json
{
  "embedding": {
    "dense": {
      "provider": "volcengine",
      "api_key": "your-volcengine-api-key",
      "model": "doubao-embedding-vision-250615",
      "dimension": 1024,
      "input": "multimodal"
    }
  },
  "vlm": {
    "provider": "volcengine",
    "api_key": "your-volcengine-api-key",
    "model": "doubao-seed-2-0-pro-260215"
  },
  "storage": {
    "workspace": "./data",
    "agfs": { "backend": "local" },
    "vectordb": { "backend": "local" }
  }
}
```

**使用 OpenAI 作为 Provider**：

```json
{
  "embedding": {
    "dense": {
      "provider": "openai",
      "api_key": "sk-...",
      "model": "text-embedding-3-large",
      "dimension": 3072
    }
  },
  "vlm": {
    "provider": "openai",
    "api_key": "sk-...",
    "model": "gpt-4o"
  }
}
```

支持的 Embedding Provider：`volcengine`、`openai`、`jina`、`voyage`、`vikingdb`。

### ovcli.conf（CLI/HTTP 客户端配置）

```json
{
  "url": "http://localhost:1933",
  "api_key": "your-api-key"
}
```

---

## 三种使用模式

| 模式 | 客户端类 | 适用场景 |
|------|----------|----------|
| **Embedded（嵌入式）** | `ov.OpenViking` / `SyncOpenViking` / `AsyncOpenViking` | Python 应用、Jupyter Notebook，无需启动服务 |
| **HTTP** | `SyncHTTPClient` / `AsyncHTTPClient` | 分布式部署、多实例共享 |
| **CLI** | `ov` 命令行工具 | 命令行操作、脚本自动化 |

---

## Python SDK 使用方法

### 嵌入式模式（最简单，无需启动服务）

```python
import openviking as ov

# 初始化（读取 ~/.openviking/ov.conf）
client = ov.OpenViking(path="./data")
client.initialize()

# 添加资源（本地文件、目录或 URL）
res = client.add_resource(
    path="https://raw.githubusercontent.com/volcengine/OpenViking/refs/heads/main/README.md",
    reason="project documentation",
    wait=True  # 等待 VLM 处理完成
)
root_uri = res["root_uri"]  # e.g. "viking://resources/README/"

# 也可以先提交，再等待
client.add_resource(path="./docs/")
client.wait_processed(timeout=120)

client.close()
```

### 浏览文件系统

```python
entries = client.ls(root_uri)           # 列出目录内容
tree = client.tree("viking://")         # 递归树形视图
stat = client.stat(root_uri)            # 获取元数据
matches = client.glob(pattern="**/*.md", uri=root_uri)  # glob 匹配
hits = client.grep(uri=root_uri, pattern="OpenViking")  # 内容搜索
```

### 读取三层内容

```python
abstract = client.abstract(root_uri)              # L0 摘要（~100 tokens）
overview = client.overview(root_uri)              # L1 概览（~2000 tokens）
content = client.read(root_uri, offset=0, limit=50)  # L2 全文（前50行）
```

### 语义搜索

```python
# find：无状态语义搜索
results = client.find("what is openviking", target_uri=root_uri, limit=5)
for r in results.resources:
    print(r.uri, r.score)

# search：会话感知搜索（结合对话历史）
results = client.search("how does retrieval work", session_id=session_id)
```

### 会话管理与记忆提取

```python
# 创建会话
session = client.session()
session_id = session.session_id

# 添加对话消息
client.add_message(session_id, role="user", content="Tell me about OpenViking")
client.add_message(session_id, role="assistant", content="It is an agent context store.")

# 会话感知搜索
results = client.search("how does retrieval work", session_id=session_id)

# 提交会话：归档消息，自动提取长期记忆
client.commit_session(session_id)
client.delete_session(session_id)
```

### 异步 API

```python
import asyncio
import openviking as ov

async def main():
    client = ov.AsyncOpenViking()
    await client.initialize()

    res = await client.add_resource(
        uri="viking://resources/docs/quickstart.md",
        path="/path/to/quickstart.md"
    )

    results = await client.find("how to configure storage backends", top_k=5)
    for result in results:
        print(f"Score: {result.score:.3f}, URI: {result.uri}")

    await client.close()

asyncio.run(main())
```

### HTTP 客户端模式

先启动服务端：

```bash
openviking-server  # 默认监听 http://localhost:1933
# 或后台运行
nohup openviking-server > /data/log/openviking.log 2>&1 &
```

然后用 HTTP 客户端连接：

```python
import openviking as ov

client = ov.SyncHTTPClient(
    url="http://localhost:1933",
    api_key="your-key",
    timeout=120.0,
)
client.initialize()

result = client.add_resource(
    path="https://raw.githubusercontent.com/volcengine/OpenViking/refs/heads/main/README.md",
    reason="demo resource",
    wait=True,
)
root_uri = result["root_uri"]

results = client.find("what is openviking", limit=3)
for r in results.resources:
    print(f"{r.uri}: {r.score}")

client.close()
```

---

## `ov` CLI 命令参考

`ov` 是用 Rust 编写的命令行工具，需要连接运行中的 OpenViking HTTP 服务。

**全局选项**：

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `-o` / `--output` | `table` | 输出格式：`table` 或 `json` |
| `-c` / `--compact` | `true` | 紧凑模式，简化输出 |

### 资源写入

```bash
# 添加本地文件、目录或 URL
ov add-resource <path> [--to <viking://uri>] [--reason <text>] [--wait]

# 添加技能（SKILL.md 文件或目录）
ov add-skill <data> [--wait]

# 一次性写入记忆（自动创建会话、添加消息、提交）
ov add-memory "用户偏好使用 TypeScript"
ov add-memory '{"role":"user","content":"..."}'
ov add-memory '[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]'
```

### 文件系统操作

```bash
# 列出目录
ov ls [viking://uri] [-r] [-a]   # -r 递归，-a 显示隐藏文件

# 树形视图
ov tree viking://resources/

# 创建目录
ov mkdir viking://resources/myproject/

# 删除（-r 递归删除非空目录）
ov rm viking://resources/old-doc.md
ov rm -r viking://resources/old-project/

# 移动/重命名
ov mv viking://resources/old.md viking://resources/new.md

# 查看元数据
ov stat viking://resources/README/
```

### 内容读取

```bash
# 读取 L0 摘要（~100 tokens）
ov abstract viking://resources/README/

# 读取 L1 概览（~2000 tokens）
ov overview viking://resources/README/

# 读取 L2 全文
ov read viking://resources/README/README.md
```

### 搜索

```bash
# 语义搜索
ov find "how to configure storage backends" --limit 5

# 在指定 URI 范围内搜索
ov find "authentication" --target viking://resources/docs/

# 内容 grep（正则）
ov grep viking://resources/ "OpenViking"

# glob 匹配
ov glob "**/*.md" --uri viking://resources/
```

### 会话管理

```bash
ov session new                          # 创建新会话
ov session list                         # 列出所有会话
ov session get <session_id>             # 查看会话详情
ov session add-message <id> --role user --content "..."  # 添加消息
ov session commit <session_id>          # 提交并提取记忆
ov session delete <session_id>          # 删除会话
```

### 系统状态

```bash
ov status          # 服务状态
ov health          # 健康检查
ov wait            # 等待处理队列清空
ov config show     # 查看当前配置
ov config validate # 验证配置文件
```

---

## 自动记忆迭代

OpenViking 让 Agent 能够"越用越聪明"。每次会话结束后（`session.commit()`），系统会：

1. 将对话归档到 `viking://session/{id}/history/archive_NNN/`
2. VLM 分析对话内容，提取结构化记忆
3. 向量相似度预过滤，识别潜在重复记忆
4. LLM 做最终决策：CREATE（新建）/ SKIP（跳过重复）/ MERGE（合并）/ DELETE（删除过时）
5. 记忆写入 `viking://user/memories/` 或 `viking://agent/memories/`

记忆分为两类：**用户记忆**（profile、preferences、entities、events）和 **Agent 记忆**（cases、patterns、tools、skills）。

---

## 与 OpenClaw 集成

OpenViking 可作为 OpenClaw 的长期记忆插件，替换其默认的 SQLite + Markdown 记忆方案：

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/volcengine/OpenViking/main/examples/openclaw-memory-plugin/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/volcengine/OpenViking/main/examples/openclaw-memory-plugin/install.ps1 | iex
```

安装脚本会引导配置 VLM 和 Embedding 模型（默认使用火山引擎的 doubao 系列），支持 local 模式（本地嵌入服务）和 remote 模式（连接已有 HTTP 服务）。

---

## 目录递归检索算法

传统向量搜索是扁平的相似度匹配，OpenViking 实现了一套**目录递归检索**算法，将语义搜索与层级结构理解结合起来：

1. **意图分析**：VLM 分析查询，生成 0-5 个扩展查询，覆盖不同语义角度
2. **初始定位**：对所有目录的 L0 摘要做向量搜索，找到高分目录
3. **精细探索**：在高分目录内做二次搜索，加载 L1 概览
4. **递归下钻**：对有子目录的节点，用以下公式传播分数：

   ```
   final_score = 0.5 × parent_directory_score + 0.5 × embedding_similarity
   ```

5. **结果聚合**：返回带完整层级路径信息的最相关上下文

这个"上下文加权"机制确保了：即使某个文件的向量相似度一般，只要它所在的目录语义高度相关，它也能获得更高的综合分数。

---

## 系统架构

OpenViking 是一个多语言项目，核心组件用不同语言实现：

- **Python**：核心业务逻辑、SDK、语义处理流水线
- **Go**：AGFS（Agent Global File System），分布式虚拟文件系统服务
- **Rust**：`ov` CLI 命令行工具
- **C++**：向量检索引擎（通过 pybind11 绑定到 Python）

---

## 背景信息

- **来源**：字节跳动火山引擎（Volcengine）Viking 团队，该团队从 2019 年起做上下文工程，曾开源 MineContext
- **发布时间**：2026 年 1 月正式开源
- **GitHub Stars**：18.8k（截至 2026-03-25）
- **GitHub**：[volcengine/OpenViking](https://github.com/volcengine/OpenViking)（另有镜像仓库 [Open-Viking/OpenViking](https://github.com/Open-Viking/OpenViking)）
- **官网**：[openviking.ai](https://www.openviking.ai/)
- **主要集成对象**：OpenClaw（字节系 AI 编程助手）
