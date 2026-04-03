# SQLite 全方位指南：写给前端开发者

> 整理日期：2026-04-01  
> 参考来源：[SQLite 官网](https://sqlite.org)、[SQLite 架构文档](https://sqlite.org/arch.html)、[SQLite 适用场景](https://sqlite.org/whentouse.html)、[better-sqlite3 GitHub](https://github.com/WiseLibs/better-sqlite3)、[Node.js SQLite 文档](https://nodejs.org/api/sqlite.html)、[SQLite Driver Benchmark](https://sqg.dev/blog/sqlite-driver-benchmark/)、[Forward Email 生产优化指南](https://forwardemail.net/en/blog/docs/sqlite-performance-optimization-pragma-chacha20-production-guide)

---

## 一、SQLite 是什么，它解决了什么问题

在理解 SQLite 之前，先想清楚它的竞争对手是谁。

MySQL、PostgreSQL、SQL Server 这些数据库，本质上是**客户端/服务器架构**：数据库是一个独立运行的进程（服务器），你的应用通过网络连接去访问它。这套架构为多用户并发、集中管理、横向扩展而设计，代价是复杂性——你需要安装、配置、维护一个独立的服务。

SQLite 不走这条路。它的官方文档有一句话说得很直白：

> **SQLite does not compete with client/server databases. SQLite competes with `fopen()`.**

SQLite 的竞争对手是文件读写。它是一个**嵌入式数据库**，整个数据库引擎是一个 C 语言库，直接链接进你的应用程序里。数据库就是磁盘上的一个 `.db` 文件，没有独立进程，没有网络连接，没有任何配置。

这个设计决策带来了一系列特性：

**零配置**：不需要安装，不需要启动服务，不需要创建用户和权限。引入库，打开文件，直接用。

**单文件**：整个数据库（所有表、索引、数据）存在一个文件里。备份就是复制文件，迁移就是移动文件，分享就是发送文件。

**极小体积**：完整的 SQLite 库编译后不到 1MB。这也是为什么它被内置进了 Android、iOS、macOS、Windows、Firefox、Chrome 等几乎所有主流平台和应用。

**可靠性极高**：SQLite 的测试代码量是源代码的 600 倍以上，是世界上测试最充分的软件之一。它支持完整的 ACID 事务，即使进程崩溃或断电，数据也不会损坏。

---

## 二、SQLite 的内部架构

理解 SQLite 的工作原理，有助于你在遇到性能问题时知道从哪里入手。

SQLite 的工作流程是：**SQL 文本 → 字节码 → 虚拟机执行**。

当你执行一条 SQL 语句时，它先经过**分词器（Tokenizer）**拆成 token，再经过**解析器（Parser）**构建语法树，然后**代码生成器（Code Generator）**将语法树编译成字节码，最后由**虚拟机（VDBE, Virtual Database Engine）**执行这段字节码。

代码生成器里有一个**查询规划器（Query Planner）**，它负责从数百万种可能的执行路径中选出最优的一条。这就是为什么加索引、写 `EXPLAIN QUERY PLAN` 能帮助你理解和优化查询。

在存储层，SQLite 使用 **B-Tree** 结构存储数据。每张表和每个索引都是一棵独立的 B-Tree，所有 B-Tree 共享同一个磁盘文件。B-Tree 以固定大小的**页（Page）**为单位读写磁盘，默认页大小是 4096 字节。

**页缓存（Page Cache）**负责缓存最近访问的页，减少磁盘 I/O。这是 SQLite 性能调优的重要抓手之一。

**VFS（Virtual File System）**是 SQLite 与操作系统之间的抽象层，让 SQLite 可以跨平台运行，也允许开发者替换底层 I/O 实现（比如实现内存数据库）。

---

## 三、SQLite 适合什么场景，不适合什么场景

### 适合的场景

**本地应用的数据存储**：桌面应用、Electron 应用、移动 App，需要在本地持久化结构化数据，SQLite 是首选。比 JSON 文件更强大（支持查询、索引、事务），比 MySQL 更轻量（无需独立服务）。

**中低流量网站的后端**：官方文档说，每天请求量低于 10 万次的网站用 SQLite 完全没问题。SQLite 官网本身就用 SQLite，每天处理 40-50 万次 HTTP 请求。

**工具脚本和数据分析**：需要对大量数据做切片、聚合、关联查询时，把数据导入 SQLite 再用 SQL 分析，比手写 JavaScript 循环高效得多。

**测试和开发环境**：用 SQLite 替代 PostgreSQL/MySQL 做本地开发和测试，零配置，速度快，测试完删掉文件就干净了。

**嵌入式设备和 IoT**：SQLite 运行在手机、电视、汽车、传感器里，不需要网络，不需要管理员。

**每用户独立数据库**：一个用户一个 SQLite 文件，天然隔离，并发问题大幅简化。Forward Email 就是这样用的——每个邮箱账户一个独立的 SQLite 数据库文件。

### 不适合的场景

**高并发写入**：SQLite 同一时刻只允许一个写操作。读操作可以并发，但写操作是串行的。如果你的应用有大量并发写入（比如多个进程同时写同一个数据库），SQLite 会成为瓶颈。

**多机共享数据库**：SQLite 依赖文件系统锁，网络文件系统（NFS、SMB）的锁实现通常有 bug，在网络文件系统上使用 SQLite 可能导致数据损坏。

**超大数据集**：SQLite 理论上支持 281TB 的数据库，但单文件的限制意味着你无法像 PostgreSQL 那样把数据分散到多个磁盘。

---

## 四、在 Node.js 中使用 SQLite

### 选哪个库？

Node.js 生态里有四个主要选项：

**better-sqlite3**：目前最推荐的选择。同步 API，性能最好，API 设计简洁。在几乎所有操作上都比其他库快 10-40%。缺点是需要编译原生模块（Node.js 版本升级时可能需要重新编译）。

**node:sqlite**：Node.js 22.5+ 内置的 SQLite 模块，无需安装任何依赖。同步 API，性能接近 better-sqlite3（约慢 10-35%）。适合不想引入原生依赖的场景，或者工具脚本。注意：Node.js v22/v24 存在 SELECT 性能回归问题（比 v20 慢约 57%），生产环境建议用 Node.js v20。

**libSQL**：Turso 团队开发的 SQLite 开源 fork，异步 API，同时支持本地文件和远程 Turso 服务器。适合需要云端同步的场景。本地性能比 better-sqlite3 慢很多（约慢 10-20 倍）。

**sqlite3（node-sqlite3）**：老牌库，异步回调 API，性能不如 better-sqlite3，不推荐新项目使用。

**结论**：新项目首选 `better-sqlite3`，如果不想引入原生依赖且 Node.js >= 22.5，可以用 `node:sqlite`。

### better-sqlite3 快速上手

```bash
npm install better-sqlite3
```

```javascript
const Database = require('better-sqlite3');

// 打开数据库（文件不存在会自动创建）
const db = new Database('myapp.db');

// 建表
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at INTEGER DEFAULT (unixepoch())
  )
`);

