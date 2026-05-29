# cut 命令完全指南：按列截取文本的利器

> 整理日期：2026-05-28

---

## 一、cut 是什么

`cut` 是 Unix/Linux 系统中一个专注于"按列截取文本"的命令行工具。它的设计哲学极其简单：给定一行文本，按照某种列的定义，把你想要的部分切出来，其余的丢掉。

与 `grep` 按行过滤不同，`cut` 是按列过滤。它不关心行的内容是否匹配某个模式，只关心每行的第几个字段、第几个字节、第几个字符。

基本语法如下：

```bash
cut [选项] [文件...]
```

如果不指定文件，`cut` 从标准输入读取，这使它非常适合在管道中使用。

---

## 二、三种截取模式

`cut` 提供三种截取模式，分别对应三个互斥的选项：

**`-b`（bytes）**：按字节位置截取。每个 ASCII 字符占 1 字节，但多字节字符（如中文 UTF-8 编码占 3 字节）会被截断，产生乱码。

**`-c`（characters）**：按字符位置截取。在支持多字节字符的实现中，`-c` 能正确处理 Unicode，不会截断一个字符的中间。

**`-f`（fields）**：按字段截取。字段由分隔符（delimiter）划分，默认分隔符是 Tab。这是日常使用中最常见的模式。

三种模式不能同时使用，必须选其一。

---

## 三、范围语法

无论是 `-b`、`-c` 还是 `-f`，都使用相同的范围语法来指定要截取的位置。编号从 **1** 开始（不是 0）。

| 语法 | 含义 |
|------|------|
| `N` | 第 N 个 |
| `N-M` | 第 N 到第 M 个（含两端） |
| `N-` | 第 N 个到行尾（含第 N 个） |
| `-M` | 从行首到第 M 个（含第 M 个） |
| `N,M,K` | 第 N、M、K 个（逗号分隔，可组合范围） |

几个例子：

```bash
# 取第 2 个字段
cut -f2

# 取第 2 到第 4 个字段
cut -f2-4

# 取第 2 个字段及之后所有字段
cut -f2-

# 取第 1 到第 3 个字段
cut -f-3

# 取第 1、3、5 个字段
cut -f1,3,5
```

---

## 四、按字段截取（最常用）

### 4.1 指定分隔符

`-d` 选项指定字段分隔符，只能是**单个字符**。默认分隔符是 Tab（`\t`）。

```bash
# 以冒号为分隔符，取第 1 个字段（用户名）
cut -d: -f1 /etc/passwd

# 以逗号为分隔符，取第 2 个字段（CSV 第二列）
echo "Alice,30,Engineer" | cut -d, -f2

# 以空格为分隔符，取第 3 个字段
echo "one two three four" | cut -d' ' -f3
```

### 4.2 `-f2` 与 `-f2-` 的关键区别

这是 `cut` 使用中最容易踩坑的地方，值得重点讲解。

假设有一个键值对格式的字符串：

```
TOKEN_VALUE=abc123
```

用 `-f2` 取第 2 个字段：

```bash
echo "TOKEN_VALUE=abc123" | cut -d= -f2
# 输出：abc123
```

看起来没问题。但如果值本身也包含等号呢？

```bash
echo "TOKEN_VALUE=a=b=c" | cut -d= -f2
# 输出：a
```

`-f2` 只取第 2 个字段，即两个等号之间的 `a`，后面的 `=b=c` 被丢弃了。

改用 `-f2-`（第 2 个字段及之后所有内容）：

```bash
echo "TOKEN_VALUE=a=b=c" | cut -d= -f2-
# 输出：a=b=c
```

这才是正确的结果。

**规律**：当你要提取"键值对中的值"，而值本身可能包含分隔符时，应该用 `-f2-` 而不是 `-f2`。这个场景在实际脚本中极为常见，比如从脚本输出中提取 token、从配置文件中提取 URL 等。

