# WebMCP：让网页成为 AI Agent 的工具服务器

> 整理日期：2026-04-02  
> 来源：W3C WebMCP 规范草案、Chrome for Developers 官方博客、MCP-B 文档、DataCamp 教程

---

## 它解决了什么问题

今天，AI Agent 操作网页的方式本质上是在模拟一个视力不太好的人类：截图、解析 DOM、猜测按钮位置、填写表单、祈祷页面布局没有变化。这种方式脆弱、昂贵、不准确。

WebMCP 提出了一个根本性的问题：**如果 AI Agent 也是你的用户，你的网站为什么不直接告诉它能做什么？**

WebMCP（Web Model Context Protocol）是 Google 和 Microsoft 工程师联合提出、在 W3C Web Machine Learning 社区组推进的浏览器原生 API 标准。它允许网页将自身功能以结构化"工具（Tools）"的形式直接暴露给 AI Agent，Agent 不再需要模拟点击，而是直接以 JSON 参数调用网页暴露的 JavaScript 函数。

---

## 核心概念

WebMCP 引入了一个新的全局对象：`navigator.modelContext`。

网页通过这个接口注册工具，每个工具包含：
- **name**：工具的唯一标识符
- **description**：自然语言描述，告诉 Agent 这个工具能做什么
- **inputSchema**：JSON Schema，定义参数类型、必填项、枚举值
- **execute**：实际执行逻辑的 JavaScript 回调函数
- **outputSchema**（可选）：描述返回值的结构

工具注册后，浏览器（或浏览器扩展、桥接层）负责将这些工具暴露给 AI Agent，Agent 发现工具、发送参数、接收结构化结果，整个过程不需要截图或 DOM 解析。

---

## 两种开发方式

### 方式一：声明式 API（Declarative API）

最轻量的接入方式，直接在 HTML 表单上添加属性注解，浏览器自动从表单结构生成 JSON Schema。

```html
<!-- 原始表单 -->
<form action="/search" method="GET">
  <input type="text" name="query" required>
  <select name="category">
    <option value="all">All</option>
    <option value="electronics">Electronics</option>
  </select>
  <button type="submit">Search</button>
</form>

<!-- 加上 WebMCP 注解后 -->
<form 
  action="/search" 
  method="GET"
  toolname="searchProducts"
  tooldescription="Search the product catalog by keyword and category"
>
  <input 
    type="text" 
    name="query" 
    required
    toolparamtitle="Search Query"
    toolparamdescription="The keyword to search for"
  >
  <select 
    name="category"
    toolparamdescription="Product category to filter results"
  >
    <option value="all">All</option>
    <option value="electronics">Electronics</option>
  </select>
  <button type="submit">Search</button>
</form>
```

四个属性就完成了接入：`toolname`、`tooldescription` 加在 `<form>` 上，`toolparamtitle`、`toolparamdescription` 加在具体字段上。浏览器会自动从 `<input>` 的 `type`、`required`、`<select>` 的 `<option>` 等信息合成 JSON Schema。

**注意**：声明式 API 的属性名称目前仍在 W3C 讨论中，尚未最终确定，生产环境使用需关注规范变化。

### 方式二：命令式 API（Imperative API）

适合动态逻辑、多步骤工作流、需要调用 API 的场景，提供完整的编程控制。

```javascript
// 基础用法
navigator.modelContext.registerTool({
  name: "searchFlights",
  description: "Search for available flights between two cities",
  inputSchema: {
    type: "object",
    properties: {
      origin: { 
        type: "string", 
        description: "Departure city IATA code (e.g., PEK, SHA)" 
      },
      destination: { 
        type: "string", 
        description: "Arrival city IATA code" 
      },
      date: { 
        type: "string", 
        format: "date",
        description: "Departure date in YYYY-MM-DD format" 
      },
      passengers: { 
        type: "integer", 
        minimum: 1, 
        maximum: 9,
        description: "Number of passengers" 
      }
    },
    required: ["origin", "destination", "date"]
  },
  execute: async ({ origin, destination, date, passengers = 1 }) => {
    const results = await flightAPI.search({ origin, destination, date, passengers });
    return {
      flights: results.map(f => ({
        flightNo: f.number,
        departure: f.departureTime,
        arrival: f.arrivalTime,
        price: f.price,
        seats: f.availableSeats
      }))
    };
  }
});
```

**动态注册与注销**：工具可以随页面状态变化动态注册/注销，这是 WebMCP 区别于传统 MCP Server 的关键特性。

