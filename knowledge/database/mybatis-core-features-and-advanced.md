# MyBatis 核心功能与高阶特性

> 整理日期：2026-05-28
> 适合读者：已完成 MyBatis 基础上手，想深入理解核心机制和高阶用法的工程师

---

## 动态 SQL：MyBatis 最强大的特性

动态 SQL 解决了"根据条件拼接 SQL"这个在任何语言里都令人头疼的问题。在 Node.js 里你可能写过这样的代码：

```javascript
// Node.js 手动拼 SQL，容易出错
let sql = 'SELECT * FROM user WHERE 1=1';
const params = [];
if (name) { sql += ' AND name = ?'; params.push(name); }
if (age) { sql += ' AND age = ?'; params.push(age); }
```

MyBatis 用 XML 标签优雅地解决了这个问题。

### if：条件判断

```xml
<select id="findUser" resultType="User">
    SELECT * FROM user
    WHERE state = 'ACTIVE'
    <if test="title != null">
        AND title LIKE #{title}
    </if>
    <if test="age != null and age > 0">
        AND age = #{age}
    </if>
</select>
```

`test` 属性里写的是 OGNL 表达式，支持 `!=`、`==`、`and`、`or`、`!`，以及访问对象属性（`author.name != null`）。

### where：智能处理 WHERE 关键字

上面的写法有个问题：如果两个 `if` 都不满足，SQL 变成 `WHERE state = 'ACTIVE'`，没问题；但如果第一个条件不存在，只有第二个 `if` 满足，SQL 会变成 `WHERE AND age = ?`，语法错误。

`<where>` 标签解决了这个问题：只有子元素有内容时才插入 `WHERE`，并自动去掉开头多余的 `AND` 或 `OR`：

```xml
<select id="findUser" resultType="User">
    SELECT * FROM user
    <where>
        <if test="state != null">state = #{state}</if>
        <if test="title != null">AND title LIKE #{title}</if>
        <if test="age != null">AND age = #{age}</if>
    </where>
</select>
```

### set：动态 UPDATE

类似 `<where>`，`<set>` 标签用于动态 UPDATE，自动去掉末尾多余的逗号：

```xml
<update id="updateUser">
    UPDATE user
    <set>
        <if test="username != null">username=#{username},</if>
        <if test="email != null">email=#{email},</if>
        <if test="bio != null">bio=#{bio}</if>
    </set>
    WHERE id=#{id}
</update>
```

这个"只更新非空字段"的模式在实际业务中非常常见，比手写 `SET username=IFNULL(?, username)` 清晰得多。

### choose / when / otherwise：switch 语句

```xml
<select id="findBlog" resultType="Blog">
    SELECT * FROM blog WHERE state = 'ACTIVE'
    <choose>
        <when test="title != null">
            AND title LIKE #{title}
        </when>
        <when test="author != null">
            AND author_name LIKE #{author.name}
        </when>
        <otherwise>
            AND featured = 1
        </otherwise>
    </choose>
</select>
```

### foreach：IN 查询和批量操作

```xml
<!-- IN 查询 -->
<select id="selectByIds" resultType="User">
    SELECT * FROM user WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</select>

<!-- 批量插入（一条 SQL 插入多行，性能远好于循环单条插入） -->
<insert id="batchInsert">
    INSERT INTO user (username, email) VALUES
    <foreach collection="users" item="user" separator=",">
        (#{user.username}, #{user.email})
    </foreach>
</insert>
```

对应 Mapper 接口：

```java
List<User> selectByIds(@Param("ids") List<Integer> ids);
int batchInsert(@Param("users") List<User> users);
```

### trim：万能的前缀/后缀处理

`<where>` 和 `<set>` 本质上是 `<trim>` 的语法糖：

```xml
<!-- 等价于 <where> -->
<trim prefix="WHERE" prefixOverrides="AND |OR ">
    ...
</trim>

<!-- 等价于 <set> -->
<trim prefix="SET" suffixOverrides=",">
    ...
</trim>
```

