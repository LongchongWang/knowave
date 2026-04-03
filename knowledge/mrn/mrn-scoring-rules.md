# MRN（美团 React Native）专项评分规则

> 整理日期：2026-03-30  
> 来源：终端研发 AI 友好型代码库评估标准 v1.0（km.sankuai.com/collabpage/2753864102）、MRN 开发最佳实践（km.sankuai.com/collabpage/2048937248）、MRN AI Coding SPEC 制定计划（km.sankuai.com/collabpage/2752499819）、React Native 官方文档（reactnative.dev）、Shopify FlashList 文档  
> 适用范围：MRN（美团 React Native）技术栈的代码库 AI 友好度评估

---

## 一、背景与定位

MRN（Meituan React Native）是美团基于开源 React Native 深度改造的移动端动态化容器，是美团"二环链路"的核心技术选型，承载绝大多数业务主流程页面。

MRN 专项评分在通用维度（仓库导航、架构文档、业务上下文、代码可读性、编码规范、测试验证、反馈回路）之外，针对 MRN 技术栈的特有问题设立专项检查项。这些问题如果不解决，AI 生成的代码要么性能差、要么只在一个平台跑、要么用了错误的包名。

**MRN 专项的核心关注点：**

MRN 与标准 React Native 的最大差异在于**私有包体系**——AI 训练数据里有标准 `react-native`，但没有 `@mrn/react-native`、`NativeModules.MRNNetwork` 这些美团私有包。因此，MRN 专项评分除了通用的 React Native 最佳实践外，还需要额外关注美团私有规范的落地情况。

---

## 二、评分总览

| 编号 | 检查项 | 满分 | 核心关注点 |
|------|--------|------|-----------|
| MRN-1 | 组件结构规范 | 100 分 | Props 类型自包含，文件结构标准化 |
| MRN-2 | 禁止 Barrel Imports | 100 分 | 导入路径直达文件，禁止桶文件 |
| MRN-3 | 列表性能规范 | 100 分 | 禁止 ScrollView+map，使用 FlashList/FlatList |
| MRN-4 | 样式管理规范 | 75 分 | RemStyleSheet/StyleSheet.create，禁止静态内联样式 |
| MRN-5 | 平台差异处理规范 | 75 分 | 平台文件后缀隔离，减少 Platform.OS 分支 |
| MRN-6 | 动画规范 | 75 分 | 使用 Reanimated，禁止 JS 线程动画 |
| MRN-7 | 自定义 Hook 抽象 | 75 分 | 业务逻辑抽离为 Hook，组件保持纯 UI |
| MRN-8 | Feature-Based 目录组织 | 75 分 | 按功能聚合，而非按技术层分散 |
| MRN-9 | 单组件 State 数量控制 | 75 分 | 单组件 state ≤ 5，避免职责过重 |
| MRN-10 | 包引用规范（MRN 特有） | 100 分 | 使用 @mrn/* 私有包，禁止直接用 react-native |
| MRN-11 | 网络请求规范（MRN 特有） | 75 分 | 使用 MRNNetwork/MSI 标准桥，封装公参注入 |
| MRN-12 | 版本区间规范（MRN 特有） | 75 分 | 版本区间选择合理，有文档说明 |

---

## 三、各项评分细则

### MRN-1：组件结构规范（满分 100 分）

**为什么重要：** AI 修改组件时，如果 Props 类型散落在全局 `types/` 目录，AI 需要额外加载一个文件才能理解组件接受什么参数。自包含的组件文件让 AI 在一个文件内完成理解和修改。

**AI 判断方式：** 扫描项目中所有组件文件（`.tsx` 文件），检查每个文件的结构是否符合标准顺序：① imports → ② 类型定义（Props type） → ③ 组件函数 → ④ StyleSheet。统计 Props 类型定义紧贴组件的文件比例，以及 Props 类型散落在其他文件（如全局 `types/` 目录）的文件数量。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 100 分 | 所有组件遵循标准结构：imports → Props type → 组件函数 → StyleSheet；Props 类型紧贴组件定义，无需跳转其他文件 |
| 良好 | 75 分 | 大部分（> 70%）组件结构规范，少数组件 Props 类型在单独 types 文件中 |
| 初级 | 50 分 | 组件结构各异，Props 类型散落在多个位置（types/、组件文件顶部、底部），无统一规范 |
| 未达标 | 0 分 | Props 类型分散在全局 types.ts 文件（反模式：修改组件时必须打开另一个文件，增加 AI 上下文加载成本） |

**标准示例：**

```tsx
// ✅ 标准结构：自包含，AI 一个文件读完
import { View, Text } from '@mrn/react-native';
import { RemStyleSheet } from '@meishi/hammer-mrn';

// Props 类型紧贴组件
interface PatientCardProps {
  patientId: string;
  name: string;
  /** 就诊状态：0=待就诊 1=就诊中 2=已完成 */
  status: 0 | 1 | 2;
  onPress: () => void;
}