### 4.3 不包含分隔符的行

默认情况下，如果某行不包含分隔符，`cut -f` 会原样输出整行（因为整行就是第 1 个字段）。如果你只想要包含分隔符的行，可以加 `-s`（`--only-delimited`）选项：

```bash
# 只输出包含冒号的行
cut -d: -f1 -s /etc/passwd
```

---

## 五、按字节截取（-b）

`-b` 按字节位置截取，适合处理纯 ASCII 文本或固定宽度的二进制格式。

```bash
# 取每行的第 1 到第 8 个字节
cut -b1-8 /var/log/syslog

# 取第 10 个字节到行尾
cut -b10- access.log

# 取第 1、5、9 个字节
cut -b1,5,9 data.txt
```

对于多字节字符（如中文），`-b` 会按字节边界截断，可能产生乱码：

```bash
echo "你好世界" | cut -b1-3
# 输出：你（UTF-8 中每个汉字占 3 字节，恰好截到第一个字符）

echo "你好世界" | cut -b1-4
# 输出：乱码（截断了"好"字的 UTF-8 编码）
```

---

## 六、按字符截取（-c）

`-c` 按字符位置截取，在 GNU coreutils 的实现中，它能正确处理多字节字符（依赖 locale 设置）。

```bash
# 取每行的第 1 到第 5 个字符
cut -c1-5 file.txt

# 取第 3 个字符到行尾
cut -c3- file.txt
```

在处理包含中文的文本时，`-c` 比 `-b` 更安全：

```bash
# 确保 locale 支持 UTF-8
export LANG=en_US.UTF-8

echo "你好世界" | cut -c1-2
# 输出：你好（正确截取了前两个字符）
```

**注意**：macOS 的 BSD `cut` 实现中，`-c` 和 `-b` 的行为相同，都按字节处理，不能正确处理多字节字符。如果需要在 macOS 上按字符截取 Unicode 文本，应该使用 `awk` 或安装 GNU coreutils（`brew install coreutils`，命令为 `gcut`）。

---

## 七、`--complement` 选项：取补集

`--complement` 选项（GNU 扩展）让 `cut` 输出**除指定字段外**的所有内容，即取补集。

```bash
# 输出除第 2 个字段外的所有字段
echo "a:b:c:d:e" | cut -d: -f2 --complement
# 输出：a:c:d:e

# 输出除第 1 到第 3 个字段外的所有字段
echo "a:b:c:d:e" | cut -d: -f1-3 --complement
# 输出：d:e
```

**macOS 兼容性**：macOS 的 BSD `cut` 不支持 `--complement`，会报错。如果需要跨平台兼容，改用 `awk`：

```bash
# 等价于 cut -d: -f2 --complement
echo "a:b:c:d:e" | awk -F: 'BEGIN{OFS=":"} {$2=""; gsub(/::/, ":"); gsub(/^:|:$/, ""); print}'
```

---

## 八、`--output-delimiter` 选项：改变输出分隔符

默认情况下，`cut` 的输出分隔符与输入分隔符相同。`--output-delimiter` 选项（GNU 扩展）允许指定不同的输出分隔符。

```bash
# 输入以冒号分隔，输出以逗号分隔
echo "a:b:c:d" | cut -d: -f1,3 --output-delimiter=,
# 输出：a,c

# 输入以 Tab 分隔，输出以 | 分隔
cut -f1,3 --output-delimiter='|' data.tsv

# 将 CSV 的特定列转换为 TSV
cut -d, -f1,2,4 --output-delimiter=$'\t' data.csv
```

**macOS 兼容性**：macOS 的 BSD `cut` 不支持 `--output-delimiter`。

---

## 九、典型使用场景

### 9.1 从 `/etc/passwd` 提取用户名

`/etc/passwd` 文件以冒号分隔，第 1 个字段是用户名：

```bash
cut -d: -f1 /etc/passwd
```

