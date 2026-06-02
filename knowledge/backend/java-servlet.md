# Java Servlet：前世今生与核心原理

## 为什么理解 Servlet 依然重要

尽管如今 Java Web 开发几乎被 Spring Boot 统治，但理解 Servlet 依然至关重要——因为 Spring MVC、Spring WebFlux、RESTEasy、Struts 等所有现代 Java Web 框架，本质上都是穿了"高级马甲"的 Servlet。无论是 Request 域对象、Filter 拦截器链，还是 Web 容器启动流程，追根溯源都离不开 Servlet 规范。理解 Servlet，就是理解 Java Web 的地基。

## CGI 时代：Web 开发的蛮荒岁月

在 1990 年代，Web 服务器处理动态请求的方式是 **CGI（Common Gateway Interface）**。开发者编写一个可执行程序（如 C 程序或 Perl 脚本），Web 服务器收到请求后 fork 一个新进程来执行这个程序，程序 stdout 的输出即为 HTTP 响应体。

CGI 的致命缺陷在于**进程模型**。每个请求都伴随进程的创建与销毁，当并发量增加时，操作系统需要频繁地进行进程调度，内存占用也随之膨胀。一台性能尚可的服务器，在 100 并发的 CGI 场景下可能已经力不从心。

此外，CGI 程序与 Web 服务器之间的接口非常原始——通过环境变量和标准输入输出传递数据，缺乏任何抽象，开发者需要自己处理协议解析、头部管理、会话跟踪等各种底层细节。

## Servlet 的诞生：问题的系统性解决

1997 年，Sun Microsystems 在 Java 1.1 推出后不久，发布了 **Servlet API 1.0**（JSR 53），作为 Java EE（彼时还叫 J2EE）规范的一部分。Servlet 的核心创新是用**多线程模型**替代了 CGI 的进程模型：

- Web 容器（如 Tomcat、Jetty）启动时便加载 Servlet 类，并保持实例存在。
- 每个 HTTP 请求由容器分配一个线程，而非启动新进程。
- 一个 Servlet 实例可以服务成千上万个并发请求，线程的创建和销毁远快于进程。

这从根本上解决了 CGI 的性能瓶颈。更重要的是，Servlet 用**标准接口（Interface）** 抽象了 HTTP 处理逻辑——开发者面向接口编程，而具体实现由各个容器厂商提供，这使得"一次编写，到处运行"的企业级梦想在 Web 领域也成为可能。

## 核心概念：接口与容器

### Servlet 接口与 HTTP 专用类

Servlet 规范定义了一组核心接口，其中最重要的是 `jakarta.servlet.Servlet`（早期版本为 `javax.servlet.Servlet`）。该接口规定了三个生命周期方法和两个约定方法：

```java
public interface Servlet {
    void init(ServletConfig config) throws ServletException;  // 容器初始化时调用
    void service(ServletRequest req, ServletResponse res)     // 每次请求调用
        throws ServletException, IOException;
    void destroy();                                            // 容器销毁时调用
    
    ServletConfig getServletConfig();
    String getServletInfo();
}
```

在实践中，开发者几乎不直接实现这个接口，而是继承 `jakarta.servlet.http.HttpServlet`（原 `javax.servlet.http.HttpServlet`）。这个抽象类已经实现了 `service()` 方法，并将请求根据 HTTP 方法（GET/POST/PUT/DELETE 等）分派到对应的 `doGet()`/`doPost()` 等处理方法：

```java
public class MyServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) 
            throws ServletException, IOException {
        resp.getWriter().write("Hello, Servlet!");
    }
}
```

### ServletContext：应用级上下文

每个 Web 应用在容器中对应一个 `ServletContext` 对象。它提供了应用级别的服务，例如在容器启动时获取初始化参数、动态注册 Servlet 和 Filter（Servlet 3.0+）、记录日志，以及获取真实文件系统路径。

### ServletConfig：单个 Servlet 的配置