// 插入数据（使用 prepare + run，防止 SQL 注入）
const insertUser = db.prepare('INSERT INTO users (name, email) VALUES (?, ?)');
const result = insertUser.run('张三', 'zhangsan@example.com');
console.log(result.lastInsertRowid); // 新插入行的 ID

// 查询单条
const getUser = db.prepare('SELECT * FROM users WHERE id = ?');
const user = getUser.get(1);
console.log(user); // { id: 1, name: '张三', email: '...', created_at: ... }

// 查询多条
const getAllUsers = db.prepare('SELECT * FROM users ORDER BY created_at DESC');
const users = getAllUsers.all();

// 事务（批量操作必用，性能提升巨大）
const insertMany = db.transaction((users) => {
  for (const user of users) {
    insertUser.run(user.name, user.email);
  }
});

insertMany([
  { name: '李四', email: 'lisi@example.com' },
  { name: '王五', email: 'wangwu@example.com' },
]);

// 关闭数据库
db.close();
```

### node:sqlite 快速上手（Node.js >= 22.5）

```javascript
import { DatabaseSync } from 'node:sqlite';

const db = new DatabaseSync('myapp.db');

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
  )
`);

const insert = db.prepare('INSERT INTO users (name) VALUES (?)');
insert.run('张三');

const getAll = db.prepare('SELECT * FROM users');
const users = getAll.all();
console.log(users);

db.close();
```

---

## 五、PRAGMA：SQLite 的调优旋钮

