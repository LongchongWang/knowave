# grep 命令完全指南：文本过滤的瑞士军刀

> 整理日期：2026-05-28

---

## 一、grep 的本质

`grep` 是 Unix/Linux 世界中最古老、最常用的文本搜索工具之一，诞生于 1973 年，由 Ken Thompson 在贝尔实验室为 Unix 系统编写。它的名字来自 `ed` 编辑器中的一条命令：**G**lobal **R**egular **E**xpression **P**rint，意为"全局正则表达式打印"。

grep 的核心职责极其简单：**逐行读取输入，将匹配指定模式的行打印到标准输出**。这个看似简单的功能，配合 Unix 管道哲学，构成了几乎所有文本处理工作流的基础。

### 基本语法

```bash
grep [选项] 模式 [文件...]
```

三种典型调用方式：

```bash
# 1. 从文件搜索
grep "error" /var/log/app.log

# 2. 从多个文件搜索
grep "TODO" src/main.js src/utils.js

# 3. 从 stdin 搜索（管道输入）
cat /var/log/app.log | grep "error"
ps aux | grep nginx
```

### 退出码

grep 的退出码是脚本编程中非常重要的信号：

- **0**：找到至少一个匹配行
- **1**：未找到任何匹配行
- **2**：发生错误（文件不存在、权限不足等）

这意味着可以直接在 `if` 语句中使用 grep 做条件判断：

```bash
if grep -q "ENABLED=true" /etc/app.conf; then
    echo "功能已启用"
fi
```

---

## 二、常用选项详解

### 大小写与匹配范围

**`-i`（ignore-case）：忽略大小写**

```bash
grep -i "error" app.log
# 匹配 error、Error、ERROR、ErRoR 等所有变体
```

**`-w`（word-regexp）：匹配完整单词**

```bash
grep -w "log" app.log
# 匹配 "log" 但不匹配 "logger"、"catalog"、"dialog"
# 单词边界由非字母数字字符（空格、标点等）界定
```

**`-x`（line-regexp）：匹配整行**

```bash
grep -x "OK" status.txt
# 只匹配内容恰好是 "OK" 的行，不匹配 "OK!" 或 " OK"
```

### 反向与计数

**`-v`（invert-match）：反向匹配**

输出所有**不**匹配模式的行，是过滤噪音的利器：

```bash
# 排除注释行和空行
grep -v "^#" config.ini | grep -v "^$"

# 查看进程时排除 grep 自身
ps aux | grep nginx | grep -v grep
```

**`-c`（count）：只输出匹配行数**

```bash
grep -c "ERROR" app.log
# 输出：42
# 注意：-c 统计的是匹配的行数，不是匹配的次数
# 如果一行出现多个匹配，仍然只计 1
```

### 行号与文件名

**`-n`（line-number）：显示行号**

```bash
grep -n "TODO" src/main.js
# 输出：
# 23:  // TODO: 处理边界情况
# 87:  // TODO: 添加错误处理
```

**`-l`（files-with-matches）：只输出包含匹配的文件名**

```bash
grep -rl "deprecated" src/
# 输出所有包含 "deprecated" 的文件路径，每个文件只输出一次
```

**`-L`（files-without-match）：只输出不包含匹配的文件名**

```bash
grep -rL "eslint-disable" src/
# 找出所有没有 eslint-disable 注释的源文件
```

### 上下文显示

在调试日志时，只看匹配行往往不够，需要前后文来理解上下文：

**`-A N`（after-context）：显示匹配行之后的 N 行**

```bash
grep -A 3 "Exception" app.log
# 显示每个 Exception 行及其后 3 行（通常是堆栈跟踪）
```

**`-B N`（before-context）：显示匹配行之前的 N 行**

```bash
grep -B 2 "NullPointerException" app.log
# 显示异常前 2 行，帮助定位触发原因
```

**`-C N`（context）：显示匹配行前后各 N 行**

```bash
grep -C 5 "FATAL" app.log
# 显示 FATAL 日志前后各 5 行，提供完整上下文
```