提取用户名和 shell（第 1 和第 7 个字段）：

```bash
cut -d: -f1,7 /etc/passwd
```

### 9.2 提取键值对中的值

这是最常见的实际场景之一。假设脚本输出如下格式：

```
ACCESS_TOKEN=eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.signature
```

提取 token 值（注意 token 本身可能包含 `.` 但不含 `=`，所以 `-f2` 和 `-f2-` 结果相同；但如果值包含 `=`，必须用 `-f2-`）：

```bash
echo "ACCESS_TOKEN=eyJhbGciOiJSUzI1NiJ9..." | cut -d= -f2-
```

更安全的写法，始终用 `-f2-`，避免值中含 `=` 时截断：

```bash
# 从脚本输出中提取 token
TOKEN=$(some_script | grep "^TOKEN=" | cut -d= -f2-)
```

### 9.3 处理 CSV 数据

```bash
# 提取 CSV 第 1、3、5 列
cut -d, -f1,3,5 data.csv

# 提取 CSV 第 2 列到最后一列
cut -d, -f2- data.csv

# 跳过 CSV 头行，提取第 2 列
tail -n +2 data.csv | cut -d, -f2
```

### 9.4 从 PATH 环境变量提取各路径

PATH 以冒号分隔，可以用 `cut` 提取特定位置的路径：

```bash
# 提取 PATH 中的第 1 个路径
echo $PATH | cut -d: -f1

# 提取 PATH 中的第 2 到第 4 个路径
echo $PATH | cut -d: -f2-4
```

不过，如果要遍历所有路径，`tr` + `while read` 或 `IFS` 分割更合适。

### 9.5 截取固定宽度文本的特定列

某些日志文件或报表是固定宽度格式，可以用 `-c` 按字符位置截取：

```bash
# 假设日志格式：时间戳(20字符) + 空格 + 级别(5字符) + 空格 + 消息
# 提取时间戳（第 1-20 个字符）
cut -c1-20 app.log

# 提取级别（第 22-26 个字符）
cut -c22-26 app.log

# 提取消息（第 28 个字符到行尾）
cut -c28- app.log
```

### 9.6 结合 grep 过滤后再截取

```bash
# 从 /etc/passwd 中找到 bash 用户，提取用户名
grep "/bin/bash" /etc/passwd | cut -d: -f1

# 从日志中找到 ERROR 行，提取时间戳
grep "ERROR" app.log | cut -d' ' -f1

# 从 ps 输出中提取进程 ID
ps aux | grep nginx | cut -d' ' -f2
```

### 9.7 批量处理日志文件提取时间戳

```bash
# 假设日志格式：2026-05-28T10:30:00 INFO message...
# 提取所有日志的时间戳（第 1 个字段，以空格分隔）
cut -d' ' -f1 /var/log/app/*.log | sort | uniq -c | sort -rn | head -20
```

---

## 十、cut 的局限性

`cut` 的设计非常简单，这既是它的优点（快速、可预测），也是它的局限：

**不支持多字符分隔符**。如果分隔符是 `::` 或 `, `（逗号加空格），`cut` 无法处理：

```bash
# 这不会按 :: 分割，而是按单个 : 分割
echo "a::b::c" | cut -d:: -f2  # 错误！-d 只接受单个字符
```

**不支持正则表达式分隔符**。无法用 `\s+`（一个或多个空格）作为分隔符，这在处理对齐格式的文本时很常见。

**字段顺序不能重排**。`-f3,1` 不会把第 3 列放在第 1 列前面，输出顺序始终按字段编号从小到大：

```bash
echo "a:b:c" | cut -d: -f3,1
# 输出：a:c（不是 c:a）
```

**不能对字段做计算或条件判断**。`cut` 只是截取，不能做任何逻辑处理。

遇到这些限制时，应该换用 `awk`。

---

## 十一、cut 与 awk 的对比

