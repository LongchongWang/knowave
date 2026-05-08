# VS Code tsserver 对 exclude 文件仍报错的原因与解决方案

整理日期：2026-05-08

## 核心洞见

`tsconfig.json` 里的 `exclude` 字段，其真正含义是**告诉编译器在扫描文件时跳过这些路径**，而不是"禁止对这些文件做任何分析"。

当你在 VS Code 里**手动打开**一个被 `exclude` 的文件时，tsserver 会为它创建一个独立的"隐式项目"（inferred project）。这个隐式项目不受你的 `tsconfig.json` 约束，会用一套默认的宽松配置来分析这个文件，结果就是报出一堆意想不到的错误。

**`exclude` 只影响"项目扫描范围"，不影响"你主动打开的文件"。** 这是 TypeScript 团队的设计决策，目的是让编辑器对任何文件都能提供基本的语言服务支持。

`tsc` 命令行编译时 `exclude` 完全正常，但 VS Code 的语言服务（tsserver）对"你打开的文件"有独立的处理逻辑，这两者是分开的。

## 解决方案

### 方案一：文件顶部加 `// @ts-nocheck`（最直接）

适合确实不想让 TS 检查这个文件的情况：

```typescript
// @ts-nocheck
// 这个文件被 tsconfig exclude，不需要类型检查
```

这是 TypeScript 官方提供的文件级别禁用指令，tsserver 会完全跳过对该文件的诊断。

### 方案二：在被排除的目录里放一个独立的 `tsconfig.json`（最彻底）

让 tsserver 用这个局部配置来处理该目录下的文件，而不是走隐式项目：

```json
{
  "compilerOptions": {
    "strict": false,
    "noEmit": true,
    "skipLibCheck": true
  }
}
```

tsserver 会优先找到这个局部配置，用它的规则来检查，报错就会消失或减少。适合整个目录（如 `scripts/`、`legacy/`）都被 exclude 的场景，一劳永逸。

### 方案三：在 `.vscode/settings.json` 里关闭 TS 验证（最粗暴）

```json
{
  "typescript.validate.enable": false
}
```

注意这会关掉整个工作区的 TS 诊断，影响范围太大，一般不推荐。

### 方案四：逐行压制（最精细）

```typescript
// @ts-ignore
someProblematicCode();
```

更推荐用 `// @ts-expect-error`，它在错误消失后会反过来提醒你删掉这行注释，更安全。

## 推荐组合

- **整个目录被 exclude**：在该目录里放一个宽松的 `tsconfig.json`，一劳永逸
- **个别文件**：在文件顶部加 `// @ts-nocheck`
- **个别行**：用 `// @ts-expect-error`

## 常见误区

很多人以为 `exclude` 不生效是因为路径写错了，反复调整 glob 模式，其实问题根本不在这里。`tsc` 编译时 `exclude` 完全正常，问题出在 VS Code 语言服务的"隐式项目"机制上。
