# 易错点速查笔记

> 从自测题中整理出的所有错误
> 每个错误都有：错在哪 → 为什么错 → 怎么记 → 窍门
> 建议：每天花 5 分钟看一遍，直到不再犯错

---

## 1. 虚拟环境命令

```
❌ python -m .venv venv
✅ python -m venv .venv
```

**为什么错：** `-m` 后面跟的是 Python 模块名，`venv` 是模块名，`.venv` 是你要创建的文件夹名。你把顺序搞反了。

**怎么记：** "用 venv 模块，在 .venv 文件夹里创建虚拟环境" → `python -m venv .venv`

```
❌ .\venv\Scripts\Activate.ps1
✅ .venv\Scripts\activate
```

**为什么错：** 路径多了个 `\`，而且 `.venv` 不是 `venv`。

**怎么记：** 激活脚本就在你创建的虚拟环境文件夹里面，`.venv\Scripts\activate`

---

## 2. YAML 格式

```yaml
# ❌ 冒号后面没空格
url:http://localhost:11434

# ✅ 冒号后面必须有空格
url: http://localhost:11434
```

**为什么错：** YAML 语法规定冒号后面必须有空格，没有空格会解析失败。

**窍门：** 写 YAML 时，每次写冒号就按一下空格键，养成肌肉记忆。

---

## 3. yaml.safe_load 不是 yaml.safeload

```python
# ❌
yaml.safeload(f)

# ✅
yaml.safe_load(f)
```

**为什么错：** Python 里多个单词组成的函数名用下划线连接，这是 Python 的命名规范。

**窍门：** "safe" 和 "load" 是两个单词，中间要断开 → `safe_load`

---

## 4. import 路径

```python
# ❌
from src.configs import config

# ✅
from src.config import config
```

**为什么错：** 你的文件是 `src/config.py`，不是 `src/configs/config.py`。import 路径要和文件路径一致。

**窍门：** import 的路径就是文件路径，把 `/` 换成 `.`，去掉 `.py`。`src/config.py` → `from src.config import ...`

---

## 5. config 键名要和 YAML 一致

```yaml
# config.yaml 里写的是
model:
  base_model: "qwen3:4b"
```

```python
# ❌ 键名对不上
config['model']['name']

# ✅ 和 YAML 里一模一样
config['model']['base_model']
```

**为什么错：** config 就是 YAML 文件转成的字典，键名必须完全一致。

**窍门：** 写 `config['xxx']` 之前，先去 YAML 里确认键名是什么，复制粘贴最安全。

---

## 6. uvicorn 命令

```
❌ uvicorn main:app --reload         ← 少了 src.
❌ uvicorn src.main：app --reload    ← 中文冒号 ：
✅ uvicorn src.main:app --reload
```

**为什么错：**
- `main:app` 找不到，因为 main.py 在 src/ 下面，必须写 `src.main`
- 中文冒号 `：` 和英文冒号 `:` 长得像但不一样，Python 只认英文的

**--reload 的真正作用：** 代码修改后自动重启服务器。不是"持续加载"，是"改了代码不用手动重启"。

**窍门：** uvicorn 后面写的是"从项目根目录到 main.py 的路径"，把 `/` 换成 `.`

---

## 7. 装饰器 @

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

**@ 的作用：** 给函数贴标签。没有 @，FastAPI 不知道这个函数是干什么的。

**类比：** 函数是一个员工，@ 是工牌。没有工牌的员工，前台不认识他，不会把客户转给他。

**你只需要记住：** 写路由就加 `@router.get/post/put/delete("/路径")`

---

## 8. FastAPI 函数参数

```python
# ❌ 加了参数，FastAPI 会当成查询参数 ?config=xxx
@app.get("/config")
def get_config(config: str):
    return config

# ✅ 不需要参数
@app.get("/config")
def get_config():
    return config
```

**为什么错：** FastAPI 里函数的参数会被自动解析为请求参数。你写了 `config: str`，FastAPI 会去找 URL 里的 `?config=xxx`，找不到就报错。

**窍门：** 函数里只写你需要从请求里拿的东西（路径参数、查询参数）。外部变量直接用，不需要当参数传进来。

---

## 9. FastAPI 自动转 JSON

```
return config（Python 字典）
    ↓ 自动转换
{"model": {...}}（JSON）
```

**原理：** FastAPI 看到你返回的是字典，自动调用 `json.dumps()` 转成 JSON 字符串发给浏览器。你不需要手动转换。

---

## 10. ollama 库全小写

```python
# ❌ O 大写
import Ollama
client = Ollama.Client(...)