每个 Servlet 实例拥有一个 `ServletConfig`，用于存储部署描述符（`web.xml`）中为该 Servlet 配置的初始化参数，例如数据库连接信息、配置开关等。

## 生命周期：三个阶段的清晰边界

Servlet 的生命周期由容器管理，经历三个阶段：

**初始化（init）**：容器启动或在首次请求到达时（取决于配置），调用 `init(ServletConfig)`。此时适合做一次性的资源初始化，如建立数据库连接池。容器会保证 `init` 在任何 `service` 调用之前完成，且只执行一次。

**服务（service）**：容器为每个请求分配一个工作线程，调用 `service(ServletRequest, ServletResponse)`。`HttpServlet` 的 `service` 实现会根据 HTTP 方法将请求路由到对应的 `doXxx` 方法。开发者的业务逻辑通常写在这里。**注意**：`init` 执行完毕后，同一个 Servlet 实例会被多个线程并发调用 `service`，因此 **doGet/doPost 等方法必须线程安全**，不要在方法内创建实例变量（局部变量天然线程安全）。

**销毁（destroy）**：容器关闭或应用卸载时，容器调用 `destroy()`。这是释放资源的最后机会，例如关闭数据库连接、取消定时任务。

## 版本演进：技术进步的脉络

### Servlet 2.x：XML 驱动时代

从 Servlet 1.0（1997）到 Servlet 2.5（2005），这个漫长的阶段以 `web.xml` 为核心。开发者必须在部署描述符中声明所有 Servlet、Filter、监听器，以及 URL 映射规则：

```xml
<web-app xmlns="http://java.sun.com/xml/ns/javaee" version="2.5">
    <servlet>
        <servlet-name>hello</servlet-name>
        <servlet-class>com.example.HelloServlet</servlet-class>
    </servlet>
    <servlet-mapping>
        <servlet-name>hello</servlet-name>
        <url-pattern>/hello</url-pattern>
    </servlet-mapping>
</web-app>
```

Servlet 2.3（2001）引入了 **Filter**（过滤器），允许在请求到达 Servlet 之前和响应返回之后插入拦截逻辑。这为身份认证、日志记录、字符编码转换等横切关注点提供了优雅的解决方案。

Servlet 2.5（2005）要求 Java 5（Generics 引入后的第一个 Servlet 规范版本），并首次增加了对注解的有限支持，尽管还没有革命性的变化。

### Servlet 3.0：注解革命的起点（2009）

Servlet 3.0（JSR 315）是历史上变化最大的版本之一，引入了三项核心新特性：

**1. 注解驱动替代 XML**：无需 `web.xml`，在 Servlet 类上使用 `@WebServlet` 注解即可完成注册：

```java
@WebServlet(urlPatterns = "/hello", loadOnStartup = 1)
public class HelloServlet extends HttpServlet {
    // 业务代码
}
```

**2. 动态注册（ServletContext.addServlet）**：在容器启动时通过代码动态注册 Servlet 和 Filter，这为**可插拔的模块化设计**奠定了基础——想像一个 JAR 包在被其他应用依赖时，自动注册自己的 Servlet 而无需修改宿主应用的 `web.xml`。

**3. 异步 Servlet 支持**：`AsyncContext` 允许在 `service()` 方法中释放请求处理线程，将耗时操作（如 IO 等待、外部 API 调用）交给后台线程池处理后，再继续响应。这在长连接、推送通知、聊天应用等场景下显著提升了吞吐量。

### Servlet 3.1：非阻塞 I/O（2013）

Servlet 3.1（JSR 340）引入了**非阻塞读写**（`ReadListener`/`WriteListener`）。传统的 Servlet 输入输出是阻塞的——容器分配一个线程，该线程在整个 IO 操作期间一直被占用。非阻塞 IO 允许在 IO 完成时收到回调通知，从而用更少的线程处理更多的并发连接。这对 Comet、WebSocket、长轮询等场景至关重要。

