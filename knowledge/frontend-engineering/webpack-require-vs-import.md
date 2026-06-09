# require 与 import：从规范差异到构建工具行为

> 整理日期：2026-06-02  
> 适用场景：React + Webpack / Vite 前端项目

---

## 两套规范的历史背景

`require` 和 `import` 不是同一套东西的两种写法，它们来自两个完全不同的模块规范，诞生于不同的历史时期。

**CommonJS（CJS）** 是 Node.js 在 2009 年引入的模块系统，`require` 是它的核心 API。它的设计目标是服务器端同步加载，因为服务器读取本地文件不需要等待网络，同步是合理的。

**ES Modules（ESM）** 是 ECMAScript 2015（ES6）正式纳入语言标准的模块系统，`import` / `export` 是它的语法。它是 JavaScript 语言层面的官方标准，设计时就考虑了浏览器异步加载的需求。

这两套规范在语法上看起来相似，但底层机制有根本差异。

---

## 核心差异：静态 vs 动态

这是理解两者最重要的一个维度。

### import 是静态的（编译时）

```js
import React from 'react';
import { useState, useEffect } from 'react';
import logo from './logo.png';
```

`import` 语句必须写在模块顶层，路径必须是字符串字面量，不能是变量，不能放在 `if` 块里。这是语言规范的强制要求，不是风格建议。

这意味着：在代码真正执行之前，构建工具（或 JS 引擎）就能通过静态分析确定所有依赖关系，形成一张完整的依赖图。

### require 是动态的（运行时）

```js
const React = require('react');
const path = condition ? './a' : './b';
const module = require(path);  // 完全合法

if (someCondition) {
  const utils = require('./utils');  // 也合法
}
```

`require` 是一个普通函数调用，在运行时执行，路径可以是任意表达式。这带来了极大的灵活性，但代价是构建工具无法在编译期确定依赖关系。

---

## 导出机制的差异

### CommonJS：导出的是值的拷贝

```js
// counter.js
let count = 0;
module.exports = { count, increment: () => count++ };

// main.js
const { count } = require('./counter');
counter.increment();
console.log(count); // 仍然是 0，因为拿到的是拷贝
```

`module.exports` 导出的是一个对象，`require` 拿到的是这个对象的引用（对于基本类型则是值的拷贝）。模块内部状态的变化不会自动反映到已经解构出来的变量上。

### ESM：导出的是活绑定（Live Binding）

```js
// counter.js
export let count = 0;
export const increment = () => count++;

// main.js
import { count, increment } from './counter';
increment();
console.log(count); // 1，因为是活绑定
```

ESM 的 `export` 导出的不是值，而是对变量的实时绑定。导入方看到的永远是最新值。这是 ESM 与 CJS 在语义上最本质的区别之一。

---

## Webpack 如何处理它们

Webpack 的核心工作是构建依赖图，然后将所有模块打包成 bundle。它对 `require` 和 `import` 的处理方式有显著差异。

### 对 import 的处理：静态分析 + Tree Shaking

Webpack 在构建阶段会对所有 `import` 语句做静态分析，精确知道每个模块导出了什么、哪些被用到了。这使得 **Tree Shaking** 成为可能。

Tree Shaking 是指在打包时自动删除未被引用的代码（dead code）。它依赖 ESM 的静态结构：

```js
// math.js
export const add = (a, b) => a + b;
export const multiply = (a, b) => a * b;  // 如果没有被 import，会被删除

// main.js
import { add } from './math';  // multiply 不会进入 bundle
```

**Tree Shaking 只对 ESM 有效，对 `require` 无效。** 因为 `require` 是运行时的，Webpack 无法在编译期确定你到底用了哪些导出。

### 对 require 的处理：运行时模拟

Webpack 会在 bundle 中注入一个 `__webpack_require__` 函数来模拟 Node.js 的 `require`。所有 `require` 调用在运行时通过这个函数查找模块。

```js
// 打包后的代码（简化示意）
var __webpack_modules__ = {
  './utils.js': function(module, exports) {
    // utils.js 的内容
  }
};

function __webpack_require__(moduleId) {
  // 查找并执行模块，返回 exports
}
```

对于动态 `require`（路径是变量），Webpack 会尝试分析可能的路径范围，将所有可能的模块都打包进来，这可能导致 bundle 体积意外增大。

### 混用时的互操作（Interop）

在实际项目中，`require` 和 `import` 经常混用。Webpack 会处理这种互操作，但有一个细节需要注意：

当用 `import` 导入一个 CJS 模块时，Webpack 会将 `module.exports` 整体作为 `default` 导出：

```js
// 某个 CJS 模块
module.exports = { foo: 1, bar: 2 };

// 用 import 引入
import utils from './utils';  // utils = { foo: 1, bar: 2 }
import { foo } from './utils';  // 可能不生效，取决于 Webpack 配置
```

反过来，用 `require` 引入一个 ESM 模块时，拿到的是整个模块对象，需要通过 `.default` 访问默认导出：

```js
const React = require('react');
// 如果 react 是 ESM，可能需要 React.default
```

---

## 图片资源的特殊情况

在前端项目里，`require` 和 `import` 不只用于 JS 模块，还常用于引入图片等静态资源。这里 Webpack 的处理逻辑是一样的，但结果取决于配置的 loader。