多个匹配块之间用 `--` 分隔，便于区分。

### 输出控制

**`-o`（only-matching）：只输出匹配的部分**

默认情况下 grep 输出整行，`-o` 只输出实际匹配的内容，每个匹配占一行：

```bash
# 从日志中提取所有 IP 地址
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log

# 提取所有 HTTP 状态码
grep -oE "HTTP/[0-9.]+ [0-9]+" access.log
```

**`-q`（quiet/silent）：静默模式**

不输出任何内容，只用退出码表示是否找到匹配。适合在脚本中做条件判断：

```bash
if grep -q "feature_flag=true" config.txt; then
    enable_feature
fi
```

**`-m N`（max-count）：最多输出 N 个匹配**

```bash
grep -m 5 "ERROR" app.log
# 找到前 5 个匹配后立即停止，不扫描剩余文件
# 对大文件非常有用，可以显著提升速度
```

**`--color`：高亮显示匹配部分**

```bash
grep --color=auto "error" app.log
# 匹配的文字会用红色高亮显示
# 大多数现代系统已将 grep 别名为 grep --color=auto
```

### 递归搜索

**`-r`（recursive）：递归搜索目录**

```bash
grep -r "TODO" src/
# 递归搜索 src/ 目录下所有文件
```

**`-R`（dereference-recursive）：递归搜索，跟随符号链接**

```bash
grep -R "config" /etc/
# 与 -r 的区别：-R 会跟随符号链接进入链接指向的目录
```

实际使用中常与其他选项组合：

```bash
# 在代码库中搜索，显示文件名和行号
grep -rn "function authenticate" src/

# 只搜索特定类型的文件
grep -r --include="*.js" "require(" src/
grep -r --exclude="*.min.js" "TODO" src/
grep -r --exclude-dir=node_modules "import" .
```

---

## 三、正则表达式

grep 支持两种正则表达式语法，理解它们的区别至关重要。

### BRE vs ERE

**BRE（Basic Regular Expressions，基本正则）** 是 `grep` 的默认模式。在 BRE 中，`+`、`?`、`|`、`()`、`{}` 等元字符需要用反斜杠转义才能发挥特殊含义：

```bash
# BRE：需要转义
grep "colou\?r" file.txt      # 匹配 color 或 colour
grep "go\+gle" file.txt       # 匹配 gogle、google、gooogle...
grep "\(foo\|bar\)" file.txt  # 匹配 foo 或 bar
```

**ERE（Extended Regular Expressions，扩展正则）** 通过 `grep -E`（或 `egrep`）启用。在 ERE 中，这些元字符直接使用，无需转义，更接近现代编程语言中的正则语法：

```bash
# ERE：直接使用
grep -E "colou?r" file.txt    # 匹配 color 或 colour
grep -E "go+gle" file.txt     # 匹配 gogle、google、gooogle...
grep -E "foo|bar" file.txt    # 匹配 foo 或 bar
grep -E "(foo|bar)+" file.txt # 匹配 foo、bar、foofoo、foobar...
```

**推荐始终使用 `grep -E`**，语法更清晰，不容易出错。

### 常用元字符速查

| 元字符 | 含义 | 示例 |
|--------|------|------|
| `.` | 匹配任意单个字符（除换行符） | `gr.p` 匹配 grep、grip、gr3p |
| `*` | 前一个元素重复 0 次或多次 | `go*gle` 匹配 ggle、gogle、google |
| `+` | 前一个元素重复 1 次或多次（ERE） | `go+gle` 匹配 gogle、google |
| `?` | 前一个元素出现 0 次或 1 次（ERE） | `colou?r` 匹配 color、colour |
| `^` | 行首锚点 | `^ERROR` 匹配以 ERROR 开头的行 |
| `$` | 行尾锚点 | `\.js$` 匹配以 .js 结尾的行 |
| `[]` | 字符类，匹配其中任意一个字符 | `[aeiou]` 匹配任意元音字母 |
| `[^]` | 否定字符类 | `[^0-9]` 匹配非数字字符 |
| `\|` | 或（BRE 需转义，ERE 不需要） | `foo\|bar` 或 `foo\|bar` |
| `()` | 分组（BRE 需转义，ERE 不需要） | `(foo)+` 匹配 foo、foofoo |
| `{n,m}` | 重复次数范围（BRE 需转义） | `[0-9]{3,5}` 匹配 3-5 位数字 |