export const PatientCard = ({ patientId, name, status, onPress }: PatientCardProps) => {
  return (
    <View style={styles.container}>
      <Text style={styles.name}>{name}</Text>
    </View>
  );
};

const styles = RemStyleSheet.create({
  container: { padding: 16 },
  name: { fontSize: 16 },
});
```

**依据来源：** 黄金法则 #2：自包含的实现；黄金法则 #1：一个概念，一个文件

---

### MRN-2：禁止 Barrel Imports（满分 100 分）

**为什么重要：** Barrel index 文件（`index.ts` 里 re-export 多个模块）会让 AI 不知道组件的真实来源，且加载一个组件时会把整个桶里的所有模块都拉进上下文。TkDodo 的实际案例：消除 barrel imports 后，模块数从 11k 降到 3.5k，减少 68%。

**AI 判断方式：** 检查项目中 `index.ts/index.tsx` 文件数量；检查这些 index 文件是否为纯 re-export（barrel）文件；在组件/模块的 import 语句中，检查是否存在 `from '../ComponentName'`（省略文件名，隐式引用 index.ts）这种形式。运行：`grep -r "from './" --include="*.tsx" | grep -v "index\|test" | head -20`。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 100 分 | 无 barrel index 文件（库的入口除外）；所有导入使用直接路径（`from './Button/Button'` 而非 `from './Button'`）；有 lint 规则禁止 barrel imports |
| 良好 | 75 分 | 极少量（< 5 个）barrel index 文件，且有明确注释说明原因；大部分导入使用直接路径 |
| 初级 | 50 分 | 存在 10～30 个 barrel index 文件，部分导入使用间接路径，但无循环导入 |
| 未达标 | 0 分 | 大量 barrel index 文件（> 30 个），导致循环导入风险，AI 不知道组件真实来源，上下文加载量剧增 |

**依据来源：** 黄金法则 #7：最多 2 层导入深度；黄金法则 #10：规范写进 lint，不要只写进文档

---

### MRN-3：列表性能规范（满分 100 分）

**为什么重要：** `ScrollView + .map()` 是 React Native 中最常见的性能反模式——所有 item 同时渲染，数据量大时严重掉帧。AI 如果在代码库里看到这种模式，会倾向于复现它。必须用 lint 规则拦截，并用 FlashList/FlatList 替代。

**AI 判断方式：** 在项目中搜索 `ScrollView` 组件的使用，检查其中是否有 `ScrollView` 内部使用 `.map()` 渲染列表的模式（反模式）。搜索命令：`grep -r "ScrollView" --include="*.tsx" -l`，再逐文件检查是否有 `.map(` 在同一组件中。同时检查是否使用了 `FlatList`/`FlashList`/`SectionList`。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 100 分 | 所有列表使用 FlashList 或 FlatList/SectionList；无 ScrollView + .map() 组合；有 lint 规则禁止该反模式；keyExtractor 使用稳定唯一 key |
| 良好 | 75 分 | 绝大多数列表使用正确组件，但有 1-2 处历史遗留的 ScrollView + .map()（已在注释中标注 TODO） |
| 初级 | 50 分 | 部分列表使用了 FlashList/FlatList，但仍有多处 ScrollView + .map()，无 lint 规则 |
| 未达标 | 0 分 | 大量 ScrollView + .map() 渲染长列表（反模式：所有 item 同时渲染，严重性能问题，AI 可能复现该模式） |

**FlashList vs FlatList 选择建议：**

FlashList（Shopify 出品）是 FlatList 的高性能替代品，API 兼容，渲染速度更快、内存占用更低。对于数据量较大（> 50 条）的列表，优先使用 FlashList。FlatList 适合数据量较小或需要精细控制的场景。两者都远优于 ScrollView + .map()。

**依据来源：** 黄金法则 #10：规范写进 lint，不要只写进文档；React Native 官方性能文档

---

### MRN-4：样式管理规范（满分 75 分）

**为什么重要：** 内联样式对象（`style={{ marginTop: 10 }}`）在每次渲染时都会创建新的 JS 对象，造成不必要的性能损耗。MRN 推荐使用 `RemStyleSheet.create()`（来自 `@meishi/hammer-mrn` 或 `@nib/mrn-base-utils`），它在 `StyleSheet.create()` 基础上增加了 rem 单位自动换算，适配不同屏幕宽度。

**AI 判断方式：** 在组件文件中搜索内联样式对象的使用模式（`style={{ ... }}`），统计其在所有 style 使用中的比例。检查是否有 `RemStyleSheet.create()` 或 `StyleSheet.create()` 使用。运行：`grep -r "style={{" --include="*.tsx" | wc -l` 对比 `grep -r "StyleSheet.create\|RemStyleSheet.create" --include="*.tsx" | wc -l`。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 所有静态样式使用 `RemStyleSheet.create()`（MRN 推荐）或 `StyleSheet.create()`；内联样式对象仅用于动态样式（依赖 props/state 的样式）；有 lint 规则禁止静态内联样式 |
| 良好 | 50 分 | 大部分（> 70%）使用 `RemStyleSheet.create()` 或 `StyleSheet.create()`，少量内联样式对象（< 20 处），无 lint 强制 |
| 初级 | 25 分 | `StyleSheet.create()` 和内联样式混用，比例各半，AI 难以判断应该使用哪种模式 |
| 未达标 | 0 分 | 大量内联样式对象（> 50%）（反模式：每次渲染创建新对象，性能损耗；AI 容易复现该反模式） |

**MRN 特有说明：** MRN 标准设备宽度为 375 rem，推荐使用 `RemStyleSheet.create()` 替代原生 `StyleSheet.create()`，宽高等数字会根据设备宽度按比例自动调整。来源：`@meishi/hammer-mrn` 或 `@nib/mrn-base-utils`。

**依据来源：** 黄金法则 #10：规范写进 lint；黄金法则 #2：自包含的实现；MRN 开发最佳实践

---

### MRN-5：平台差异处理规范（满分 75 分）

**为什么重要：** 大量 `if (Platform.OS === 'ios')` 分支会让单个文件同时包含两个平台的逻辑，AI 修改时容易只改一个平台而遗漏另一个。较大的平台差异应该用文件后缀（`.ios.tsx`/`.android.tsx`）隔离，让 AI 在处理单一平台时只需加载对应文件。

**AI 判断方式：** 搜索 `Platform.OS` 在代码中的使用频率（`grep -r "Platform.OS" --include="*.ts" --include="*.tsx" | wc -l`）；检查是否使用了平台特定文件后缀（`.ios.tsx`/`.android.tsx`）。统计大量 `if (Platform.OS === 'ios')` 逻辑分支的文件数量。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 较大的平台差异使用 `.ios.tsx`/`.android.tsx` 文件后缀拆分；`Platform.OS` 仅用于细微差异（如样式值微调）；无大量 if-else platform 分支 |
| 良好 | 50 分 | 混合使用平台文件和 `Platform.OS`，但有明确注释说明选择原因；无超过 10 行的 platform 分支 |
| 初级 | 25 分 | 主要依靠 `Platform.OS` 条件分支处理差异，文件内平台代码混杂，可读性差 |
| 未达标 | 0 分 | 大量 `Platform.OS` 嵌套导致代码分支复杂，难以理解单一平台的逻辑；或跨平台差异完全未处理 |

**依据来源：** 黄金法则 #1：一个概念，一个文件（平台差异用文件后缀隔离，而非 if-else 混写）；黄金法则 #4：扁平优于嵌套

---

### MRN-6：动画规范（满分 75 分）

**为什么重要：** RN 内置 `Animated` API 的动画在 JS 线程执行，容易因 JS 线程繁忙而掉帧。`react-native-reanimated` 的 Worklets 模式将动画逻辑移到 UI 线程，实现真正的 60fps 流畅动画。最差的反模式是用 `setState + setTimeout` 实现动画，完全在 JS 线程执行，严重掉帧。

**AI 判断方式：** 搜索 `Animated`（RN 内置动画库）的使用情况（`grep -r "from '@mrn/react-native'" --include="*.tsx" | grep "Animated"`）；检查是否使用了 `react-native-reanimated`（`grep -r "reanimated" package.json`）；检查 `useNativeDriver` 是否正确使用。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 所有动画使用 `react-native-reanimated`（Worklets 模式）；有 lint 规则禁止 RN 内置 `Animated` API；动画逻辑与 UI 逻辑分离 |
| 良好 | 50 分 | 大部分动画使用 Reanimated，少量简单动画使用内置 `Animated` 并正确配置 `useNativeDriver: true` |
| 初级 | 25 分 | 混合使用两种动画库，或使用内置 `Animated` 但未启用 `useNativeDriver`（JS 线程动画） |
| 未达标 | 0 分 | 用 `setState + setTimeout` 实现动画（反模式：全部在 JS 线程执行，严重掉帧） |

**依据来源：** 黄金法则 #10：规范写进 lint；黄金法则 #5：显式优于隐式；React Native 性能文档

---

### MRN-7：自定义 Hook 抽象（满分 75 分）

**为什么重要：** 组件文件里混杂数据获取、副作用、业务逻辑，会让 AI 在修改 UI 时不得不理解大量业务代码，反之亦然。自定义 Hook 是 React/RN 生态里最友好的抽象层——函数签名即文档，AI 只需看 Hook 的输入输出就能理解它做什么。

**AI 判断方式：** 检查项目中 `hooks/` 目录结构；统计组件文件中直接包含数据获取/副作用逻辑的比例（搜索组件文件中 `useEffect + fetch` 或 `axios/request` 的共现）；检查是否有 `use[FeatureName].ts` 格式的自定义 Hook 文件。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 业务逻辑全部抽离为自定义 Hook（`usePatientData`、`useVisitForm` 等）；组件文件中几乎无直接的数据获取逻辑；Hook 与组件 1:1 对应或按功能聚合 |
| 良好 | 50 分 | 大部分复杂逻辑有对应 Hook，但部分组件仍有内联的数据获取逻辑 |
| 初级 | 25 分 | 少量 Hook 存在（多为通用 utils 类），业务逻辑主要在组件内部 |
| 未达标 | 0 分 | 无自定义 Hook，所有逻辑内联在组件（反模式：UI 和业务逻辑强耦合，AI 修改组件时无法单独理解/修改业务逻辑） |

**依据来源：** 黄金法则 #1：一个概念，一个文件（UI 逻辑和业务逻辑分别是两个概念）；黄金法则 #2：自包含的实现

---

### MRN-8：Feature-Based 目录组织（满分 75 分）

**为什么重要：** 技术层目录（`components/`、`hooks/`、`utils/`）让功能相关的文件分散在多个顶层目录，AI 理解一个功能需要跨目录加载多个文件。Feature-Based 目录让一个功能的所有文件聚合在一起，AI 修改一个功能只需在一个目录内操作。

**AI 判断方式：** 检查项目目录的组织方式。判断是否为 Feature-Based 组织（`features/patientList/`、`features/visitForm/`）还是技术层组织（`components/`、`containers/`、`pages/`）。特别检查：功能相关的组件、hooks、样式、测试是否放在同一个 feature 目录下。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | Feature-Based 目录，每个 feature 下包含组件、hooks、types、tests，修改一个功能只需在一个目录内操作 |
| 良好 | 50 分 | 混合结构，有 features 目录但仍有大量 shared components/utils；功能相关文件有 60%+ 集中在 feature 目录 |
| 初级 | 25 分 | 技术层目录为主（components/hooks/utils），功能代码分散，AI 需要跨多个顶层目录才能理解一个功能 |
| 未达标 | 0 分 | 平铺目录或无结构（所有组件在一个目录下），文件数量多（> 50 个）时 AI 无从下手 |

**MRN 项目默认结构说明：** MRN 脚手架（Talos CLI）生成的默认结构是 `pages/`、`components/` 这种技术层组织。这是起点，不是终点——随着业务增长，应逐步迁移到 Feature-Based 结构。

**依据来源：** 黄金法则 #5：显式优于隐式；黄金法则 #8：每个目录都有 README

---

### MRN-9：单组件 State 数量控制（满分 75 分）

**为什么重要：** 一个组件里有 10 个 `useState`，说明这个组件承担了太多职责。AI 修改其中一个 state 时，很难保证不影响其他 state 的逻辑。state 过多是组件需要拆分的信号。

**AI 判断方式：** 扫描所有组件文件（`.tsx`），统计每个组件中 `useState` 调用次数。计算超标组件（> 5 个 state）的数量和比例；特别标注超过 10 个 state 的组件（需要充足理由）。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 所有组件 state 数量 ≤ 5；无组件超过 10 个 state；状态集中由 zustand store 管理 |
| 良好 | 50 分 | 大部分（> 80%）组件 state ≤ 5，存在少量（1-3 个）state 在 6-10 的组件，有合理业务原因 |
| 初级 | 25 分 | 超过 20% 的组件有 6-10 个 state，存在 state 分散、逻辑不内聚的问题 |
| 未达标 | 0 分 | 存在 state > 10 的组件且无合理理由（反模式：state 过多说明组件职责过重，AI 难以安全修改单一状态而不影响其他） |

**依据来源：** 黄金法则 #2：自包含的实现（state 过多说明组件承担了多个概念）；黄金法则 #1：一个概念，一个文件

---

### MRN-10：包引用规范（满分 100 分）【MRN 特有】

**为什么重要：** 这是 MRN 专项中 ROI 最高的检查项。AI 训练数据里有标准 `react-native`，但没有 `@mrn/react-native`。如果代码库里混用了标准包和 MRN 私有包，AI 生成的代码会用错包名，导致运行时报错。

**AI 判断方式：** 扫描所有 `.ts`/`.tsx` 文件中的 import 语句，统计 `from 'react-native'`（标准包）和 `from '@mrn/react-native'`（MRN 私有包）的使用比例。检查 `package.json` 中是否有 `react-native` 直接依赖（应该只有 `@mrn/react-native`）。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 100 分 | 所有基础组件从 `@mrn/react-native` 引入；`package.json` 中无 `react-native` 直接依赖；有 lint 规则禁止 `from 'react-native'`；CLAUDE.md 中有包引用规范说明 |
| 良好 | 75 分 | 绝大多数（> 90%）使用 `@mrn/react-native`，少量历史代码仍用 `react-native`，已标注 TODO |
| 初级 | 50 分 | 混用两种包，比例各半，无 lint 规则，AI 无法判断应该用哪个 |
| 未达标 | 0 分 | 大量使用标准 `react-native` 包（反模式：AI 生成代码时会继续用错误的包名，导致运行时报错） |

**MRN 包引用对照表：**

| 标准 RN 写法（❌ 禁止） | MRN 正确写法（✅ 使用） |
|----------------------|----------------------|
| `from 'react-native'` | `from '@mrn/react-native'` |
| `from 'react-navigation'` | `from '@mrn/react-navigation'` |
| `StyleSheet.create()` | `RemStyleSheet.create()`（来自 `@meishi/hammer-mrn`）|
| `fetch()` / `axios` | `NativeModules.MRNNetwork.request()` 或 MSI 标准桥 |

**依据来源：** MRN 开发最佳实践；MRN AI Coding SPEC 制定计划；黄金法则 #5：显式优于隐式

---

### MRN-11：网络请求规范（满分 75 分）【MRN 特有】

**为什么重要：** MRN 的网络请求不能用标准的 `fetch()` 或 `axios`，必须通过 `NativeModules.MRNNetwork.request()` 或 MSI 标准桥（`@msi-extend`）发起，才能自动注入美团公参（用户 ID、设备信息、AB 实验参数等）。AI 如果不知道这个规范，会生成无法携带公参的网络请求代码。

**AI 判断方式：** 搜索项目中 `fetch(`、`axios`、`XMLHttpRequest` 的使用（`grep -r "fetch(\|axios\|XMLHttpRequest" --include="*.ts" --include="*.tsx"`）；检查是否有统一的网络请求封装层（`BaseApi`、`request.ts` 等）；检查封装层是否使用了 `MRNNetwork` 或 MSI 标准桥。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | 所有网络请求通过统一封装层发起；封装层使用 `MRNNetwork.request()` 或 MSI 标准桥；公参自动注入，业务代码无需手动传公参；有 CLAUDE.md 说明网络请求规范 |
| 良好 | 50 分 | 有统一封装层，但部分业务代码绕过封装层直接调用；或封装层文档不完整 |
| 初级 | 25 分 | 网络请求方式混乱，部分用封装层，部分直接用 `fetch()`/`axios`，无统一规范 |
| 未达标 | 0 分 | 直接使用 `fetch()` 或 `axios`（反模式：无法自动注入公参，AI 生成的网络请求代码无法在 MRN 环境正常工作） |

**依据来源：** MRN 开发最佳实践；MSI 标准桥文档；黄金法则 #5：显式优于隐式

---

### MRN-12：版本区间规范（满分 75 分）【MRN 特有】

**为什么重要：** MRN 具有 Native 依赖属性，高版本区间的代码发到不支持的低版本 App 上会崩溃。版本区间选择不当是 MRN 开发中最常见的线上事故来源之一。AI 如果不了解版本区间机制，可能生成使用了高版本 API 但版本区间设置过低的代码。

**AI 判断方式：** 检查 `mrn.config.js` 中的版本区间配置；检查是否有版本区间选择的文档说明（CLAUDE.md 或 README）；检查是否有 CI 检查防止版本区间设置错误。

| 级别 | 分值 | 判断标准 |
|------|------|---------|
| 优秀 | 75 分 | `mrn.config.js` 中版本区间配置合理；有文档说明版本区间选择原则（如：使用了 X API 需要 Y 版本以上）；有 CI 检查或 lint 规则防止版本区间设置过低；CLAUDE.md 中有版本区间注意事项 |
| 良好 | 50 分 | 版本区间配置合理，但无文档说明选择原因；或有文档但无自动化检查 |
| 初级 | 25 分 | 版本区间配置存在，但选择依据不清晰，团队靠经验判断 |
| 未达标 | 0 分 | 无版本区间配置或配置明显不合理（如版本区间过低，使用了高版本 API）；无任何文档说明 |

**依据来源：** MRN 开发最佳实践；黄金法则 #5：显式优于隐式

---

## 四、MRN 专项反模式速查表

| 反模式 | 危害 | 对应检查项 | 修复方向 |
|--------|------|-----------|---------|
| `from 'react-native'` | AI 生成代码用错包名，运行时报错 | MRN-10 | 全局替换为 `@mrn/react-native`，加 lint 规则 |
| `ScrollView + .map()` 渲染长列表 | 所有 item 同时渲染，严重掉帧 | MRN-3 | 替换为 FlashList 或 FlatList |
| Props 类型在全局 `types/` 目录 | AI 修改组件需加载额外文件 | MRN-1 | Props 类型移到组件文件内 |
| Barrel index 文件（`index.ts` re-export） | AI 上下文加载量剧增，来源不明 | MRN-2 | 删除 barrel 文件，改用直接路径导入 |
| `setState + setTimeout` 实现动画 | JS 线程动画，严重掉帧 | MRN-6 | 迁移到 react-native-reanimated |
| 内联样式对象 `style={{ ... }}` | 每次渲染创建新对象，性能损耗 | MRN-4 | 改用 `RemStyleSheet.create()` |
| 大量 `Platform.OS` if-else 分支 | 单文件包含两平台逻辑，AI 容易遗漏 | MRN-5 | 较大差异用 `.ios.tsx`/`.android.tsx` 隔离 |
| 直接 `fetch()` / `axios` 发请求 | 无法注入公参，MRN 环境不可用 | MRN-11 | 改用 MRNNetwork 或 MSI 标准桥封装 |
| 单组件 > 10 个 `useState` | 职责过重，AI 难以安全修改 | MRN-9 | 拆分组件或抽离为自定义 Hook |
| 业务逻辑内联在组件 | UI 和业务强耦合，AI 无法单独修改 | MRN-7 | 抽离为 `use[FeatureName]` 自定义 Hook |

---

## 五、MRN 专项评分权重建议

MRN 专项各检查项的权重建议（供综合评分时参考）：

**阻塞项（出现即严重扣分，需优先修复）：**
- MRN-10 包引用规范：直接影响 AI 生成代码的可运行性
- MRN-3 列表性能规范：直接影响用户体验，且 AI 容易复现反模式

**高优先级（影响 AI 生成质量）：**
- MRN-1 组件结构规范：影响 AI 理解组件的效率
- MRN-2 禁止 Barrel Imports：影响 AI 上下文加载量
- MRN-11 网络请求规范：影响 AI 生成代码的可用性

**中优先级（影响代码质量和可维护性）：**
- MRN-7 自定义 Hook 抽象
- MRN-8 Feature-Based 目录组织
- MRN-9 单组件 State 数量控制

**低优先级（影响性能和规范性）：**
- MRN-4 样式管理规范
- MRN-5 平台差异处理规范
- MRN-6 动画规范
- MRN-12 版本区间规范

---

## 六、与通用维度的关系

MRN 专项评分是通用维度评分的**补充**，不是替代。一个 MRN 项目的完整评分由两部分组成：

**通用维度（适用所有技术栈）：** 仓库定位与导航、架构文档完整性、业务上下文可读性、代码可读性、编码规范与自动化护栏、测试验证、反馈回路。

**MRN 专项（MRN 特有）：** 本文档中的 MRN-1 至 MRN-12。

通用维度中有几项对 MRN 项目特别重要：

**5.3 TypeScript / 强类型覆盖率（满分 100 分）：** MRN 项目使用 TypeScript，强类型覆盖率直接影响 AI 生成代码的准确性。Props 类型、API 返回值类型、状态类型都应该有完整的 TypeScript 定义。

**1.1 上下文入口文件（满分 100 分）：** MRN 项目的 CLAUDE.md 应该包含 MRN 特有的约束：包引用规范（`@mrn/react-native` 而非 `react-native`）、网络请求规范（MRNNetwork/MSI）、版本区间注意事项、禁止事项列表。这是 AI 写出正确 MRN 代码的前提。

---

## 七、参考资料

- 终端研发 AI 友好型代码库评估标准 v1.0：https://km.sankuai.com/collabpage/2753864102
- MRN 开发最佳实践：https://km.sankuai.com/collabpage/2048937248
- MRN AI Coding SPEC 制定计划：https://km.sankuai.com/collabpage/2752499819
- MRN 技术栈全景：https://km.sankuai.com/collabpage/2752999018
- MRN 容器架构演进技术落地方案：https://km.sankuai.com/collabpage/2732667855
- React Native 性能文档：https://reactnative.dev/docs/performance
- Shopify FlashList：https://shopify.github.io/flash-list/
- TkDodo：Barrel Imports 的危害（11k → 3.5k 模块，减少 68%）