# ✅ 全小写
import ollama
client = ollama.Client(...)
```

**为什么：** Python 包名约定全小写。`Ollama` 大写开头会报 `ModuleNotFoundError`。

**窍门：** Python 里 99% 的包名都是全小写（torch, transformers, fastapi, ollama...）

---

## 11. Ollama host 要有 http://

```python
# ❌ 没有协议前缀
client = ollama.Client(host="localhost:11434")

# ✅ 有 http://
client = ollama.Client(host="http://localhost:11434")
```

**为什么：** 网络地址必须有协议前缀（http:// 或 https://），不然不知道用什么协议连接。

**窍门：** 浏览器地址栏里 `http://` 是自动加的，但代码里必须手动写。

---

## 12. Ollama messages vs message

```python
# 发出去：messages（复数，因为是一个消息列表）
client.chat(messages=[{"role": "user", "content": "你好"}])

# 收回来：message（单数，因为只返回一条回复）
response["message"]["content"]
```

**为什么不一样：** 发送时你可以发多条消息（对话历史），所以是列表 messages。返回时只返回一条回复，所以是单数 message。

**窍门：** "发出去是群发（messages），收回来是单条（message）"

---

## 13. APIRouter 拼写

```python
# ❌ APIRputer（r 和 t 颠倒了）
router = APIRputer()

# ✅ APIRouter
router = APIRouter()
```

**窍门：** Router = 路由器，网络里的 Router 也是这个词。`API + Router` = API 路由器。

---

## 14. .gitignore 完整内容

```gitignore
.venv/              ← 虚拟环境（不是 .\venv）
__pycache__/        ← Python 缓存（不是 __pycatch__，是 cache）
*.pyc               ← 编译文件
.env                ← 环境变量
.vscode/            ← VSCode
.idea/              ← PyCharm
output/             ← 训练产出
*.safetensors       ← 模型文件
```

**窍门：** cache = 缓存，不是 catch = 抓住。`__pycache__` 里存的是 Python 编译的缓存文件。

---

## 15. Git 配置命令

```bash
git config --global user.email "你的邮箱"
git config --global user.name "why"
```

**窍门：** `--global` = 全局，所有项目都用这个身份。只需设一次。

---

## 16. Git 推送到 GitHub 完整流程

```bash
git init                                        # 1. 初始化
git config --global user.email "邮箱"           # 2. 设身份
git config --global user.name "why"
git add .                                       # 3. 暂存
git commit -m "说明"                            # 4. 提交
git remote add origin https://github.com/...    # 5. 关联远程
git branch -M main                              # 6. 改分支名
git push -u origin main                         # 7. 推送
```

**窍门：** 记顺序 "初始化 → 身份 → 暂存 → 提交 → 关联 → 推送"

---

## 17. .gitignore 对已暂存的文件不生效

```
已经 git add .venv/ 了 → .gitignore 不管用

解决：git rm -r --cached .venv/
```

**原理：** .gitignore 只管"还没被 Git 追踪的文件"。已经 add 进暂存区的文件，Git 已经在追踪了，.gitignore 管不到。

**窍门：** 先写 .gitignore，再 git add。顺序反了就用 `git rm -r --cached` 补救。

---

## 18. Docker Compose 命令

```bash
docker compose up -d          # 启动（不是 docker compose -d）
docker compose down           # 停止
docker compose ps             # 查看状态（不是 status）
docker compose logs 服务名    # 查看日志
```

**你犯的错：** `docker compose -d` 少了 `up`。`-d` 是 `up` 的参数，不能单独用。

**窍门：** `up` = 启动，`down` = 停止，`ps` = 状态（ps = process status 的缩写）

---

## 19. Docker Compose 配置口诀

```yaml
ports:
  - "5432:5432"
#   ↑    ↑
#  左我  右他     ← 口诀：左我右他

volumes:
  - postgres_data:/var/lib/postgresql/data
#   ↑                ↑
#  左名              右路               ← 口诀：左名右路
```

**怎么记：**
- ports：左边是我的电脑，右边是容器内部
- volumes：左边是给卷起个名字，右边是容器里数据放哪

---

## 20. SQLAlchemy 类型大小写

```python
# ❌ Datetime（小写 t）
from sqlalchemy import Datetime

# ✅ DateTime（大写 T）
from sqlalchemy import DateTime
```

**为什么：** SQLAlchemy 的类型名是大驼峰（每个单词首字母大写）。`Date` + `Time` = `DateTime`。