### 字符类（POSIX）

POSIX 字符类在方括号内使用，可移植性更好：

```bash
grep "[[:alpha:]]" file.txt   # 匹配字母（等同 [a-zA-Z]）
grep "[[:digit:]]" file.txt   # 匹配数字（等同 [0-9]）
grep "[[:alnum:]]" file.txt   # 匹配字母或数字
grep "[[:space:]]" file.txt   # 匹配空白字符（空格、Tab 等）
grep "[[:upper:]]" file.txt   # 匹配大写字母
grep "[[:lower:]]" file.txt   # 匹配小写字母
grep "[[:punct:]]" file.txt   # 匹配标点符号
```

### 锚点与边界

```bash
# 行首和行尾
grep "^$" file.txt            # 匹配空行
grep "^[[:space:]]*$" file.txt # 匹配只含空白字符的行

# 单词边界（\b）
grep -E "\bword\b" file.txt   # 精确匹配单词 word
grep -E "\bfoo\b" file.txt    # 匹配 foo，但不匹配 foobar 或 afoo
```

### 转义特殊字符

当需要搜索包含正则元字符的字面字符串时，需要用反斜杠转义：

```bash
grep "\." file.txt            # 搜索字面点号，而非"任意字符"
grep "1\.2\.3" version.txt    # 搜索 1.2.3（版本号）
grep "\$HOME" script.sh       # 搜索字面 $HOME 字符串
grep "\[ERROR\]" app.log      # 搜索 [ERROR]（含方括号）
```

或者使用 `grep -F`（固定字符串模式）完全禁用正则解析：

```bash
grep -F "1.2.3" version.txt   # 所有字符都视为字面量
grep -F "[ERROR]" app.log     # 不需要转义方括号
```

---

## 四、grep 家族

### grep（标准版本）

默认使用 BRE，是最通用的版本，几乎在所有 Unix/Linux 系统上都可用。

### egrep（扩展正则）

等同于 `grep -E`，使用 ERE 语法。在现代系统上，`egrep` 通常是 `grep -E` 的别名或符号链接。推荐直接使用 `grep -E` 而非 `egrep`，因为后者在某些系统上已被标记为废弃。

```bash
egrep "foo|bar" file.txt
# 等同于
grep -E "foo|bar" file.txt
```

### fgrep（固定字符串）

等同于 `grep -F`，将模式视为固定字符串而非正则表达式，不解析任何元字符。由于跳过了正则引擎，速度更快，适合搜索包含大量特殊字符的字符串：

```bash
fgrep "price: $19.99" catalog.txt
# 等同于
grep -F "price: $19.99" catalog.txt
# 无需转义 $ 和 .
```

### grep -P（Perl 兼容正则 PCRE）

`-P` 选项启用 PCRE（Perl Compatible Regular Expressions），支持更强大的正则特性：

```bash
# \d、\w、\s 等 Perl 风格简写
grep -P "\d{4}-\d{2}-\d{2}" log.txt    # 匹配日期格式 YYYY-MM-DD
grep -P "\w+@\w+\.\w+" emails.txt      # 简单邮箱匹配

# 零宽断言（lookahead/lookbehind）
grep -P "(?<=user_id=)\d+" log.txt     # 提取 user_id= 后面的数字
grep -P "foo(?=bar)" file.txt          # 匹配后面跟着 bar 的 foo
grep -P "(?<!un)happy" file.txt        # 匹配不以 un 开头的 happy

# 非贪婪匹配
grep -oP "<.+?>" html.txt             # 提取 HTML 标签（非贪婪）
```

