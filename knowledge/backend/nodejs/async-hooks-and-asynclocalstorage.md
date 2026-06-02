# async_hooks 与 AsyncLocalStorage：Node.js 异步上下文追踪的前世今生

## 问题的起源：一个看似简单却极难回答的问题

在 Node.js 中，当一段同步代码发起异步操作后，如果想知道「这个操作是由哪个请求触发的」，应该怎么做？

```js
// 你在处理一个 HTTP 请求
function handleRequest(req, res) {
  const userId = req.user.id;

  // 3 层异步调用之后
  doSomethingAsync().then(() => {
    // 这里还能拿到 userId 吗？
    log('done'); // 你想在日志里打出是哪个用户发的请求
  });
}
```

在 JavaScript 回调时代，这个问题有一个朴素的解法：**逐层传递上下文**。但随着调用链变长，这种做法会迅速导致「参数泥潭」——每个函数都要多加一个参数，真正业务逻辑反而被稀释了。线程局部存储（Thread-Local Storage）在多线程语言中早就解决了这个问题，Node.js 社区自然也在寻找类似的方案。

## 演进史：从 domain 到 AsyncLocalStorage

### 第一代：domain 模块（Node.js 0.x ~ 4.x）

domain 是 Node.js 最早提供的上下文解决方案，核心思路是把一组异步操作绑定到一个「域」上：

```js
const domain = require('domain');
const d = domain.create();

d.run(() => {
  setTimeout(() => {
    console.log(process.domain); // 仍然是同一个域
  }, 100);
});
```

这个方案有两个致命缺陷。第一，它依赖 `process.domain` 全局变量，在多个请求并发时会互相污染——一个请求的错误可能导致另一个请求的域信息被覆盖。第二，domain 对 Promise 的支持几乎为零，而在 Node.js 8 之后社区全面转向 async/await，domain 因此彻底失效。Node.js 官方在文档中明确标注 domain 为「pending deprecation」，建议所有新代码不要再使用它。

### 第二代：cls-hooked（社区方案，Node.js 8.2.1+）

domain 废弃后，社区出现了多个基于 `async_hooks` 实验性 API 实现的 CLS（Continuation Local Storage，延续局部存储）库，其中最流行的是 **cls-hooked**。cls-hooked 填补了官方方案缺失的空白，在 Express、Koa 等框架的中间件中被广泛采用。

但 cls-hooked 本身有几个问题：内存泄漏风险（上下文不清理）、在 async/await 场景下行为不稳定、以及没有任何官方保障。它是「能用」，但不「好用」。

### 第三代：async_hooks + AsyncLocalStorage（Node.js 12+，Stable in Node.js 26）

Node.js 在 v12.0.0（2019年4月）首次引入了 `AsyncLocalStorage`，在 v13.10.0 获得完整支持，随后通过 v12.17.0 进入 LTS 稳定版。到 Node.js 26，AsyncLocalStorage 正式标记为 Stable，成为官方推荐的唯一方案。

## async_hooks 模块：底层基础设施

`async_hooks` 模块是整个上下文追踪体系的底层引擎。它允许你监听 Node.js 内部异步资源的生命周期事件。

### 核心概念：asyncId 和 triggerAsyncId

每个异步操作在 Node.js 内部都有一个唯一标识：asyncId 是这个异步操作的身份证，triggerAsyncId 是触发这个异步操作的父操作的身份证。通过追踪这两个 ID 的变化，就能还原出完整的异步调用链。

```js
const async_hooks = require('async_hooks');

const hook = async_hooks.createHook({
  init(asyncId, type, triggerAsyncId, resource) {
    console.log(`AsyncOp: id=${asyncId}, type=${type}, trigger=${triggerAsyncId}`);
  },
  before(asyncId) {
    console.log(`Before: ${asyncId}`);
  },
  after(asyncId) {
    console.log(`After: ${asyncId}`);
  },
  destroy(asyncId) {
    console.log(`Destroy: ${asyncId}`);
  }
});

hook.enable();
```

类型（type）包括 `Timeout`、`TCPSOCKET`、`FSEVENTWRAP`、`GETADDRINFOREQ` 等，代表不同的异步资源类型。

### 生命周期钩子

async_hooks 提供了四个生命周期钩子：`init`（异步资源创建时）、`before`（回调即将执行时）、`after`（回调执行完毕后）、`destroy`（异步资源被销毁时）。通过这些钩子，你可以追踪任意异步操作的开销、调用频率和调用链。