`awk` 是 `cut` 的超集，几乎所有 `cut` 能做的事 `awk` 都能做，而且 `awk` 还能做更多。但 `cut` 在简单场景下更简洁、更快。

### 等价写法对比

| cut 写法 | awk 等价写法 |
|----------|-------------|
| `cut -d: -f1` | `awk -F: '{print $1}'` |
| `cut -d: -f1,3` | `awk -F: '{print $1, $3}'`（注意输出分隔符变成空格） |
| `cut -d: -f2-` | `awk -F: '{$1=""; sub(/^:/, ""); print}'` 或更简洁的写法 |
| `cut -c1-5` | `awk '{print substr($0, 1, 5)}'` |

### 何时用 cut

- 分隔符是单个字符
- 只需要提取固定字段，不需要重排
- 不需要条件判断或计算
- 追求简洁的命令行写法
- 性能敏感场景（`cut` 比 `awk` 快，因为更简单）

### 何时用 awk

- 分隔符是多字符或正则表达式（`awk -F'::'`、`awk -F'[[:space:]]+'`）
- 需要重排字段顺序（`awk '{print $3, $1}'`）
- 需要条件过滤（`awk '$2 > 100 {print $1}'`）
- 需要对字段做计算（`awk '{sum += $3} END {print sum}'`）
- 需要自定义输出格式（`awk '{printf "%-10s %5d\n", $1, $2}'`）

### 一个典型的选择场景

```bash
# 简单提取，用 cut 更简洁
cut -d: -f1 /etc/passwd

# 需要条件过滤，用 awk
awk -F: '$3 >= 1000 {print $1}' /etc/passwd

# 需要重排字段，用 awk
awk -F: '{print $3, $1}' /etc/passwd
```

---

## 十二、实战示例：从脚本输出中提取 token

这是一个完整的实战场景，展示为什么 `-f2-` 比 `-f2` 更安全。

假设有一个认证脚本，输出格式如下：

```
Authenticating...
ACCESS_TOKEN=Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIn0.sig
REFRESH_TOKEN=dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4=
Expires in: 3600 seconds
```

提取 `ACCESS_TOKEN` 的值：

```bash
# 方法一：grep + cut（推荐）
ACCESS_TOKEN=$(auth_script | grep "^ACCESS_TOKEN=" | cut -d= -f2-)

# 方法二：如果确定值中不含 =，可以用 -f2
ACCESS_TOKEN=$(auth_script | grep "^ACCESS_TOKEN=" | cut -d= -f2)
```

为什么推荐 `-f2-`？因为 Bearer token 的格式是 `Bearer <jwt>`，而 JWT 本身是 Base64 编码，不含 `=`（或只在末尾有填充 `=`）。但如果 token 格式变化，或者你处理的是其他类型的值（如 URL、Base64 编码的字符串），值中可能含有 `=`。养成用 `-f2-` 的习惯，可以避免这类隐患。

**完整脚本示例**：

```bash
#!/bin/bash

# 从认证脚本获取 token
AUTH_OUTPUT=$(./auth.sh 2>&1)

# 提取各个 token（使用 -f2- 确保值中的 = 不被截断）
ACCESS_TOKEN=$(echo "$AUTH_OUTPUT" | grep "^ACCESS_TOKEN=" | cut -d= -f2-)
REFRESH_TOKEN=$(echo "$AUTH_OUTPUT" | grep "^REFRESH_TOKEN=" | cut -d= -f2-)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Error: Failed to extract ACCESS_TOKEN" >&2
    exit 1
fi

echo "Got token: ${ACCESS_TOKEN:0:20}..."  # 只打印前 20 个字符
```

---

## 十三、macOS vs Linux 的差异

`cut` 有两个主要实现：

- **GNU coreutils 版本**：Linux 系统默认使用，功能更丰富
- **BSD 版本**：macOS 系统默认使用，功能较少

### 主要差异

