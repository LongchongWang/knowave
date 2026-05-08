# TypeScript、JS、MJS 模块系统综述

> 整理日期：2026-05-08  
> 来源：对话整理 + Node.js 官方文档 + TypeScript 官方文档

---

## 从一个困惑说起

在 TypeScript 里写 `import foo from './bar.js'`，但磁盘上根本没有 `bar.js`，只有 `bar.ts`。这看起来像是一个 bug，但它其实是一个经过深思熟虑的设计决策。要理解它，需要从头捋清楚整个模块系统的演化脉络。

---

## 第一层：Node.js 的两套模块系统

Node.js 历史上有两套完全不同的模块系统并存，它们的解析规则截然不同。

**CommonJS（CJS）** 是 Node.js 的原生模块系统，诞生于 2009 年。它的核心是 `require()`，解析规则非常宽松：你可以写 `require('./bar')`，Node.js 会自动尝试 `bar`、`bar.js`、`bar.json`、`bar/index.js` 等一系列路径，直到找到为止。这种"猜测"行为让开发者写起来很方便，但代价是解析过程是同步的、不透明的。

**ECMAScript Modules（ESM）** 是 JavaScript 语言标准（ES2015）定义的模块系统，使用 `import`/`export` 语法。Node.js 从 v12 开始正式支持它。ESM 的解析规则完全不同：**路径必须精确，不允许省略扩展名，不允许省略 `index.js`**。

Node.js 官方文档对此的解释是：ESM 的解析语义对齐了浏览器的 URL 解析行为。在浏览器里，`import './bar'` 和 `import './bar.js'` 是两个完全不同的 URL，服务器不会替你猜测。Node.js 的 ESM 实现选择了同样的严格语义，以保持跨环境的一致性。

---

## 第二层：文件扩展名如何决定模块类型

Node.js 用以下规则判断一个文件应该用哪套系统加载：

`.mjs` 文件永远以 ESM 加载。`.cjs` 文件永远以 CJS 加载。这两个扩展名是明确的、无歧义的信号。

`.js` 文件则取决于**最近的父级 `package.json`** 里的 `"type"` 字段。如果 `"type": "module"`，则 `.js` 文件以 ESM 加载；如果 `"type": "commonjs"` 或者没有这个字段，则以 CJS 加载。

这个设计的含义是：`.js` 是一个"模糊"的扩展名，它的语义由 `package.json` 上下文决定。而 `.mjs` 和 `.cjs` 是"明确"的扩展名，不受上下文影响。

```
文件扩展名     加载方式
.mjs        → 永远 ESM
.cjs        → 永远 CJS
.js         → 由最近父级 package.json 的 "type" 字段决定
              "type": "module"    → ESM
              "type": "commonjs"  → CJS
              （无 type 字段）    → CJS（默认）
```

---

## 第三层：TypeScript 的编译模型

TypeScript 是一个编译到 JavaScript 的语言。`tsc` 把 `.ts` 文件编译成 `.js` 文件（或 `.mjs`、`.cjs`），然后 Node.js 运行编译产物，而不是 `.ts` 源文件。

这里有一个关键的时间差：**TypeScript 在编译时做类型检查，Node.js 在运行时执行 JS**。TypeScript 编译器需要在编译时就知道：你写的这条 `import` 语句，在运行时 Node.js 会用哪套规则去解析它？

这就是 `tsconfig.json` 里 `module` 和 `moduleResolution` 两个选项存在的原因。它们不是在控制 TypeScript 自己怎么找文件，而是在告诉 TypeScript：**你的编译产物将在什么环境下运行，那个环境会用什么规则解析模块**。

---

## 第四层：`moduleResolution: "node16"` / `"nodenext"` 的核心逻辑

在旧的 `moduleResolution: "node"` 模式下，TypeScript 模拟的是 CJS 的解析规则——可以省略扩展名，TypeScript 会自动尝试 `.ts`、`.tsx`、`.d.ts` 等。这对于纯 CJS 项目工作得很好。

但当你的项目是 ESM（`"type": "module"` 或使用 `.mjs`），编译产物将在 Node.js 的 ESM 环境下运行。ESM 要求精确的扩展名。如果 TypeScript 允许你写 `import './bar'`，编译出来的 JS 里也是 `import './bar'`，Node.js 运行时就会报错找不到模块。

`moduleResolution: "node16"` 的设计原则是：**TypeScript 的模块解析行为必须精确模拟运行时的行为**。既然运行时（Node.js ESM）要求写 `.js`，TypeScript 就要求你在源码里也写 `.js`。

这里有一个让人困惑的地方：你写的是 `import './bar.js'`，但磁盘上是 `bar.ts`。TypeScript 是怎么找到它的？