**注意**：`-P` 选项在 macOS 的原生 grep（BSD grep）上不可用，需要安装 GNU grep（`brew install grep`）。

---

## 五、在管道中的典型用法

grep 的真正威力在于与其他命令组合使用。

### 过滤日志

```bash
# 基础过滤
cat app.log | grep "ERROR"
# 更简洁的写法（直接传文件）
grep "ERROR" app.log

# 过滤特定时间段的错误
grep "2026-05-28" app.log | grep "ERROR"

# 查看最近 100 行中的错误
tail -100 app.log | grep "ERROR"

# 实时监控日志中的错误
tail -f app.log | grep --line-buffered "ERROR"
```

### 提取特定格式的行

```bash
# 提取包含 TOKEN_VALUE 的行
grep "TOKEN_VALUE=" output.txt

# 提取 HTTP 4xx 和 5xx 错误
grep -E "HTTP/[0-9.]+ [45][0-9]{2}" access.log

# 提取非空、非注释行（常用于读取配置文件）
grep -v "^[[:space:]]*#" config.ini | grep -v "^[[:space:]]*$"
```

### 结合 cut/awk 提取字段

```bash
# 从 /etc/passwd 中提取用户名（第一列）
grep "bash" /etc/passwd | cut -d: -f1

# 从 CSV 中提取特定列
grep "2026-05" sales.csv | awk -F, '{print $3}'

# 提取日志中的 IP 地址
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn
```

### 结合 wc -l 统计数量

```bash
# 统计错误行数
grep -c "ERROR" app.log
# 或者
grep "ERROR" app.log | wc -l

# 统计包含错误的文件数量
grep -rl "ERROR" logs/ | wc -l
```

### 多条件过滤

```bash
# OR 条件：匹配 ERROR 或 WARN
grep -E "ERROR|WARN" app.log

# AND 条件：同时包含 user 和 failed（顺序不限）
grep "user" app.log | grep "failed"

# 排除特定模式
grep "ERROR" app.log | grep -v "expected error"

# 链式过滤：ERROR 且不是 404
grep "ERROR" access.log | grep -v "404"
```

### 排除注释行

```bash
# 排除以 # 开头的注释行
grep -v "^#" config.ini

# 排除注释行和空行（处理配置文件的标准做法）
grep -v "^[[:space:]]*#" config.ini | grep -v "^[[:space:]]*$"

# 统计有效配置项数量
grep -v "^[[:space:]]*[#;]" config.ini | grep -v "^[[:space:]]*$" | wc -l
```

---

## 六、grep 家族性能与替代工具

### 性能瓶颈

标准 grep 在处理大型代码库时存在几个性能问题：不了解项目结构（会扫描 `node_modules`、`.git` 等无关目录）、不支持并行搜索、对二进制文件处理不够智能。

### ripgrep（rg）