```javascript
// 使用 AbortController 管理工具生命周期
const controller = new AbortController();

navigator.modelContext.registerTool(
  {
    name: "addToCart",
    description: "Add the current product to shopping cart",
    inputSchema: {
      type: "object",
      properties: {
        quantity: { type: "integer", minimum: 1 }
      },
      required: ["quantity"]
    },
    execute: async ({ quantity }) => {
      await cart.add(currentProductId, quantity);
      return { success: true, cartTotal: cart.total };
    }
  },
  { signal: controller.signal }  // 组件卸载时 abort 即可注销工具
);

// React 组件卸载时
useEffect(() => {
  return () => controller.abort();
}, []);
```

**只读提示（readOnlyHint）**：对于不修改状态的查询类工具，可以声明 `annotations: { readOnlyHint: true }`，帮助 Agent 判断是否需要用户确认。

### React 集成

社区已有 `react-webmcp` 库，提供 Hook 封装：

```javascript
import { useWebMCPTool } from 'react-webmcp';

function ProductPage({ productId }) {
  useWebMCPTool({
    name: "getProductDetails",
    description: "Get detailed information about the current product",
    inputSchema: { type: "object", properties: {} },
    execute: async () => {
      return await fetchProduct(productId);
    }
  });
  // Hook 内部处理注册和注销，组件卸载时自动清理
}
```

---

## 开发环境搭建

目前 WebMCP 处于早期预览阶段，需要特定环境：

**浏览器要求**：Chrome Canary 146.0.7672.0 或更高版本（稳定版、Beta、Dev 均不支持）。

**启用实验性标志**：
1. 打开 `chrome://flags/#enable-webmcp-testing`
2. 将 "WebMCP for testing" 设为 Enabled
3. 重启浏览器

**验证是否生效**：
```javascript
// 在 DevTools Console 中运行
console.log(navigator.modelContext); // 应输出对象而非 undefined
```