### 为什么不要直接使用 async_hooks 的高级 API

Node.js 官方在文档中明确写道：

> We do not recommend using the createHook, AsyncHook, and executionAsyncResource APIs as they have usability issues, safety risks, and performance implications. Async context tracking use cases are better served by the stable AsyncLocalStorage API.

这段警告值得认真对待。直接使用 `createHook` 的问题在于：需要手动管理生命周期、容易产生内存泄漏、且对 Promise 链的追踪存在边界情况。`AsyncLocalStorage` 对这些底层细节做了大量优化，内存安全性和正确性都有保障，生产环境应该直接用 `AsyncLocalStorage`。

## AsyncLocalStorage：正确用法

### 基本 API

```js
const { AsyncLocalStorage } = require('async_hooks');

const als = new AsyncLocalStorage();
```

三个核心方法：`run(store, fn, ...args)` 在给定存储中执行函数，`getStore()` 获取当前存储，`enterWith(store)` 将当前存储延续到后续异步操作（慎用）。

```js
function logWithId(msg) {
  const id = AsyncLocalStorage.getStore();
  console.log(`[${id}] ${msg}`);
}

async function handleRequest(req) {
  const requestId = Math.random().toString(36).slice(2);

  als.run({ requestId, userId: req.user.id }, async () => {
    // 这里以及之后的整个异步链中都能拿到上下文
    logWithId('request started'); // [abc123] request started

    await doSomethingAsync();
    await doAnotherAsync();

    logWithId('request done'); // [abc123] request done
  });
}
```

### 典型应用场景

**全链路日志追踪**是最常见的用法。在每个请求入口注入 traceId，后续所有日志自动带上这个 ID，无需手动传递。

```js
const als = new AsyncLocalStorage();

// HTTP 中间件
app.use((req, res, next) => {
  const traceId = req.headers['x-trace-id'] || uuid();
  als.run({ traceId, userId: req.user?.id }, () => next());
});
```

**OpenTelemetry 集成**也大量依赖 AsyncLocalStorage。Node.js 的 OpenTelemetry SDK 用它来确保 trace context 在异步调用链中正确传播，从而实现端到端的分布式追踪。

**请求级别的资源管理**。例如在数据库连接池中标记当前请求使用的连接，在日志中附带请求上下文，在错误处理中知道是哪个请求抛出了异常。

### 在 Express/Koa 中的集成模式

```js
// Express 中间件模式
const als = new AsyncLocalStorage();

app.use((req, res, next) => {
  const store = {
    traceId: req.headers['x-trace-id'] || generateTraceId(),
    startTime: Date.now(),
    userId: req.user?.id
  };
  als.run(store, () => {
    // 在路由处理器的所有异步代码中都能 getStore()
    next();
  });
});

// 任何地方直接获取
app.get('/api/test', async (req, res) => {
  const store = als.getStore();
  console.log(store.traceId); // 一定存在
});
```

## 性能：代价有多大？

AsyncLocalStorage 基于 async_hooks 实现，理论上每个异步操作都有额外的上下文管理开销。但这个开销在实践中有多大？

根据 Platformatic 团队在 2025 年对 Node.js v22.17.1 和 v24.4.1 的综合基准测试：启用 AsyncLocalStorage 的开销在空 HTTP 服务器场景下约为 5-8%，在有业务逻辑的场景中通常低于 3%。这个代价在大多数应用场景下完全可以接受。

Node.js 团队一直在持续优化 AsyncLocalStorage 的性能，每一代 LTS 版本都有可见的改善。如果你的应用是高性能网关或对延迟极为敏感，建议先在预发环境做实际压测，而不是基于理论判断。

## 常见踩坑

### 1. Worker 线程的上下文隔离

每个 Worker 线程有自己独立的 AsyncLocalStorage 实例，不会继承主线程的存储。如果需要在线程间传递上下文，必须显式通过消息队列传递：

```js
// 主线程
const worker = new Worker('./worker.js');
worker.postMessage({ traceId, userId });

// Worker 线程
parentPort.on('message', ({ traceId, userId }) => {
  als.run({ traceId, userId }, () => {
    // 显式注入，而不是等待自动继承
  });
});
```

### 2. setTimeout / setInterval 不会自动继承上下文

定时器回调默认在新的异步上下文中执行，不会继承当前存储。这是 Node.js 内部实现的设计权衡：

