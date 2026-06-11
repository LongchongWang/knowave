# Apache Thrift 入门指南

> 整理日期：2026-06-11
> 目的：让读者读完后能理解代码仓库中 Thrift 相关代码的含义和工作方式

## 一、Thrift 是什么

Apache Thrift 是一个跨语言的 RPC（远程过程调用）框架。它让你用一种中间语言（IDL）定义服务接口和数据结构，然后自动生成各种编程语言的客户端和服务端代码，使不同语言编写的服务能相互通信。

通俗来说：你写一份 `.thrift` 接口描述文件，Thrift 编译器帮你生成 Java、Python、Go、C++ 等语言的序列化/反序列化代码和 RPC 桩代码。客户端调用远程方法就像调用本地方法一样。

## 二、历史与背景

Thrift 由 Facebook 在 2007 年开发。当时 Facebook 内部不限制开发语言，导致大量服务使用不同语言编写，需要一个工具让它们高效通信。Facebook 的工程师考察了已有方案后，发现没有满意的，于是自行设计了 Thrift。

关键时间线：

- **2007 年 4 月**：Facebook 将 Thrift 开源，并发布了白皮书《Thrift: Scalable Cross-Language Services Implementation》
- **2008 年 5 月**：进入 Apache 孵化器
- **2010 年 10 月**：成为 Apache 顶级项目（TLP）
- **至今**：最新版本 0.20+，支持 28 种编程语言

Thrift 的设计时间早于 Google 的 gRPC（2015 年开源）。在国内互联网公司，Thrift 的采用非常广泛，美团、字节跳动、百度等都在其内部 RPC 框架中基于 Thrift 做了深度定制。

## 三、核心架构——四层软件栈

Thrift 的架构是分层的，从下到上：

```
+-------------------------------------------+
|              Server                        |
|   (single-threaded, event-driven etc)      |
+-------------------------------------------+
|             Processor                      |
|         (compiler generated)               |
+-------------------------------------------+
|             Protocol                       |
|       (JSON, compact, binary etc)          |
+-------------------------------------------+
|            Transport                       |
|          (raw TCP, HTTP etc)               |
+-------------------------------------------+
```

**Transport 层（传输层）**：负责字节流的读写，屏蔽底层网络细节。类似于"管道"，上层不需要关心数据是通过 TCP Socket、HTTP 还是文件传输的。常见实现有 TSocket（TCP）、THttpTransport（HTTP）、TFramedTransport（带帧长度前缀，配合非阻塞服务器使用）、TBufferedTransport（带缓冲）。

**Protocol 层（协议层）**：负责数据的序列化和反序列化，即"怎么把内存中的数据结构变成字节流"。常见实现：

- **TBinaryProtocol**：标准二进制编码，简单直接（默认）
- **TCompactProtocol**：压缩二进制编码，使用 varint 和 zigzag 编码，体积更小
- **TJSONProtocol**：JSON 格式，便于调试但性能差

**Processor 层（处理层）**：由编译器自动生成。它从 Protocol 读取请求数据，找到对应的处理函数，调用用户实现的 handler，然后把结果写回。你不需要手写这一层。

**Server 层（服务层）**：把上面各层组装在一起，监听端口、接受连接、将请求交给 Processor 处理。常见实现有 TSimpleServer（单线程）、TThreadPoolServer（线程池）、TNonblockingServer（非阻塞 IO）。

这种分层设计的好处是各层可以自由组合。比如你可以把 TCompactProtocol 配合 TFramedTransport 使用，不需要改任何业务代码。

## 四、IDL 语法——读懂 .thrift 文件

IDL（Interface Definition Language）是 Thrift 的核心。当你在代码仓库中看到 `.thrift` 文件时，需要理解以下语法：

### 4.1 Namespace

声明生成代码的包名/命名空间：

```thrift
namespace java com.meituan.service.hello
namespace py hello_service
namespace go hello
```

