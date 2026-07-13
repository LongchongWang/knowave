# Binlog 与 CDC：MySQL 增量数据同步的底层逻辑

> 整理日期：2026-06-24
> 来源：MySQL 官方文档、Canal GitHub 仓库、Debezium 官方文档、阿里云 DTS 产品文档

## 这篇文章在讲什么

当你在做业务系统时迟早会遇到一个问题：数据库里的数据变了，怎么让其他系统（缓存、搜索引擎、数据仓库）也跟着变？最朴素的办法是轮询——定时去数据库扫一遍，找出变化。但轮询有天然的延迟问题，而且对数据库是额外负担。更优雅的方案是监听数据库的变更日志，让数据库自己告诉你哪些数据变了。这就是 CDC（Change Data Capture，变更数据捕获）的核心思路，而 MySQL 的 Binlog 则是这条路上最重要的基础设施。

这篇文章从 Binlog 的底层机制讲起，再延伸到基于 Binlog 的 CDC 工具生态（Canal、Debezium、DTS），帮你建立完整的认知框架。

---

## 一、Binlog 是什么

Binlog（Binary Log，二进制日志）是 MySQL Server 层维护的一份变更记录。注意这里说的是"Server 层"而不是"存储引擎层"——这意味着无论你用 InnoDB 还是 MyISAM，只要通过 MySQL Server 执行了写操作，都会被记录到 Binlog 中。这一点很重要，它与 InnoDB 自己的 Redo Log（重做日志）是两回事：Redo Log 是存储引擎层面的崩溃恢复机制，Binlog 是 Server 层面的逻辑变更记录。

Binlog 最初的设计目标有两个：一是主从复制（Replication），二是数据恢复（Point-in-Time Recovery）。但随着分布式架构的普及，Binlog 被赋予了第三个角色——作为 CDC 的数据源，驱动各种下游系统的数据同步。

### 1.1 三种 Binlog 格式

MySQL 支持三种 Binlog 格式，通过 `binlog_format` 参数控制：

**STATEMENT 格式** 记录的是 SQL 语句本身。比如执行 `UPDATE user SET age = age + 1 WHERE city = 'Beijing'`，Binlog 里存的就是这条 SQL。优点是日志量小，缺点是存在不确定性——如果 SQL 中用了 `NOW()`、`UUID()`、`RAND()` 等非确定性函数，从库重放时结果可能不一致。

**ROW 格式** 记录的是每一行数据变更前后的完整内容。同样是上面那条 UPDATE，如果影响了 1000 行，Binlog 里就会有 1000 条记录，每条都包含变更前的值和变更后的值。日志量显著增大，但能保证绝对的一致性。这是 CDC 场景的首选格式，因为下游系统需要精确知道每一行数据的变化。

**MIXED 格式** 是前两者的自动混合：一般的 SQL 用 STATEMENT 格式记录，遇到非确定性函数等场景自动切换为 ROW 格式。看似两全其美，但在 CDC 场景下不够可靠——因为你无法保证所有变更都以 ROW 格式记录。

在生产环境中，如果你打算基于 Binlog 做数据同步，**必须将 `binlog_format` 设置为 ROW**。这一点所有 CDC 工具都会作为前置条件检查。

### 1.2 Binlog 的事件结构

Binlog 文件由一系列事件（Event）组成。ROW 格式下，核心的事件类型包括：

- **FORMAT_DESCRIPTION_EVENT**：文件头，描述 Binlog 版本等元信息
- **TABLE_MAP_EVENT**：定义后续行事件对应的表结构（库名、表名、列类型）
- **WRITE_ROWS_EVENT**：INSERT 操作，包含新增行的完整数据
- **UPDATE_ROWS_EVENT**：UPDATE 操作，包含变更前和变更后的行数据
- **DELETE_ROWS_EVENT**：DELETE 操作，包含被删除行的完整数据
- **QUERY_EVENT**：DDL 语句（CREATE/ALTER/DROP 等）
- **XID_EVENT**：事务提交标记

理解这个结构很重要——它决定了 CDC 工具能提供什么样的信息。ROW 格式下，UPDATE 事件同时包含 before 和 after 数据，这让下游系统可以做差异比较、审计日志、条件过滤等高级处理。

### 1.3 主从复制：Binlog 的原始用法

在讨论 CDC 之前，先理解 MySQL 主从复制的流程，因为几乎所有 CDC 工具都是在模拟这个流程：