PRAGMA 是 SQLite 特有的配置命令，相当于数据库的"设置项"。正确配置 PRAGMA 能让性能提升数倍。

### WAL 模式（最重要的一个）

```sql
PRAGMA journal_mode = WAL;
```

SQLite 默认使用**回滚日志（Rollback Journal）**模式：写数据前先把原始数据备份到 journal 文件，写完后删除 journal。这种模式下，写操作会阻塞所有读操作。

**WAL（Write-Ahead Logging，预写日志）**模式完全不同：写操作先追加到 WAL 文件，读操作继续读原始数据库文件，两者互不阻塞。这让并发读写性能大幅提升（官方数据约 +40%）。

WAL 模式的代价是会产生额外的 `-wal` 和 `-shm` 文件，但这是正常现象，不用担心。

### 生产环境推荐配置

```javascript
// 打开数据库后立即执行
db.pragma('journal_mode = WAL');
db.pragma('synchronous = NORMAL');    // 平衡安全性和性能（默认 FULL 太慢）
db.pragma('foreign_keys = ON');       // 启用外键约束（默认关闭！）
db.pragma('busy_timeout = 30000');    // 等待锁超时 30 秒，避免 SQLITE_BUSY 错误
db.pragma('cache_size = -64000');     // 64MB 页缓存（负数表示 KB）
db.pragma('temp_store = MEMORY');     // 临时表存内存（小数据库适用）
```

**关于 `synchronous`**：
- `FULL`（默认）：每次写操作都等待磁盘确认，最安全，最慢
- `NORMAL`：大多数情况下安全，性能约是 FULL 的 3 倍，推荐
- `OFF`：最快，但断电可能损坏数据库，不推荐生产使用

**关于 `foreign_keys`**：SQLite 默认**不启用**外键约束，这是一个容易踩的坑。如果你的表有外键关系，必须手动开启。

### 事务的重要性

SQLite 的写操作如果不在事务里，每条语句都会自动开启并提交一个事务，而每次提交都涉及磁盘 fsync。插入 1000 条数据，不用事务可能需要几秒，用事务只需要几毫秒。

```javascript
// 慢：每条 INSERT 都是独立事务
for (const item of items) {
  db.prepare('INSERT INTO ...').run(item);
}

// 快：所有 INSERT 在一个事务里
const insert = db.prepare('INSERT INTO ...');
const insertAll = db.transaction((items) => {
  for (const item of items) insert.run(item);
});
insertAll(items);
```

---

## 六、数据类型：SQLite 的"动态类型"

SQLite 的类型系统和其他数据库不一样，理解这一点能避免很多困惑。

SQLite 使用**类型亲和性（Type Affinity）**而非严格类型。列的类型声明只是一个"建议"，实际存储的值可以是任意类型。SQLite 有五种存储类型：`NULL`、`INTEGER`、`REAL`、`TEXT`、`BLOB`。

常见的类型声明会被映射到这五种存储类型：
- `INT`、`INTEGER`、`BIGINT` → INTEGER
- `REAL`、`FLOAT`、`DOUBLE` → REAL
- `TEXT`、`VARCHAR`、`CHAR` → TEXT
- `BLOB` → BLOB
- `BOOLEAN` → INTEGER（0 或 1）
- `DATETIME`、`TIMESTAMP` → 通常存为 TEXT（ISO 8601）或 INTEGER（Unix 时间戳）

**日期时间的处理**：SQLite 没有专门的日期类型。推荐用 `INTEGER` 存 Unix 时间戳（`unixepoch()`），查询效率高，排序方便。

```sql
-- 推荐：存 Unix 时间戳
created_at INTEGER DEFAULT (unixepoch())

-- 查询最近 7 天
SELECT * FROM posts WHERE created_at > unixepoch('now', '-7 days')
```

---

## 七、索引与查询优化

### 什么时候需要索引

索引是用空间换时间。没有索引的查询会做全表扫描（O(n)），有索引的查询是 B-Tree 查找（O(log n)）。

需要加索引的场景：
- `WHERE` 子句中频繁出现的列
- `ORDER BY` 的列（避免排序操作）
- `JOIN` 的关联列
- `UNIQUE` 约束（SQLite 自动创建）

```sql
-- 为 email 列创建唯一索引
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- 为 user_id + created_at 创建复合索引（适合"某用户的最新帖子"这类查询）
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at DESC);
```