**调试工具**：安装 Chrome 扩展 [Model Context Tool Inspector](https://chromewebstore.google.com/detail/webmcp-model-context-tool/gbpdfapgefenggkahomfgkhfehlcenpd)，可以列出当前页面所有注册的工具、手动执行工具、查看 Schema，还内置了 Gemini API 支持，可以用自然语言测试工具调用。

**生产环境 Polyfill**：对于不支持原生 WebMCP 的浏览器，可以使用 `@mcp-b/webmcp-polyfill`：

```bash
npm install @mcp-b/webmcp-polyfill
```

```javascript
import '@mcp-b/webmcp-polyfill';
// 之后 navigator.modelContext 在所有现代浏览器中均可用
```

---

## WebMCP vs MCP Server：本质区别

这是理解 WebMCP 定位最关键的问题。两者不是竞争关系，而是在不同层次解决不同问题。

| 维度 | MCP Server | WebMCP |
|------|-----------|--------|
| **运行环境** | 服务端进程（Node.js/Python 等） | 浏览器页面（客户端 JavaScript） |
| **传输协议** | stdio、HTTP/SSE | 浏览器中介、扩展消息、中继 |
| **工具注册时机** | 启动时固定注册，连接后不可变更 | 页面生命周期内动态注册/注销 |
| **上下文共享** | 需要显式传递认证信息 | 天然共享用户的登录态、Cookie、内存状态 |
| **部署方式** | 需要独立部署服务端进程 | 直接在前端代码中实现，无需后端 |
| **安全模型** | 由服务端自行控制 | 浏览器原生安全模型（同源策略、HTTPS 要求） |
| **标准化状态** | Anthropic 主导的开放协议，已广泛采用 | W3C 社区组草案，仅 Chrome 早期预览 |
| **适用场景** | 后端数据库、API、文件系统、开发工具 | 网页应用的前端功能、表单操作、UI 交互 |

**一个关键的技术差异**：MCP Server 的官方 SDK 强制要求在 transport 连接前完成所有工具注册（连接后注册会抛出异常）。这对服务端进程合理，但在浏览器中行不通——页面已经加载，但工具随着 JavaScript 执行才逐步出现。WebMCP 的动态注册模型正是为解决这个问题而设计的。

**两者如何协作**：WebMCP 和 MCP Server 可以通过"桥接层"连接。例如 `@mcp-b/chrome-devtools-mcp` 是一个标准 MCP Server，通过 Chrome DevTools Protocol 桥接到浏览器，让桌面 AI Agent（Claude Desktop、Cursor 等）能够调用网页上注册的 WebMCP 工具。请求路径：MCP Client → chrome-devtools-mcp（MCP Server）→ Chrome DevTools Protocol → 浏览器 → WebMCP 工具执行。

---

## 优势

**零基础设施成本**：工具运行在浏览器 tab 里，不需要部署任何服务端进程。对于已有 Web 应用的团队，接入成本极低，声明式 API 甚至只需要在 HTML 上加几个属性。

**天然的上下文共享**：工具执行时自动拥有用户的完整会话状态——登录态、Cookie、本地存储、内存中的应用状态。MCP Server 要实现同等效果需要复杂的认证传递机制。

**动态工具注册**：工具可以随页面状态实时变化。用户登录前只暴露 `login` 工具，登录后暴露账户相关工具；进入商品详情页注册 `addToCart`，离开时自动注销。这种动态性是 MCP Server 架构难以实现的。

**浏览器原生安全模型**：HTTPS 强制要求（`SecureContext`）、同源策略、用户可见的交互确认（`:tool-form-active` CSS 伪类让用户看到 Agent 正在操作哪个表单）。安全边界由浏览器而非开发者自行维护。

**渐进式接入**：现有网站不需要重写，声明式 API 可以在不改变任何业务逻辑的情况下让表单变成 Agent 可调用的工具。

---

## 劣势与局限

**规范尚未稳定**：截至 2026 年初，WebMCP 仍是 W3C 社区组草案（CG-DRAFT），不是正式标准。声明式 API 的属性名称、Consumer API（`listTools`/`executeTool`）的接口形态、跨域 iframe 策略等关键问题仍在讨论中。2026 年 3 月规范已经移除了 `provideContext` 和 `clearContext` 方法，说明 API 仍在变动。

**浏览器支持极为有限**：目前只有 Chrome Canary 146+ 在实验性标志下支持，Firefox 和 Safari 均无公开支持信号。Edge 继承 Chromium 支持，但也需要开启标志。生产环境必须依赖 Polyfill。

**必须有活跃的浏览器 Tab**：工具调用在浏览器 tab 的 JavaScript 上下文中执行，没有无头（headless）或后台执行模型。Agent 无法调用一个没有打开的页面上的工具。

**无跨站点发现机制**：Agent 必须先访问页面才能知道它提供了哪些工具，没有类似 `robots.txt` 或 `.well-known/webmcp` 的预访问发现机制（规范中提到了这个方向但尚未定义）。

**UI 同步负担**：工具调用修改应用状态后，浏览器不会自动同步 UI，开发者需要确保工具调用路径和用户交互路径走同一套状态更新逻辑，对复杂 SPA 可能需要重构。

**安全威胁尚未完全解决**：Prompt Injection（恶意网页通过工具描述注入指令操控 Agent）和工具链数据泄露问题在规范中被承认但尚未给出完整解决方案。

---

## 当前状态与展望

WebMCP 于 2025 年 8 月由 Google 和 Microsoft 工程师在 W3C 提出，2026 年 2 月随 Chrome 146 Canary 发布早期预览版。GitHub 仓库 `MiguelsPizza/WebMCP` 已被接受为 W3C 可交付成果，正式进入标准化轨道。

从时间线看，WebMCP 代表了 Web 与 AI Agent 交互范式的一次根本性转变：从"AI 模拟人类操作网页"到"网页主动声明自己能为 AI 做什么"。这个方向是正确的，但距离生产可用还需要等待规范稳定和浏览器广泛支持。

对于开发者，现在是了解和实验的好时机，但生产环境接入需要谨慎评估 Polyfill 的稳定性和规范变动风险。

---

## 参考资料

- [W3C WebMCP 规范草案](https://webmachinelearning.github.io/webmcp/) — 权威规范文档
- [Chrome for Developers: WebMCP 早期预览版](https://developer.chrome.google.cn/blog/webmcp-epp?hl=zh-cn) — Google 官方介绍
- [MCP-B 文档：WebMCP vs MCP](https://docs.mcp-b.ai/explanation/webmcp-vs-mcp) — 深度对比分析
- [MCP-B 文档：规范状态与局限性](https://docs.mcp-b.ai/explanation/design/spec-status-and-limitations) — 已知问题汇总
- [DataCamp WebMCP Tutorial](https://www.datacamp.com/tutorial/webmcp-tutorial) — 实战教程
- [Patrick Brosset: WebMCP updates](https://patrickbrosset.com/articles/2026-02-23-webmcp-updates-clarifications-and-next-steps/) — 规范编辑者的进展更新
