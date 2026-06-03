# Maven：Java 世界的 npm，写给前端开发者

> 整理日期：2026-06-02  
> 参考来源：[Apache Maven 官网](https://maven.apache.org/)、[Maven 构建生命周期官方文档](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html)

---

## 先建立直觉：Maven 是什么

如果你熟悉前端工具链，Maven 在 Java 世界里扮演的角色大致等于：

**npm + webpack + CI 脚本** 的合体。

更具体地说：

- `package.json` → `pom.xml`（项目描述文件）
- `npm install` → `mvn install`（下载依赖）
- `npm run build` → `mvn package`（打包构建）
- `node_modules/` → `~/.m2/repository/`（本地依赖缓存）
- npm registry → Maven Central（中央仓库）

Maven 的名字来自意第绪语，意思是"知识的积累者"。它由 Apache 基金会维护，是 Java 生态中最主流的项目管理与构建工具，另一个常见的替代品是 Gradle（更灵活，Android 项目默认使用）。

---

## 为什么 Java 需要 Maven

在 Maven 出现之前，Java 项目的构建是一团乱麻：每个项目都有自己写的 Ant 脚本，JAR 包直接提交进代码仓库，没有统一的依赖管理方式。

Maven 解决了两个核心问题：

**一、依赖从哪来、怎么管理。** 你只需要在 `pom.xml` 里声明"我需要 Spring Boot 3.2.0"，Maven 会自动从中央仓库下载，并且递归解析所有传递依赖（你依赖的库所依赖的库）。这和 npm 的 `node_modules` 机制非常相似。

**二、项目怎么构建。** Maven 定义了一套标准的构建生命周期，所有 Maven 项目都遵循同样的流程：编译 → 测试 → 打包 → 安装 → 发布。你不需要为每个项目重新写构建脚本。

---

## pom.xml：项目的身份证

`pom.xml`（Project Object Model）是 Maven 项目的核心配置文件，相当于 `package.json`。

一个典型的 `pom.xml` 长这样：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <!-- 项目坐标：GAV（GroupId + ArtifactId + Version） -->
    <groupId>com.meituan.medicine</groupId>
    <artifactId>medicine-ai-backend</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <!-- 依赖声明 -->
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>3.2.0</version>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>  <!-- 只在测试时用，不打进最终包 -->
        </dependency>
    </dependencies>
</project>
```

### GAV 坐标系统

Maven 用三个维度唯一标识一个依赖，合称 **GAV**：

- `groupId`：组织/公司标识，通常是反转的域名，如 `com.meituan`、`org.springframework`
- `artifactId`：具体模块名，如 `spring-boot-starter-web`
- `version`：版本号，`SNAPSHOT` 表示开发中的快照版本

这相当于 npm 的 `@scope/package-name@version`，只是拆成了三个字段。

### 依赖 scope（作用域）

Maven 的 `scope` 类似于 npm 的 `dependencies` vs `devDependencies`，但更细：

| scope | 含义 | 类比 |
|-------|------|------|
| `compile`（默认） | 编译、运行、打包都需要 | `dependencies` |
| `test` | 只在测试时需要 | `devDependencies` |
| `provided` | 编译时需要，运行时由容器提供（如 Servlet API） | `peerDependencies` |
| `runtime` | 编译时不需要，运行时需要（如 JDBC 驱动） | 无直接对应 |

---

## 构建生命周期：Maven 的核心设计

这是 Maven 最重要的概念，也是它与 npm scripts 最大的不同。

Maven 内置了三套生命周期：

- **default**：处理项目的编译、测试、打包、部署（最常用）
- **clean**：清理上次构建产物
- **site**：生成项目文档网站

每套生命周期由一系列**阶段（phase）**组成，阶段是有序的，执行某个阶段会自动执行它之前的所有阶段。

`default` 生命周期的关键阶段（按顺序）：

```
validate → compile → test → package → verify → install → deploy
```

- `validate`：校验项目配置是否正确
- `compile`：编译源代码（`.java` → `.class`）
- `test`：运行单元测试
- `package`：打包成 JAR/WAR 文件
- `verify`：运行集成测试并验证
- `install`：把打好的包安装到本地仓库（`~/.m2/`），供本机其他项目引用
- `deploy`：把包发布到远程仓库，供团队共享

**关键理解**：当你运行 `mvn package`，Maven 会自动先执行 `validate`、`compile`、`test`，再执行 `package`。你不需要手动串联这些步骤。

这和 npm scripts 的区别在于：npm scripts 是你自己定义的命令，Maven 的生命周期是内置的、有顺序保证的标准流程。

### 常用命令速查

```bash
mvn clean          # 删除 target/ 目录（构建产物）
mvn compile        # 只编译，不测试
mvn test           # 编译 + 运行测试
mvn package        # 编译 + 测试 + 打包成 JAR
mvn install        # 编译 + 测试 + 打包 + 安装到本地仓库
mvn clean package  # 先清理再打包（最常用的组合）
mvn clean package -DskipTests  # 跳过测试（开发时常用）
```

---

## 仓库体系：依赖从哪里来

Maven 的依赖解析遵循三级查找顺序：

```
本地仓库（~/.m2/repository/）
    ↓ 找不到
私服仓库（公司内部 Nexus/Artifactory）
    ↓ 找不到
中央仓库（Maven Central，https://repo.maven.apache.org/）
```

**本地仓库**就是你电脑上的缓存，第一次下载后就不用再联网了，和 npm 的 `node_modules` 缓存类似，但是全局共享的（不是每个项目一份）。

**私服仓库**是公司内部搭建的 Maven 仓库，用于存放公司内部的 JAR 包，以及对中央仓库的代理（加速下载）。美团内部有自己的 Maven 私服，`pom.xml` 里通常会配置指向内网地址。

**中央仓库**是 Maven 的官方公共仓库，托管了几乎所有开源 Java 库。你可以在 [search.maven.org](https://search.maven.org) 搜索任何依赖。

---

## 传递依赖：npm 的 node_modules 地狱在 Java 里的版本

当你依赖 Spring Boot，Spring Boot 本身又依赖了几十个库，这些库又各自依赖了其他库……Maven 会自动解析这整棵依赖树，这叫**传递依赖（Transitive Dependencies）**。

这带来了一个经典问题：**版本冲突**。比如你的项目依赖了 A 和 B，A 依赖 `jackson 2.14`，B 依赖 `jackson 2.12`，Maven 该用哪个版本？

Maven 的解决策略是**最近路径优先**：依赖树中离根节点最近的版本胜出。如果路径相同，先声明的优先。

当你遇到版本冲突时，可以用 `<exclusion>` 手动排除某个传递依赖：

```xml
<dependency>
    <groupId>com.example</groupId>
    <artifactId>some-library</artifactId>
    <version>1.0</version>
    <exclusions>
        <exclusion>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

---

## 插件体系：Maven 的扩展机制

Maven 本身只是一个框架，具体的构建任务（编译、打包、测试）都由**插件（Plugin）**完成。

每个生命周期阶段背后都绑定了默认插件：

- `compile` 阶段 → `maven-compiler-plugin`（调用 javac 编译）
- `test` 阶段 → `maven-surefire-plugin`（运行 JUnit 测试）
- `package` 阶段 → `maven-jar-plugin`（打包成 JAR）

你也可以在 `pom.xml` 里配置额外的插件，比如 Spring Boot 的打包插件：

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```

这个插件会把你的应用打包成一个"fat JAR"（包含所有依赖的可执行 JAR），可以直接用 `java -jar app.jar` 运行。

---

## 多模块项目（Multi-module）

大型 Java 项目通常会拆分成多个模块，比如：

```
my-project/
├── pom.xml          ← 父 POM（parent）
├── my-api/
│   └── pom.xml      ← 子模块
├── my-service/
│   └── pom.xml      ← 子模块
└── my-web/
    └── pom.xml      ← 子模块
```

父 `pom.xml` 声明所有子模块，并统一管理依赖版本（通过 `<dependencyManagement>`），子模块只需声明依赖名，不需要写版本号。

这类似于 npm workspace 或 pnpm monorepo 的概念，但 Maven 的多模块支持是内置的，不需要额外工具。

---

## 与前端工具链的对照总结

| 概念 | 前端 | Maven |
|------|------|-------|
| 项目配置文件 | `package.json` | `pom.xml` |
| 依赖声明 | `dependencies` / `devDependencies` | `<dependency>` + `scope` |
| 安装依赖 | `npm install` | `mvn install`（或 IDE 自动触发） |
| 本地缓存 | `node_modules/`（项目级） | `~/.m2/repository/`（全局共享） |
| 公共仓库 | npm registry | Maven Central |
| 私有仓库 | Verdaccio / 公司 npm 私服 | Nexus / Artifactory |
| 构建脚本 | `npm run build`（自定义） | `mvn package`（标准生命周期） |
| 打包产物 | `dist/`（JS bundle） | `target/*.jar` 或 `*.war` |
| 跳过测试 | 无直接对应 | `-DskipTests` |
| 多包管理 | pnpm workspace | Maven 多模块 |

---

## 常见坑

**1. SNAPSHOT 版本的陷阱**

版本号带 `-SNAPSHOT` 的依赖是"快照版本"，Maven 每次构建都会检查远程仓库是否有更新。在 CI 环境中，这可能导致构建不稳定（今天能构建，明天因为快照更新而失败）。生产环境应该使用正式版本号。

**2. 依赖冲突难以排查**

当出现 `ClassNotFoundException` 或 `NoSuchMethodError` 时，往往是依赖版本冲突导致的。可以用 `mvn dependency:tree` 命令查看完整的依赖树，找出冲突来源。

**3. 本地仓库损坏**

有时候下载中断会导致本地仓库里有损坏的 JAR 文件，Maven 不会自动重新下载。解决方法是删除 `~/.m2/repository/` 下对应的目录，强制重新下载。

**4. 镜像配置**

在国内，直接访问 Maven Central 很慢。通常需要在 `~/.m2/settings.xml` 里配置阿里云镜像：

```xml
<mirrors>
    <mirror>
        <id>aliyun</id>
        <mirrorOf>central</mirrorOf>
        <url>https://maven.aliyun.com/repository/central</url>
    </mirror>
</mirrors>
```

公司内部项目通常已经配置好了指向内网私服的镜像，不需要手动配置。

---

## 参考来源

- [Apache Maven 官网 - What is Maven?](https://maven.apache.org/what-is-maven.html)
- [Introduction to the Build Lifecycle](https://maven.apache.org/guides/introduction/introduction-to-the-lifecycle.html)
- [Introduction to the POM](https://maven.apache.org/guides/introduction/introduction-to-the-pom.html)
- [Introduction to Dependency Mechanism](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)