[ripgrep](https://github.com/BurntSushi/ripgrep) 是目前最快的文本搜索工具，由 Rust 编写，在大多数场景下比 grep 快 **10-100 倍**。

核心优势：

- **自动忽略 `.gitignore`**：不搜索 `node_modules`、`dist`、`.git` 等目录
- **并行搜索**：利用多核 CPU 并行处理文件
- **智能编码处理**：自动跳过二进制文件，支持 UTF-8/UTF-16 等多种编码
- **默认递归**：无需 `-r` 选项，默认就是递归搜索当前目录
- **彩色输出**：默认高亮显示匹配内容

```bash
# 安装
brew install ripgrep  # macOS
apt install ripgrep   # Ubuntu/Debian

# 基本用法（与 grep 高度兼容）
rg "TODO" src/
rg -i "error" app.log
rg -n "function" --type js src/

# 搜索特定文件类型
rg "import" -t ts          # 只搜索 TypeScript 文件
rg "SELECT" -t sql         # 只搜索 SQL 文件

# 显示统计信息
rg --stats "TODO" src/

# 搜索但忽略 .gitignore（强制搜索所有文件）
rg -u "TODO" .             # -u 取消一层忽略规则
rg -uu "TODO" .            # -uu 取消两层（包括隐藏文件）
rg -uuu "TODO" .           # -uuu 完全不忽略任何文件
```

### ag（The Silver Searcher）

[ag](https://github.com/ggreer/the_silver_searcher) 是 ripgrep 出现之前最流行的高速搜索工具，同样自动忽略 `.gitignore`，比 grep 快约 5-10 倍。

```bash
brew install the_silver_searcher
ag "TODO" src/
ag -i "error" app.log
```

### 何时用 grep vs awk/sed

这三个工具各有侧重，选择时遵循以下原则：

**用 grep 当**：只需要过滤行（判断某行是否匹配），不需要对内容做变换。grep 是最快的行过滤器。

**用 awk 当**：需要按字段处理数据（CSV、日志的特定列），或需要做简单的计算和统计。awk 是一个完整的文本处理语言。

**用 sed 当**：需要对文本做替换、删除、插入等变换操作。sed 是流编辑器，擅长文本变换。

```bash
# grep：只过滤，不变换
grep "ERROR" app.log

# awk：按字段处理
awk '/ERROR/ {print $1, $2, $NF}' app.log

# sed：文本替换
sed 's/ERROR/CRITICAL/g' app.log
```

---

## 七、实战场景

### 场景一：在代码库中搜索函数定义

```bash
# 搜索 JavaScript/TypeScript 函数定义
grep -rn "function authenticate" src/
grep -rn "const authenticate\s*=" src/
grep -rn "authenticate\s*(" src/ --include="*.ts"

# 使用 ripgrep（推荐，更快且自动忽略 node_modules）
rg "def authenticate" --type py    # Python
rg "func authenticate" --type go   # Go
rg "authenticate\(" --type ts      # TypeScript

# 搜索类定义
grep -rn "^class " src/ --include="*.py"
grep -rn "export class " src/ --include="*.ts"
```

### 场景二：从日志中提取 IP 地址

```bash
# 提取所有 IPv4 地址
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log

# 统计各 IP 的访问次数，按频率排序
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log | sort | uniq -c | sort -rn | head -20

# 找出访问次数超过 1000 次的 IP（可能是爬虫或攻击）
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" access.log \
  | sort | uniq -c | sort -rn \
  | awk '$1 > 1000 {print $2, $1}'

# 提取特定 IP 的所有请求
grep "192.168.1.100" access.log
```

### 场景三：检查配置文件中是否存在某个配置项

这是 Shell 脚本中最常见的 grep 用法之一：

```bash
#!/bin/bash

CONFIG_FILE="/etc/app/config.ini"

# 检查配置项是否存在
if grep -q "^max_connections" "$CONFIG_FILE"; then
    echo "max_connections 已配置"
    # 提取当前值
    current_value=$(grep "^max_connections" "$CONFIG_FILE" | cut -d= -f2 | tr -d ' ')
    echo "当前值：$current_value"
else
    echo "警告：max_connections 未配置，将使用默认值"
fi

# 检查是否启用了某个功能
check_feature() {
    local feature="$1"
    local config="$2"
    if grep -qE "^${feature}\s*=\s*(true|yes|1|on)" "$config"; then
        return 0  # 已启用
    else
        return 1  # 未启用
    fi
}

if check_feature "debug_mode" "$CONFIG_FILE"; then
    echo "调试模式已开启"
fi
```

### 场景四：统计错误日志中各类错误的数量

```bash
#!/bin/bash

LOG_FILE="app.log"

echo "=== 错误统计报告 ==="
echo "文件：$LOG_FILE"
echo "时间：$(date)"
echo ""

# 统计各级别日志数量
echo "--- 日志级别分布 ---"
for level in DEBUG INFO WARN ERROR FATAL; do
    count=$(grep -c "\[$level\]" "$LOG_FILE" 2>/dev/null || echo 0)
    printf "%-8s: %d\n" "$level" "$count"
done

echo ""
echo "--- TOP 10 错误类型 ---"
# 提取错误类型（假设格式为 [ERROR] ExceptionType: message）
grep "\[ERROR\]" "$LOG_FILE" \
  | grep -oE "[A-Z][a-zA-Z]+Exception|[A-Z][a-zA-Z]+Error" \
  | sort | uniq -c | sort -rn | head -10

echo ""
echo "--- 最近 5 条 FATAL 错误 ---"
grep "\[FATAL\]" "$LOG_FILE" | tail -5

echo ""
echo "--- 错误时间分布（按小时）---"
grep "\[ERROR\]" "$LOG_FILE" \
  | grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}" \
  | cut -d: -f1 \
  | sort | uniq -c \
  | awk '{printf "  %s:00 - %d 次\n", $2, $1}'
```

### 场景五：代码审查辅助

```bash
# 找出所有 TODO/FIXME/HACK 注释
grep -rn -E "(TODO|FIXME|HACK|XXX|BUG):" src/ --include="*.{js,ts,py,go}"

# 找出可能的硬编码密码或密钥
grep -rn -iE "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}" src/

# 找出 console.log（应在生产代码中移除）
grep -rn "console\.log" src/ --include="*.ts" | grep -v "\.test\."

# 找出过长的行（超过 120 字符）
grep -n ".\{121\}" src/main.ts

# 找出可能的 SQL 注入风险（字符串拼接构造 SQL）
grep -rn -E "\"SELECT.*\+|'SELECT.*\+" src/ --include="*.java"
```

---

## 八、常见陷阱与注意事项

**陷阱一：特殊字符未转义**

```bash
# 错误：. 会匹配任意字符
grep "192.168.1.1" access.log  # 也会匹配 192X168Y1Z1

# 正确：转义点号
grep "192\.168\.1\.1" access.log
# 或使用 -F
grep -F "192.168.1.1" access.log
```

**陷阱二：忘记 -r 导致搜索目录失败**

```bash
# 错误：grep 不会自动递归目录
grep "TODO" src/  # 可能报错或只搜索目录本身

# 正确
grep -r "TODO" src/
```

**陷阱三：管道中的缓冲问题**

```bash
# 实时监控日志时，输出可能被缓冲
tail -f app.log | grep "ERROR"  # 可能有延迟

# 解决：使用 --line-buffered
tail -f app.log | grep --line-buffered "ERROR"
```

**陷阱四：macOS 与 GNU grep 的差异**

macOS 默认安装的是 BSD grep，与 GNU grep 存在一些差异：

- BSD grep 不支持 `-P`（PCRE）
- 某些选项的行为略有不同
- 解决方案：`brew install grep`，然后使用 `ggrep` 或将 GNU grep 加入 PATH

```bash
brew install grep
# 将 GNU grep 加入 PATH（在 .zshrc 或 .bashrc 中添加）
export PATH="/usr/local/opt/grep/libexec/gnu/bin"
```

---

## 八、实战场景

### 场景一：在代码库中搜索函数定义

```bash
# 搜索 Python 函数定义
grep -rn "^def " --include="*.py" src/

# 搜索 JavaScript/TypeScript 函数
grep -rn "function\s\+\w\+" --include="*.js" --include="*.ts" src/

# 搜索箭头函数（需要 -E）
grep -rEn "const \w+ = \(" --include="*.ts" src/

# 搜索类方法定义
grep -rn "  \w\+(" --include="*.java" src/

# 搜索特定函数的所有调用位置
grep -rn "processOrder(" --include="*.ts" .
```

### 场景二：从日志中提取 IP 地址

```bash
# 提取所有 IPv4 地址
grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' access.log

# 提取并去重排序
grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' access.log | sort -u

# 统计每个 IP 的访问次数
grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}' access.log | sort | uniq -c | sort -rn | head -20

# 提取特定 IP 段的访问记录
grep -E '^192\.168\.' access.log

# 提取 IPv6 地址（简化版）
grep -Eo '([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}' access.log
```

### 场景三：检查配置文件中是否存在某个配置项（用于脚本判断）

这是 grep 在 Shell 脚本中最常见的用法之一——利用退出码做条件判断：

```bash
#!/bin/bash

# 检查 nginx 配置中是否启用了 gzip
if grep -q "gzip on" /etc/nginx/nginx.conf; then
    echo "gzip 已启用"
else
    echo "gzip 未启用，建议开启以提升性能"
fi

# 检查 /etc/hosts 中是否已有某条记录，避免重复添加
HOST_ENTRY="127.0.0.1 myapp.local"
if ! grep -qF "$HOST_ENTRY" /etc/hosts; then
    echo "$HOST_ENTRY" | sudo tee -a /etc/hosts
    echo "已添加 hosts 记录"
fi

# 检查环境变量文件中是否已配置某个 key
check_env_key() {
    local key="$1"
    local env_file="${2:-.env}"
    if grep -qE "^${key}=" "$env_file"; then
        echo "✓ $key 已配置"
        return 0
    else
        echo "✗ $key 未配置"
        return 1
    fi
}

check_env_key "DATABASE_URL"
check_env_key "REDIS_URL"
check_env_key "JWT_SECRET"

# 批量检查必要配置项
REQUIRED_KEYS=("DATABASE_URL" "REDIS_URL" "JWT_SECRET" "API_KEY")
MISSING=0
for key in "${REQUIRED_KEYS[@]}"; do
    if ! grep -qE "^${key}=" .env; then
        echo "缺少必要配置：$key"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo "错误：有 $MISSING 个必要配置项缺失，请检查 .env 文件"
    exit 1
fi
```

### 场景四：统计错误日志中各类错误的数量

```bash
# 统计各级别日志数量
echo "=== 日志级别统计 ==="
for level in ERROR WARN INFO DEBUG; do
    count=$(grep -c "\[$level\]" app.log 2>/dev/null || echo 0)
    printf "%-8s: %d\n" "$level" "$count"
done

# 提取错误类型并统计（假设格式为 "ERROR: SomeException: message"）
echo "=== 错误类型 TOP 10 ==="
grep "^ERROR" app.log \
    | grep -Eo '[A-Z][a-zA-Z]+Exception' \
    | sort | uniq -c | sort -rn | head -10

# 按小时统计错误数量（假设时间戳格式为 2024-01-15 14:23:45）
echo "=== 每小时错误数量 ==="
grep "ERROR" app.log \
    | grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}' \
    | sort | uniq -c

# 提取最近 100 个错误的堆栈信息（错误后跟着的缩进行）
grep -A 5 "ERROR" app.log | tail -600

# 找出出现频率最高的错误消息
grep "ERROR" app.log \
    | sed 's/.*ERROR: //' \
    | sort | uniq -c | sort -rn | head -5

# 实时监控新增错误（tail -f + grep）
tail -f app.log | grep --line-buffered "ERROR"
```

### 场景五：代码审查辅助

```bash
# 查找可能的 TODO/FIXME/HACK 注释
grep -rn --include="*.ts" --include="*.js" -E "(TODO|FIXME|HACK|XXX|BUG)" src/

# 查找硬编码的 IP 地址（可能是安全隐患）
grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}' --include="*.ts" src/ \
    | grep -v '127\.0\.0\.1\|0\.0\.0\.0\|localhost'

# 查找可能的密钥泄露（简单检测）
grep -rEin '(password|secret|api_key|token)\s*=\s*["\x27][^"\x27]{8,}' --include="*.ts" src/

# 查找 console.log（生产代码中不应出现）
grep -rn 'console\.log' --include="*.ts" src/ | grep -v '__tests__'

# 查找过长的行（超过 120 字符）
grep -rn '.\.\{121\}' --include="*.ts" src/
```

---

## 九、常见陷阱与注意事项

**陷阱一：特殊字符未转义**

```bash
# 错误：. 在正则中匹配任意字符
grep "192.168.1.1" /etc/hosts  # 会匹配 192X168Y1Z1

# 正确：转义点号
grep "192\.168\.1\.1" /etc/hosts

# 或使用 -F 固定字符串模式
grep -F "192.168.1.1" /etc/hosts
```

**陷阱二：引号问题**

```bash
# 单引号：Shell 不解析，原样传给 grep（推荐）
grep '$HOME' file.txt  # 搜索字面量 $HOME

# 双引号：Shell 会展开变量
grep "$HOME" file.txt  # 搜索 /Users/username 的实际值

# 需要在模式中使用变量时用双引号
PATTERN="error"
grep "$PATTERN" log.txt
```

**陷阱三：二进制文件**

```bash
# grep 默认会跳过二进制文件并输出 "Binary file matches"
# 强制将二进制文件当文本处理
grep -a "pattern" binary_file

# 排除二进制文件
grep -I "pattern" *  # -I 等同于 --binary-files=without-match
```

**陷阱四：macOS 与 GNU grep 的差异**

macOS 默认安装的是 BSD grep，与 GNU grep 存在一些差异：

- BSD grep 不支持 `-P`（PCRE）
- 某些选项的行为略有不同
- 解决方案：`brew install grep`，然后使用 `ggrep` 或将 GNU grep 加入 PATH

```bash
brew install grep
# 将 GNU grep 加入 PATH（在 .zshrc 或 .bashrc 中添加）
export PATH="/usr/local/opt/grep/libexec/gnubin:$PATH"
```

**陷阱五：递归搜索时的符号链接**

```bash
# -r 不跟随符号链接，-R 跟随符号链接
# 在有循环符号链接的目录中，-R 可能导致无限循环
grep -r "pattern" .   # 安全，不跟随符号链接
grep -R "pattern" .   # 危险，可能无限循环
```

---

## 十、快速参考卡片

| 场景 | 命令 |
|------|------|
| 基础搜索 | `grep "pattern" file` |
| 忽略大小写 | `grep -i "pattern" file` |
| 显示行号 | `grep -n "pattern" file` |
| 反向匹配 | `grep -v "pattern" file` |
| 递归搜索 | `grep -r "pattern" dir/` |
| 扩展正则 | `grep -E "pat1|pat2" file` |
| 固定字符串 | `grep -F "literal.string" file` |
| PCRE | `grep -P "\d{3}-\d{4}" file` |
| 只输出匹配部分 | `grep -o "pattern" file` |
| 显示上下文 | `grep -C 3 "pattern" file` |
| 统计匹配行数 | `grep -c "pattern" file` |
| 只输出文件名 | `grep -l "pattern" *.log` |
| 完整单词匹配 | `grep -w "word" file` |
| 静默判断 | `grep -q "pattern" file && echo yes` |
| 最多 N 个匹配 | `grep -m 5 "pattern" file` |
| 高亮显示 | `grep --color=always "pattern" file` |

---

## 总结

grep 是 Unix/Linux 工具箱中最基础也最强大的文本处理工具之一。掌握它的核心在于三点：

第一，理解正则表达式。BRE、ERE、PCRE 三种模式各有适用场景，日常工作中 `-E` 扩展正则已能覆盖绝大多数需求，只有需要 `\d`、`\w`、lookahead 等高级特性时才需要 `-P`。

第二，善用退出码。grep 的退出码设计让它天然适合在 Shell 脚本中做条件判断，`-q` 静默模式配合 `if grep -q` 是检查配置项存在性的标准写法。

第三，知道何时换工具。对于大型代码库的日常搜索，ripgrep（rg）在速度和易用性上全面超越 grep；对于复杂的文本转换，awk 和 sed 比 grep 更合适；对于结构化数据（JSON/CSV），专用工具（jq/csvkit）更可靠。

grep 的价值不在于它是最快或功能最丰富的，而在于它无处不在——任何 Unix/Linux 系统上都有它，任何管道组合中都能用它。这种普遍性使它成为每个开发者和运维工程师必须熟练掌握的基础技能。

---

*整理日期：2026-05-28*
</parameter>