### 4.2 基本数据类型

| 类型 | 说明 |
|------|------|
| `bool` | 布尔值 |
| `byte` / `i8` | 8 位整数 |
| `i16` | 16 位整数 |
| `i32` | 32 位整数 |
| `i64` | 64 位整数 |
| `double` | 64 位浮点数 |
| `string` | UTF-8 字符串 |
| `binary` | 字节数组 |

注意：没有 `float`（32 位浮点），只有 `double`。也没有 `unsigned` 类型。

### 4.3 容器类型

```thrift
list<string>          // 有序列表
set<i32>              // 无序去重集合
map<string, i64>      // 键值映射
```

容器可以嵌套：`map<string, list<i32>>`。

### 4.4 Struct（结构体）

Struct 是最核心的复合类型，类似于 Java 的 POJO 或 TypeScript 的 interface：

```thrift
struct UserInfo {
    1: required i64 userId,
    2: required string userName,
    3: optional string email,
    4: optional i32 age = 0,
    5: optional list<string> tags,
}
```

关键规则：

- 每个字段必须有一个**唯一数字编号**（如 `1:`、`2:`），这是序列化时的标识符，一旦发布就不应再修改
- 字段可标记 `required`（必填）或 `optional`（可选）。不标记时为 default requiredness（写时必传，读时可缺）
- 可以设置默认值（如 `= 0`）
- 字段间用逗号或分号分隔，可混用

**为什么用数字编号而不是字段名？** 这是实现向前/向后兼容的关键。序列化后的二进制数据不包含字段名，只包含编号和值。新增字段时只要用新编号，老代码遇到不认识的编号就跳过，新代码遇到缺失的 optional 字段就用默认值。

### 4.5 Enum（枚举）

```thrift
enum OrderStatus {
    CREATED = 0,
    PAID = 1,
    SHIPPED = 2,
    DELIVERED = 3,
    CANCELLED = 4,
}
```

底层用 i32 存储。

### 4.6 Exception（异常）

和 struct 结构相同，但语义表示一个可抛出的异常：

```thrift
exception NotFoundException {
    1: string message,
    2: i32 errorCode,
}
```

### 4.7 Service（服务接口）

这是 RPC 的核心——定义远程可调用的方法：

```thrift
service HelloService {
    string sayHello(1: string username),
    UserInfo getUserInfo(1: i64 userId) throws (1: NotFoundException e),
    oneway void logAction(1: string action),
}
```

- 方法可以有返回值，也可以是 `void`
- 可以声明 `throws` 抛出自定义异常
- `oneway` 表示"发完就忘"——客户端不等待响应，适用于日志上报等场景
- 一个 service 可以 `extends` 另一个 service

### 4.8 Include 和 Typedef

```thrift
include "common.thrift"        // 引入其他 thrift 文件
typedef i64 Timestamp           // 类型别名
```

引用其他文件的类型时需要加前缀：`common.UserInfo`。

### 4.9 一个完整的 .thrift 文件示例

```thrift
namespace java com.meituan.mtthrift.test

include "common.thrift"

enum StatusCode {
    SUCCESS = 0,
    FAIL = 1,
}

struct GetOrderRequest {
    1: required i64 orderId,
    2: optional string source,
}

struct GetOrderResponse {
    1: required StatusCode code,
    2: optional string message,
    3: optional common.OrderDetail order,
}

exception ServiceException {
    1: string message,
    2: i32 code,
}

service OrderService {
    GetOrderResponse getOrder(1: GetOrderRequest request) throws (1: ServiceException e),
    oneway void reportMetrics(1: string metricsJson),
}
```

## 五、如何使用——从 IDL 到可运行的代码

### 5.1 安装 Thrift 编译器

macOS：

```bash
brew install thrift
```

验证：

```bash
thrift --version
# Apache Thrift version 0.20.0
```

