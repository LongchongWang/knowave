# useEffect 与 DOMContentLoaded：执行时序与 React 调度原语

> 整理日期：2026-07-13  
> 来源：对话整理 + 浏览器实测 + HTML Living Standard + React Scheduler 设计

---

## 从一个矛盾说起

「React 的 `useEffect` 和 `DOMContentLoaded` 谁先执行？」——这是一个看似简单、却到处能搜到矛盾答案的问题。有人说是 `DOMContentLoaded` 先，有人说是 `useEffect` 先，还有人给出「看情况」的模糊结论。

矛盾的根源不在谁记错了，而在于这个问题**依赖浏览器事件循环的实现细节，且存在一个容易被忽略的边界条件**。本文把它彻底拆开：先把三个时机的规范定义钉死，再分场景给出确定的顺序，最后解释 React 为什么用 `MessageChannel` 作为调度原语——它正是时序之争的关键一环。

> 本文的边界结论（第四节）经过浏览器实测验证：用 DevTools Network throttle 延迟一个 `defer` 脚本的下载，可以观察到 `useEffect` 提前到 `DOMContentLoaded` 之前执行。规范推理给「可能」，实测给「确定」——事件循环时序这类实现敏感的问题，以实测为准。

---

## 一、三个时机的规范定义

在比较「谁先」之前，必须先精确知道它们各自在什么时候触发。

### 1.1 DOMContentLoaded