### EXPLAIN QUERY PLAN

```sql
EXPLAIN QUERY PLAN
SELECT * FROM posts WHERE user_id = 1 ORDER BY created_at DESC;
```

输出中看到 `SCAN` 说明在全表扫描，看到 `SEARCH` 说明在用索引。

---

## 八、常见陷阱

**陷阱一：忘记开启外键约束**。SQLite 默认不检查外键，`PRAGMA foreign_keys = ON` 必须在每次打开数据库连接后执行（不是持久化的）。

**陷阱二：并发写入导致 `SQLITE_BUSY`**。多个进程/线程同时写同一个数据库时，后来的写操作会等待锁。设置 `busy_timeout` 让它等待而不是立即报错。如果并发写入很频繁，考虑用连接池或者改用 PostgreSQL。

**陷阱三：不用事务做批量插入**。如前所述，不用事务的批量插入极慢。

**陷阱四：在 WAL 模式下删除 `-wal` 和 `-shm` 文件**。这两个文件是 WAL 模式的一部分，不能手动删除。正确关闭数据库连接后，SQLite 会自动合并它们。

**陷阱五：在 Electron/Node.js 版本升级后原生模块失效**。better-sqlite3 是原生模块，Node.js 或 Electron 版本升级后需要重新编译：`npm rebuild better-sqlite3`。

---

## 九、与 ORM 配合使用

如果不想手写 SQL，可以配合 ORM 使用。

**Drizzle ORM**：目前最受前端开发者欢迎的 TypeScript ORM，类型安全，API 接近 SQL，支持 better-sqlite3 和 node:sqlite。

```typescript
import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

const sqlite = new Database('myapp.db');
const db = drizzle(sqlite);

const users = sqliteTable('users', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
});

// 类型安全的查询
const allUsers = await db.select().from(users);
```

**Prisma**：功能更全面的 ORM，支持 SQLite，适合需要数据库迁移管理的项目。

**Kysely**：SQL 查询构建器（不是完整 ORM），类型安全，比 ORM 更接近原生 SQL，适合喜欢控制 SQL 的开发者。

---

## 十、SQLite 在前端生态的新动向

**Turso**：基于 libSQL（SQLite fork）的云数据库服务，提供"边缘 SQLite"——数据库部署在离用户最近的边缘节点，延迟极低。适合全球分布的应用。

**Cloudflare D1**：Cloudflare Workers 的内置 SQLite 数据库，在边缘运行，与 Workers 深度集成。

**Electric SQL / PowerSync**：本地优先（Local-First）架构的同步层，让 SQLite 数据库在客户端和服务端之间自动同步，实现离线优先的应用。

**Bun 内置 SQLite**：Bun 运行时内置了 SQLite 支持（`bun:sqlite`），API 与 better-sqlite3 类似，性能极高。

这些新动向的共同趋势是：**把 SQLite 从"本地小数据库"扩展到"分布式、可同步的数据层"**。

---

## 十一、选型决策框架

```
你的数据需要在多台服务器之间共享？
  → 是：用 PostgreSQL/MySQL
  → 否：继续

你的应用有大量并发写入（每秒数百次写操作）？
  → 是：用 PostgreSQL/MySQL
  → 否：继续

你的数据库文件会超过几十 GB？
  → 是：考虑 PostgreSQL
  → 否：SQLite 完全够用

→ 用 SQLite
```

对于大多数前端开发者做的项目——个人工具、Electron 应用、中小型 Web 服务、CLI 工具、本地数据处理——SQLite 是最省心的选择。

---

## 参考资料

- [SQLite 官网](https://sqlite.org)
- [SQLite 架构文档](https://sqlite.org/arch.html)
- [SQLite 适用场景](https://sqlite.org/whentouse.html)
- [better-sqlite3 GitHub](https://github.com/WiseLibs/better-sqlite3)
- [Node.js 内置 SQLite 文档](https://nodejs.org/api/sqlite.html)
- [SQLite Driver Benchmark（2026）](https://sqg.dev/blog/sqlite-driver-benchmark/)
- [Forward Email SQLite 生产优化指南](https://forwardemail.net/en/blog/docs/sqlite-performance-optimization-pragma-chacha20-production-guide)