1. **主库** 把所有写操作记录到 Binlog 文件
2. **从库** 的 IO 线程连接主库，发送 `COM_BINLOG_DUMP` 命令，请求从某个位点开始读取 Binlog
3. 主库的 **Binlog Dump 线程** 把 Binlog 事件推送给从库
4. 从库的 IO 线程把收到的事件写入本地的 **Relay Log**（中继日志）
5. 从库的 **SQL 线程** 读取 Relay Log，重放其中的操作，使数据与主库保持一致

CDC 工具的核心思路就是在第 2 步"伪装"成一个从库，骗过主库，拿到 Binlog 数据流。拿到数据后不是重放 SQL，而是解析成结构化的变更事件，发送给下游系统。

---

## 二、Java 生态中的 Binlog 解析

### 2.1 底层库：mysql-binlog-connector-java

在 Java 生态中，解析 MySQL Binlog 的底层库是 `mysql-binlog-connector-java`（GitHub: shyiko/mysql-binlog-connector-java）。这个库实现了 MySQL 客户端/服务器协议中的 Binlog 复制部分，能够连接 MySQL 并以事件流的方式接收和解析 Binlog。

基本用法非常简洁：

```java
BinaryLogClient client = new BinaryLogClient("hostname", 3306, "username", "password");
client.registerEventListener(event -> {
    EventData data = event.getData();
    if (data instanceof WriteRowsEventData) {
        // 处理 INSERT 事件
    } else if (data instanceof UpdateRowsEventData) {
        // 处理 UPDATE 事件，包含 before/after 数据
    } else if (data instanceof DeleteRowsEventData) {
        // 处理 DELETE 事件
    }
});
client.connect();
```

这个库支持直接连接 MySQL 实时接收 Binlog 事件，也支持解析离线的 Binlog 文件。它是 Canal、Debezium（MySQL Connector）、Maxwell 等上层工具的共同底层依赖。

但直接使用这个底层库做生产级数据同步并不现实——你需要自己处理位点管理（记住消费到哪里了）、故障恢复、高可用、数据过滤、格式转换等一系列问题。这就是 Canal 和 Debezium 这类上层框架存在的意义。

### 2.2 Canal：阿里巴巴的 Binlog 解析器

Canal（GitHub: alibaba/canal）是阿里巴巴在 2013 年开源的 MySQL 增量数据订阅与消费组件。它的名字取"水道/管道"之意，核心定位是 MySQL Binlog 的解析和投递。

**工作原理**可以用一句话概括：Canal 伪装成一个 MySQL 从库，通过 MySQL 的主从复制协议获取 Binlog，解析后以结构化事件的形式提供给下游消费。

具体流程是这样的：Canal Server 启动后，向 MySQL 主库发送 `COM_BINLOG_DUMP` 命令（和真正的从库完全一样），MySQL 主库验证通过后开始推送 Binlog 事件。Canal 内置的 Parser 模块负责解析这些二进制事件，提取出表名、操作类型、变更前后的行数据等结构化信息，存入内存环形缓冲区（基于 Disruptor 实现）。下游的客户端（Canal Client）通过 TCP 协议或消息队列（Kafka/RocketMQ）来消费这些事件。

**Canal 的架构**分为三个核心角色：

- **Canal Server**：负责连接 MySQL、解析 Binlog、缓存事件。一个 Server 可以管理多个 Instance，每个 Instance 对应一个 MySQL 数据源。
- **Canal Client**：消费端，通过 `CanalConnector` API 拉取事件。支持批量获取（`getWithoutAck`）和消费确认（`ack`），保证不丢数据。
- **Canal Admin**（可选）：提供 Web 管理界面，管理 Server 和 Instance 的配置。

Canal 在国内的 Java 技术栈中使用非常广泛，主要因为它诞生于阿里内部的实际业务需求（跨机房数据同步），经过了海量数据的生产验证。但它也有明显的局限：只支持 MySQL 作为数据源，不支持 PostgreSQL、MongoDB 等其他数据库。

**关键配置**（让 Canal 正常工作的前提）：

```ini
# MySQL 侧必须开启 Binlog 并设为 ROW 格式
[mysqld]
log-bin=mysql-bin
binlog-format=ROW
server-id=1

# 创建 Canal 专用用户并授权
GRANT SELECT, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'canal'@'%';
```

```properties
# Canal 实例配置（instance.properties）
canal.instance.master.address=127.0.0.1:3306
canal.instance.dbUsername=canal
canal.instance.dbPassword=canal
canal.instance.filter.regex=.*\\..*  # 监听所有库所有表
```