Linux（Ubuntu/Debian）：

```bash
apt-get install thrift-compiler
```

或者从源码编译（当需要特定版本时）。

### 5.2 生成代码

```bash
thrift --gen java hello.thrift       # 生成 Java 代码
thrift --gen py hello.thrift         # 生成 Python 代码
thrift --gen go hello.thrift         # 生成 Go 代码
```

生成的代码包括：

- 每个 struct/enum/exception 对应一个类（含序列化/反序列化逻辑）
- 每个 service 生成一个 `Iface` 接口（你需要实现）、一个 `Client` 类（调用方使用）、一个 `Processor` 类（服务端框架使用）

### 5.3 典型使用模式

**服务端**：实现 `Service.Iface` 接口 → 创建 Processor → 选择 Transport/Protocol/Server → 启动

**客户端**：创建 Transport → 创建 Protocol → 创建 Client → 调用方法

这是原生 Apache Thrift 的使用方式。在实际公司项目中，这些样板代码通常由框架封装掉了（见下节）。

## 六、美团公司级 Thrift 基建

在美团内部，你不会直接使用原生 Apache Thrift，而是使用公司封装的 **MTthrift** 框架和 **OCTO 服务治理平台**。

### 6.1 MTthrift

MTthrift 是美团基于 Apache Thrift 深度定制的 Java RPC 通信框架，每天为 5000+ 服务提供 3000 亿+次调用量支持。它在原生 Thrift 的基础上集成了：

- **MCC**（配置中心）：动态配置下发
- **CAT**（监控）：调用链路埋点和性能监控
- **MTrace**（链路追踪）：分布式调用链追踪
- **服务注册与发现**：通过 MNS 注册中心，服务自动注册和发现
- **负载均衡**：智能路由、同机房优先、权重路由
- **服务鉴权**：通道鉴权和接口鉴权

### 6.2 OCTO 服务治理平台

OCTO 是美团统一的微服务治理平台，MTthrift 是其核心通信框架之一。OCTO 提供的能力包括：

- 服务注册与发现
- 负载均衡与路由（SET 路由、LiteSet 灰度链路、泳道隔离）
- 服务鉴权
- 容错处理、降级熔断（集成 Rhino）
- 灰度发布
- 流量录制与回放
- 调用数据可视化

管理平台入口：https://octo.mws.sankuai.com

### 6.3 两种接口定义方式

在美团内部使用 MTthrift 有两种方式定义接口：

**方式一：IDL 方式（传统）**

编写 `.thrift` 文件，使用 Genthrift 工具（https://octo.mws.sankuai.com/compile-online）在线生成 Java 代码，或使用 Maven 插件在构建时自动生成。

```thrift
namespace java com.meituan.mtthrift.test
service HelloService {   
    string sayHello(1: string username)
    string sayBye(1: string username)
}
```

**方式二：Thrift 注解方式（更简便）**

直接在 Java 接口上使用 Swift 注解，不需要写 `.thrift` 文件：

```java
@ThriftService
public interface HelloService {
    @ThriftMethod
    String sayHello(@ThriftField(1) String username);
}
```

注解方式更符合 Java 开发习惯，但有一些隐含的坑（如漏加注解不会编译报错但运行时 NPE、泛型兼容性问题等）。

### 6.4 在 MDP 项目中接入

如果你的项目使用 MDP（美团开发平台）框架，接入 Thrift 非常简单：

```xml
<dependency> 
    <groupId>com.meituan.mdp.boot</groupId> 
    <artifactId>mdp-boot-starter-thrift</artifactId> 
</dependency>
```

服务端：

```java
@MdpThriftServer
public class HelloServiceImpl implements HelloService.Iface { 
    @Override
    public String sayHello(String username) {
        return "Hello, " + username;
    }
}
```

客户端：

