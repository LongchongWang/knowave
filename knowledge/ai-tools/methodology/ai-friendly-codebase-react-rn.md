# AI 友好型项目：React / React Native 专项实践

> 整理日期：2026-03-26  
> 前置阅读：[AI 友好型项目：定义、标准与改造方法论](./ai-friendly-codebase.md)  
> 来源：ZenReact、Callstack React Native Best Practices、propelcode.ai、TkDodo Blog

---

## 为什么 React/RN 需要专项讨论

通用的 AI 友好型项目原则（文件大小、浅层依赖、上下文文件）对 React/RN 同样适用，但这个生态有几个独特的挑战：

**组件是 AI 的基本工作单元。** AI 每次修改的往往是一个组件，而不是一个服务函数。组件的结构是否清晰，直接决定 AI 能否在不加载其他文件的情况下理解和修改它。

**React/RN 特有的反模式会严重干扰 AI。** Barrel imports（桶文件）、Props 类型散落、样式与逻辑混杂、深层 Context 依赖——这些在 React 生态里极为常见，但对 AI 来说是噩梦。

**RN 还有平台差异的额外复杂度。** iOS/Android 的差异、原生模块、Bridge/JSI 架构，AI 如果没有足够的上下文，很容易生成只在一个平台上能跑的代码。

---

## 一、组件结构：让 AI 一眼看懂

### 类型定义紧贴组件

Props 类型应该和组件定义放在同一个文件里，而不是放在全局 `types/` 目录。AI 修改组件时，不应该需要打开另一个文件才能知道这个组件接受什么参数。

```tsx
// ❌ 差：类型在别处，AI 需要加载 types/components.ts
import { ButtonProps } from '../types/components';
export const Button = ({ label, onPress }: ButtonProps) => { ... }

// ✅ 好：类型和组件在一起，自包含
interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button = ({ label, onPress, variant = 'primary', disabled = false }: ButtonProps) => {
  // ...
};
```

### 组件文件的标准结构

一个 AI 友好的组件文件应该从上到下依次是：imports → 类型定义 → 组件实现 → 样式（RN）。这个顺序让 AI 在读到组件实现之前，已经知道了所有依赖的类型。

```tsx
// 1. Imports（只引入直接依赖）
import React, { useState, useCallback } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

// 2. 类型定义（紧贴组件）
interface ProductCardProps {
  id: string;
  title: string;
  price: number;
  onAddToCart: (id: string) => void;
}

// 3. 组件实现
export const ProductCard = ({ id, title, price, onAddToCart }: ProductCardProps) => {
  const [isAdding, setIsAdding] = useState(false);

  const handlePress = useCallback(async () => {
    setIsAdding(true);
    await onAddToCart(id);
    setIsAdding(false);
  }, [id, onAddToCart]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.price}>¥{price}</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={handlePress}
        disabled={isAdding}
      >
        <Text>{isAdding ? '添加中...' : '加入购物车'}</Text>
      </TouchableOpacity>
    </View>
  );
};

// 4. 样式（RN 专属，紧贴组件）
const styles = StyleSheet.create({
  container: { padding: 16, borderRadius: 8 },
  title: { fontSize: 16, fontWeight: '600' },
  price: { fontSize: 14, color: '#666' },
  button: { marginTop: 8, padding: 12, backgroundColor: '#007AFF', borderRadius: 6 },
});
```

### 单一职责：一个组件只做一件事

如果一个组件既负责数据获取、又负责渲染、又处理复杂交互逻辑，AI 修改其中任何一部分都需要理解全部。拆分的原则是：**数据逻辑放进 Hook，UI 逻辑留在组件**。

```tsx
// ❌ 差：数据获取、状态管理、UI 全混在一起
const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setLoading(true);
    fetch('/api/products').then(r => r.json()).then(data => {
      setProducts(data);
      setLoading(false);
    });
  }, []);
  // ... 100 行 UI 代码
};

// ✅ 好：数据逻辑抽到 Hook，组件只管渲染
// hooks/useProducts.ts
export const useProducts = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  // 数据获取逻辑...
  return { products, loading };
};

// components/ProductList.tsx
const ProductList = () => {
  const { products, loading } = useProducts();
  if (loading) return <LoadingSpinner />;
  return <FlatList data={products} renderItem={({ item }) => <ProductCard {...item} />} />;
};
```

---

## 二、目录结构：Feature-Based 优于 Type-Based

### 按功能组织，而不是按文件类型