### 2.3 Debezium：Red Hat 的通用 CDC 平台

Debezium（GitHub: debezium/debezium）是 Red Hat 开源的 CDC 平台，定位比 Canal 更广：它不仅支持 MySQL，还支持 PostgreSQL、MongoDB、Oracle、SQL Server、Cassandra 等十多种数据库。

Debezium 的架构与 Canal 有本质不同。Canal 是一个独立的服务，自己管理与 MySQL 的连接和事件缓冲；Debezium 的主部署方式是作为 **Kafka Connect** 的 **Source Connector** 运行——它把自己嵌入 Kafka Connect 框架中，利用 Kafka Connect 提供的分布式任务调度、位点管理、容错恢复等基础设施。

换句话说，Debezium 的典型数据流是：**Source DB → Debezium Connector（运行在 Kafka Connect 中）→ Kafka Topic → 下游消费者**。每张表的变更事件会被发送到对应的 Kafka Topic 中，变更事件采用统一的 JSON/Avro 格式，包含 `before`（变更前数据）、`after`（变更后数据）、`source`（源信息，如 Binlog 文件名和位点）、`op`（操作类型：c/u/d/r）等字段。

Debezium 的 MySQL Connector 底层同样是使用 `mysql-binlog-connector-java` 库来解析 Binlog，但在此之上增加了 Schema 历史管理（跟踪表结构变化）、Snapshot 全量快照（首次启动时全量读取存量数据）、心跳机制等生产级特性。

**Canal 与 Debezium 的核心差异**可以这样理解：Canal 是"专注 MySQL 的轻量级方案"，Debezium 是"Kafka 生态下的通用 CDC 平台"。如果你的技术栈以 Java + MySQL 为主，没有 Kafka 依赖，Canal 更轻便；如果已经在用 Kafka，或者需要对接多种数据库，Debezium 是更合理的选择。

---

## 三、DTS：云厂商的托管方案

DTS（Data Transmission Service，数据传输服务）是云厂商提供的托管式数据传输产品。阿里云和腾讯云都有同名产品，核心能力大同小异。本节以阿里云 DTS 为例说明。

### 3.1 DTS 解决的问题

Canal 和 Debezium 都是开源的自建方案，你需要自己部署、运维、监控、处理故障。在云环境下，DTS 提供了"开箱即用"的替代方案——你只需要在控制台配置源端和目标端，DTS 就能自动完成数据传输。

DTS 的三大核心功能：

**数据迁移（Migration）**：将数据从一个数据库迁移到另一个数据库，支持全量迁移 + 增量迁移。典型场景是上云迁移（本地 MySQL → 阿里云 RDS）或数据库版本升级。增量迁移的底层原理就是解析源端 Binlog，和 Canal 的机制一样。迁移过程中业务不需要停机，DTS 会先迁移存量数据，再持续同步增量数据，最后在切换时保证数据一致。

**数据同步（Synchronization）**：建立源端和目标端之间的持续同步关系。和迁移不同，同步是"常驻"的——数据源一直在变，同步也一直在进行。典型场景包括异地容灾（跨地域同步）、读写分离（主库写 → 从库读）、分析型同步（MySQL → AnalyticDB/Elasticsearch/Kafka）。

**数据订阅（Change Tracking）**：本质上就是托管版的 CDC。DTS 捕获源端数据库的 Binlog 变更，以消息流的形式提供给消费端。消费端通过 DTS 提供的 SDK 拉取变更事件，进行业务处理。这和 Canal Client 消费 Canal Server 的模式非常相似，区别在于 DTS 的服务端是云厂商维护的，你不需要关心部署和运维。

### 3.2 DTS 的架构设计

DTS 的内部架构遵循典型的 CDC 管道模式：

1. **采集模块**：连接源数据库，实时采集 Binlog（MySQL）或 WAL（PostgreSQL）等变更日志
2. **存储模块**：将采集到的变更事件持久化到内部存储（通常是分布式消息队列），保证数据不丢
3. **投递模块**：将变更事件写入目标端（数据库、消息队列、搜索引擎等）
4. **校验模块**：在迁移/同步过程中进行数据一致性校验，确保源端和目标端数据一致

每个模块都做了冗余设计（主备部署），单个模块故障时自动切换，对用户透明。

### 3.3 DTS vs 自建 CDC 的取舍

选择 DTS 还是自建 Canal/Debezium，本质上是"运维成本 vs 灵活度"的权衡：