答案是：TypeScript 在 `node16` 模式下，看到 `.js` 扩展名时，会**同时**去查找对应的 `.ts` 文件。也就是说，`import './bar.js'` 在 TypeScript 的视角里，会去找 `bar.ts`（或 `bar.tsx`、`bar.d.ts`）。编译后，输出的 JS 文件里保留 `import './bar.js'`，这正是 Node.js 运行时需要的路径。

这个设计的本质是：**import 路径描述的是输出文件的位置，而不是源文件的位置**。TypeScript 只是在编译时帮你把 `.js` 映射到对应的 `.ts` 源文件。

---

## 第五层：`.mts` 和 `.cts` 的存在意义

TypeScript 4.7 引入了 `.mts` 和 `.cts` 扩展名，分别对应 `.mjs` 和 `.cjs` 的输出。

`.mts` 文件永远编译为 `.mjs`，永远以 ESM 语义处理，不受 `package.json` 的 `"type"` 字段影响。`.cts` 文件永远编译为 `.cjs`，永远以 CJS 语义处理。

这对于需要在同一个包里同时提供 ESM 和 CJS 版本（即"双模式包"，dual package）的场景非常有用。

```
源文件扩展名     编译产物扩展名     Node.js 加载方式
.ts          →  .js           →  由 package.json "type" 决定
.mts         →  .mjs          →  永远 ESM
.cts         →  .cjs          →  永远 CJS
```

---

## `module` 与 `moduleResolution` 的取值详解

这两个选项经常让人困惑，因为它们名字相近，但控制的是完全不同的两件事。一句话区分：**`module` 决定编译产物用什么格式**，**`moduleResolution` 决定 TypeScript 编译时怎么找文件**。

### `module`：控制输出格式

这个选项告诉 TypeScript：你的代码最终会在什么环境下运行，那个环境期望看到什么格式的模块代码。TypeScript 据此决定如何把 `import`/`export` 语句编译成 JS。

**`commonjs`**：把所有 `import` 编译成 `require()`，把 `export` 编译成 `module.exports`。这是最传统的 Node.js 格式，也是历史上最常见的选择。适合运行在老版本 Node.js 或需要 CJS 格式的场景。

**`es2015` / `es2020` / `es2022` / `esnext`**：保留 `import`/`export` 语法不变，输出标准 ESM 格式。数字代表目标 ES 版本，主要影响的是其他语法特性（比如 `esnext` 允许使用最新的 JS 特性），对模块格式本身影响不大。这类选项通常配合打包工具（Vite、webpack）使用，因为打包工具会接管模块解析，不需要 TypeScript 操心运行时的细节。

**`nodenext`**（以及 `node16`、`node18`、`node20`）：这是专门为现代 Node.js 设计的选项。它的特殊之处在于，**输出格式不是固定的**——同一个项目里，`.ts` 文件可能被编译成 CJS，也可能被编译成 ESM，取决于文件扩展名（`.mts` → `.mjs`，`.cts` → `.cjs`）和 `package.json` 的 `"type"` 字段。这正是 Node.js 自身的行为，TypeScript 在这里做的是精确模拟。设置 `module: "nodenext"` 会自动隐含 `moduleResolution: "nodenext"`。

**`preserve`**（TypeScript 5.4 引入）：不转换任何模块语法，原样保留。ESM 的 `import`/`export` 保持不变，CJS 风格的 `import x = require(...)` 也保持不变。这个选项是为"我有其他工具（如 esbuild、swc）来处理模块转换，TypeScript 只需要做类型检查"的场景设计的。配合 `moduleResolution: "bundler"` 使用。

**`amd` / `umd` / `system`**：历史遗留格式，分别对应 RequireJS、通用模块定义、SystemJS。现代项目基本不会用到。

### `moduleResolution`：控制编译时的文件查找算法

这个选项告诉 TypeScript：当你写 `import foo from './bar'` 时，TypeScript 应该按照什么规则去磁盘上找对应的文件。注意，这只影响编译时的类型检查，不影响运行时。

**`classic`**：TypeScript 最早的解析算法，现在只为向后兼容而存在。它不模拟任何真实的运行时行为，查找规则比较奇特（比如非相对路径会一层层向上找）。**不要在新项目里使用它。**

**`node`**（也写作 `node10`）：模拟 Node.js 的 CJS `require()` 解析算法。可以省略扩展名，会自动尝试 `index.js`，会查找 `node_modules`。这是很长一段时间内的默认选项，对应 `module: "commonjs"` 的场景。问题在于它模拟的是 Node.js v12 之前的旧行为，不理解 ESM，也不理解 `package.json` 的 `exports` 字段。