`DOMContentLoaded` 是 `Document` 上的事件。按 HTML Living Standard 的 ["the end" 算法](https://html.spec.whatwg.org/multipage/parsing.html#the-end)，当 HTML 文档解析完成时，浏览器依次：

1. 将 `document.readyState` 置为 `"interactive"`；
2. 按文档顺序执行所有 `defer` 脚本；
3. 派发 `DOMContentLoaded` 事件。

也就是说，`defer` 脚本的执行被夹在「解析完成」与 `DOMContentLoaded` 派发之间。MDN 对 `defer` 的描述也明确这一点：[defer 脚本保证在 DOMContentLoaded 之前执行](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#attr-defer)。

### 1.2 defer 脚本

`defer` 是 `<script>` 的属性，语义是：**异步下载、推迟执行**。具体行为（见 [HTML Standard, script processing model](https://html.spec.whatwg.org/multipage/scripting.html#prepare-the-script-element)）：

- 下载不阻塞 HTML 解析；
- 执行被推迟到 HTML 解析完成后的 "the end" 阶段；
- 多个 `defer` 脚本**按文档出现顺序**执行；
- 执行发生在 `DOMContentLoaded` 派发之前。

`type="module"` 的脚本默认具有 `defer` 语义，所以现代打包产物（Vite、webpack 的 ESM 产物等）入口通常都是 defer 行为。

### 1.3 useEffect

`useEffect` 是 React 的 passive effect。它的执行时机**不由浏览器规范定义，而由 React 运行时调度**：

- React 在 commit 阶段把真实 DOM 更新到页面上之后，把 passive effect 回调**通过 `MessageChannel.postMessage` 排入宏任务队列**；
- 该回调在当前同步执行栈结束、下一个事件循环迭代时执行。

关键点：`useEffect` 回调是一个**宏任务**，不是同步代码、也不是微任务。它和 `DOMContentLoaded` 的先后之争，本质上是「一个宏任务」与 "the end" 同步流程的先后之争。

---

## 二、主流结论：DOMContentLoaded 先于 useEffect

在大多数实际场景下，`DOMContentLoaded` 先触发，`useEffect` 后执行。原因如下：

当 React 入口是 `defer`/`module` 脚本时（现代打包的默认情况），时序是：

```
"the end" task（一个同步流程，内部不中断）：
  ├─ 执行 defer 脚本①（React 入口 app.js）
  │    └─ createRoot().render() → commit DOM
  │       └─ MessageChannel.postMessage 调度 useEffect  [入宏任务队列，暂不执行]
  ├─ 执行 defer 脚本②（若有）
  └─ 派发 DOMContentLoaded  ✅ 先
↓ 下一个事件循环迭代（宏任务）
useEffect 回调执行                ✅ 后
```

"the end" 算法在「所有 defer 脚本都已下载完成」的前提下是**同步连续**执行的：执行 defer → 派发 DCL，中间不会切到别的宏任务。而 `useEffect` 的 `MessageChannel` 任务是 "the end" 这个同步流程结束后的下一个宏任务，必然排在 DCL 之后。

> 这就是「DOMContentLoaded 先」的规范依据，也是绝大多数本地开发环境（脚本秒下、无慢网络）下观察到的真相。

---

## 三、React 入口是否 defer，会影响什么

一个常见疑问：如果 React 入口**不是** defer（比如 body 末尾的同步内联 `<script>`），会不会改变结论？

会改变的是 **React mount 的时机**，但**不改变 useEffect 与 DCL 的先后**：

- 同步脚本在 HTML 解析中途就执行，React 提前 mount 并 postMessage 调度 useEffect；
- 但 `useEffect` 回调仍是宏任务，要等当前同步流程（解析 + "the end"）结束才跑；
- 只要 "the end" 不被打断（见下一节），DCL 仍在 "the end" 同步流程内派发，先于 useEffect。

所以「React 入口是否 defer」只影响 React mount 相对于其他 defer 脚本的位置，**不影响 DCL 与 useEffect 的先后**——后者由 "the end" 是否同步连续决定。

---

## 四、边界：慢下载的 defer 会打断 "the end"

这是本文最关键、也最容易被忽略的一点，也是各种矛盾答案的来源。

### 4.1 规范机制：spin the event loop

"the end" 算法在执行 defer 脚本时，如果某个 defer 脚本**还没下载完**（`readyState` 非 complete），不能立刻执行。此时规范要求 [spin the event loop](https://html.spec.whatwg.org/multipage/webappapis.html#spin-the-event-loop)：

> spin the event loop 会暂停当前算法的同步执行，把控制权交还给事件循环；在等待条件满足（脚本下载完成）期间，主线程可以处理其他任务；条件满足后再恢复算法继续执行。

「下载」是网络线程的事，不占主线程。所以等待下载期间，**主线程空闲**，事件循环会去消费宏任务队列里已经排着的任务——包括 React 在更早执行的同步脚本里 postMessage 排入的 `useEffect` 任务。

### 4.2 实测验证

用 DevTools Network 面板把一个 `defer` 脚本的下载 throttle 到 Slow 3G，配合一个同步执行的 React 入口（或任何在解析中途 postMessage 宏任务的脚本），可以观察到：

```
解析中途：同步脚本执行 → React mount → postMessage 调度 useEffect
解析完成 → "the end" 开始 → defer 脚本没下完 → spin the event loop 让出主线程
↓ 主线程消费宏任务队列
useEffect 回调执行              ✅ 先
↓ defer 脚本下载完成
defer 脚本执行 → 派发 DOMContentLoaded  ✅ 后
```

实测结果：**`useEffect` 在 `DOMContentLoaded` 之前执行**，且早于那个慢下载的 defer 脚本的执行。

### 4.3 二分结论

把「谁先」压缩成一张确定表：

| 场景 | 顺序 |
|------|------|
| defer 脚本在解析完成时都已下载好 | "the end" 同步连续跑完 → **DOMContentLoaded 先，useEffect 后** |
| 有 defer 脚本仍在下载（慢网络 / 大体积） | "the end" spin the event loop 让出主线程，useEffect 宏任务插队 → **useEffect 先，DOMContentLoaded 后** |

这解释了为什么不同人说法不一：他们的网络条件、脚本体积、入口脚本类型不同，落在了表格的不同行。

> 注意：第二节「主流结论」之所以成立，前提是「所有 defer 脚本都已下载完」。一旦这个前提被慢网络打破，结论翻转。规范推理只能给出「可能翻转」，实测才能确认浏览器在该版本下确实翻转。

---

## 五、为什么是 MessageChannel——React 调度原语的选择

第四节能成立，前提是 `useEffect` 被排成一个**宏任务**。这就引出另一个问题：React Scheduler 为什么用 `MessageChannel`，而不是 `Promise`、`setTimeout` 或 `requestIdleCallback`？

React Scheduler 需要一个异步原语，把任务推迟到「当前同步栈结束后、但尽快执行」，同时满足「时间切片 + 主动让步 + 精确优先级」。四个候选各有问题。

### 5.1 不用 Promise（微任务）

`Promise.then` / `queueMicrotask` 是**微任务**。微任务的特性是：在当前 task 结束后、浏览器 paint 或处理下一个宏任务之前，**把整个微任务队列一次性清空**，不让出主线程。

这正是 React **不想要**的。Scheduler 的核心目标是时间切片——干一段活，就把主线程让给浏览器去 paint、响应输入，避免长任务卡帧。用微任务调度，连续的任务会紧贴着执行，浏览器没机会渲染，直接掉帧。

→ 微任务不让出主线程，与「让步」目标冲突。

### 5.2 不用 setTimeout

`setTimeout` 是宏任务，方向对（能让步），但有两个硬伤：

1. **嵌套延迟惩罚**：按 [HTML Standard - timers](https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html)，`setTimeout` 嵌套超过 5 次后，强制最小 4ms 延迟。Scheduler 高频调度会很快触发这个惩罚，每次多 4ms，累积起来调度明显变慢（详见 [MDN: setTimeout](https://developer.mozilla.org/zh-CN/docs/Web/API/setTimeout)）。
2. **首次即有延迟**：即使 `setTimeout(fn, 0)`，实现上也常有 0~1ms 的最小延迟，不够紧。

### 5.3 不用 requestIdleCallback

`requestIdleCallback`（rIC）是浏览器为「低优先级后台任务」设计的 API：一帧渲染完后，若有剩余时间才调用回调，并给一个 `deadline` 告诉你还剩多少 ms。它和 React Scheduler 的目标错位：

- **帧率耦合**：rIC 的触发节奏等于帧节奏（~16.6ms 一次机会）。主线程忙时某一帧没空闲，回调被推迟，连续几帧繁忙就持续拖延——React 不能容忍「主线程一忙，UI 更新就卡住不发」。Scheduler 要的是「同步栈一结束就尽快让出并续上」，rIC 给不了这种紧度。
- **无优先级**：rIC 回调队列先进先出，回调之间没有优先级概念。而 React Fiber 的核心是优先级调度——用户输入要能打断低优先级渲染、过期任务要立即同步执行。这套抢占机制 rIC 提供不了，React 必须自己实现。
- **兼容性差**：Safari 历史上长期不支持；SSR / Node 环境不存在；移动端实现参差。Scheduler 是 React 的核心，不能依赖一个兼容性不稳的 API。
- **时机不可控**：后台 tab 会被限制、帧负载影响触发，行为不一致。Scheduler 需要可预测的调度。
- **被动 vs 主动**：rIC 是「等浏览器空闲叫我」（被动），React 要的是「自己掐时间片让步后立刻续上」（主动）。模型不匹配。

### 5.4 选 MessageChannel

`MessageChannel.postMessage` 是**宏任务**（满足让步目标），且：

- **没有 4ms 嵌套惩罚**，高频调度不被拖慢；
- **调度更紧**，基本是「下一个事件循环迭代立即执行」；
- **优先级中性**，不绑帧、不受 timer 延迟策略影响，纯粹排进任务队列；
- **兼容性好**，几乎全环境可用，不支持时可降级 `setTimeout`。

所以 React Scheduler 的选择顺序是：**优先 `MessageChannel`，环境不支持时降级 `setTimeout`**。这也正是 `useEffect` 回调会成为宏任务、从而在第四节里能插队到 DCL 之前的根本原因。

> 一句话：**要宏任务（让步）+ 不要 4ms 延迟（紧）= `MessageChannel`。**

---

## 六、实践结论与避坑

把上面的分析落到日常开发：

1. **`useEffect` 不保证 defer 脚本已执行完。** 慢网络下，defer 脚本的执行会被拖到 `useEffect` 之后。不要在 `useEffect` 里直接读 defer 脚本注入的全局变量（如 `window.SomeSDK`）——它可能是 `undefined`。
2. **`useEffect` 不保证在 `DOMContentLoaded` 之后。** 同一原因，DCL 也会被慢 defer 拖后。
3. **要依赖外部脚本，自己控时序**：用动态 `import()`，或轮询等待全局变量就绪。把时序控制权拿回自己手里。
4. **必须在「defer + DOM 就绪」后跑的逻辑**：监听 `DOMContentLoaded` 时注意，`addEventListener` 只能在事件派发**之前**注册才有效——React 入口脚本执行时若 DCL 还没发能接住，若已发过（同步入口跑得晚）就接不到。更稳的做法是判断 `document.readyState`：已过 `"loading"` 就直接执行，否则监听。
5. **想等所有资源（含图片、iframe）就绪**，用 `window.load`，它在所有上述时机之后。

---

## 七、方法论小结

这次讨论本身比结论更值得记下的一点：**事件循环时序是浏览器实现敏感的问题，规范推理只能给「可能」，实测才给「确定」。** 纯靠规范推理下「永远谁先」的绝对结论，往往会在某个边界（如本文的慢下载 defer）翻车。能写最小页面跑日志的，就别只靠推理——让证据替自己说话。

---

## 参考出处

- [HTML Living Standard — the end（解析完成算法）](https://html.spec.whatwg.org/multipage/parsing.html#the-end)
- [HTML Living Standard — spin the event loop](https://html.spec.whatwg.org/multipage/webappapis.html#spin-the-event-loop)
- [HTML Living Standard — script processing model（defer 语义）](https://html.spec.whatwg.org/multipage/scripting.html#prepare-the-script-element)
- [HTML Living Standard — timers（setTimeout 嵌套 4ms 惩罚）](https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html)
- [MDN — `<script>`: defer 属性](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script#attr-defer)
- [MDN — DOMContentLoaded 事件](https://developer.mozilla.org/en-US/docs/Web/API/Document/DOMContentLoaded_event)
- [MDN — setTimeout（最小延迟说明）](https://developer.mozilla.org/zh-CN/docs/Web/API/setTimeout)
- React Scheduler 源码：`packages/scheduler` 中的 host config 实现，优先 `MessageChannel`、降级 `setTimeout`。
