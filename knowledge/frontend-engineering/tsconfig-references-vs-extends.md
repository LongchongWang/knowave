# tsconfig 的 references 与 extends：配置继承与项目引用

## 它们解决的是两个完全不同的问题

`extends` 和 `references` 都出现在 tsconfig.json 的顶层字段中，也都涉及"多个 tsconfig 之间的关系"，但它们解决的问题截然不同。一句话概括：`extends` 是**配置复用**（DRY 原则），`references` 是**文件管辖划分**（让不同文件归不同 tsconfig 管）。

---

## extends：配置继承

### 引入时间

TypeScript 2.1（2016 年）引入，TypeScript 5.0（2023 年）扩展为支持数组形式。

### 核心机制

`extends` 的值是一个路径（或路径数组），指向另一个 tsconfig.json。编译器加载时，先加载基础文件中的配置，然后用当前文件中的同名字段**覆盖**基础配置。

```jsonc
// tsconfig.base.json — 整个仓库的公共配置
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

```jsonc
// packages/app/tsconfig.json — 具体项目继承并覆盖
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "jsx": "react-jsx",   // 新增
    "target": "ES2020"    // 覆盖基础配置中的 ES2022
  },
  "include": ["src"]
}
```

### 覆盖规则的细节

这是容易踩坑的地方。`compilerOptions` 中的各个字段是**逐字段浅覆盖**（不是深合并）。也就是说，如果基础配置有 `"lib": ["ES2022", "DOM"]`，子配置写了 `"lib": ["ES2020"]`，最终结果是 `["ES2020"]`——不会合并成 `["ES2022", "DOM", "ES2020"]`。

而 `files`、`include`、`exclude` 这三个顶层字段的行为更直接：子配置中一旦出现，就**完全替换**基础配置中的对应字段，不做任何合并。

另一个需要记住的规则是：**`references` 字段不会被继承**。即使基础配置里写了 `references`，子配置也不会拿到——这是刻意设计，因为引用关系是每个配置自身的结构性声明，不应该被"默默继承"。

### TypeScript 5.0 的数组 extends

从 5.0 开始，`extends` 支持传入数组，实现多重继承：

```jsonc
{
  "extends": [
    "@tsconfig/node20/tsconfig.json",
    "@company/tsconfig-strict/tsconfig.json"
  ]
}
```

数组中后面的配置优先级更高（后来者覆盖前者）。这让社区的 `@tsconfig/bases` 和公司内部的公共配置可以灵活组合。

### 路径解析

`extends` 的路径遵循 Node.js 风格的解析：相对路径从当前 tsconfig 所在目录解析，也可以使用 npm 包名（如 `@tsconfig/node20/tsconfig.json`），编译器会从 `node_modules` 中查找。

### 典型使用场景

当你有多个 tsconfig 需要**共享相同的编译器配置**时。比如 monorepo 中所有子包共享严格模式和模块策略，或者测试配置继承主配置但额外加上 `types: ["jest"]`。

---

## references：项目引用（文件管辖划分）

### 引入时间

TypeScript 3.0（2018 年）引入。

### 本质：告诉编译器和 IDE "某些文件不归我管，归另一个 tsconfig 管"

references 最核心的作用是**划分文件的管辖权**。一个主 tsconfig 通过 `"references": [{ "path": "./tsconfig.node.json" }]` 声明了一个子配置，相当于说："某些文件不归我管，归这个子配置管。"

这样，TypeScript 编译器和 IDE（VS Code 的 tsserver）就知道各自 `include` 的文件由各自的配置检查，两者互不干扰。如果不靠 references 做显式声明，IDE 只能通过"就近匹配"猜哪个 tsconfig 该管哪个文件，行为不稳定。

**粒度是文件，不是包。** 这一点至关重要。references 不是"包对包"的依赖声明，而是"配置对文件"的管辖声明。同一个目录下的不同文件，完全可以归不同的 tsconfig 管。

### 最典型的例子：Vite 项目

Vite 创建的 TypeScript 项目会生成这样的结构：

```jsonc
// tsconfig.json — 主配置，自己不管任何文件，只做分发
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

```jsonc
// tsconfig.app.json — 管浏览器环境的文件
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx"
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"]
}
```

