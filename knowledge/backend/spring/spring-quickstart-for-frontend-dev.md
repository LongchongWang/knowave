# Spring 快速上手：写给前端/Node.js 开发者

> 整理日期：2026-05-29  
> 面向读者：熟悉 Node.js / Express，正在转型 Java 后端开发

---

## 先建立一个整体认知

在动手写代码之前，先把 Spring 生态的层次关系搞清楚，否则很容易在一堆名词里迷失。

```
Spring Framework（地基）
    └── Spring Boot（脚手架）
            ├── Spring MVC（Web 层，处理 HTTP）
            ├── Spring Data（数据访问层）
            ├── Spring Security（认证与授权）
            └── Spring Cloud（微服务工具集）
```

先说一个容易混淆的点：Java 的运行时是 **JVM**（Java Virtual Machine），负责执行字节码、管理内存、垃圾回收，这才和 Node.js runtime 是同一个层次的概念。Spring Framework 不是运行时，它是跑在 JVM 上的**应用框架**。

**Spring Framework** 是整个生态的核心应用框架，类比 Express.js——但比 Express 丰富得多，因为它还提供了 Express 没有的几个核心能力：

- **IoC 容器（Inversion of Control）**：负责创建和管理应用中所有的对象（称为 Bean）。你不需要手动 `new` 对象，框架帮你创建好，并自动把依赖注入进来。类比一个全局的"对象工厂"，你只需要声明"我需要什么"，它负责"给你什么"。
- **AOP（Aspect-Oriented Programming，面向切面编程）**：允许你把日志、事务、权限检查等"横切关注点"从业务代码中剥离出来，统一管理。类比 Express 的中间件，但更强大——它可以精确拦截特定类的特定方法，而不只是 HTTP 请求。
- **事务管理（Transaction Management）**：统一管理数据库事务，让你用一个 `@Transactional` 注解就能保证一组数据库操作要么全部成功、要么全部回滚，不需要手动写 `BEGIN / COMMIT / ROLLBACK`。
- **Spring MVC**：内置的 Web 框架，处理 HTTP 请求路由、参数绑定、响应序列化。这部分才是最直接对标 Express 路由系统的东西。
- **数据访问抽象**：统一封装 JDBC、ORM 等数据库操作，提供一致的异常体系和模板方法，让数据库操作更简洁。

**Spring Boot** 是在 Spring Framework 之上的"约定优于配置"封装层。它不提供新功能，而是通过自动配置、内嵌服务器、starter 依赖等机制，让你几乎零配置就能启动一个生产级应用。类比"Express + 完整项目脚手架 + 自动装配"，你只需要写业务代码。

实际开发中，你几乎总是在用 **Spring Boot**，它把其他所有东西都整合好了。

---

## 项目结构：和 Node.js 的对照

一个标准的 Spring Boot REST API 项目结构如下：

```
src/main/java/com/example/myapp/
├── MyApplication.java          # 启动类（类比 app.js）
├── controller/
│   └── UserController.java     # Web 层，处理 HTTP 请求（类比 routes/）
├── service/
│   └── UserService.java        # 业务逻辑层（类比 services/）
├── repository/
│   └── UserRepository.java     # 数据访问层（类比 models/）
├── entity/
│   └── User.java               # 数据库实体（类比 Sequelize Model）
├── dto/
│   ├── UserCreateDTO.java      # 请求体 DTO（类比 req.body 的类型定义）
│   └── UserResponseDTO.java    # 响应体 DTO
└── exception/
    └── GlobalExceptionHandler.java  # 全局异常处理（类比 Express error middleware）
```

Node.js 与 Spring Boot 的对照关系：

| Node.js (Express) | Spring Boot |
|---|---|
| `routes/` | `controller/` |
| `services/` | `service/` |
| `models/` (Sequelize) | `entity/` + `repository/` |
| `middleware/` | `aspect/` + `filter/` |
| `app.js` | `MyApplication.java` |
| `package.json` | `pom.xml` |
| `npm install` | `mvn install` |

---

## IoC 与依赖注入：Spring 最核心的思想

### 什么是 IoC（控制反转）

在传统编程中，对象自己负责创建它所依赖的对象（主动控制）；IoC 把这个控制权交给了框架容器（反转控制）。

```javascript
// Node.js 传统方式：Service 自己 new 依赖
class UserService {
  constructor() {
    this.db = new Database(); // 自己创建依赖
  }
}

// IoC 方式：依赖从外部注入
class UserService {
  constructor(db) {  // 依赖由外部传入
    this.db = db;
  }
}
// 由框架/容器负责创建 Database 实例并注入
```

Spring 的 IoC 容器（`ApplicationContext`）就是那个"外部"，它负责创建、管理所有对象（称为 **Bean**），并自动处理它们之间的依赖关系。

### 核心注解：@Component 家族