`<trim>` 更灵活，可以处理任意前缀/后缀的清理需求。

### sql 片段复用

```xml
<!-- 定义可复用的 SQL 片段 -->
<sql id="userColumns">id, username, email, created_at</sql>

<!-- 在其他语句中引用 -->
<select id="selectAll" resultType="User">
    SELECT <include refid="userColumns"/> FROM user
</select>
```

---

## 结果映射进阶：关联查询

### 一对一关联（association）

场景：每个 `User` 有一个 `Address`。

```xml
<resultMap id="userWithAddressMap" type="User">
    <id property="id" column="user_id"/>
    <result property="username" column="username"/>
    <!-- 嵌套结果映射：一次 JOIN 查询，MyBatis 自动拆分结果 -->
    <association property="address" javaType="Address">
        <id property="id" column="addr_id"/>
        <result property="city" column="city"/>
        <result property="street" column="street"/>
    </association>
</resultMap>

<select id="selectUserWithAddress" resultMap="userWithAddressMap">
    SELECT u.id AS user_id, u.username,
           a.id AS addr_id, a.city, a.street
    FROM user u
    LEFT JOIN address a ON u.address_id = a.id
    WHERE u.id = #{id}
</select>
```

### 一对多关联（collection）

场景：每个 `User` 有多个 `Order`。

```xml
<resultMap id="userWithOrdersMap" type="User">
    <id property="id" column="user_id"/>
    <result property="username" column="username"/>
    <!-- collection：一对多，ofType 指定集合元素类型 -->
    <collection property="orders" ofType="Order">
        <id property="id" column="order_id"/>
        <result property="amount" column="amount"/>
        <result property="status" column="status"/>
    </collection>
</resultMap>

<select id="selectUserWithOrders" resultMap="userWithOrdersMap">
    SELECT u.id AS user_id, u.username,
           o.id AS order_id, o.amount, o.status
    FROM user u
    LEFT JOIN orders o ON o.user_id = u.id
    WHERE u.id = #{id}
</select>
```

MyBatis 会自动把多行结果（同一个 user_id 对应多个 order）合并成一个 `User` 对象，其 `orders` 属性是一个 `List<Order>`。

### 延迟加载版（嵌套 select）

上面的方式是"一次 JOIN 查全部"，另一种方式是"先查 user，需要时再查 orders"（懒加载）：

```xml
<resultMap id="userLazyMap" type="User">
    <id property="id" column="id"/>
    <collection property="orders" ofType="Order"
                select="com.example.mapper.OrderMapper.selectByUserId"
                column="id"
                fetchType="lazy"/>
</resultMap>
```

`fetchType="lazy"` 表示只有当你第一次访问 `user.getOrders()` 时，才会触发第二条 SQL 查询。这是通过 CGLIB 动态代理实现的——MyBatis 返回的 `User` 对象实际上是一个代理对象。

**选择建议**：如果你确定每次都需要关联数据，用 JOIN 一次查完（性能更好）；如果关联数据只在某些场景下需要，用懒加载（减少不必要的查询）。

---

## 缓存机制

### 一级缓存（本地缓存）

一级缓存是 SqlSession 级别的，默认自动开启，无需配置。同一个 SqlSession 内，相同的查询语句+参数，第二次直接从内存 HashMap 返回，不访问数据库：

```java
try (SqlSession session = sqlSessionFactory.openSession()) {
    User u1 = session.selectOne("selectById", 1);  // 查数据库
    User u2 = session.selectOne("selectById", 1);  // 直接返回缓存
    System.out.println(u1 == u2);  // true，同一个对象引用
}
```

一级缓存在以下情况失效：执行了 INSERT/UPDATE/DELETE、调用 `session.clearCache()`、SqlSession 关闭。

**重要提示**：在 Spring Boot 集成中，每个方法调用默认使用独立的 SqlSession（除非在同一个 `@Transactional` 事务中），所以一级缓存在 Spring 环境下实际上几乎不起作用。