```js
// 两种写法等价，Webpack 都会交给对应 loader 处理
import logo from './logo.png';
const logo = require('./logo.png');
```

**Webpack 4** 需要配置 `file-loader` 或 `url-loader`：
- `file-loader`：将图片复制到输出目录，返回最终 URL 字符串
- `url-loader`：小图片转为 base64 Data URI 内联，大图片降级为 `file-loader`

**Webpack 5** 内置了 Asset Modules，不再需要额外 loader：

```js
// webpack.config.js
module.exports = {
  module: {
    rules: [
      {
        test: /\.(png|jpg|gif|svg)$/,
        type: 'asset',  // 自动判断：小图内联，大图输出文件
        parser: {
          dataUrlCondition: {
            maxSize: 8 * 1024  // 8KB 以下转 base64
          }
        }
      }
    ]
  }
};
```

Asset Modules 的四种类型：
- `asset/resource`：输出独立文件，返回 URL（等同于 `file-loader`）
- `asset/inline`：转为 base64 Data URI（等同于 `url-loader`）
- `asset/source`：返回文件原始内容字符串（等同于 `raw-loader`）
- `asset`：自动选择，小于阈值内联，大于阈值输出文件

无论用 `require` 还是 `import` 引入图片，Webpack 都会将其纳入依赖图，交给对应的 loader/asset module 处理，最终返回一个可用的 URL 字符串或 base64 字符串。

---

## Vite vs Webpack：为什么 Vite 不支持 require

这是一个在迁移项目时经常踩的坑，值得单独说清楚。

### Webpack 为什么支持 require

Webpack 是一个**打包器（bundler）**，它在构建时会遍历整个依赖图，把所有模块（无论是 ESM 还是 CJS）都转换成自己内部的模块格式，最终输出一个或多个 bundle 文件。在这个过程中，Webpack 会把所有 `require` 调用替换成自己注入的 `__webpack_require__` 函数，所以 `require` 在 Webpack 的输出产物里是完全可以工作的——它已经不是原始的 Node.js `require` 了，而是 Webpack 模拟出来的。

这意味着：**Webpack 对 `require` 的支持是主动兼容的结果，不是理所当然的。**

### Vite 为什么不支持 require

Vite 的开发模式走的是完全不同的路线。它**不打包**，而是直接利用浏览器原生的 ES Modules 支持，按需向浏览器提供模块文件。浏览器请求哪个模块，Vite 就即时转换哪个模块，返回标准的 ESM 格式。

浏览器原生只认识 `import`，不认识 `require`。Vite 没有像 Webpack 那样注入一个运行时来模拟 `require`，所以如果你的代码里写了 `require`，浏览器在执行时会直接报错：

```
ReferenceError: require is not defined
```

Vite 的生产构建（`vite build`）底层用的是 Rollup，同样是以 ESM 为核心，也不会帮你处理 `require`。

### 一个常见的迁移陷阱

从 Webpack 项目迁移到 Vite 时，最常见的报错就是代码里残留的 `require`。尤其是图片引用，老项目里经常这样写：

```js
// Webpack 项目里可以正常工作
const logo = require('./logo.png');

// 迁移到 Vite 后必须改成
import logo from './logo.png';
```

还有一种更隐蔽的情况：某些第三方库或老的工具函数内部使用了 `require`，在 Webpack 下没问题，到 Vite 下就会炸。这时候需要检查依赖，或者用 Vite 的 `@vitejs/plugin-commonjs` 插件（底层是 `@rollup/plugin-commonjs`）来做兼容转换。

### 核心区别对比

|  | Webpack | Vite（开发模式） |
|--|---------|----------------|
| 工作方式 | 打包，输出 bundle | 不打包，原生 ESM 按需提供 |
| 对 `require` 的支持 | 支持，运行时模拟 | 不支持，浏览器不认识 |
| 对 `import` 的支持 | 支持 | 支持（原生） |
| 冷启动速度 | 慢（需要打包整个项目） | 快（无需打包） |
| 模块规范立场 | CJS + ESM 兼容 | ESM 优先 |

---

## 实践建议

在 React + Webpack 项目中，推荐统一使用 `import`，原因如下：

1. **Tree Shaking 生效**：`import` 让 Webpack 能删除未使用的代码，减小 bundle 体积
2. **语义更清晰**：`import` 的静态结构让依赖关系一目了然，便于代码审查和工具分析
3. **活绑定语义**：对于需要响应模块内部状态变化的场景，ESM 的活绑定更符合预期
4. **未来方向**：ESM 是 JavaScript 官方标准，生态正在全面向 ESM 迁移

`require` 仍然有其用武之地：需要条件加载、路径动态拼接、或者在 Node.js 脚本（如 webpack.config.js 本身）中使用时，`require` 更自然。

---

## 参考来源

- [Webpack 官方文档 - ECMAScript Modules](https://webpack.js.org/guides/ecma-script-modules/)
- [Webpack 官方文档 - Asset Modules](https://webpack.js.org/guides/asset-modules/)
- [Webpack 官方文档 - Tree Shaking](https://webpack.js.org/guides/tree-shaking/)
- [MDN - JavaScript modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