### Servlet 4.0：HTTP/2 支持（2017）

Servlet 4.0（JSR 369）是 Tomcat 9 和 Undertow 等现代容器的核心规范，引入了 **HTTP/2** 支持，包括服务器推送（Server Push）、流优先级（Stream Priority）和_header 压缩（HPACK）。Servlet 4.0 还在 API 层面新增了 `HttpServletRequest.getHttpServletMapping()` 方法，让应用可以感知到请求具体匹配了哪个 URL 模式。

### Servlet 5.0 和 6.0：Jakarta EE 时代（2020-2022）

2021 年的 Servlet 5.0（JSR 400）和 2022 年的 Servlet 6.0（JSR 421）最显著的变化是**命名空间从 `javax.*` 迁移到 `jakarta.*`**。

这一变化的根源是 2017 年 Oracle 将 Java EE 移交给 Eclipse 基金会管理。由于 "Java" 商标归 Oracle 所有，Eclipse 基金会无法继续在 `javax` 命名空间下演化这些 API。于是采用了印尼首都**雅加达（Jakarta）** 作为新名称，API 包名从 `javax.servlet` 变为 `jakarta.servlet`。

迁移带来的实际影响是：Spring Boot 3.0+ 将所有依赖从 `javax` 改为 `jakarta`，使用 Spring Boot 2.x 的项目如果想升级到 3.0，需要进行全链路的命名空间替换（通常是 IDE 的批量重构就能处理，但涉及第三方库的兼容性检查）。

Servlet 6.0 同时引入了 `jakarta.servlet.http.HttpServletRequest.isUserInRole()` 的改进，以及对 Jakarta Naming and Directory Interface（JNDI）的更新支持。

## Filter 拦截器链：请求处理的管道模型

除了 Servlet，Filter 是 Servlet 规范中最有影响力的组件。Filter 链（FilterChain）采用**责任链模式**，多个 Filter 按配置顺序串联，每个 Filter 可以选择：
- 处理请求后调用 `chain.doFilter(request, response)` 将控制权传递给下一个 Filter；
- 或直接返回响应，中断链条。

一个经典的字符编码 Filter 看起来像这样：

```java
@WebFilter(urlPatterns = "/*")
public class EncodingFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        req.setCharacterEncoding("UTF-8");
        chain.doFilter(req, res);  // 传递给下一个 Filter 或 Servlet
    }
}
```

Filter 在 Spring Security、Spring MVC 的 Interceptor 机制中都有对应的设计，但 Spring 的拦截器只作用于 Spring 容器管理的 Bean，而 Filter 运行在 Servlet 容器层面，对所有请求都生效，包括静态资源。

## 为什么现代框架依然是 Servlet

Spring MVC 的核心是一个名为 `DispatcherServlet` 的前端控制器（Front Controller）——它拦截所有匹配 `/` 的请求，然后根据 URL 找到对应的 Controller 方法进行处理。从请求处理流程看，这与直接写一个 Servlet 处理请求并无本质区别，只是 Spring 在之上构建了参数绑定、视图解析、内容协商、异常处理等丰富的抽象层。

**理解 Servlet，就理解了 Spring MVC 底层在做什么。** 当你配置 `DispatcherServlet` 的 URL 映射、调试 Spring Security Filter 链的顺序，或者排查请求为什么没有到达 Controller 时，对 Servlet 和 Filter 生命周期的理解就是破局的关键。

## 参考来源

- [Java Servlet Specification - GitHub Pages](https://javaee.github.io/servlet-spec/)
- [Jakarta Servlet Specification](https://jakarta.ee/specifications/servlet/)
- [Baeldung: Java EE to Jakarta EE Migration](https://www.baeldung.com/java-jakarta-enterprise-edition-migration)
- [廖雪峰：Servlet 规范](https://liaoxuefeng.com/books/jerrymouse/servlet-spec/index.html)
