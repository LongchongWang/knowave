# MyBatis 快速上手：写给前端/Node.js 开发者

> 整理日期：2026-05-28
> 适合读者：熟悉 Node.js、有 SQL 基础、正在转型 Java 后端开发的工程师

---

## 先建立一个心智模型

在 Node.js 生态里，你大概用过这些东西：

- `pg` / `mysql2`：原生驱动，直接写 SQL，手动处理结果集
- `Knex.js`：SQL 构建器，帮你拼 SQL，但结果映射还是手动
- `Sequelize` / `Prisma`：ORM，对象优先，自动生成 SQL

**MyBatis 的定位大约是 Knex.js 和 Sequelize 之间**——你写 SQL（像 Knex），但它帮你做参数绑定和结果映射（像 ORM）。国内互联网公司（美团、阿里、京东）普遍选择 MyBatis，原因很简单：业务 SQL 复杂，DBA 要审查，需要精确控制查询性能。

对应关系速查：

| Node.js 生态 | Java/MyBatis 生态 |
|---|---|
| `pg` / `mysql2` 原生驱动 | JDBC（Java Database Connectivity） |
| `Knex.js` SQL 构建器 | MyBatis（半 ORM，SQL 优先） |
| `Sequelize` / `Prisma` ORM | JPA / Hibernate（全 ORM，对象优先） |
| 数据库连接池（`pg-pool`） | `SqlSessionFactory`（连接池管理者） |
| 一次数据库操作的 client | `SqlSession`（单次会话，非线程安全） |
| DAO / Repository 接口 | Mapper 接口（MyBatis 自动生成实现） |

---

## 为什么不直接用 JDBC？

原生 JDBC 写一个简单查询是这样的：

```java
// 原生 JDBC —— 大量样板代码，和 Node.js 的 pg 原生驱动类似
Connection conn = DriverManager.getConnection(url, user, password);
PreparedStatement ps = conn.prepareStatement("SELECT * FROM user WHERE id = ?");
ps.setInt(1, userId);
ResultSet rs = ps.executeQuery();
User user = new User();
while (rs.next()) {
    user.setId(rs.getInt("id"));
    user.setName(rs.getString("name"));
    user.setEmail(rs.getString("email"));
}
rs.close();
ps.close();
conn.close();
```

MyBatis 等价写法：

```java
// MyBatis —— 只需关注 SQL 本身
User user = userMapper.selectById(userId);
```

MyBatis 省掉了：连接管理、参数绑定、结果集遍历、对象映射、异常处理、资源关闭。官方说"省掉了将近 95% 的代码"，这个数字基本属实。

---

## 核心组件：四个对象

理解 MyBatis 只需要搞清楚四个对象，以及它们各自的生命周期。

**SqlSessionFactoryBuilder**：用完即丢。它的唯一职责是从配置文件构建 `SqlSessionFactory`，构建完就没用了。

**SqlSessionFactory**：应用级单例，伴随应用整个生命周期。类比 Node.js 里的数据库连接池（`pg.Pool`），全局只创建一次。

**SqlSession**：请求级，用完必须关闭，**绝对不能存在静态字段里**（非线程安全）。类比 Node.js 里从连接池取出的一个 `client`，用完要 `release()`。

**Mapper 接口**：你定义的 Java 接口，MyBatis 在运行时通过动态代理自动生成实现类。你只写接口，不写实现——这是 MyBatis 最"魔法"的地方。

```java
// 你只需要定义这个接口
public interface UserMapper {
    User selectById(int id);
    List<User> selectAll();
    int insert(User user);
    int update(User user);
    int deleteById(int id);
}
// MyBatis 自动帮你生成实现，不需要你写任何实现代码
```

---

## 第一个 MyBatis 项目（Spring Boot 版）

实际工作中你几乎不会单独用 MyBatis，而是通过 `mybatis-spring-boot-starter` 集成到 Spring Boot 里。

### 第一步：加依赖

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.mybatis.spring.boot</groupId>
    <artifactId>mybatis-spring-boot-starter</artifactId>
    <version>3.0.3</version>