```jsonc
// tsconfig.node.json — 管 Node.js 环境的文件
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": ["node"]
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

这里的逻辑很清楚：`vite.config.ts` 运行在 Node.js 环境，需要 Node 类型定义、不需要 DOM；`src/` 下的业务代码运行在浏览器，需要 DOM、不需要 Node。它们是同一个项目里的文件，但需要不同的类型环境。references 让 IDE 精确知道哪个文件归哪个配置管。

### 如果不用 references 会怎样

假设你在根 tsconfig 里同时 `include` 了 `src/` 和 `vite.config.ts`，并且 `lib` 里同时包含 `DOM` 和 Node 类型。表面上"能用"，但实际上：`src/` 下的代码能访问 `process`、`__dirname` 等 Node 全局变量而不报错，`vite.config.ts` 里也能写 `document.querySelector` 而不报错——类型隔离完全失效，IDE 的检查形同虚设。

### 扩展场景：monorepo 跨包

references 在 monorepo 中也能发挥作用，此时每个包有自己的 tsconfig，根配置通过 references 列出所有子包。配合 `composite: true` 和 `tsc --build` 可以实现按依赖拓扑的增量编译。但这是 references 的**高级用法**，不是它的本质定义。

```jsonc
// monorepo 根 tsconfig.json
{
  "files": [],
  "references": [
    { "path": "packages/utils" },
    { "path": "packages/core" },
    { "path": "packages/app" }
  ]
}
```

在这个场景中，被引用的子项目需要 `composite: true`，它会：强制开启 `declaration`（产出 .d.ts），强制所有源文件必须被 `include` 覆盖，开启 `incremental`（产出 .tsbuildinfo 用于增量判断）。然后 `tsc --build` 能按拓扑顺序只重编有变化的子项目。

但即使你不用 `tsc --build`（比如用 Vite 做打包、只在 CI 跑 `tsc --noEmit` 做类型检查），references 对 IDE 的类型解析和跳转体验仍然有价值。

### composite 不是必须的

在 Vite 那个例子中，`tsconfig.node.json` 和 `tsconfig.app.json` 并不需要设置 `composite: true`。`composite` 只在你需要 `tsc --build` 做增量编译时才是必须的。如果你只是为了让 IDE 正确地把文件分配给不同配置，references 本身就够了。

---

## 核心区别对照

**解决的问题**。`extends` 解决"配置写得重复"，`references` 解决"哪个文件该用哪套配置"。

**作用方向**。`extends` 是纵向的"继承"：子配置从父配置拿到默认值。`references` 是横向的"分治"：主配置把文件的管辖权分发给多个子配置。

**对 IDE 的意义**。`extends` 对 IDE 行为无直接影响（只是配置值不同）。`references` 直接决定了 IDE 用哪个配置来分析某个文件——这决定了你能看到什么类型、报什么错。

**是否涉及编译**。`extends` 纯粹是配置层面的事，不改变编译行为。`references` 配合 `composite` + `tsc --build` 时能实现增量编译，但不用 `tsc --build` 时它仍然对 IDE 有效。

---

## 实际项目中如何配合使用

在真实项目中，`extends` 和 `references` 经常一起出现。一个典型的 Vite + monorepo 项目：

```
monorepo/
├── tsconfig.base.json          ← 公共编译选项（extends 的目标）
├── tsconfig.json               ← 总控，files: []，只做 references 分发
├── packages/
│   ├── utils/
│   │   └── tsconfig.json       ← extends base，管自己的 src/
│   └── app/
│       ├── tsconfig.json       ← 总控，references app 和 node
│       ├── tsconfig.app.json   ← extends base，管 src/（浏览器）
│       └── tsconfig.node.json  ← extends base，管 vite.config.ts（Node）
```

`extends` 负责让各子配置不用重复写 `strict: true`、`moduleResolution` 等公共选项；`references` 负责划分文件的管辖归属，确保 IDE 对每个文件使用正确的类型环境。

---

## 常见误解澄清

**误解一："references 的粒度是包"**。不是。references 的粒度是文件。一个单体项目里的 `vite.config.ts` 和 `src/main.ts` 就可以归不同的 tsconfig 管。monorepo 跨包只是 references 的一种应用场景，不是它的定义。

**误解二："references 只有配合 tsc --build 才有用"**。不是。即使你完全不用 tsc 编译（比如用 Vite/esbuild 做转译），references 对 IDE 仍然有效——它告诉 tsserver 用哪个配置分析哪个文件。

**误解三："references 会让被引用配置的选项继承过来"**。不会。references 纯粹是管辖权声明，不涉及任何配置合并。两个通过 references 关联的配置，compilerOptions 可以完全不同（这正是它的设计目的）。

**误解四："用了 extends 就不需要 references"**。extends 解决"配置写得重复"，references 解决"文件该归谁管"。它们是正交的两个维度。

---

## 参考来源

- [TypeScript 官方文档 - extends](https://www.typescriptlang.org/tsconfig/extends.html)
- [TypeScript 官方文档 - Project References](https://www.typescriptlang.org/docs/handbook/project-references.html)
- [TypeScript 官方文档 - composite](https://www.typescriptlang.org/tsconfig/composite.html)
- [TypeScript 5.0 Release Notes - extends 数组支持](https://devblogs.microsoft.com/typescript/announcing-typescript-5-0/)
- [探究 tsconfig.node.json 文件和 references 字段的作用](https://juejin.cn/post/7126043888573218823)
- [Why does Vite create multiple TypeScript config files](https://www.geeksforgeeks.org/typescript/why-does-vite-create-multiple-typescript-config-files-tsconfigjson-tsconfigappjson-and-tsconfignodejson/)