按文件类型组织（`components/`、`hooks/`、`utils/` 各一个大目录）是 React 项目最常见的结构，但对 AI 来说很糟糕——AI 要理解"商品详情页"这个功能，需要在三个不同目录里来回跳转。

按功能（Feature）组织，把同一个功能的所有文件放在一起，AI 只需要进入一个目录就能理解整个功能。

```
src/
├── features/
│   ├── product/
│   │   ├── components/
│   │   │   ├── ProductCard.tsx      # 组件 + 类型 + 样式都在这里
│   │   │   └── ProductList.tsx
│   │   ├── hooks/
│   │   │   └── useProducts.ts       # 只服务于 product 功能的 Hook
│   │   ├── screens/
│   │   │   └── ProductDetailScreen.tsx
│   │   └── index.ts                 # 只导出这个功能的公开 API
│   └── cart/
│       ├── components/
│       ├── hooks/
│       └── index.ts
├── shared/                          # 真正跨功能共享的东西
│   ├── components/                  # Button、Input 等通用组件
│   ├── hooks/                       # useDebounce 等通用 Hook
│   └── utils/
└── navigation/
    └── AppNavigator.tsx
```

每个 `feature/` 目录下的 `index.ts` 是这个功能的"公开 API"，只导出外部需要用到的东西。这样 AI 在其他地方引用这个功能时，只需要看 `index.ts` 就够了。

### 每个目录加 README

在每个主要目录下放一个简短的 `README.md`，说明这个目录里有什么、命名规则、如何新增。AI 不用打开文件就能知道该去哪里找什么、该怎么扩展。

```markdown
# features/product/

商品相关功能模块。

## 文件说明
- `components/` - 商品相关 UI 组件（ProductCard、ProductList 等）
- `hooks/` - 商品数据获取和状态管理 Hook
- `screens/` - 商品相关页面（详情页、列表页）
- `index.ts` - 对外公开 API，其他模块只能通过这里引用

## 新增组件
在 `components/` 下创建 `ComponentName.tsx`，包含类型定义和样式。
如需对外暴露，在 `index.ts` 中添加导出。
```

---

## 三、Barrel Imports：React 生态最常见的 AI 杀手

Barrel imports（桶文件）是指用 `index.ts` 把一个目录下所有东西重新导出，让外部可以用 `import { A, B, C } from './components'` 这样的方式引入。

这在人类开发者看来很方便，但对 AI 是灾难：

**AI 无法知道 `Button` 来自哪里。** 当 AI 看到 `import { Button, Card, Modal } from './components'` 时，它不知道 `Button` 的实现在哪个文件，需要先读 `index.ts`，再找到对应文件，消耗额外的上下文预算。

**Barrel imports 会导致 AI 生成的代码引入整个模块。** AI 倾向于模仿已有的 import 风格，如果项目里到处是 barrel imports，AI 生成的新代码也会这样写，导致 bundle 越来越大。

```tsx
// ❌ 差：barrel import，AI 不知道 Button 在哪里
import { Button, Card, Modal, Input } from '../components';

// ✅ 好：直接 import，AI 立刻知道每个组件的位置
import { Button } from '../shared/components/Button';
import { Card } from '../features/product/components/ProductCard';
```

**例外：** Feature 的 `index.ts` 作为对外 API 是合理的 barrel，因为它明确定义了模块边界。问题在于把整个 `components/` 目录做成 barrel。

---

## 四、Custom Hooks：AI 最喜欢的抽象层

Custom Hook 是 React/RN 里对 AI 最友好的抽象方式，原因是：

一个好的 Hook 是完全自包含的——它的输入（参数）和输出（返回值）在函数签名里一目了然，AI 不需要理解内部实现就能知道如何使用它。

```tsx
// 这个 Hook 的签名就是完整的文档
// AI 看到签名就知道：传入 productId，返回 product 数据、loading 状态、error 信息
export const useProduct = (productId: string): {
  product: Product | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
} => {
  // 实现细节...
};
```

**Hook 的命名要表达意图，而不是实现。** `useProductData` 比 `useFetchProductFromAPI` 好，因为前者表达的是"我需要商品数据"，后者暴露了实现细节（如果以后改成 GraphQL，名字就不对了）。

**一个 Hook 只做一件事。** 不要把数据获取、表单验证、埋点上报全塞进一个 Hook。AI 修改其中一个功能时，不应该需要理解其他功能。

---

## 五、React Native 专项：平台差异的处理

RN 项目有一个 React Web 没有的挑战：iOS 和 Android 的行为差异。如果 AI 不知道这些差异，很容易生成只在一个平台上能跑的代码。

### 在 CLAUDE.md 里明确平台约定