**窍门：** SQLAlchemy 的类型都是大驼峰：`Integer`、`String`、`DateTime`、`Boolean`

---

## 21. 每个字段必须用 Column() 包裹

```python
# ❌ 直接写类型
agent_name = (String, nullable=False)

# ✅ 用 Column() 包起来
agent_name = Column(String, nullable=False)
```

**为什么：** `Column()` 是 SQLAlchemy 定义列的方式。不包起来，Python 以为你在定义一个普通变量。

**窍门：** 每个字段都是 `Column(类型, 约束)` 的格式，没有例外。

---

## 22. 参数名是 nullable 不是 allow_none

```python
# ❌
Column(String, allow_none=False)

# ✅
Column(String, nullable=False)
```

**窍门：** nullable = "可空的"，SQLAlchemy 用的是数据库术语，不是 Python 术语。

---

## 23. primary_key 拼写

```python
# ❌ primay_key（少了 r）
# ✅ primary_key
```

**窍门：** primary = 主要的，pri-ma-ry，三个音节。

---

## 24. Python 保留字不能做字段名

```python
# ❌ input 是 Python 保留字（内置函数 input()）
input = Column(String)

# ✅ 改名
input_text = Column(String)
```

**常见的 Python 保留字：** input, output, type, id, class, return, import, from, if, else, for, while, def, True, False, None

**窍门：** 字段名加后缀 `_text`、`_data`、`_info` 就能避开大部分保留字。

---

## 25. lambda 延迟执行

```python
# ❌ 定义类时就执行了，所有记录同一个时间
default=datetime.now(timezone.utc)

# ✅ 每次插入时才执行
default=lambda: datetime.now(timezone.utc)
```

**原理：**
- 不加 lambda：`datetime.now()` 在 Python 读到这行代码时就执行了，结果固定
- 加 lambda：`lambda: datetime.now()` 创建了一个"待执行的指令"，每次调用时才执行

**类比：**
- 不加 lambda = 拍一张照片，所有证件都用这张
- 加 lambda = 每次办证件时现场拍一张

**窍门：** 看到 `default=某个会变的值`（时间、随机数），就加 `lambda:`

---

## 26. DATABASE_URL 括号匹配

```python
# ❌ 括号嵌套错
f"postgresql://{db['user']}:{db['password']@{db['host']}:{db['port']}/{db['name']}}"
#                                   ↑ 这个 } 提前闭合了

# ✅ 每个 {} 独立
f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
```

**窍门：** f-string 里每个 `{}` 都是独立的，不要嵌套。一个变量一个 `{}`。

---

## 27. engine 和 SessionLocal

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL)        # 拨号连接
SessionLocal = sessionmaker(bind=engine)    # 会话工厂
```

**engine = 拨号连接：** 告诉 SQLAlchemy "数据库在哪、怎么连"。只创建一次。

**SessionLocal = 会话工厂：** 每次要操作数据库，从它那拿一个"会话"（db）。用完关掉。

**类比：** engine 是电话号码，SessionLocal 是电话机。每次打电话（操作数据库）用电话机拨号，打完挂电话（close）。

---

## 28. 为什么要开/关会话

```python
db = SessionLocal()   # 开
# ... 操作 ...
db.close()            # 关
```

**为什么不关：** 数据库连接是有限资源（就像银行窗口有限）。不关 = 办完业务不走，后面的人排队等。关了 = 办完走人，窗口空出来。

**为什么不用全局 db：** 多个请求同时用同一个 db = 两个人同时在一个窗口办业务，会搞混。每个函数单独开/关 = 每人一个窗口。

---

## 29. CRUD 操作顺序

```python
# ❌ SessionLocal() 放在创建对象之后
task = Task(question=question)
db = SessionLocal()        # 太晚了，task 还没和数据库关联

# ✅ 先开会话，再创建对象
db = SessionLocal()
task = Task(question=question)
```

**原理：** 对象要通过会话（db）才能和数据库交互。先有会话，再创建对象，对象才能被 db 管理。

---

## 30. db.delete() 不要赋值

```python
# ❌ delete 不返回值，task 变成 None 了
task = db.delete(task)

