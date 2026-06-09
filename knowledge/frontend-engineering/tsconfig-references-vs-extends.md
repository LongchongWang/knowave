# tsconfig 的 references 与 extends：配置继承与项目引用

## 它们解决的是两个完全不同的问题

`extends` 和 `references` 都出现在 tsconfig.json 的顶层字段中，也都涉及"多个 tsconfig 之间的关系"，但它们解决的问题截然不同。一句话概括：`extends` 是**配置复用**（DRY 原则），`references` 是**构建拆分**（分治原则）。

如果你用 Node.js 做类比：`extends` 相当于把公共的 ESLint 配置抽成 `@company/eslint-config-base` 让各项目继承；`references` 则相当于把一个巨型仓库拆成多个 workspace packages，各自独立构建、通过声明依赖关系协同。

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

另一个需要记住的规则是：**`references` 字段不会被继承**。即使基础配置里写了 `references`，子配置也不会拿到——这是刻意设计，因为项目引用关系是每个项目自身的结构性声明，不应该被"默默继承"。

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

`extends` 的使用场景可以总结为：当你有多个 tsconfig 需要**共享相同的编译器配置**时。比如 monorepo 中所有子包共享严格模式和模块策略，或者测试配置继承主配置但额外加上 `types: ["jest"]`。

---

## references：项目引用

### 引入时间

TypeScript 3.0（2018 年）引入，与 `--build` 模式和 `composite` 选项配套使用。

### 解决什么问题

想象一个 monorepo 中有 `packages/core`、`packages/utils`、`packages/app` 三个包，`app` 依赖 `core`，`core` 依赖 `utils`。在没有 `references` 之前，你只有两个选择：要么用一个巨大的 tsconfig 把所有文件一起编译（改一行代码就全量重编），要么各自独立编译但丧失跨包的类型检查能力。

`references` 让你声明包与包之间的依赖拓扑，然后 `tsc --build` 会：按拓扑顺序编译（先 utils → 再 core → 最后 app），对未变更的包跳过编译（增量构建），并且在类型层面正确地跨包解析。

### 核心配置

项目引用需要两侧配合：

**被引用的项目**必须开启 `composite: true`：

```jsonc
// packages/utils/tsconfig.json
{
  "compilerOptions": {
    "composite": true,       // 必须
    "declaration": true,     // composite 自动隐含
    "declarationMap": true,  // 推荐，支持跳转到源码
    "outDir": "./dist"
  },
  "include": ["src"]
}
```

`composite: true` 做了几件事：强制开启 `declaration`（必须产出 .d.ts），强制所有源文件必须被 `include` 或 `files` 覆盖（不能有"漏网之鱼"），开启 `incremental`（产出 .tsbuildinfo 文件用于增量判断）。

**引用方**在自己的 tsconfig 中声明依赖：

```jsonc
// packages/app/tsconfig.json
{
  "compilerOptions": {
    "outDir": "./dist"
  },
  "references": [
    { "path": "../core" },
    { "path": "../utils" }
  ],
  "include": ["src"]
}
```

### tsc --build 模式

配好 references 后，编译命令从 `tsc` 变为 `tsc --build`（简写 `tsc -b`）。这个模式下编译器会：

1. 解析整个引用图，计算拓扑排序
2. 检查每个项目的 `.tsbuildinfo` 文件，判断是否需要重编
3. 只重编有变化的项目及其下游依赖
4. 编译完一个项目后，下游项目通过其 `.d.ts` 文件获取类型信息

这就是为什么大型 monorepo 使用 references 后构建速度能大幅提升——改了 `utils` 里一个函数，只需要重编 `utils` → `core`（如果 core 用了那个函数）→ `app`（如果 app 用了 core 受影响的部分），而不是全量编译。

### 隔离性保证

references 带来一个重要的副作用：**源文件隔离**。被引用的项目对引用方来说是"不透明的"——引用方只能看到被引用项目产出的 `.d.ts` 声明文件，看不到源码。这意味着如果 `app` 中的某个文件试图 `import` `utils` 的内部实现细节（没有通过 `utils` 的公共 API 导出），编译器会报错。这是刻意的设计，用于强制模块边界。