| 特性 | GNU cut（Linux） | BSD cut（macOS） |
|------|-----------------|-----------------|
| `--complement` | 支持 | **不支持** |
| `--output-delimiter` | 支持 | **不支持** |
| `-c` 处理多字节字符 | 支持（依赖 locale） | 与 `-b` 相同，按字节处理 |
| 长选项（`--fields` 等） | 支持 | 部分支持 |

### 在 macOS 上使用 GNU cut

如果需要在 macOS 上使用 GNU cut 的完整功能，可以通过 Homebrew 安装：

```bash
brew install coreutils
```

安装后，GNU cut 的命令名为 `gcut`：

```bash
gcut --complement -d: -f2 /etc/passwd
```

如果想让 `cut` 直接指向 GNU 版本，可以将 `/opt/homebrew/opt/coreutils/libexec/gnubin` 加入 PATH（注意这会影响所有 coreutils 命令）：

```bash
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
```

### 编写跨平台脚本的建议

如果脚本需要同时在 macOS 和 Linux 上运行：

1. 只使用两者都支持的基础功能（`-d`、`-f`、`-b`、`-c`、`-s`）
2. 避免使用 `--complement` 和 `--output-delimiter`，改用 `awk` 实现等价功能
3. 避免用 `-c` 处理多字节字符，改用 `awk` 的 `substr`

---

## 十四、常见误区与注意事项

**误区一：认为 `-f3,1` 会先输出第 3 列再输出第 1 列**。`cut` 始终按字段编号从小到大输出，`-f3,1` 等价于 `-f1,3`。如果需要重排，用 `awk '{print $3, $1}'`。

**误区二：用 `-f2` 提取键值对的值**。如前所述，当值本身包含分隔符时，`-f2` 会截断。养成用 `-f2-` 的习惯。

**误区三：用 `-d` 指定多字符分隔符**。`-d` 只接受单个字符，`-d::` 不会按 `::` 分割，而是只取第一个字符 `:` 作为分隔符（GNU 版本会报错，BSD 版本行为未定义）。

**误区四：期望 cut 能处理引号包裹的 CSV 字段**。标准 CSV 中，字段值可以用引号包裹，且引号内可以包含逗号（如 `"Smith, John"`）。`cut` 不理解 CSV 引号规则，会错误地在引号内的逗号处分割。处理真正的 CSV 应该用 `awk`、Python 的 `csv` 模块，或专门的工具如 `csvkit`。

**误区五：在 macOS 上用 `-c` 处理中文**。macOS 的 BSD `cut` 中 `-c` 和 `-b` 行为相同，都按字节处理，无法正确截取中文字符。

---

## 十五、快速参考

```bash
# 按字段截取（最常用）
cut -d: -f1 file          # 以 : 分隔，取第 1 字段
cut -d, -f2-4 file        # 以 , 分隔，取第 2-4 字段
cut -d= -f2- file         # 以 = 分隔，取第 2 字段到行尾（安全提取值）
cut -f1,3,5 file          # 以 Tab 分隔，取第 1、3、5 字段

# 按字节截取
cut -b1-10 file           # 取第 1-10 字节
cut -b20- file            # 取第 20 字节到行尾

# 按字符截取
cut -c1-5 file            # 取第 1-5 个字符

# GNU 扩展（Linux 专用）
cut -d: -f2 --complement file          # 取除第 2 字段外的所有字段
cut -d: -f1,3 --output-delimiter=, file  # 输出分隔符改为逗号

# 常用组合
grep "pattern" file | cut -d: -f1     # 过滤后截取
cut -d: -f1 /etc/passwd               # 提取所有用户名
echo "KEY=val=ue" | cut -d= -f2-      # 安全提取键值对的值
```

---

## 参考资料

- GNU coreutils 官方文档：[cut invocation](https://www.gnu.org/software/coreutils/manual/html_node/cut-invocation.html)
- POSIX 标准：[cut utility](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/cut.html)
- `man cut`（本机手册页）
