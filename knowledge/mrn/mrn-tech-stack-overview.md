# 美团 MRN 技术栈全景

> 整理日期：2026-03-26
> 来源：美团内部学城文档（km.sankuai.com）

---

## 一、MRN 是什么

MRN（Meituan React Native）是美团基于开源 React Native 深度改造的移动端动态化容器，是美团"二环链路"的核心技术选型。

理解 MRN 的关键是理解美团的**三环容器分级体系**：

| 层级 | 技术方案 | 适用场景 | 特点 |
|------|----------|----------|------|
| 一环 | Native + 局部动态化 | 首页、核心搜索入口、频道页 | 极致性能，开发成本最高，动态性最弱 |
| **二环** | **MRN 动态化方案** | **绝大多数业务主流程页面** | **性能与效率平衡，是 C 端动态化的主要承载区间** |
| 三环 | H5 + 小程序方案 | 非主流程页面、活动页、端外复用 | 快速迭代，跨端复用，性能天花板较低 |

MRN 的核心价值在于：接近 Native 的性能 + JS 动态发布能力 + 多端/多 App 复用性。

---

## 二、技术层次架构

MRN 的技术体系从底层到上层分为四个层次：

### 2.1 底层容器层（MRN 容器）

基于 React Native 改造，当前正在从**旧架构**向**新架构**演进：

**旧架构**：JS 和 Native 通过 Bridge 异步通信，消息需要 JSON 序列化/反序列化，存在性能瓶颈。

**新架构（Fabric + TurboModules + JSI）**：
- **JSI（JavaScript Interface）**：C++ 与 JS 之间的直接绑定层，实现内存级通信，消除序列化开销
- **Fabric**：新的渲染系统，支持同步渲染和优先级调度
- **TurboModules**：原生模块按需懒加载，减少启动耗时

目标：2026 年上半年完成平台升级，业务获得至少 15% 的性能收益，支撑 Android/iOS/鸿蒙三端齐发。

### 2.2 框架层（MRNModule / MCOne）

在 MRN 容器之上，美团建设了业务开发框架：

- **MRNModule（又名 MCModule）**：MRN 业务开发框架 1.0/2.0，提供大量开箱即用的业务能力（网络、路由、埋点等），上层标签属性从偏 Native 重构成更偏 React 前端风格
- **MCOne**：在 MRNModule 基础上升级，支持小程序及 H5 跨端，目标是成为**支持跨端的移动端业务开发框架**

三者关系：`MRN 容器` → `MRNModule/MCModule` → `MCOne`

### 2.3 跨端层（Max）

Max 是美团到店跨端解决方案，让开发者用一套 React DSL 写出能跑在 MRN、Web、微信小程序的代码。

Max 分为三个子方案：
- **MaxAir**（高效率跨端）：产出跨 MRN/H5/小程序（运行时）的页面，App 端性能最佳
- **MaxPro**（高性能跨端）：产出跨 MRN/H5/小程序原生（编译时）的页面，全渠道最佳性能，开发要求高
- **MaxMini**（模块级跨端）：产出跨 MRN/H5/小程序使用的组件，适合业务组件跨端复用

Max 标准分层：
- **Max 完整标准集**：可使用原 MRN 组件能力 + Max 增强能力
- **Max 跨端标准集**：额外获得端内跨容器及端外（小程序/H5）同构能力

### 2.4 标准化层（MSI）

**MSI（Meituan Standard Interface，美团标准桥）**：美团业务容器统一的桥能力，通过标准化提高复用性和研发效率，是 MRN 标准化的核心约束——业务仅可使用 MSI 公开的桥能力，不使用自定义桥或 KNB 桥。

---

## 三、核心包体系

### 基础组件与工具

| 包名 | 说明 |
|------|------|
| `@mrn/react-native` | 基础组件库，等同于 `react-native`，提供 View/Image/FlatList/TouchableOpacity 等 |
| `@mrn/mrn-utils` | 工具库，包含环境信息（env）、AB 实验（getABStrategy）、埋点（lxTrackMPT/lxTrackModuleView）等 |
| `@mrn/react-navigation` | 路由导航，等同于 `react-navigation` |
| `@mrn/react-native-pull-refresh` | 下拉刷新组件 |
| `@mrn/react-native-shadow-view` | 阴影组件 |
| `@mrn/react-native-safe-area-view` | 安全区域组件 |
| `@mrn/react-native-blur-view` | 模糊效果组件 |
| `@mrn/react-native-skeleton-drawer` | 骨架屏组件 |
| `@mrn/react-native-spring-scrollview` | 弹性滚动列表 |
| `@mrn/auto-height-image` | 自适应高度图片 |
| `@mrn/mrn-privacy-api` | 隐私 API |

### 视觉规范组件库