```java
@Service
public class MyService { 
    @MdpThriftClient(remoteAppKey = "com.meituan.helloService", timeout = 100) 
    private HelloService.Iface helloService; 
    
    public void doSomething() {
        String result = helloService.sayHello("world");
    }
}
```

通过注解声明即可完成服务注册和客户端初始化，框架自动处理连接管理、服务发现、负载均衡等。

### 6.5 关键内部文档

- MTthrift 开发指南：https://km.sankuai.com/collabpage/28257152
- MTthrift MDP 官方文档：https://km.sankuai.com/collabpage/424852675
- Thrift IDL 开发规范：https://km.sankuai.com/page/28187039
- OCTO 服务治理 PRFAQ：https://km.sankuai.com/collabpage/1275090121
- MTthrift 常见问题 FAQ：https://km.sankuai.com/collabpage/119713785

## 七、Thrift vs JSON——为什么不用 JSON

在微服务间通信中，选择 Thrift 而非 JSON 的核心原因：

### 7.1 性能差距

| 维度 | Thrift (Binary/Compact) | JSON |
|------|------------------------|------|
| 序列化体积 | 小 60-70% | 基准 |
| 序列化速度 | 快 5-10 倍 | 基准 |
| 反序列化速度 | 快 5-10 倍 | 基准 |

Thrift 使用二进制编码，字段用数字编号标识（而非完整字段名字符串），整数使用变长编码（varint），不需要 JSON 的括号、引号、逗号等格式字符。

举个例子：一个 `{"userId": 12345, "userName": "张三"}` 在 JSON 中约 40 字节，在 Thrift Compact 协议中约 15 字节。

### 7.2 强类型与接口契约

Thrift IDL 是一份严格的接口契约。编译器会为你生成强类型代码，字段类型错误在编译期就能发现。而 JSON 是弱类型的，类型不匹配只有在运行时才会暴露。

### 7.3 向前/向后兼容

Thrift 的字段编号机制天然支持接口演进：

- **新增字段**：用新编号，设为 optional。老版本客户端收到新字段会自动跳过
- **删除字段**：把字段标记为 deprecated（不再使用该编号），新版本代码不读取该字段，但老版本发来的数据仍能正常解析

JSON 也能做到兼容（忽略未知字段），但缺乏强制约束，容易出错。

### 7.4 代码生成与多语言支持

从一份 IDL 自动生成 28 种语言的代码。Java 服务和 Python 服务、Go 服务之间可以无缝通信，不需要手动维护多份数据模型。

### 7.5 内建 RPC 支持

Thrift 不仅仅是序列化格式，它是完整的 RPC 框架——包含服务定义、异常声明、网络传输等。JSON 只是数据格式，要做 RPC 还需要额外的 HTTP 框架、路由、错误码约定等。

### 7.6 什么时候 JSON 更合适？

- 浏览器与服务器通信（HTTP API）
- 需要人类可读的调试场景
- 对外开放的 API（第三方接入）
- 配置文件
- 简单的内部工具或脚本

内部服务间的高频 RPC 调用，Thrift（或 Protobuf）是更好的选择。

## 八、Thrift vs Protobuf

Thrift 的主要竞品是 Google 的 Protocol Buffers + gRPC。核心区别：

| 维度 | Thrift | Protobuf + gRPC |
|------|--------|----------------|
| 出品方 | Facebook → Apache | Google |
| 定位 | 序列化 + RPC 一体 | 序列化（Protobuf）和 RPC（gRPC）分离 |
| 传输协议 | 自定义 TCP 协议 | 基于 HTTP/2 |
| 流式传输 | 不原生支持 | 支持（单向流、双向流） |
| 性能 | 两者接近 | 两者接近 |
| 生态 | 美团/字节等国内大厂广泛使用 | 全球开源生态更活跃 |

在美团体系内，因为历史原因和深度定制，MTthrift 是主流选择。

## 九、读懂代码仓库中 Thrift 相关代码

