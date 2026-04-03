# Socket 与网络编程基础

**整理日期**: 2026-03-23

---

## 一、Unix 的"一切皆文件"哲学

### 1.1 核心理念

Unix 操作系统的设计哲学将几乎所有资源抽象为**文件**，使得用户可以用统一的接口（`open`/`read`/`write`/`close`）来操作它们。

### 1.2 具体体现

| 资源类型 | 文件路径示例 | 说明 |
|---------|-------------|------|
| 普通文件 | `/home/user/doc.txt` | 存储数据 |
| 硬件设备 | `/dev/sda`、`/dev/tty` | 磁盘、终端 |
| 进程信息 | `/proc/1234/status` | 进程状态 |
| 网络协议栈 | `/proc/net/tcp` | TCP 连接信息 |
| 内核参数 | `/sys/kernel/debug/` | 调试信息 |

### 1.3 设计优势

- **统一性**：程序员不需要学习多种 API，掌握文件操作就能与系统各种资源交互
- **可组合性**：Shell 管道 `|` 能连接任意程序，因为它们都读写标准输入输出（也是文件）
- **透明性**：用户可以用 `cat`、`less` 等工具查看系统状态

### 1.4 为什么 lsof 可以查端口号

`lsof`（List Open Files）能查端口，正是因为**网络连接在 Unix 中也被视为文件**。

当创建一个网络连接时，系统会分配一个**文件描述符**（file descriptor）来表示这个 socket。`lsof` 遍历 `/proc` 文件系统，读取每个进程打开的文件描述符，当发现是 socket 类型时，会去 `/proc/net/tcp` 等文件中查找对应的端口信息。

---

## 二、Socket 详解

### 2.1 什么是 Socket

Socket（套接字）是操作系统提供的**网络通信端点的抽象**，是进程间通信（IPC）的一种机制。

**本质**：Socket 是内核中的一个数据结构，包含通信所需的所有信息：
- 协议类型（TCP、UDP、Unix Domain Socket 等）
- 本地地址（IP + 端口）
- 远端地址（IP + 端口，对于连接型协议）
- 连接状态（LISTEN、ESTABLISHED、CLOSE_WAIT 等）
- 缓冲区（发送缓冲区和接收缓冲区）

从程序员角度看，Socket 表现为一个**整数文件描述符**，可以用标准的文件操作接口来读写数据。

### 2.2 "套接字"译名的由来

"套接"原本是机械工程术语，指两个部件**套在一起连接**的动作。Socket 在英语中也有"插座"的意思——插头插进插座就连接在一起。网络 socket 也是类似概念：两个程序通过 socket "插接"在一起进行通信。

这个译名虽然晦涩，但自 1980 年代沿用至今，已成为行业标准。

### 2.3 Socket 的类型

| 类型 | 描述 | 典型用途 |
|-----|------|---------|
| **Stream Socket (SOCK_STREAM)** | 面向连接、可靠、基于字节流 | TCP 通信 |
| **Datagram Socket (SOCK_DGRAM)** | 无连接、不可靠、基于数据报 | UDP 通信 |
| **Raw Socket (SOCK_RAW)** | 直接访问底层协议 | ping、网络抓包 |
| **Unix Domain Socket** | 同一主机进程间通信 | 本地服务（如 MySQL）|

### 2.4 TCP Socket 工作流程

**服务端：**
```c
socket()       // 创建 socket，返回 fd
    ↓
bind()         // 绑定 IP 和端口
    ↓
listen()       // 开始监听连接请求
    ↓
accept()       // 接受客户端连接，返回新的 fd（用于该连接）
    ↓
read()/write() // 收发数据
    ↓
close()        // 关闭连接
```

**客户端：**
```c
socket()       // 创建 socket
    ↓
connect()      // 连接到服务端
    ↓
read()/write() // 收发数据
    ↓
close()        // 关闭连接
```

### 2.5 Socket vs 端口 vs 连接

- **Socket**：内核中的通信端点对象，是软件概念
- **端口**：16 位数字标识符（0-65535），用于区分同一 IP 上的不同服务
- **连接**：两个 socket 之间的关联，由四元组唯一标识：`{本地IP:本地端口, 远端IP:远端端口}`

**一个端口可以有多个 socket：**

```
服务端监听 socket: 0.0.0.0:8080 (LISTEN)
    ├── 连接1 socket: 192.168.1.10:8080 <-> 10.0.0.5:54321 (ESTABLISHED)
    ├── 连接2 socket: 192.168.1.10:8080 <-> 10.0.0.6:12345 (ESTABLISHED)
    └── 连接3 socket: 192.168.1.10:8080 <-> 10.0.0.7:98765 (ESTABLISHED)
```