### 二级缓存（全局缓存）

二级缓存是 Mapper namespace 级别的，跨 SqlSession 共享，需要显式开启：

```xml
<!-- mybatis-config.xml 或 application.yml 中开启全局开关 -->
<settings>
    <setting name="cacheEnabled" value="true"/>
</settings>

<!-- 在具体的 Mapper XML 中声明使用缓存 -->
<cache
    eviction="LRU"          <!-- 淘汰策略：LRU/FIFO/SOFT/WEAK -->
    flushInterval="60000"   <!-- 60秒刷新一次 -->
    size="512"              <!-- 最多缓存 512 个对象 -->
    readOnly="true"/>       <!-- 只读模式，性能更好 -->
```

使用二级缓存时，实体类需要实现 `Serializable` 接口（因为需要序列化存储）。

**实践建议**：二级缓存在分布式环境下容易产生数据不一致问题（多台机器各自有缓存，数据更新后其他机器的缓存不会自动失效）。生产环境通常用 Redis 等外部缓存替代，而不是 MyBatis 内置的二级缓存。

---

## 插件（Interceptor）机制

MyBatis 的插件机制允许你拦截四个核心对象的方法调用，实现 AOP 式的横切逻辑。这是 MyBatis 生态中分页、监控、多租户等功能的实现基础。

可以拦截的四个对象：

- `Executor`：执行器，负责执行 SQL（`update`、`query` 等）
- `ParameterHandler`：参数处理器，负责设置 SQL 参数
- `ResultSetHandler`：结果集处理器，负责处理查询结果
- `StatementHandler`：语句处理器，负责创建 Statement

### 自定义插件示例：SQL 执行时间监控

```java
@Intercepts({
    @Signature(
        type = Executor.class,
        method = "query",
        args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class}
    )
})
public class SqlTimingInterceptor implements Interceptor {

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = invocation.proceed();  // 执行原方法
        long elapsed = System.currentTimeMillis() - start;

        MappedStatement ms = (MappedStatement) invocation.getArgs()[0];
        if (elapsed > 1000) {
            // 慢 SQL 告警
            log.warn("慢 SQL 告警 [{}] 耗时: {}ms", ms.getId(), elapsed);
        }

        return result;
    }
}
```

注册插件：

```xml
<!-- mybatis-config.xml -->
<plugins>
    <plugin interceptor="com.example.plugin.SqlTimingInterceptor"/>
</plugins>
```

### 常用生态插件

**PageHelper**：最流行的 MyBatis 分页插件，通过拦截 `Executor.query` 自动在 SQL 后追加 `LIMIT` 子句：

```java
// 使用 PageHelper，只需在查询前调用 startPage
PageHelper.startPage(pageNum, pageSize);
List<User> users = userMapper.selectAll();
PageInfo<User> pageInfo = new PageInfo<>(users);
// pageInfo.getTotal() 总记录数
// pageInfo.getList() 当前页数据
```

**MyBatis-Plus**：在 MyBatis 基础上提供了大量增强功能，是目前国内最流行的 MyBatis 增强框架，下一节详细介绍。

---

## MyBatis-Plus：生产环境的标配

MyBatis-Plus（简称 MP）是 MyBatis 的增强工具，在不改变 MyBatis 任何特性的基础上，提供了大量开箱即用的功能。

### 核心功能

**内置 CRUD**：继承 `BaseMapper<T>` 接口，自动获得 20+ 个常用方法，不需要写任何 XML：

```java
@Mapper
public interface UserMapper extends BaseMapper<User> {
    // 不需要写任何方法，BaseMapper 已经提供了：
    // selectById, selectList, selectPage, insert, updateById, deleteById 等
}
```

```java
// 直接使用，无需写 SQL
User user = userMapper.selectById(1);
List<User> users = userMapper.selectList(null);  // 查全部
int count = userMapper.deleteById(1);
```