这四个注解在技术上几乎等价，都是告诉 Spring 容器"请管理这个类"，区别在于语义：

| 注解 | 语义层次 | 类比 Node.js |
|---|---|---|
| `@Component` | 通用组件 | 普通工具类 |
| `@Controller` / `@RestController` | Web 层，处理 HTTP | Express Router |
| `@Service` | 业务逻辑层 | Service 类 |
| `@Repository` | 数据访问层 | DAO/Model 层 |

```java
// 数据访问层
@Repository
public class UserRepository {
    // 操作数据库
}

// 业务逻辑层
@Service
public class UserService {
    @Autowired
    private UserRepository userRepository; // Spring 自动注入
    
    public User findById(Long id) {
        return userRepository.findById(id);
    }
}

// Web 层
@RestController
public class UserController {
    @Autowired
    private UserService userService; // Spring 自动注入
}
```

### 依赖注入的推荐方式：构造器注入

```java
@Service
public class UserService {
    private final UserRepository userRepository;
    
    // Spring 4.3+ 单构造器可省略 @Autowired
    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
}
```

构造器注入是推荐方式，因为依赖关系在编译期就确定了，便于单元测试。

---

## Spring Boot 的启动与配置

### 启动类

```java
@SpringBootApplication  // 这一个注解等于三个注解的组合
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

`@SpringBootApplication` 等价于 `@SpringBootConfiguration + @EnableAutoConfiguration + @ComponentScan`，它会自动扫描同包及子包下所有带 `@Component` 家族注解的类，注册为 Bean。

### application.yml 配置

```yaml
# application.yml（类比 .env 文件，但功能更强大）
server:
  port: 8080
  
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: root
    password: secret
  jpa:
    hibernate:
      ddl-auto: update  # 自动建表/更新表结构
    show-sql: true

# 自定义配置
app:
  jwt-secret: my-secret-key
  token-expiry: 86400
```

读取自定义配置：

```java
// 方式一：@Value 注解（简单场景）
@Component
public class JwtConfig {
    @Value("${app.jwt-secret}")
    private String jwtSecret;
    
    @Value("${app.token-expiry:3600}")  // 带默认值
    private int tokenExpiry;
}

// 方式二：@ConfigurationProperties（推荐，类型安全）
@Component
@ConfigurationProperties(prefix = "app")
public class AppConfig {
    private String jwtSecret;
    private int tokenExpiry;
    // getter/setter...
}
```

### Starter 依赖机制

Starter 是 Spring Boot 提供的"一键引入"依赖包，类比 npm 的 meta-package。引入一个 starter，就自动引入了该功能所需的所有依赖，并触发对应的自动配置。

```xml
<!-- pom.xml（类比 package.json） -->
<dependencies>
    <!-- Web 开发：包含 Spring MVC + 内嵌 Tomcat + Jackson JSON -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- JPA 数据库：包含 Hibernate + Spring Data JPA -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    
    <!-- 安全 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
</dependencies>
```

---

## Spring MVC：写 HTTP 接口

这是你最常用的部分，和 Express 路由非常相似。

```java
@RestController  // = @Controller + @ResponseBody，返回值自动序列化为 JSON
@RequestMapping("/api/users")  // 类比 router.use('/api/users', ...)
public class UserController {

    @Autowired
    private UserService userService;

    // GET /api/users
    @GetMapping
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    // GET /api/users/123
    @GetMapping("/{id}")
    public User getUserById(@PathVariable Long id) {  // 路径参数，类比 req.params.id
        return userService.findById(id);
    }

    // GET /api/users?page=1&size=10
    @GetMapping("/search")
    public List<User> searchUsers(
            @RequestParam String name,                    // 查询参数，类比 req.query.name
            @RequestParam(defaultValue = "0") int page,  // 带默认值
            @RequestParam(required = false) String email  // 可选参数
    ) {
        return userService.search(name, page, email);
    }

    // POST /api/users
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)  // 返回 201 状态码
    public User createUser(@RequestBody UserCreateDTO dto) {  // 请求体，类比 req.body
        return userService.create(dto);
    }

    // PUT /api/users/123
    @PutMapping("/{id}")
    public User updateUser(@PathVariable Long id, @RequestBody UserUpdateDTO dto) {
        return userService.update(id, dto);
    }

    // DELETE /api/users/123
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id) {
        userService.delete(id);
        return ResponseEntity.noContent().build();  // 返回 204
    }
}
```

### 全局异常处理

类比 Express 的 error middleware：

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleNotFound(ResourceNotFoundException ex) {
        return new ErrorResponse("NOT_FOUND", ex.getMessage());
    }

    @ExceptionHandler(ValidationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ErrorResponse handleValidation(ValidationException ex) {
        return new ErrorResponse("VALIDATION_ERROR", ex.getMessage());
    }
}
```