### 根级 tsconfig 的 references

通常在 monorepo 根目录会放一个"总控"tsconfig：

```jsonc
// tsconfig.json（仓库根目录）
{
  "files": [],
  "references": [
    { "path": "packages/utils" },
    { "path": "packages/core" },
    { "path": "packages/app" }
  ]
}
```

`files: []` 意味着这个 tsconfig 自身不编译任何文件，它的唯一作用是声明"这个仓库由哪些子项目构成"。然后在根目录执行 `tsc --build` 就会按顺序编译所有子项目。

---

## 核心区别对照

从以下几个维度理解它们的本质差异：

**作用方向**。`extends` 是纵向的"继承"：子 tsconfig 从父 tsconfig 拿到默认值。`references` 是横向的"依赖"：项目 A 声明它在编译时依赖项目 B 的产出。

**影响范围**。`extends` 只影响编译器选项的默认值，不改变编译行为本身。`references` 改变了整个编译模型——从"一次性全量编译"变成"按依赖图增量编译"。

**是否可以单独使用**。`extends` 可以独立使用，一个简单的单体项目继承 `@tsconfig/node20` 是再正常不过的事。`references` 则必须配合 `composite: true` 和 `tsc --build` 才有意义。

**编译时的关系**。使用 `extends` 时，最终只有一个"生效的配置"被送给编译器。使用 `references` 时，每个子项目保留自己独立的 tsconfig，编译器会多次执行，每次针对一个子项目。

---

## 实际项目中如何配合使用

在真实的 monorepo 中，`extends` 和 `references` 几乎总是一起出现。原因很简单：你既需要 references 来做增量构建和模块隔离，又不想在每个子包的 tsconfig 里重复写一遍 `strict: true`、`moduleResolution: "bundler"` 等公共配置。

典型的目录结构和配置关系：

```
monorepo/
├── tsconfig.base.json          ← 公共编译选项
├── tsconfig.json               ← 总控文件，只有 references
├── packages/
│   ├── utils/
│   │   └── tsconfig.json       ← extends base + composite: true
│   ├── core/
│   │   └── tsconfig.json       ← extends base + composite: true + references utils
│   └── app/
│       └── tsconfig.json       ← extends base + references core, utils
```

```jsonc
// tsconfig.base.json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

```jsonc
// packages/core/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "composite": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "references": [
    { "path": "../utils" }
  ],
  "include": ["src"]
}
```

这样，`extends` 负责消除配置重复，`references` 负责定义编译顺序和模块边界，各司其职。

---

## 常见误解澄清

**误解一："references 会让被引用项目的配置继承过来"**。不会。references 纯粹是构建依赖声明，不涉及任何配置合并。两个通过 references 关联的项目，compilerOptions 可以完全不同。

**误解二："用了 extends 就不需要 references"**。extends 只是让你少写几行配置，不解决增量编译和模块隔离的问题。如果你的 monorepo 全量编译要 2 分钟，加 extends 还是 2 分钟；加 references 可能变成 10 秒。

**误解三："references 中的 path 指向 ts 源文件目录"**。path 指向的是一个包含 tsconfig.json 的目录（或直接指向一个 tsconfig 文件）。编译器会读取那个 tsconfig，以它定义的范围为一个"项目单元"。

---

## 参考来源

- [TypeScript 官方文档 - extends](https://www.typescriptlang.org/tsconfig/extends.html)
- [TypeScript 官方文档 - Project References](https://www.typescriptlang.org/docs/handbook/project-references.html)
- [TypeScript 官方文档 - composite](https://www.typescriptlang.org/tsconfig/composite.html)
- [TypeScript 5.0 Release Notes - extends 数组支持](https://devblogs.microsoft.com/typescript/announcing-typescript-5-0/)
- [@tsconfig/bases - 社区共享配置集合](https://github.com/tsconfig/bases)