| 包名 | 说明 |
|------|------|
| `@ss/mtd-react-native` | MTD UI 组件库（相当于 antd），视觉规范组件，如 `<Loading.view loadingMessage='努力加载中…'/>` |
| `@ss/mtdr-react-native` | MTD React Native 扩展组件 |

### 网络请求

```typescript
// MRN 网络请求方式
NativeModules.MRNNetwork.request({
  url: 'https://...',
  method: 'POST',
  data: {},
  // ...
})
```

参考文档：`https://km.sankuai.com/docs/mrn/page/293902581#id-request`

### 业务组件库

| 包名 | 说明 |
|------|------|
| `@meishi/hammer-mrn` | 到餐业务组件库（Rate 评分组件等） |
| `@meishi/hammer-js` | 到餐 JS 工具库 |
| `@meishi/query-location-permission-mrn` | 位置权限查询 |

---

## 四、工程体系

### 4.1 核心概念

- **Bundle**：MRN 的发布单位，一个 Bundle 可以包含多个 Component
- **Component**：注册在 Bundle 中的 React 组件，对应一个页面或模块
- **版本区间**：MRN 具有 Native 依赖属性，高版本区间的代码不能发到不支持的低版本容器，选择版本区间时需谨慎

### 4.2 项目结构

通过 Talos CLI 创建的标准项目结构：

```
project/
├── mrn.config.js       # Bundle 配置（业务线、bundleName、debug 配置等）
├── index.tsx           # Bundle 入口，用来注册组件（可注册多个）
├── package.json
└── src/
    ├── pages/          # 页面组件
    ├── components/     # 公共组件
    ├── api/            # 网络请求
    │   └── index.js    # 网络请求入口（包含 BaseApi）
    └── router/         # 路由配置
        └── routers.ts
```

### 4.3 项目创建

```bash
# 通过 Talos CLI 创建（推荐）
# 访问 https://talos.sankuai.com/#/cli/MRN 生成创建脚本
yarn && yarn start
```

`@mrn/mrn-cli` 的 `init` 脚本已废弃，推荐使用 Talos 的 MRN 创建脚本生成器。

### 4.4 开发调试

**本地调试**：
1. 连接公司 WiFi（手机连 Meituan，PC 连 Meituan-Test）
2. `yarn && yarn start` 启动服务，获取二维码和服务地址
3. App 中切换到 MRN 面板（🔯图标），配置 Bundle 地址为本地服务地址
4. 重启 App 进入对应页面

**测试包调试**：
- FSD 打包后，在交付页面点击 Bundle 锁定，生成二维码
- App 调试面板中扫描二维码一键锁包

### 4.5 发布流程

通过 FSD（美团前端发布平台）打包发布，支持灰度发布和线上监控。

---

## 五、性能优化体系

MRN 的性能优化分为**启动性能**和**运行时性能**两大方向：

### 启动性能

容器侧：
- 轻量级 JS 引擎切换
- RAMBundle + TurboModule 按需加载
- RN 引擎预热、复用与保活

业务侧：
- 包体积优化、分包懒加载
- 首屏接口裁剪
- 精简视图层级、减少重复渲染
- 标记核心请求并提升网络优先级

### 运行时性能

容器侧：
- 主线程直调（新架构 JSI）
- 同步渲染
- 优先级调度

业务侧：
- 视图拍平，优化视图层级
- 减少滑动监听器数量
- 控制滑动过程中的数据更新频率
- 长列表使用高性能列表组件

---

## 六、容器演进路径

当前 MRN 正处于架构升级的关键时期：

1. **短期（2026 Q1-Q2）**：推进 MRN 新架构（Fabric + TurboModules + JSI）落地，目标 26 年上半年完成平台升级
2. **中期**：业务可先选择逐步采用 Max 规范，降低未来底层切换成本
3. **长期**：RN + Yoga 路线（MRN）与 WebView 路线（H5/小程序）并行演进，分别服务高性能和跨端复用场景

**对业务开发者的影响**：
- 新架构升级后，`NativeModule` 的调用方式会有变化（JSI 直调替代 Bridge）
- 建议新项目遵循 Max 规范写法，降低未来迁移成本
- 组件库统一使用 MSI 标准桥，避免自定义桥

---

## 七、参考资源

- MRN 官方文档站：`https://mrn.sankuai.com/docs/`
- MRN 学城文档空间：`https://km.sankuai.com/space/MRNDOCS`
- Max 文档：`https://sky.sankuai.com/max/instruction/basic/directory`
- MRN 开发最佳实践：`https://km.sankuai.com/collabpage/2048937248`
- MRN 容器架构演进技术落地方案：`https://km.sankuai.com/collabpage/2732667855`
- 容器演进路径决策逻辑：`https://km.sankuai.com/collabpage/2748774526`
- MC-One 开发指南：`https://km.sankuai.com/collabpage/1769430165`