**`node16` / `node18` / `node20` / `nodenext`**：模拟现代 Node.js 的完整解析行为，同时支持 CJS 和 ESM 两套算法。具体用哪套，取决于当前文件被判定为 CJS 还是 ESM（判定规则和 Node.js 一致）。这个模式下，ESM 文件里的相对路径 import 必须写完整扩展名；CJS 文件里的 `require()` 则仍然可以省略扩展名。同时，这个模式会识别 `package.json` 的 `exports` 字段，这对于正确解析现代 npm 包非常重要。`node16` 和 `nodenext` 目前行为相同，`nodenext` 是"跟随 Node.js 最新版本"的别名。

**`bundler`**（TypeScript 5.0 引入）：模拟 Vite、esbuild、webpack 等打包工具的解析行为。它的特点是"两头都要"：像 ESM 一样识别 `package.json` 的 `exports` 字段，但像 CJS 一样允许省略扩展名和 `index` 文件。这是因为打包工具通常会在内部做路径补全，不需要开发者手动写 `.js`。这个模式要求 `module` 设置为 `esnext` 或 `preserve`，不能和 `module: "commonjs"` 搭配。

### 两者的搭配关系

这两个选项不是完全独立的，有些组合是合法的，有些会报错。官方推荐的搭配如下：

```jsonc
// 场景一：用 tsc 直接编译，产物跑在 Node.js 上
{
  "module": "nodenext"
  // moduleResolution 自动隐含为 "nodenext"，不需要单独写
}

// 场景二：用 Vite / esbuild / webpack 等打包工具
{
  "module": "esnext",
  "moduleResolution": "bundler"
}

// 场景三：传统 Node.js CJS 项目（老项目维护）
{
  "module": "commonjs",
  "moduleResolution": "node"
}

// 场景四：编写库，追求最严格的兼容性检查
{
  "module": "node18"
  // 同样自动隐含 moduleResolution: "nodenext"
}
```

一个常见的错误配置是 `module: "esnext"` + `moduleResolution: "node"`。这会导致 TypeScript 认为输出是 ESM，但用旧的 CJS 解析规则找文件，两者的假设互相矛盾，容易产生运行时能跑但类型检查有问题、或者反过来的情况。TypeScript 5.0 之后对这类不一致的组合会给出警告。

### 速查表

| 使用场景 | `module` | `moduleResolution` | 是否需要写 `.js` 扩展名 |
|---|---|---|---|
| 直接用 tsc 编译跑 Node.js | `nodenext` | `nodenext`（自动） | ESM 文件需要，CJS 不需要 |
| Vite / esbuild / webpack | `esnext` | `bundler` | 不需要 |
| 传统 Node.js CJS 项目 | `commonjs` | `node` | 不需要 |
| 编写 npm 库 | `node18` | `nodenext`（自动） | ESM 文件需要 |
| tsx / ts-node（打包器模式） | `esnext` | `bundler` | 不需要 |

---

## 为什么这个设计"奇怪"但正确

你觉得在 `.ts` 文件里写 `.js` 扩展名很奇怪，这个直觉完全合理。它违反了"所见即所得"的直觉——你看到的是 `.js`，但实际对应的是 `.ts`。

但这个设计的替代方案更糟糕。如果 TypeScript 允许你写 `import './bar'`，然后在编译时自动把它改写成 `import './bar.js'`，那么 TypeScript 就在悄悄修改你的代码语义，这会带来更多不可预期的问题。TypeScript 团队明确拒绝了这个方向，理由是：**TypeScript 不应该修改 import 路径，因为这超出了"类型擦除"的范畴**。

所以最终的设计是：你写什么，编译出来就是什么。TypeScript 只负责类型检查，不负责重写路径。代价是你需要在源码里写"未来的"路径（即编译产物的路径）。

如果你觉得这个约束太烦，有两个常见的逃脱方案：一是使用 `moduleResolution: "bundler"`（配合 Vite、esbuild 等工具），打包工具会帮你处理扩展名；二是使用 `tsx` 或 `ts-node` 等运行时直接执行 `.ts` 文件，完全绕过这个问题。

---

## 参考来源

- [Node.js 官方文档：ECMAScript Modules](https://nodejs.org/api/esm.html)
- [Node.js 官方文档：Packages（`"type"` 字段）](https://nodejs.org/api/packages.html)
- [TypeScript TSConfig Reference：moduleResolution](https://www.typescriptlang.org/tsconfig/moduleResolution.html)
- [TypeScript TSConfig Reference：module](https://www.typescriptlang.org/tsconfig/module.html)
- [TypeScript Handbook：Modules - Choosing Compiler Options](https://www.typescriptlang.org/docs/handbook/modules/guides/choosing-compiler-options.html)