# ✅ 直接调用
db.delete(task)
```

**原理：** `db.delete()` 的作用是"标记这个对象要被删除"，它不返回任何东西。

---

## 31. .first() 的作用

```python
db.query(Task).filter(Task.id == 1).first()
#                                   ^^^^^
```

**first() = 取查询结果的第一条。**

为什么需要它：`filter()` 返回的是一个"查询集"（可以理解为结果列表），不是具体对象。`.first()` 把第一条取出来，才是你要的那个 Task 对象。

**不加 .first()：** 返回的是查询对象，不是 Task，你没法访问 `.question`、`.status` 等属性。

---

## 32. filter 条件的顺序

```python
# ❌ 把变量写在左边
task = db.query(Task).filter(task_id == Task.id).first()

# ✅ 字段写在左边，值写在右边
task = db.query(Task).filter(Task.id == task_id).first()
```

**为什么：** SQLAlchemy 的 `filter()` 需要左边是模型字段（`Task.id`），右边是你要比较的值（`task_id`）。虽然结果一样，但约定俗成字段在左，值在右。

---

## 33. get 函数不需要 None 检查

```python
# ❌ 查不到返回 False，但函数签名说返回 Task
def get_task(task_id: int) -> Task:
    if task is None:
        return False    # 类型不一致

# ✅ 查不到就返回 None，调用方自己判断
def get_task(task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()
    return task         # 可能是 Task，也可能是 None
```

**原理：** `.first()` 找不到就返回 None。get 函数只需要返回结果（可能是 None），不需要自己处理"找不到"的情况。处理逻辑应该放在调用方（路由层）。

---

## 34. HTTP 方法对应 CRUD

| 方法 | 操作 | 记忆 |
|------|------|------|
| POST | 创建（Create） | POST = 邮寄，把新数据"寄"给服务器 |
| GET | 查询（Read） | GET = 获取，从服务器"拿"数据 |
| PUT | 修改（Update） | PUT = 放置，把修改后的数据"放"回去 |
| DELETE | 删除（Delete） | DELETE = 删除，英文一样 |

**窍门：** 浏览器地址栏 = GET。POST/PUT/DELETE 要用 `/docs` 页面或 curl。

---

## 35. 注册路由

```python
# main.py
from src.api.tasks import router as tasks_router

app = FastAPI()
app.include_router(tasks_router)    # 把子路由挂到主应用
```

**为什么要 include_router：** APIRouter 是"子路由"，自己不能运行。必须挂到 FastAPI 主应用上，FastAPI 才知道它的存在。

**类比：** APIRouter 是分店，FastAPI 是总部。分店要在总部登记，客户才能找到。

---

## 36. Docker 启动命令

```
❌ docker compose -d          ← 少了 up
✅ docker compose up -d
```

**原理：** `up` 是"启动"，`-d` 是 `up` 的参数（后台运行）。不能跳过 `up` 直接用 `-d`。

---

## 37. 验证表是否建好

```bash
docker compose exec postgres psql -U postgres -d cognitive_probe -c "\dt"
```

**拆解：**
- `docker compose exec postgres` — 进入 postgres 容器
- `psql -U postgres -d cognitive_probe` — 连接数据库
- `-c "\dt"` — 执行 `\dt` 命令（display tables = 显示所有表）

---

## 38. 访问 /tasks/1 返回 not found

可能原因：
1. 还没创建过 id=1 的任务
2. 创建了但被删除了
3. id 写错了

---

## 速记口诀汇总

| 知识点 | 口诀 |
|--------|------|
| 虚拟环境 | `python -m venv .venv`（模块在前，文件夹在后） |
| YAML | 冒号后面必须有空格 |
| safe_load | safe 和 load 之间有下划线 |
| import 路径 | 文件路径把 / 换成 . |
| config 键名 | 和 YAML 里一模一样，复制粘贴 |
| uvicorn | `src.main:app`（英文冒号） |
| 装饰器 @ | 给函数贴标签 |
| ollama | 全小写 |
| Ollama host | 要有 http:// |
| messages | 发出去复数，收回来单数 |
| APIRouter | API + Router |
| Docker | up 启动，down 停止，ps 状态 |
| ports | 左我右他 |
| volumes | 左名右路 |
| DateTime | 大写 T |
| Column | 每个字段都要包 |
| nullable | 不是 allow_none |
| primary_key | 有 r |
| input | 是保留字，改名 input_text |
| lambda | "等需要时再执行" |
| SessionLocal | 开头创建，结尾关闭 |
| db.delete | 不要赋值 |
| .first() | 取第一条结果 |
| filter | 字段在左，值在右 |
| POST/GET/PUT/DELETE | 创建/查询/修改/删除 |
| include_router | 子路由挂到主应用 |
| docker compose up | up 不能省 |