```js
als.run({ id: 1 }, () => {
  setTimeout(() => {
    console.log(als.getStore()); // null !
  }, 100);
});
```

如果需要让定时器继承上下文，必须显式处理：

```js
als.run({ id: 1 }, () => {
  const store = als.getStore();
  setTimeout(() => {
    als.run(store, () => {
      console.log(als.getStore()); // { id: 1 }
    });
  }, 100);
});
```

### 3. Promise 微任务边界

在 `.then()` 的同步部分，`getStore()` 可以正常获取存储。但如果 `.then()` 的回调本身是异步的，该回调是否能获取存储取决于 Promise 的实现方式。AsyncLocalStorage 对标准 Promise 的支持是完整的，但对于手写的非标准 Promise 链，可能存在边界情况。

### 4. 不要在模块顶层创建存储

AsyncLocalStorage 实例应该在模块顶层声明，但 `run()` 调用应在请求入口处执行。在模块加载阶段没有请求上下文，`run()` 没有任何意义：

```js
// 正确：在模块顶层实例化
const als = new AsyncLocalStorage();

// 错误：在模块顶层调用 run()（没有请求上下文）
als.run({ some: 'data' }, () => { /* ... */ });
```

### 5. 内存泄漏：存储必须有清理机制

AsyncLocalStorage 的存储与异步调用链绑定。如果一个长时间存活的异步操作（如长连接、Streaming 响应）持有存储引用，可能会导致内存泄漏。在这些场景下，考虑使用 `als.enterWith(null)` 显式清除上下文。

## TC39 AsyncContext 提案：Web 标准的方向

Node.js 的 `AsyncLocalStorage` 已经走向标准化。TC39 正在推进 **AsyncContext 提案**（Stage 2，2026年5月草案），目标是让这个能力成为 JavaScript 语言标准的一部分，跨越 Node.js、Deno、Bun 和浏览器。

提案定义了两个核心 API：

```js
// AsyncContext.Variable — 相当于 Node.js 的 AsyncLocalStorage
const requestId = new AsyncContext.Variable();
requestId.run('req-123', () => {
  console.log(requestId.get()); // 'req-123'
});

// AsyncContext.Snapshot — 捕获当前上下文快照，延迟执行
const snapshot = AsyncContext.Snapshot.get();
snapshot.run(() => {
  // 在未来的任意时刻执行时，仍然持有快照时的上下文
});
```

提案明确声明了**非目标**：不拦截异步任务调度、不处理跨域错误冒泡。这是一个纯上下文传播的提案，聚焦于解决问题的一个切面。

Node.js 已经在 v22.x 中通过 `--experimental-async-context` flag 提供了实验性实现。Deno 和 Bun 也在各自路线图中规划了支持。浏览器方面，Chrome 有实验性支持（需开启 flag），但距离生产可用仍有距离。

## 最佳实践总结

**应该做的**：始终优先使用 `AsyncLocalStorage`，不要自行在 `async_hooks` 之上构建替代品。在每个 HTTP 请求入口统一初始化存储，中间件层和业务层代码无需传递任何上下文参数。通过包装数据库操作确保 SQL 日志也带上 traceId。在定时器回调中显式传递存储引用。

**不应该做的**：不要混用 domain 和 AsyncLocalStorage。不要在模块顶层调用 `run()`。不要假设定时器和 Worker 线程自动继承上下文。不要在存储中放入大对象或闭包引用，应保持存储的轻量。生产环境中不要使用 `executionAsyncResource()` API。

## 参考来源

- [Node.js 官方文档：Asynchronous context tracking](https://nodejs.org/api/async_context.html)
- [Node.js 官方文档：async_hooks](https://nodejs.org/api/async_hooks.html)
- [TC39 proposal-async-context（GitHub）](https://github.com/tc39/proposal-async-context)
- [TC39 AsyncContext 规范草案](https://tc39.es/proposal-async-context/)
- [Node.js 中 AsyncLocalStorage 的前世今生和未来（掘金）](https://juejin.cn/post/7233625509107499067)
- [The Hidden Cost of Async Context in Node.js（Platformatic Blog）](https://blog.platformatic.dev/the-hidden-cost-of-context)
- [Node 异步上下文追踪方案演进史与 AsyncLocalStorage 详解（阿里云）](https://developer.aliyun.com/article/1496780)
- [AsyncLocalStorage Benchmarks](https://enterprise-tim.github.io/async-node-stats/)