</dependency>
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <scope>runtime</scope>
</dependency>
```

版本对应关系：Spring Boot 3.x 用 starter 3.x，Spring Boot 2.x 用 starter 2.x。

### 第二步：配置数据库连接

```yaml
# application.yml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb?useUnicode=true&characterEncoding=utf8
    username: root
    password: your_password
    driver-class-name: com.mysql.cj.jdbc.Driver

mybatis:
  mapper-locations: classpath:mapper/*.xml   # XML 文件位置
  type-aliases-package: com.example.model    # 实体类包，省去写全限定名
  configuration:
    map-underscore-to-camel-case: true        # 下划线转驼峰，强烈建议开启
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl  # 开发时打印 SQL
```

`map-underscore-to-camel-case: true` 这个配置非常重要——它让数据库的 `user_name` 字段自动映射到 Java 的 `userName` 属性，省去大量手动映射。

### 第三步：定义实体类

```java
// User.java
public class User {
    private Integer id;
    private String username;
    private String email;
    private LocalDateTime createdAt;  // 对应数据库 created_at（开启驼峰映射后自动对应）

    // getter/setter 省略，实际项目用 Lombok 的 @Data 注解自动生成
}
```

### 第四步：定义 Mapper 接口

```java
// UserMapper.java
@Mapper  // 告诉 Spring Boot 这是一个 MyBatis Mapper
public interface UserMapper {
    User selectById(int id);
    List<User> selectAll();
    int insert(User user);
    int update(User user);
    int deleteById(int id);
}
```

`@Mapper` 注解让 Spring Boot 自动扫描并注册这个接口。也可以在启动类上加 `@MapperScan("com.example.mapper")` 批量扫描，就不用每个接口都加 `@Mapper` 了。

### 第五步：写 Mapper XML

在 `src/main/resources/mapper/` 目录下创建 `UserMapper.xml`：

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper
  PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "https://mybatis.org/dtd/mybatis-3-mapper.dtd">

<!-- namespace 必须与 Mapper 接口的全限定类名完全一致 -->
<mapper namespace="com.example.mapper.UserMapper">

    <!-- 查询单个 -->
    <select id="selectById" parameterType="int" resultType="User">
        SELECT * FROM user WHERE id = #{id}
    </select>

    <!-- 查询列表 -->
    <select id="selectAll" resultType="User">
        SELECT * FROM user
    </select>

    <!-- 插入，useGeneratedKeys 让 MyBatis 把自增主键回填到 user.id -->
    <insert id="insert" parameterType="User" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO user (username, email) VALUES (#{username}, #{email})
    </insert>

    <!-- 更新 -->
    <update id="update" parameterType="User">
        UPDATE user SET username=#{username}, email=#{email} WHERE id=#{id}
    </update>

    <!-- 删除 -->
    <delete id="deleteById" parameterType="int">
        DELETE FROM user WHERE id = #{id}
    </delete>

</mapper>
```

### 第六步：在 Service 里使用

```java
@Service
public class UserService {

    @Autowired
    private UserMapper userMapper;  // Spring 自动注入，不需要手动创建

    public User getUser(int id) {
        return userMapper.selectById(id);
    }

    public void createUser(User user) {
        userMapper.insert(user);
        // 插入后 user.getId() 已经有值了（自增主键回填）
    }
}
```

这就是完整的 MyBatis + Spring Boot 基础用法。整个流程和 Node.js 里用 TypeORM 或 Prisma 的感觉很像：定义模型、定义操作接口、在 Service 里注入使用。

---

## 参数传递：`#{}` vs `${}`

这是 MyBatis 最重要的安全知识点，必须搞清楚。

`#{}` 是预处理参数，等价于 JDBC 的 `PreparedStatement` 的 `?` 占位符，**防 SQL 注入**，99% 的场景用这个。

`${}` 是字符串直接替换，**有 SQL 注入风险**，只用于动态表名、列名等无法用预处理的场景，且值必须来自可信来源。

```xml
<!-- 正确：值参数用 #{} -->
SELECT * FROM user WHERE id = #{id}
-- 实际执行：SELECT * FROM user WHERE id = ?（参数化查询）

<!-- 危险：值参数用 ${} 会有注入风险 -->
SELECT * FROM user WHERE id = ${id}
-- 实际执行：SELECT * FROM user WHERE id = 1（字符串拼接）

<!-- 合理：动态表名用 ${} -->
SELECT * FROM ${tableName} ORDER BY ${columnName}
```

多参数传递时，推荐用 `@Param` 注解明确命名：

```java
// Mapper 接口
User findByNameAndAge(@Param("name") String name, @Param("age") int age);

// 对应 XML
// SELECT * FROM user WHERE username = #{name} AND age = #{age}
```

---

## 结果映射：resultType vs resultMap

开启 `map-underscore-to-camel-case` 后，大多数简单场景直接用 `resultType` 就够了：

```xml
<select id="selectById" resultType="User">
    SELECT * FROM user WHERE id = #{id}
</select>
```

当列名和属性名无法自动对应，或者需要映射关联对象时，用 `resultMap`：

```xml
<resultMap id="userResultMap" type="User">
    <id property="id" column="user_id"/>           <!-- 主键用 id 标签 -->
    <result property="userName" column="user_name"/>
    <result property="createdAt" column="created_at"/>
</resultMap>

<select id="selectById" resultMap="userResultMap">
    SELECT user_id, user_name, created_at FROM user WHERE user_id = #{id}
</select>
```

---

## 注解方式：简单 CRUD 的快捷写法

对于简单的 CRUD，可以不写 XML，直接在 Mapper 接口上用注解：

```java
public interface UserMapper {

    @Select("SELECT * FROM user WHERE id = #{id}")
    User selectById(int id);

    @Insert("INSERT INTO user(username, email) VALUES(#{username}, #{email})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(User user);

    @Update("UPDATE user SET username=#{username} WHERE id=#{id}")
    int update(User user);

    @Delete("DELETE FROM user WHERE id = #{id}")
    int deleteById(int id);
}
```

注解方式代码更紧凑，适合简单 CRUD；XML 方式 SQL 与代码分离，适合复杂查询和团队协作（DBA 可以直接审查 XML 文件）。两种方式可以在同一个 Mapper 里混用。

---

## 事务处理

Spring Boot 集成后，事务管理非常简单，加 `@Transactional` 注解即可：

```java
@Service
public class OrderService {

    @Autowired
    private OrderMapper orderMapper;

    @Autowired
    private StockMapper stockMapper;

    @Transactional  // 方法内所有数据库操作在同一个事务里
    public void createOrder(Order order) {
        orderMapper.insert(order);
        stockMapper.decreaseStock(order.getProductId(), order.getQuantity());
        // 如果任何一步抛出异常，整个事务自动回滚
    }
}
```

这和 Node.js 里手动 `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` 相比，简洁很多。

---

## 常见坑

**坑一：SqlSession 不是线程安全的**。在 Spring Boot 集成中，框架帮你管理 SqlSession 的生命周期，不需要手动处理。但如果你在非 Spring 环境下使用 MyBatis，记住每个线程必须有自己的 SqlSession，不能共享。

**坑二：namespace 写错**。XML 文件的 `namespace` 必须和 Mapper 接口的全限定类名完全一致（包括包名），否则 MyBatis 找不到对应关系，会报 `Invalid bound statement` 错误。

**坑三：XML 文件位置**。`application.yml` 里配置的 `mapper-locations: classpath:mapper/*.xml` 对应的是 `src/main/resources/mapper/` 目录，不是 `src/main/java/` 目录。

**坑四：忘记开启驼峰映射**。数据库字段 `created_at` 和 Java 属性 `createdAt` 默认不会自动对应，需要在配置里加 `map-underscore-to-camel-case: true`，或者手动写 `resultMap`。

**坑五：`${}` 注入风险**。永远不要把用户输入直接放进 `${}` 里，只用 `#{}` 传递用户输入的值。

---

## 参考资料

- [MyBatis 官方文档（中文）](https://mybatis.org/mybatis-3/zh_CN/index.html)
- [mybatis-spring-boot-starter GitHub](https://github.com/mybatis/spring-boot-starter)