```markdown
## 平台差异处理规范

- 平台特定代码使用 `.ios.tsx` / `.android.tsx` 后缀，不要用 `Platform.OS` 做大量条件判断
- 样式中的阴影：iOS 用 `shadow*` 属性，Android 用 `elevation`，统一封装在 `shared/styles/shadow.ts`
- 键盘处理：统一使用 `KeyboardAvoidingView`，behavior 在 iOS 用 'padding'，Android 用 'height'
- 安全区域：所有页面必须使用 `SafeAreaView` 或 `useSafeAreaInsets`
```

### 性能敏感的 RN 特有规范

Callstack 的 React Native 最佳实践里，有几条对 AI 生成代码影响最大的规则，应该写进 CLAUDE.md：

```markdown
## 性能规范（AI 必须遵守）

- 长列表禁止使用 ScrollView + map，必须使用 FlashList（@shopify/flash-list）
  - 错误示例：<ScrollView>{items.map(item => <Item />)}</ScrollView>
  - 正确示例：<FlashList data={items} renderItem={...} estimatedItemSize={100} />

- 禁止在组件内定义内联样式对象（每次渲染都会创建新对象）
  - 错误示例：<View style={{ padding: 16, margin: 8 }}>
  - 正确示例：使用 StyleSheet.create() 定义，或使用项目的样式系统

- 动画必须使用 Reanimated（react-native-reanimated），不要用 Animated API
  - Reanimated 在 UI 线程运行，不会被 JS 线程阻塞

- 禁止 barrel imports（见上文），会导致 bundle 体积膨胀
```

---

## 六、CLAUDE.md 的 React/RN 模板

一个针对 React Native 项目的 CLAUDE.md 应该包含以下内容：

```markdown
# 项目：[项目名称]

## 技术栈
- React Native [版本] + TypeScript
- 状态管理：Zustand（全局）/ React Query（服务端状态）/ useState（本地）
- 导航：React Navigation v6
- 样式：StyleSheet.create（禁止内联样式对象）
- 列表：FlashList（禁止 ScrollView + map）
- 动画：Reanimated v3

## 目录结构
- `src/features/` - 按功能组织的业务代码
- `src/shared/` - 跨功能共享的组件、Hook、工具函数
- `src/navigation/` - 导航配置
- 每个 feature 目录有 README.md 说明其内容

## 组件规范
- Props 类型定义紧贴组件，不放全局 types 目录
- 文件结构：imports → 类型 → 组件 → StyleSheet
- 数据逻辑抽到 Custom Hook，组件只负责渲染
- 禁止 barrel imports，使用直接路径导入

## 参考文件
- 标准组件示例：`src/features/product/components/ProductCard.tsx`
- 标准 Hook 示例：`src/features/product/hooks/useProducts.ts`
- 标准页面示例：`src/features/product/screens/ProductDetailScreen.tsx`

## 禁止事项
- 禁止 ScrollView + map 渲染列表
- 禁止内联样式对象
- 禁止在组件文件外定义 Props 类型
- 禁止 barrel imports（components/index.ts 这类）
- 禁止直接使用 Animated API，统一用 Reanimated
```

---

## 七、历史 RN 项目的改造优先级

如果要改造一个历史 RN 项目，按收益从高到低排序：

**第一优先：写 CLAUDE.md。** 成本最低，收益最高。把项目的技术栈、目录结构、禁止事项写清楚，AI 立刻就能生成符合规范的代码。

**第二优先：把性能禁忌写进 lint 规则。** 比如禁止 `ScrollView` 里直接 `map`，禁止内联样式对象。这些规则一旦变成 lint error，AI 就会自动修复。

**第三优先：为最常改动的功能模块写 README。** 不需要全量改造目录结构，只需要在改动最频繁的几个目录下加 README，说明里面有什么、怎么扩展。

**第四优先（持续进行）：每次修改组件时，顺手把 Props 类型移到组件文件里。** 不需要专门开一个"重构"任务，改到哪里顺手改，积累下来效果显著。

---

## 参考来源

- [AI-Optimized React Development](https://zenreact.dev/blog/ai-optimized-react-development) — ZenReact
- [React Native Best Practices for AI Agents](https://www.callstack.com/blog/announcing-react-native-best-practices-for-ai-agents) — Callstack
- [Please Stop Using Barrel Files](https://tkdodo.eu/blog/please-stop-using-barrel-files) — TkDodo
- [Structuring Your Codebase for AI Tools](https://www.propelcode.ai/blog/structuring-codebases-for-ai-tools-2025-guide) — Propel, 2025