**条件构造器（Wrapper）**：类型安全的条件构造，类似 Knex.js 的链式调用：

```java
// QueryWrapper：字符串方式
QueryWrapper<User> wrapper = new QueryWrapper<>();
wrapper.eq("username", "张三")
       .gt("age", 18)
       .orderByDesc("created_at");
List<User> users = userMapper.selectList(wrapper);

// LambdaQueryWrapper：Lambda 方式，避免字符串硬编码（推荐）
LambdaQueryWrapper<User> lambdaWrapper = new LambdaQueryWrapper<>();
lambdaWrapper.eq(User::getUsername, "张三")
             .gt(User::getAge, 18)
             .orderByDesc(User::getCreatedAt);
List<User> users = userMapper.selectList(lambdaWrapper);
```

**分页**：内置分页插件，比 PageHelper 更原生：

```java
// 配置分页插件（Spring Boot 中）
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
    return interceptor;
}

// 使用分页
Page<User> page = new Page<>(1, 10);  // 第1页，每页10条
Page<User> result = userMapper.selectPage(page, null);
result.getRecords();  // 当前页数据
result.getTotal();    // 总记录数
```

**自动填充**：自动填充 `created_at`、`updated_at` 等字段：

```java
@Component
public class MyMetaObjectHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        this.strictInsertFill(metaObject, "createdAt", LocalDateTime.class, LocalDateTime.now());
        this.strictInsertFill(metaObject, "updatedAt", LocalDateTime.class, LocalDateTime.now());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        this.strictUpdateFill(metaObject, "updatedAt", LocalDateTime.class, LocalDateTime.now());
    }
}
```

实体类上标注需要自动填充的字段：

```java
@TableField(fill = FieldFill.INSERT)
private LocalDateTime createdAt;

@TableField(fill = FieldFill.INSERT_UPDATE)
private LocalDateTime updatedAt;
```

**逻辑删除**：软删除，查询时自动过滤已删除数据：

```java
// 实体类
@TableLogic
private Integer deleted;  // 0=未删除，1=已删除

// 调用 deleteById 时，实际执行 UPDATE user SET deleted=1 WHERE id=?
// 查询时自动加上 WHERE deleted=0
```

---

## 批量操作的正确姿势

批量操作有两种方式，性能差异很大。

**方式一：foreach 批量 SQL（推荐）**

一条 SQL 插入多行，性能最好：

```xml
<insert id="batchInsert">
    INSERT INTO user (username, email) VALUES
    <foreach collection="users" item="user" separator=",">
        (#{user.username}, #{user.email})
    </foreach>
</insert>
```

注意：MySQL 单条 SQL 有大小限制（默认 `max_allowed_packet` = 64MB），数据量很大时需要分批。

**方式二：BATCH 执行器**

适合需要获取每条记录自增主键的场景：

```java
try (SqlSession session = sqlSessionFactory.openSession(ExecutorType.BATCH)) {
    UserMapper mapper = session.getMapper(UserMapper.class);
    for (User user : users) {
        mapper.insert(user);
    }
    session.commit();
    session.flushStatements();
}
```

BATCH 执行器会把多条 SQL 合并成一次网络请求发送给数据库，减少网络往返次数。

---

## 多数据源

实际项目中经常需要连接多个数据库（主库/从库，或不同业务库）。Spring Boot + MyBatis 的多数据源配置：

```java
// 主数据源配置
@Configuration
@MapperScan(basePackages = "com.example.mapper.primary", sqlSessionFactoryRef = "primarySqlSessionFactory")
public class PrimaryDataSourceConfig {

    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource.primary")
    public DataSource primaryDataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean
    @Primary
    public SqlSessionFactory primarySqlSessionFactory(@Qualifier("primaryDataSource") DataSource dataSource) throws Exception {
        SqlSessionFactoryBean factory = new SqlSessionFactoryBean();
        factory.setDataSource(dataSource);
        factory.setMapperLocations(new PathMatchingResourcePatternResolver()
            .getResources("classpath:mapper/primary/*.xml"));
        return factory.getObject();
    }
}
```

