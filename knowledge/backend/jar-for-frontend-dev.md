# JAR 包是什么：写给前端开发者

> 整理日期：2026-06-02  
> 来源：Oracle JAR File Specification、Oracle Java 官方文档

---

## 从一个类比开始

如果你熟悉前端工程，可以这样理解 JAR 包：

| 前端世界 | Java 世界 |
|---------|---------|
| `.js` 源码文件 | `.java` 源码文件 |
| `tsc` 编译 TypeScript | `javac` 编译 Java |
| `.js` 编译产物 | `.class` 字节码文件 |
| `npm pack` 打包成 `.tgz` | `jar` 打包成 `.jar` |
| `node_modules/` 里的包 | Maven 本地仓库里的 JAR |

JAR（Java Archive）本质上就是 Java 世界的"npm 包"——一个把编译产物和资源文件打包在一起的压缩包。

---

## Java 源码到 JAR 的完整链路

理解 JAR 包，必须先理解 Java 代码的执行路径。这条路径和前端有一个关键的不同：**Java 有一个中间层——字节码（Bytecode）**。

```
.java 源码
    ↓  javac 编译
.class 字节码文件
    ↓  jar 打包
.jar 文件
    ↓  JVM 运行
机器码（运行时 JIT 编译）
```

### 第一步：.java → .class（编译）

Java 源码文件（`.java`）经过 `javac` 编译器编译后，生成 `.class` 文件。`.class` 文件里存储的不是机器码，而是**字节码（Bytecode）**——一种平台无关的中间表示。

```java
// Hello.java（源码）
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

```bash
javac Hello.java   # 生成 Hello.class
```

`.class` 文件是二进制格式，人类无法直接阅读。你可以用 `javap -c Hello.class` 反汇编查看字节码指令。

**为什么要有字节码这一层？** 这是 Java "Write Once, Run Anywhere"（一次编写，到处运行）的核心设计。字节码不针对任何特定 CPU 架构，由各平台的 JVM（Java Virtual Machine）负责在运行时将字节码翻译成本地机器码执行。

### 第二步：.class → .jar（打包）

一个 Java 项目通常有几十甚至几百个 `.class` 文件，加上图片、配置文件等资源。`jar` 命令把这些文件打包成一个 `.jar` 文件：

```bash
jar cf myapp.jar Hello.class config.properties
```

JAR 文件本质上是一个 **ZIP 压缩包**，你可以直接用 `unzip` 解压，或者用 `jar tf myapp.jar` 查看内容。

---

## JAR 文件的内部结构

解压一个典型的 JAR 文件，你会看到：

```
myapp.jar
├── META-INF/
│   └── MANIFEST.MF          ← 清单文件（类似 package.json）
├── com/
│   └── example/
│       ├── Hello.class      ← 编译后的字节码
│       └── Utils.class
└── config.properties        ← 资源文件
```

### MANIFEST.MF：JAR 的"package.json"

`META-INF/MANIFEST.MF` 是 JAR 的核心元数据文件，格式是简单的键值对：

```
Manifest-Version: 1.0
Main-Class: com.example.Hello
Class-Path: lib/commons-lang.jar lib/gson.jar
Created-By: 17.0.2 (Oracle Corporation)
```

- `Main-Class`：指定可执行 JAR 的入口类（类似 `package.json` 的 `main` 字段）
- `Class-Path`：声明依赖的其他 JAR（类似 `dependencies`）

有了 `Main-Class`，就可以直接运行 JAR：

```bash
java -jar myapp.jar
```

---

## JAR 的三种用途

### 1. 库（Library JAR）

最常见的用途。把可复用的代码打包成 JAR，供其他项目依赖。Maven Central（Java 的 npm registry）上有数百万个这样的 JAR。

```xml
<!-- pom.xml 中声明依赖，Maven 自动下载对应 JAR -->
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.10.1</version>
</dependency>
```

### 2. 可执行 JAR（Executable JAR）

包含 `Main-Class` 的 JAR，可以直接用 `java -jar` 运行。Spring Boot 应用默认打包成这种格式，一个 JAR 文件包含了应用代码、所有依赖、甚至内嵌的 Tomcat 服务器。

### 3. WAR / EAR（Web 应用归档）

WAR（Web Application Archive）和 EAR（Enterprise Application Archive）是 JAR 的变体，专门用于部署到 Tomcat、JBoss 等应用服务器。现代 Spring Boot 项目通常不再用 WAR，直接用可执行 JAR。

---

## 源码 JAR（Sources JAR）

你在 Maven 仓库里经常会看到两个 JAR：

- `gson-2.10.1.jar`：编译后的字节码，运行时使用
- `gson-2.10.1-sources.jar`：原始 `.java` 源码，供 IDE 展示

这就是为什么在 IntelliJ IDEA 里点击第三方库的类，能看到带注释的源码——IDE 自动下载了 sources JAR 并关联起来。

---

## 常见误区

**误区一：JAR 里是源码**  
不是。JAR 里是编译后的 `.class` 字节码，不是 `.java` 源码。字节码可以被反编译（工具如 CFR、Fernflower），但反编译结果会丢失注释和部分变量名。

**误区二：JAR 可以直接在浏览器运行**  
不能。JAR 需要 JVM 才能运行，和浏览器的 JS 引擎是完全不同的运行时。虽然历史上有 Java Applet 技术，但已于 2017 年被废弃。

**误区三：JAR 和 ZIP 是不同格式**  
JAR 就是 ZIP，只是约定了内部结构（必须有 `META-INF/MANIFEST.MF`）。你可以用任何 ZIP 工具打开 JAR 文件。

---

## 与前端工具链的对照总结

| 概念 | 前端 | Java |
|------|------|------|
| 源码文件 | `.ts` / `.js` | `.java` |
| 编译器 | `tsc` / `babel` | `javac` |
| 编译产物 | `.js`（或 bundle） | `.class`（字节码） |
| 打包工具 | webpack / rollup | `jar` 命令 / Maven |
| 分发包格式 | `.tgz`（npm pack） | `.jar` |
| 包管理器 | npm / pnpm | Maven / Gradle |
| 包注册中心 | npm registry | Maven Central |
| 元数据文件 | `package.json` | `MANIFEST.MF` + `pom.xml` |
| 运行时 | Node.js / 浏览器 | JVM |

---

## 参考来源

- [JAR File Specification — Oracle Java SE 17](https://docs.oracle.com/en/java/javase/17/docs/specs/jar/jar.html)
- [javac — The Java Compiler — dev.java](https://dev.java/learn/jvm/tools/core/javac/)
- [JAR Files in Java — GeeksforGeeks](https://www.geeksforgeeks.org/java/jar-files-java/)