DTS 的优势在于免运维、开箱即用、与云数据库深度集成（无需额外配置权限和网络），适合云上业务快速搭建数据管道。劣势在于厂商锁定、按流量/实例计费（成本随数据量增长）、自定义能力有限（你无法深度定制数据转换逻辑）。

自建方案（Canal/Debezium）的优势在于完全可控、免费、可深度定制。劣势在于运维负担重——你需要自己处理高可用、监控告警、位点管理、版本升级等问题，在大规模场景下运维成本可能远超 DTS 的费用。

一个实用的选型思路：如果是初创团队或中小规模业务，优先用 DTS 快速上线；如果是大厂有专业的中间件团队，或者需要深度定制的数据处理逻辑，自建方案更合适。

---

## 四、CDC 工具选型速览

除了 Canal、Debezium、DTS，CDC 领域还有几个值得了解的工具：

**Maxwell**（GitHub: zendesk/maxwell）是 Zendesk 开源的轻量级 MySQL CDC 工具。和 Canal 类似也是解析 MySQL Binlog，但设计理念更简单——它直接把变更事件以 JSON 格式发送到 Kafka/Redis/RabbitMQ 等，不需要额外的客户端 SDK。适合想快速把 MySQL 变更投递到 Kafka 的场景，但功能不如 Canal 丰富（不支持 TCP 模式、不支持表级别的精细过滤）。

**Flink CDC**（GitHub: apache/flink-cdc）是 Apache Flink 社区推出的 CDC Connector 集合，底层集成了 Debezium。它的特点是把 CDC 数据源直接接入 Flink 的流处理管道，支持全量 + 增量的无缝切换，且在 Flink CDC 2.0 之后实现了无锁读取（不需要全局锁做 Snapshot），对生产库更友好。如果你已经在用 Flink 做流处理，Flink CDC 是最自然的选择。

**各工具核心对比**：

| 维度 | Canal | Debezium | Maxwell | DTS |
|------|-------|----------|---------|-----|
| 数据源 | 仅 MySQL | MySQL/PG/MongoDB/Oracle/SQL Server 等 | 仅 MySQL | 取决于云厂商，通常覆盖主流数据库 |
| 下游投递 | TCP Client / Kafka / RocketMQ | Kafka（原生）| Kafka / Redis / RabbitMQ | 数据库 / MQ / 搜索引擎等 |
| 全量快照 | 不支持（需自行处理）| 支持 | 支持 | 支持 |
| Schema 变更跟踪 | 有限支持 | 完善（维护 Schema 历史）| 基础支持 | 完善 |
| 部署方式 | 独立服务 | Kafka Connect Connector | 独立服务 | 云服务（SaaS）|
| 开发语言 | Java | Java | Java | - |
| 社区活跃度 | 高（国内主流）| 高（国际主流）| 中 | - |
| 运维成本 | 中 | 中高（依赖 Kafka 集群）| 低 | 极低（免运维）|

---

## 五、一些容易混淆的概念

**Binlog vs Redo Log**：Binlog 是 MySQL Server 层的逻辑日志，记录"做了什么操作"；Redo Log 是 InnoDB 引擎层的物理日志，记录"哪个数据页的哪个偏移量做了什么修改"。Binlog 用于复制和 CDC，Redo Log 用于崩溃恢复。两者通过两阶段提交（2PC）保证一致性。

**CDC vs ETL**：ETL（Extract-Transform-Load）是批处理模式，定期抽取全量或增量数据，有天然的延迟。CDC 是事件驱动模式，数据变更即时触发，延迟可以做到秒级甚至毫秒级。CDC 可以看作 ETL 中 "Extract" 环节的实时化替代。

**DTS vs Canal**：DTS 是云厂商的托管服务，Canal 是开源的自建方案。两者的底层原理完全一样（都是解析 Binlog），区别在于一个帮你运维，一个你自己运维。

---

## 参考来源

- [MySQL 8.4 Reference Manual: Replication Formats](https://dev.mysql.com/doc/refman/8.4/en/replication-formats.html)
- [Canal GitHub 仓库](https://github.com/alibaba/canal)
- [mysql-binlog-connector-java GitHub 仓库](https://github.com/shyiko/mysql-binlog-connector-java)
- [Debezium Architecture 文档](https://debezium.io/documentation/reference/stable/architecture.html)
- [阿里云 DTS 产品概述](https://www.alibabacloud.com/help/en/dts/product-overview/what-is-dts)
- [Debezium vs Canal CDC 工具对比](https://cloud.tencent.com/developer/article/1893807)