实际项目中更推荐使用 `dynamic-datasource-spring-boot-starter`（苞米豆出品），通过 `@DS("slave")` 注解切换数据源，比手动配置简洁很多。

---

## 常见高阶场景

### 枚举类型映射

数据库存数字，Java 用枚举，MyBatis-Plus 可以自动转换：

```java
public enum StatusEnum implements IEnum<Integer> {
    ACTIVE(1, "激活"),
    INACTIVE(0, "未激活");

    private final Integer value;
    private final String desc;

    @Override
    public Integer getValue() { return value; }
}

// 实体类
@TableField
private StatusEnum status;  // 自动与数据库的 0/1 互转
```

### 自定义 TypeHandler

处理特殊类型（如 JSON 字段）：

```java
@MappedTypes(List.class)
@MappedJdbcTypes(JdbcType.VARCHAR)
public class JsonListTypeHandler extends BaseTypeHandler<List<String>> {

    private static final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, List<String> parameter, JdbcType jdbcType) throws SQLException {
        ps.setString(i, objectMapper.writeValueAsString(parameter));
    }

    @Override
    public List<String> getNullableResult(ResultSet rs, String columnName) throws SQLException {
        String json = rs.getString(columnName);
        return json == null ? null : objectMapper.readValue(json, new TypeReference<>() {});
    }
    // ... 其他方法
}
```

### 拦截器实现多租户

通过插件自动在所有 SQL 中追加租户条件：

```java
@Intercepts({@Signature(type = StatementHandler.class, method = "prepare", args = {Connection.class, Integer.class})})
public class TenantInterceptor implements Interceptor {

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        StatementHandler handler = (StatementHandler) invocation.getTarget();
        BoundSql boundSql = handler.getBoundSql();
        String sql = boundSql.getSql();

        // 在 SQL 中追加租户条件
        String tenantId = TenantContext.getCurrentTenantId();
        String newSql = sql + " AND tenant_id = '" + tenantId + "'";

        // 通过反射修改 SQL
        Field field = BoundSql.class.getDeclaredField("sql");
        field.setAccessible(true);
        field.set(boundSql, newSql);

        return invocation.proceed();
    }
}
```

实际项目中推荐使用 MyBatis-Plus 内置的 `TenantLineInnerInterceptor`，更安全、更完善。

---

## MyBatis vs MyBatis-Plus vs JPA 选型建议

| 场景 | 推荐方案 |
|---|---|
| 复杂业务 SQL、报表查询、遗留数据库 | MyBatis（手写 SQL，精确控制） |
| 标准 CRUD 为主，偶有复杂查询 | MyBatis-Plus（内置 CRUD + 条件构造器） |
| 领域模型驱动，数据库无关 | JPA/Hibernate |
| 国内互联网公司标准选择 | MyBatis-Plus（事实标准） |

国内互联网公司的主流选择是 MyBatis-Plus，它在 MyBatis 的基础上提供了足够的便利性，同时保留了对 SQL 的完全控制权。

---

## 调试技巧

**打印完整 SQL**：在 `application.yml` 中配置：

```yaml
mybatis:
  configuration:
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl
```

或者针对特定 Mapper 配置日志级别：

```yaml
logging:
  level:
    com.example.mapper: debug
```

**使用 p6spy**：可以打印带参数值的完整 SQL（而不是带 `?` 的预处理 SQL），方便调试：

```xml
<dependency>
    <groupId>p6spy</groupId>
    <artifactId>p6spy</artifactId>
    <version>3.9.1</version>
</dependency>
```

---

## 参考资料

- [MyBatis 官方文档（中文）](https://mybatis.org/mybatis-3/zh_CN/index.html)
- [MyBatis-Plus 官方文档](https://baomidou.com/)
- [PageHelper 官方文档](https://pagehelper.github.io/)
