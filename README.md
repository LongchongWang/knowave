# 个人文档中心

> 本地知识库 + 学城个人空间的统一入口

**学城个人空间**：[https://km.sankuai.com/space/~wanglongchong](https://km.sankuai.com/space/~wanglongchong)

---

## 本地目录

| 目录 | 用途 |
|------|------|
| [notes/](./notes/) | 日常笔记、随手记录 |
| [projects/](./projects/) | 项目文档、技术方案 |
| [knowledge/](./knowledge/) | 知识沉淀、学习总结 |
| [references/](./references/) | 参考资料、收藏文章 |
| [journal/](./journal/) | 工作日志、周报月报 |
| [templates/](./templates/) | 常用文档模板 |

---

## 学城文档索引

> 空间 ID：4954700 | 最后同步：2026-03-21

### 工作与项目

| 文档 | 学城链接 | 说明 |
|------|----------|------|
| Landing日志 | [🔗](https://km.sankuai.com/page/2427045911) | 持续更新中 |
| 医药开发小组 | [🔗](https://km.sankuai.com/page/2434702621) | 小组文档 |
| 医药业务 | [🔗](https://km.sankuai.com/page/2449754164) | 业务相关 |
| 一横流水线 | [🔗](https://km.sankuai.com/page/2570304902) | 流水线文档 |
| 工具架构组 | [🔗](https://km.sankuai.com/page/2745797636) | 架构组文档 |
| 需求管理 | [🔗](https://km.sankuai.com/page/2481198827) | 需求管理 |
| 技术方案 | [🔗](https://km.sankuai.com/page/2465886054) | 技术方案归档 |

### 技术知识

| 文档 | 学城链接 | 说明 |
|------|----------|------|
| Web技术 | [🔗](https://km.sankuai.com/page/2450644353) | 前端技术 |
| 微前端 | [🔗](https://km.sankuai.com/page/2656882007) | 微前端相关 |
| 服务端技术 | [🔗](https://km.sankuai.com/page/2719999043) | 后端技术 |
| 数据库 | [🔗](https://km.sankuai.com/page/2718538114) | 数据库知识 |
| AI | [🔗](https://km.sankuai.com/page/2685998478) | AI 相关 |

### 成长与规范

| 文档 | 学城链接 | 说明 |
|------|----------|------|
| 原则、规范与约定 | [🔗](https://km.sankuai.com/page/2438856079) | 个人规范 |
| 方法论 | [🔗](https://km.sankuai.com/page/2473534180) | 方法论沉淀 |
| 目标与述职 | [🔗](https://km.sankuai.com/page/2623370372) | OKR & 述职 |
| 培训材料 | [🔗](https://km.sankuai.com/page/2718783660) | 培训相关 |
| 天马行空 | [🔗](https://km.sankuai.com/page/2723195530) | 想法与创意 |

### 日常记录

| 文档 | 学城链接 | 说明 |
|------|----------|------|
| 周报 | [🔗](https://km.sankuai.com/page/2438806486) | 周报归档 |
| 我发布过的文章 | [🔗](https://km.sankuai.com/page/2740061216) | 已发布文章 |
| 我的草稿 | [🔗](https://km.sankuai.com/page/2739641344) | 草稿箱 |

---

## 快速操作

```bash
# 激活学城 CLI 工具
source ~/.meituan-local-tools/.venv/bin/activate

# 搜索学城文档
km search "关键词"

# 读取某篇文档（替换 DOC_ID）
km get DOC_ID

# 查看个人空间结构
km hierarchy-info

# 在学城创建新文档（替换 PARENT_ID）
km create --title "文档标题" --content "# 内容" --parent PARENT_ID
```

---

## 语义搜索（OpenViking）

本地文档已接入 [OpenViking](https://github.com/volcengine/OpenViking) 上下文数据库，支持自然语言语义搜索。

### 首次配置

```bash
# 1. 安装 OpenViking
pip install openviking

# 2. 设置 OpenAI API Key（写入 ~/.zshrc 或 ~/.bash_profile 永久生效）
export OPENAI_API_KEY=sk-...

# 3. 一次性导入所有本地文档（需要几分钟，会调用 OpenAI API 生成摘要）
python openviking/ingest.py
```

### 日常使用

```bash
# 语义搜索（自然语言提问）
python openviking/search.py "测试框架怎么选"
python openviking/search.py "AI Agent 如何管理记忆" --limit 8
python openviking/search.py "拖延症" --show-content

# 交互式搜索模式（连续提问）
python openviking/search.py

# 查看已导入的文档结构
python openviking/ingest.py --status

# 增量导入新文档
python openviking/ingest.py --file knowledge/ai-tools/openviking.md
python openviking/ingest.py --dir knowledge/ai-tools
```

### 配置说明

配置文件位于 `openviking/ov.conf`，当前使用 OpenAI：
- **Embedding 模型**：`text-embedding-3-small`（1536 维）
- **VLM 模型**：`gpt-4o-mini`（用于生成 L0/L1 摘要）
- **向量数据库**：本地存储，数据位于 `openviking/data/`

> 如需切换到其他模型（如 Ollama 本地模型），修改 `openviking/ov.conf` 中的 `embedding` 和 `vlm` 配置即可。