---

## Spring Data JPA：数据库操作

### 定义实体

```java
@Entity  // 标记为 JPA 实体，对应数据库表
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)  // 自增主键
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false)
    private String email;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    // 必须有无参构造器（JPA 规范要求）
    public User() {}
    
    // getter/setter...
}
```

### Repository 接口

Spring Data JPA 最强大的地方：通过方法名自动生成 SQL。

```java
// 继承 JpaRepository，自动获得 CRUD 方法
public interface UserRepository extends JpaRepository<User, Long> {

    // 方法名查询：Spring 自动解析方法名生成 SQL
    List<User> findByUsername(String username);
    
    Optional<User> findByEmail(String email);
    
    List<User> findByUsernameContaining(String keyword);  // LIKE %keyword%
    
    boolean existsByEmail(String email);

    // 自定义 JPQL 查询
    @Query("SELECT u FROM User u WHERE u.email = :email AND u.active = true")
    Optional<User> findActiveUserByEmail(@Param("email") String email);
}
```

方法名关键词速查：

| 关键词 | 示例 | 等价 SQL |
|---|---|---|
| `findBy` | `findByName` | `WHERE name = ?` |
| `And` | `findByNameAndAge` | `WHERE name = ? AND age = ?` |
| `Containing` | `findByNameContaining` | `WHERE name LIKE %?%` |
| `OrderBy` | `findByAgeOrderByNameDesc` | `ORDER BY name DESC` |
| `In` | `findByAgeIn` | `WHERE age IN (...)` |
| `IsNull` | `findByEmailIsNull` | `WHERE email IS NULL` |
| `True` | `findByActiveTrue` | `WHERE active = true` |

### Service 层使用

```java
@Service
@Transactional  // 类级别事务，所有方法默认在事务中执行
public class UserService {

    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    public User findById(Long id) {
        return userRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("用户不存在: " + id));
    }

    public User create(UserCreateDTO dto) {
        if (userRepository.existsByEmail(dto.getEmail())) {
            throw new DuplicateEmailException("邮箱已存在");
        }
        User user = new User();
        user.setUsername(dto.getUsername());
        user.setEmail(dto.getEmail());
        return userRepository.save(user);  // save() 自动处理 INSERT/UPDATE
    }
}
```

---

## 事务管理：@Transactional

```java
@Service
public class OrderService {

    @Transactional  // 默认：RuntimeException 时回滚
    public Order createOrder(OrderDTO dto) {
        Order order = orderRepository.save(new Order(dto));
        inventoryService.decreaseStock(dto.getProductId(), dto.getQuantity());
        // 如果这里抛出 RuntimeException，整个事务回滚
        return order;
    }

    @Transactional(readOnly = true)  // 只读事务，性能优化
    public List<Order> findUserOrders(Long userId) {
        return orderRepository.findByUserId(userId);
    }

    @Transactional(rollbackFor = Exception.class)  // 所有异常都回滚
    public void riskyOperation() throws Exception { ... }
}
```

**最重要的坑：** `@Transactional` 基于 AOP 代理实现，同一个类内部的方法调用（`this.methodA()`）不会触发事务，因为绕过了代理对象。

---

## 快速上手路径

**第一步：** 用 [Spring Initializr](https://start.spring.io/) 创建项目，选择 Web + JPA + H2（内存数据库），下载后用 IntelliJ IDEA 打开。

**第二步：** 跑通一个完整的 CRUD API，理解 Controller → Service → Repository 的分层调用链。

**第三步：** 深入理解 IoC/DI 原理，搞清楚 Bean 是什么、Spring 容器如何管理它们。

**第四步：** 按需学习 Spring Security（JWT 认证）、Spring Data（复杂查询）、Spring Cache（Redis 缓存）。

推荐资源：[Spring 官方 Guides](https://spring.io/guides)（每个 Guide 都是一个完整的小项目）、[Baeldung.com](https://www.baeldung.com/)（Spring 最权威的第三方教程网站）。

---

## 与 Node.js 最大的思维差异

**同步阻塞 vs 异步非阻塞：** Spring MVC 默认是同步阻塞模型（每个请求占用一个线程），而 Node.js 是单线程事件循环。Spring 也有响应式方案（Spring WebFlux），但学习曲线更陡。对于大多数业务场景，Spring MVC 的线程池模型已经足够。

**强类型 vs 动态类型：** Java 的强类型系统意味着你需要为请求体、响应体、数据库实体分别定义 DTO/Entity 类。这增加了代码量，但也带来了编译期检查和更好的 IDE 支持。

**注解驱动 vs 中间件链：** Spring 大量使用注解（`@Transactional`、`@Cacheable`、`@Secured` 等）来声明横切关注点，底层由 AOP 实现。Node.js 则通过中间件链（`app.use(middleware)`）来实现类似效果。