---

## 三、Socket API 与跨平台实现

### 3.1 Socket API 的起源

Socket API 最初是 **BSD Unix（1983 年）用 C 语言实现的**，定义在 `<sys/socket.h>` 头文件中。这是操作系统提供的**系统调用接口**，理论上任何语言都可以调用。

**注意**：BSD Socket API 不是 C 语言的一部分，而是操作系统提供的接口。C 是调用者，BSD Socket API 是被调用者。

### 3.2 核心 API 函数

```c
#include <sys/socket.h>  // 头文件由操作系统提供

int socket(int domain, int type, int protocol);
int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
int listen(int sockfd, int backlog);
int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
ssize_t send(int sockfd, const void *buf, size_t len, int flags);
ssize_t recv(int sockfd, void *buf, size_t len, int flags);
int close(int fd);
```

### 3.3 不同平台的 Socket API

| 平台 | API 名称 | 主要差异 |
|-----|---------|---------|
| **BSD/Unix/Linux** | BSD Socket API | 最原始的实现，标准 |
| **Windows** | Winsock (WSA*) | 需要初始化 `WSAStartup`，关闭用 `closesocket` |
| **macOS** | BSD Socket API | 与 BSD 兼容 |

**跨平台代码示例：**

```c
// Unix/Linux/macOS
#include <sys/socket.h>
close(sockfd);

// Windows
#include <winsock2.h>
closesocket(sockfd);
WSACleanup();
```

### 3.4 各语言对 Socket API 的封装

| 语言 | Socket 库/方式 |
|-----|---------------|
| **C/C++** | 原生 BSD Socket API |
| **Python** | `socket` 模块（标准库） |
| **Java** | `java.net.Socket` / `ServerSocket` |
| **Go** | `net` 包 |
| **Node.js** | `net` 模块（底层 libuv + C/C++） |
| **Rust** | `std::net` |

### 3.5 Node.js 的 net 模块实现

Node.js 采用分层架构：

```
JavaScript 代码
    ↓
net.createServer() / socket.write()  // JS 层接口
    ↓
libuv（C 库）                        // 跨平台异步 I/O
    ↓
操作系统原生 Socket API              // BSD Socket / Winsock
    ↓
内核网络协议栈                        // TCP/IP 实现
```

**libuv** 是 Node.js 的核心 C 库，提供跨平台的异步 I/O，内部封装了各操作系统的 socket 实现差异。

---

## 四、基于 Socket 的应用

Socket 是网络编程的基础设施，几乎所有网络应用底层都用它：

| 应用层协议 | 基于 Socket 的实现 |
|-----------|------------------|
| HTTP/HTTPS | Nginx、Apache、Tomcat、各种 Web 框架 |
| 数据库 | MySQL、PostgreSQL、Redis、MongoDB |
| 消息队列 | Kafka、RabbitMQ、RocketMQ |
| 远程调用 | gRPC、Dubbo、Thrift |
| 实时通信 | WebSocket、MQTT、游戏服务器 |
| 文件传输 | FTP、SFTP、rsync |
| 邮件服务 | SMTP、POP3、IMAP |

---

## 五、为什么 Socket 被设计成文件

Unix 把 Socket 设计成文件，带来了几个关键优势：

1. **统一接口**：用 `read()`/`write()` 收发数据，用 `close()` 关闭，无需学习新 API
2. **与 select/poll/epoll 配合**：可以像监控普通文件一样监控 socket 的可读/可写状态
3. **进程间传递**：通过 `sendmsg()` 配合 `SCM_RIGHTS`，可以把 socket 传给其他进程

这就是为什么 `lsof` 能看到 socket——在内核眼里，它就是一种特殊的文件。

---

## 六、Python Socket 编程示例

```python
import socket

# 创建一个 TCP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 绑定地址和端口（对应 C 的 bind()）
server.bind(('0.0.0.0', 8080))

# 开始监听（对应 C 的 listen()）
server.listen(5)

print("服务器启动，等待连接...")
while True:
    # 接受连接（对应 C 的 accept()）
    client, addr = server.accept()
    print(f"客户端 {addr} 连接")
    
    # 收发数据（对应 C 的 recv/send）
    data = client.recv(1024)
    client.send(b"Hello!")
    
    client.close()
```

这段 Python 代码底层最终调用的就是 C 语言的 socket 系统调用。

---

## 参考

- BSD Socket API 原始文档
- Unix 操作系统设计哲学
- Node.js libuv 源码