当你在项目中遇到 Thrift 相关代码时，需要识别以下几类文件：

### 9.1 `.thrift` 文件

IDL 定义文件，通常在 `src/main/thrift/` 或独立的 `api` 模块中。这是接口的「源头」，阅读它就能理解服务提供了哪些方法、接收什么参数、返回什么结果。

### 9.2 生成的代码

通常在 `target/generated-sources/` 或 `gen-java/` 目录中。这些代码**不要手动修改**。它们包含：

- `XxxService.java`：包含 `Iface`（接口定义）、`Client`（客户端桩）、`Processor`（服务端处理器）等内部类
- 每个 struct 对应一个 Java 类，包含 `read()`、`write()` 方法（序列化逻辑）和 `isSet()` 方法（判断字段是否被设置）

### 9.3 服务实现类

实现 `XxxService.Iface` 接口的类，通常带有 `@MdpThriftServer` 或 `@ThriftServerPublisher` 注解。这是真正的业务逻辑所在。

### 9.4 客户端引用

带有 `@MdpThriftClient` 注解的字段，通过 `remoteAppKey` 指定要调用的远程服务。框架自动完成服务发现和连接管理。

### 9.5 常见的 Maven 依赖

```xml
<!-- 美团优化版 libthrift -->
<dependency>
    <groupId>org.apache.thrift</groupId>
    <artifactId>libthrift</artifactId>
    <version>0.9.3-mt</version>
</dependency>

<!-- MTthrift 框架 -->
<dependency>
    <groupId>com.meituan.service.mobile</groupId>
    <artifactId>mtthrift</artifactId>
</dependency>

<!-- MDP Thrift Starter -->
<dependency>
    <groupId>com.meituan.mdp.boot</groupId>
    <artifactId>mdp-boot-starter-thrift</artifactId>
</dependency>

<!-- Swift 注解（注解方式定义接口时使用） -->
<dependency>
    <groupId>com.facebook.swift</groupId>
    <artifactId>swift-annotations</artifactId>
</dependency>
```

## 十、注意事项与常见坑

1. **字段编号不可修改**：一旦发布的 struct，已有字段的编号不能改。新增字段用新编号，废弃字段保留编号不复用。

2. **不支持 Java 富类型**：Thrift IDL 不支持 BigDecimal、Date、LocalDateTime 等 Java 特有类型。通常用 i64 表示时间戳，用 string 表示金额。美团内部有扩展方案支持富类型映射（参见 https://km.sankuai.com/collabpage/1393736674）。

3. **Null 值处理**：Thrift 的 optional 字段如果未设置，反序列化后得到的是类型默认值（0、空字符串等），而非 null。使用 `isSetXxx()` 方法判断字段是否真正被设置过。

4. **required 的代价**：required 字段一旦定义就无法删除（否则破坏兼容性）。推荐新字段一律用 optional。

5. **统一协议 vs 原生协议**：美团内部的 OCTO 统一协议是在原生 Thrift 协议上的封装，支持鉴权、压缩等高级功能。新服务应默认使用统一协议。

6. **注解方式的坑**：使用 Thrift 注解定义接口时，漏加 `@ThriftMethod` 或 `@ThriftField` 不会编译报错，但运行时会抛 NPE。建议仔细检查或使用 IDE 插件辅助。

## 参考来源

- Apache Thrift 官方文档：https://thrift.apache.org/docs
- Apache Thrift IDL 规范：https://thrift.apache.org/docs/idl
- Apache Thrift 概念文档：https://thrift.apache.org/docs/concepts
- Facebook 原始论文：*Thrift: Scalable Cross-Language Services Implementation* (2007)
- 美团 MTthrift 开发指南：https://km.sankuai.com/collabpage/28257152
- 美团 OCTO PRFAQ：https://km.sankuai.com/collabpage/1275090121
- 美团 MTthrift MDP 文档：https://km.sankuai.com/collabpage/424852675
