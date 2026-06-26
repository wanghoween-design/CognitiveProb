# CognitiveProbe 项目搭建学习笔记

> 从零开始搭建一个 FastAPI + Docker + Ollama 的 Multi-Agent 项目
> 整理时间：2026-05-28

---

## 一、虚拟环境

### 为什么要虚拟环境？

每个项目依赖的包版本不同。比如项目 A 用 PyTorch 2.1，项目 B 用 PyTorch 1.9，不隔离会冲突。虚拟环境给每个项目一个独立的"小房间"。

### 常用命令

```bash
# 创建虚拟环境（在项目根目录下）
python -m venv .venv

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 激活后终端前面会出现 (.venv)，表示在虚拟环境里

# 退出虚拟环境
deactivate
```

### 命名约定

`.venv` 前面加点表示隐藏文件夹，是社区约定俗成的写法。

---

## 二、requirements.txt

### 为什么要写它？

记录项目依赖的所有第三方包。换台电脑或别人想跑你的项目，`pip install -r requirements.txt` 一条命令装齐。

### 格式

```
包名==版本号      # 锁定精确版本，适合对版本敏感的包（如 torch）
包名>=版本号      # 最低版本，适合稳定的包（如 pyyaml）
```

### 为什么要锁定版本？

不写版本号，pip 会装最新版，过几个月可能和你的代码不兼容。锁定版本确保"现在能跑，以后也能跑"。

### 我们项目的依赖

```
# 基础
pyyaml>=6.0              # 读取 config.yaml 配置文件
fastapi>=0.104.0         # Web 框架，提供 REST API
uvicorn>=0.24.0          # FastAPI 的运行服务器
pydantic>=2.5.0          # 数据验证，FastAPI 内部依赖

# LLM
ollama>=0.3.0            # 调用本地 Ollama 模型

# 数据库
psycopg2-binary>=2.9.0   # 连接 PostgreSQL
redis>=5.0.0             # 连接 Redis
```

### 常用命令

```bash
# 安装所有依赖
pip install -r requirements.txt

# 安装单个包
pip install 包名

# 查看已安装的包
pip list

# 导出当前环境所有依赖（自动生成 requirements.txt）
pip freeze > requirements.txt
```

---

## 三、配置管理（config.yaml + config.py）

### 为什么要单独管理配置？

如果把模型名、端口号、密码写在代码里，换环境就得改代码。放在 YAML 文件里，改配置不用动代码。

### config.yaml 示例

```yaml
model:
  base_model: "qwen3:4b"           # Ollama 里已下载的模型名
  embedding_model: "nomic-embed-text"

ollama:
  base_url: "http://localhost:11434"  # Ollama 服务地址
  timeout: 120
  num_ctx: 4096
```

### config.py 加载器

```python
from pathlib import Path
import yaml

# 项目根目录（config.py 在 src/ 下，往上走一层才到项目根目录）
ROOT_DIR = Path(__file__).parent.parent

def load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = ROOT_DIR / "configs" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 全局配置实例，只读一次，其他文件 import 就能用
config = load_config()
```

### 为什么用全局变量？

配置只需要读一次，不需要每次都重新解析文件。其他文件 `from src.config import config` 就能直接用。

### 使用方式

```python
from src.config import config

print(config["model"]["base_model"])    # "qwen3:4b"
print(config["ollama"]["base_url"])     # "http://localhost:11434"
```

---

## 四、FastAPI 基础

### 最小 FastAPI 应用

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

### 逐行解释

| 代码 | 作用 |
|------|------|
| `FastAPI()` | 创建应用实例，整个程序的入口 |
| `@app.get("/health")` | 定义路由，访问 `/health` 时触发下面的函数 |
| `return {"status": "ok"}` | 返回字典，FastAPI 自动转成 JSON |

### 运行命令

```bash
uvicorn src.main:app --reload
```

| 部分 | 含义 |
|------|------|
| `uvicorn` | ASGI 服务器，让 FastAPI 能接收 HTTP 请求 |
| `src.main:app` | 找 `src/main.py` 里的 `app` 变量 |
| `--reload` | 代码改了自动重启（开发时用，上线要去掉） |

### APIRouter —— 路由拆分

当接口变多时，全放一个文件会很大。用 `APIRouter` 把接口按职责拆分：

```python
# src/api/health.py
from fastapi import APIRouter

router = APIRouter()         # 用 APIRouter 代替 FastAPI()

@router.get("/health")
def health():
    return {"status": "ok"}
```

```python
# src/main.py
from fastapi import FastAPI
from src.api.health import router as health_router

app = FastAPI(title="CognitiveProbe")
app.include_router(health_router)    # 把子路由挂到主应用上
```

### 为什么要拆分？

- 每个文件负责一类功能，几十行，一目了然
- 找接口不用在一个 500 行的文件里翻
- 类比：不会把所有函数写在一个 .py 里，按职责分文件是基本原则

### 访问 API 文档

启动后访问 `http://127.0.0.1:8000/docs`，FastAPI 自动生成交互式 API 文档。

---

## 五、Ollama 连接

### 什么是 Ollama？

本地运行 LLM 的工具。装好后一条命令就能下载和运行模型，不用管 CUDA、PyTorch 等底层依赖。

### 常用命令

```bash
# 查看已下载的模型
ollama list

# 下载模型
ollama pull qwen3:4b

# 命令行直接对话
ollama run qwen3:4b
```

### Python 调用 Ollama

```python
import ollama

client = ollama.Client(host="http://localhost:11434")
response = client.chat(
    model="qwen3:4b",
    messages=[{"role": "user", "content": "你好"}]
)
print(response["message"]["content"])
```

### 接入 FastAPI

```python
from src.config import config
import ollama

@app.get("/test_llm")
def test_llm():
    client = ollama.Client(host=config["ollama"]["base_url"])
    response = client.chat(
        model=config["model"]["base_model"],
        messages=[{"role": "user", "content": "你好，请用一句话介绍你自己"}]
    )
    return {"response": response["message"]["content"]}
```

### 关键点

- 地址从配置读（`config["ollama"]["base_url"]`），不是硬编码
- 模型名从配置读（`config["model"]["base_model"]`），换模型只改 YAML
- `response["message"]` 是单数，不是 `messages`（容易打错）

---

## 六、.gitignore

### 为什么要写它？

有些文件不该提交到 Git：
- `.venv/` — 虚拟环境，几 GB 大，每台电脑不一样
- `__pycache__/` — Python 自动生成的缓存
- `.env` — 密码密钥，不能泄露
- `output/` — 训练产出，太大

### 我们的 .gitignore

```
# 虚拟环境
.venv/

# Python 缓存
__pycache__/
*.pyc

# 环境变量
.env

# IDE
.vscode/
.idea/

# 训练产出
output/
checkpoint/
*.safetensors

# 系统文件
.DS_Store
Thumbs.db

# 项目特有
_docs/
.claude/
CodeGuard/
learning/
```

### 验证 .gitignore 生效

```bash
git status
```

被忽略的文件不会出现在列表里。

---

## 七、Git 基础

### 为什么要用 Git？

- 记录每次修改，出问题可以回退
- 多人协作不会互相覆盖
- 面试必备，项目必须有 Git 历史

### 核心概念

| 概念 | 类比 |
|------|------|
| 工作区 | 你正在编辑的文件 |
| 暂存区 | 准备提交的文件清单 |
| 仓库 | 提交后的历史记录 |
| 远程仓库 | GitHub 上的备份 |

### 常用命令

```bash
# 初始化仓库
git init

# 设置身份（只需一次）
git config --global user.email "你的邮箱"
git config --global user.name "why"

# 查看状态（哪些文件改了、哪些没提交）
git status

# 把文件加入暂存区
git add .                    # 所有文件
git add src/main.py          # 指定文件

# 提交
git commit -m "提交说明"

# 查看提交历史
git log --oneline

# 关联远程仓库
git remote add origin https://github.com/xxx/xxx.git

# 推送到 GitHub
git push -u origin main      # 第一次推送，-u 记住关联
git push                     # 之后直接 push

# 拉取远程更新
git pull
```

### 提交信息怎么写？

用中文简要说明做了什么，比如：
- `"项目初始化：配置、FastAPI骨架、Ollama连接"`
- `"添加用户认证功能"`
- `"修复登录时的空指针bug"`

不要写 `"update"` 或 `"fix"` 这种看不出来改了什么的信息。

---

## 八、Docker Compose

### 为什么要用 Docker？

你的项目需要 PostgreSQL、Redis 等服务。手动安装这些服务很麻烦，不同系统安装方式不同。Docker 把它们打包成"容器"，一条命令启动，换电脑也能跑。

### docker-compose.yml 基础

```yaml
services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:16                    # 用官方镜像，不用自己装
    container_name: cognitive_postgres    # 容器名字，方便管理
    environment:
      POSTGRES_USER: postgres             # 用户名
      POSTGRES_PASSWORD: postgres123      # 密码
      POSTGRES_DB: cognitive_probe        # 数据库名
    ports:
      - "5432:5432"                       # 容器端口:电脑端口
    volumes:
      - postgres_data:/var/lib/postgresql/data   # 数据持久化

  # Redis 缓存
  redis:
    image: redis:7
    container_name: cognitive_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

# 声明数据卷（容器删了数据还在）
volumes:
  postgres_data:
  redis_data:
```

### 逐块解释

| 配置项 | 作用 |
|--------|------|
| `image` | 用哪个 Docker 镜像，冒号后面是版本号 |
| `container_name` | 容器名字，`docker ps` 时看到的名字 |
| `environment` | 环境变量，相当于配置参数 |
| `ports` | 端口映射，左边是你电脑，右边是容器内部 |
| `volumes` | 数据持久化，不写的话容器删了数据就丢了 |

### 常用命令

```bash
# 启动所有服务（后台运行）
docker compose up -d

# 查看运行状态
docker compose ps

# 停止所有服务
docker compose down

# 停止并删除数据卷（慎用，数据会丢）
docker compose down -v

# 查看某个服务的日志
docker compose logs postgres
docker compose logs redis

# 进入容器内部（调试用）
docker compose exec postgres bash
```

### 端口映射图解

```
你的电脑                    Docker 容器
localhost:5432   ──────→   postgres:5432
localhost:6379   ──────→   redis:6379
```

应用代码连 `localhost:5432`，Docker 自动转发到容器里的 PostgreSQL。

---

## 九、Python 连接数据库

### PostgreSQL（psycopg2）

```python
import psycopg2

# 建立连接
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="postgres123",
    dbname="cognitive_probe"
)

# 创建游标，执行 SQL
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

# 关闭连接
cur.close()
conn.close()
```

### 为什么需要 psycopg2？

Python 不能直接连 PostgreSQL，需要一个"驱动"。`psycopg2` 是最常用的 PostgreSQL Python 驱动。

### 为什么用 psycopg2-binary？

`psycopg2` 编译时需要 C 依赖，Windows 上经常装不上。`psycopg2-binary` 预编译好了，直接装就能用。

### Redis（redis-py）

```python
import redis

# 建立连接
r = redis.Redis(host="localhost", port=6379)

# 写入
r.set("name", "cognitive_probe")

# 读取（返回 bytes，需要 .decode() 转成字符串）
value = r.get("name").decode()
print(value)  # "cognitive_probe"

# 删除
r.delete("name")
```

### Redis vs PostgreSQL 的区别

| 维度 | PostgreSQL | Redis |
|------|-----------|-------|
| 类型 | 关系数据库 | 缓存/键值存储 |
| 数据持久化 | 永久存储 | 默认内存，可配置持久化 |
| 速度 | 较慢（磁盘读写） | 极快（内存读写） |
| 适用场景 | 结构化数据、复杂查询 | 缓存、会话、消息队列 |
| 类比 | 硬盘 | 内存 |

### 项目中的分工

- PostgreSQL — 存任务记录、Agent 日志、评估结果（需要永久保存）
- Redis — 缓存 Agent 结果、管理会话状态（临时数据，快就行）

---

## 十、项目目录结构

```
Multi-Agent/
├── configs/
│   └── config.yaml          # 所有配置集中在这里
├── src/
│   ├── api/                 # 路由层（FastAPI 接口定义）
│   │   ├── __init__.py
│   │   ├── health.py        # 健康检查接口
│   │   ├── config_route.py  # 配置查看接口
│   │   └── test_llm.py      # LLM 测试接口
│   ├── agents/              # Agent 层（后续开发）
│   │   └── __init__.py
│   ├── models/              # 数据模型层（后续开发）
│   │   └── __init__.py
│   ├── config.py            # 配置加载器
│   └── main.py              # 应用入口，只负责注册路由
├── .gitignore
├── docker-compose.yml       # Docker 服务编排
├── requirements.txt         # Python 依赖
└── test_config.py           # 配置测试脚本
```

### 为什么要这样分层？

| 目录 | 职责 | 好处 |
|------|------|------|
| `api/` | 接口定义 | 接口和业务逻辑分离，改接口不影响核心代码 |
| `agents/` | Agent 逻辑 | 后面加新 Agent 只需加文件，不改已有代码 |
| `models/` | 数据结构 | 请求/响应格式统一管理 |
| `configs/` | 配置文件 | 换环境只改配置，不改代码 |

---

## 十一、常用命令速查表

```bash
# ====== 虚拟环境 ======
python -m venv .venv           # 创建
.venv\Scripts\activate         # 激活（Windows）
deactivate                     # 退出

# ====== pip ======
pip install -r requirements.txt   # 安装依赖
pip install 包名                  # 安装单个包
pip list                          # 查看已安装

# ====== FastAPI ======
uvicorn src.main:app --reload     # 启动开发服务器

# ====== Docker ======
docker compose up -d              # 启动服务
docker compose down               # 停止服务
docker compose ps                 # 查看状态
docker compose logs 服务名        # 查看日志

# ====== Git ======
git status                        # 查看状态
git add .                         # 暂存所有
git commit -m "说明"              # 提交
git push                          # 推送到 GitHub
git pull                          # 拉取更新
git log --oneline                 # 查看历史

# ====== Ollama ======
ollama list                       # 查看已下载模型
ollama pull 模型名                # 下载模型
ollama run 模型名                 # 命令行对话
```

---

## 十二、SQLAlchemy ORM（数据库操作）

### 什么是 ORM？

ORM（Object-Relational Mapping）= 用 Python 对象操作数据库，不用写 SQL。

```
Python 世界                    数据库世界
─────────                      ──────────
class Task       ←→           tasks 表
Task(id=1, ...)  ←→           一行记录
db.add(task)     ←→           INSERT INTO tasks ...
db.query(Task)   ←→           SELECT * FROM tasks
```

### 为什么要用 ORM？

| 方式 | 写法 | 问题 |
|------|------|------|
| 直接写 SQL | `cur.execute("INSERT INTO tasks (status) VALUES ('running')")` | 容易写错，没有类型检查 |
| ORM | `db.add(Task(status="running"))` | 像操作 Python 对象，IDE 能提示 |

---

### 第一步：定义模型（建表蓝图）

文件：`src/models/task.py`

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """所有表模型的基类，必须继承它 SQLAlchemy 才认"""
    pass


class Task(Base):
    __tablename__ = "tasks"          # 对应数据库里的表名

    id = Column(Integer, primary_key=True)                    # 主键，自动递增
    question = Column(String, nullable=False)                 # 字符串，不能为空
    status = Column(String, default="pending")                # 字符串，默认值 "pending"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))  # 自动填入当前时间
```

#### 逐行拆解

| 代码 | 作用 | 类比 |
|------|------|------|
| `DeclarativeBase` | 所有表模型的基类 | 就像"注册中心"，继承了它 SQLAlchemy 才认 |
| `__tablename__ = "tasks"` | 表名 | Excel 工作表的标签名 |
| `Column(Integer, primary_key=True)` | 整数主键 | 表格的第一列，每行的唯一编号 |
| `Column(String, nullable=False)` | 字符串，必填 | 不填就报错 |
| `Column(String, default="pending")` | 字符串，有默认值 | 不填自动用 "pending" |
| `Column(DateTime, default=lambda: ...)` | 时间戳 | 不填自动用当前时间 |

#### 数据类型对照

| Python 类型 | SQLAlchemy 类型 | 数据库类型 | 用途 |
|------------|----------------|-----------|------|
| `int` | `Integer` | INTEGER | 整数 |
| `str` | `String` | TEXT | 字符串 |
| `datetime` | `DateTime` | TIMESTAMP | 日期时间 |
| `bool` | `Boolean` | BOOLEAN | 布尔值 |
| `float` | `Float` | FLOAT | 浮点数 |

#### 为什么 `default=lambda: datetime.now(timezone.utc)` 要用 lambda？

```python
# 错误写法：在定义类时就执行了，所有记录用同一个时间
created_at = Column(DateTime, default=datetime.now(timezone.utc))

# 正确写法：每次插入时才执行，每条记录有自己的时间
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

---

### 第二步：配置数据库连接

文件：`src/models/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config

db = config["database"]
DATABASE_URL = f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
```

#### 逐行拆解

| 代码 | 作用 |
|------|------|
| `config["database"]` | 从 config.yaml 读数据库配置（不硬编码） |
| `DATABASE_URL` | 连接字符串，格式：`postgresql://用户:密码@地址:端口/库名` |
| `create_engine(DATABASE_URL)` | 创建引擎 = "拨号连接数据库" |
| `sessionmaker(bind=engine)` | 会话工厂 = "每次操作数据库从这里拿会话" |

#### 连接字符串格式

```
postgresql://postgres:postgres123@localhost:5432/cognitive_probe
          └─┬──┘ └────┬────┘    └───┬───┘ └─┬┘ └────┬──────┘
           用户       密码         地址    端口     库名
```

#### config.yaml 中的数据库配置

```yaml
database:
  host: "localhost"
  port: 5432
  user: "postgres"
  password: "postgres123"
  name: "cognitive_probe"
```

**注意：** 这里的配置必须和 `docker-compose.yml` 里的 PostgreSQL 环境变量一致。

---

### 第三步：CRUD 操作（增删改查）

文件：`src/models/crud.py`

#### 完整代码

```python
from src.models.database import SessionLocal
from src.models.task import Task


# ========== 增 ==========
def create_task(question: str) -> Task:
    db = SessionLocal()
    task = Task(question=question)    # 创建对象（还没存）
    db.add(task)                      # 加入会话（准备存）
    db.commit()                       # 提交（真正存入数据库）
    db.refresh(task)                  # 刷新，拿到数据库生成的 id 和 created_at
    db.close()                        # 关闭会话
    return task


# ========== 查 ==========
def get_task(task_id: int) -> Task:
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()  # 按 id 查找
    db.close()
    return task


# ========== 改 ==========
def change_task(task_id: int, question: str) -> Task:
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:                  # 先检查存不存在
        db.close()
        return None
    task.question = question          # 直接改属性
    task.status = "done"
    db.commit()                       # 提交修改
    db.refresh(task)
    db.close()
    return task


# ========== 删 ==========
def delete_task(task_id: int) -> bool:
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        db.close()
        return False
    db.delete(task)                   # 标记删除
    db.commit()                       # 真正删除
    db.close()
    return True
```

#### CRUD 核心操作速查

```
增：db.add(task)          → db.commit()
查：db.query(Task).filter(Task.id == 1).first()
改：task.question = "新值" → db.commit()
删：db.delete(task)       → db.commit()
```

#### 常见错误

```python
# 错误：位置参数
task = Task(question)          # TypeError

# 正确：关键字参数
task = Task(question=question) # OK

# 错误：db.delete() 不返回值
task = db.delete(task)         # task 变成 None 了

# 正确：不赋值
db.delete(task)                # OK

# 错误：db.refresh() 需要参数
db.refresh()                   # TypeError

# 正确：传入对象
db.refresh(task)               # OK
```

#### 每次操作都要开/关会话

```python
db = SessionLocal()   # 开会话
# ... 操作 ...
db.close()            # 关会话
```

**为什么要关？** 数据库连接是有限资源，不关的话连接会越来越多，最终数据库拒绝连接。

---

### 第四步：接 FastAPI

文件：`src/api/tasks.py`

```python
from fastapi import APIRouter
from src.models.crud import create_task, get_task, change_task, delete_task

router = APIRouter()

@router.post("/tasks")
def create(question: str):
    task = create_task(question)
    return {"id": task.id, "question": task.question, "status": task.status}

@router.get("/tasks/{task_id}")
def read(task_id: int):
    task = get_task(task_id)
    if task is None:
        return {"error": "not found"}
    return {"id": task.id, "question": task.question, "status": task.status}

@router.put("/tasks/{task_id}")
def update(task_id: int, question: str):
    task = change_task(task_id, question)
    if task is None:
        return {"error": "not found"}
    return {"id": task.id, "question": task.question, "status": task.status}

@router.delete("/tasks/{task_id}")
def delete(task_id: int):
    success = delete_task(task_id)
    if success:
        return {"message": "deleted"}
    return {"error": "not found"}
```

#### HTTP 方法对应 CRUD

| HTTP 方法 | 对应操作 | 路由装饰器 |
|-----------|---------|-----------|
| POST | 创建（Create） | `@router.post("/tasks")` |
| GET | 查询（Read） | `@router.get("/tasks/{task_id}")` |
| PUT | 修改（Update） | `@router.put("/tasks/{task_id}")` |
| DELETE | 删除（Delete） | `@router.delete("/tasks/{task_id}")` |

#### 测试方式

浏览器只能测 GET。POST/PUT/DELETE 要用：
- FastAPI 自动文档：`http://127.0.0.1:8000/docs`（推荐）
- curl 命令行

---

### 完整流程图

```
用户请求
   ↓
FastAPI 路由 (api/tasks.py)     ← 接收 HTTP 请求
   ↓
CRUD 函数 (models/crud.py)     ← 业务逻辑
   ↓
SQLAlchemy ORM (models/task.py) ← 转成 SQL
   ↓
psycopg2 驱动                   ← 发送给数据库
   ↓
PostgreSQL (Docker 容器)        ← 执行 SQL，存数据
```

### 如何自己写一个新的表？

步骤模板：

```
1. models/xxx.py    → 定义模型类（class Xxx(Base): ...）
2. models/crud.py   → 写增删改查函数
3. api/xxx.py       → 写 FastAPI 路由
4. main.py          → 注册路由 app.include_router(xxx_router)
```

---

## 十三、端到端流程（提问→模型回答→存库）

### 为什么需要这个？

之前 FastAPI、Ollama、数据库是各干各的。端到端流程把它们串起来：用户提问 → 调用模型 → 结果存入数据库。

### 接口代码

```python
import re
import ollama
from fastapi import APIRouter
from src.config import config
from src.models.crud import create_task
from src.models.database import SessionLocal

router = APIRouter()

@router.post("/ask")
def ask(question: str):
    # 1. 创建任务，存入数据库
    task = create_task(question)

    # 2. 调用 Ollama 模型回答
    client = ollama.Client(host=config["ollama"]["base_url"])
    response = client.chat(
        model=config["model"]["base_model"],
        messages=[{"role": "user", "content": question}]
    )
    answer = response["message"]["content"]

    # 3. 去掉 <think> 标签（模型的思考过程）
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()

    # 4. 更新任务状态
    task.status = "done"
    db = SessionLocal()
    db.merge(task)
    db.commit()
    db.close()

    return {"id": task.id, "question": question, "answer": answer}
```

### 逐行解释

| 代码 | 作用 |
|------|------|
| `create_task(question)` | 创建任务，存入数据库（status="pending"） |
| `ollama.Client(host=...)` | 创建 Ollama 客户端 |
| `client.chat(model=..., messages=...)` | 调用模型 |
| `response["message"]["content"]` | 取出回复文本 |
| `re.sub(r"<think>.*?</think>", "", ...)` | 用正则去掉模型思考过程 |
| `db.merge(task)` | 把修改后的对象同步到数据库 |
| `db.commit()` | 提交修改 |

### 调用链

```
POST /ask?question=企鹅会飞吗
    ↓
api/tasks.py — 创建任务、调用模型、更新状态
    ↓
crud.py — create_task() 存入数据库
    ↓
database.py — SessionLocal() 拿会话
    ↓
PostgreSQL — 存储任务记录
    ↓
Ollama — qwen3:4b 生成回答
    ↓
返回 JSON — {"id": 6, "question": "...", "answer": "..."}
```

### 常见问题

**Q: `<think>` 标签是什么？**
A: qwen3 模型在回答前会先"思考"，思考过程用 `<think>...</think>` 包裹。用户不需要看到这个，所以用正则去掉。

**Q: 为什么要 `db.merge(task)` 而不是 `db.add(task)`？**
A: `task` 是之前 `create_task` 创建的，已经有 id 了。`merge` 是"更新已有记录"，`add` 是"插入新记录"。如果用 `add` 会报主键冲突。

**Q: 浏览器直接访问 `/ask?question=xxx` 行不行？**
A: 不行。`/ask` 是 POST 接口，浏览器地址栏发的是 GET。要用 `/docs` 页面或 curl 测试。

---

## 十四、Router 理解

### 一个文件一个 router，多个路由

```python
# src/api/tasks.py
router = APIRouter()        # 只有这一个 router

@router.post("/tasks")      # 挂到 router 上
def create(...): ...

@router.get("/tasks/{id}")  # 也挂到同一个 router
def read(...): ...

@router.post("/ask")        # 也是
def ask(...): ...
```

### main.py 只需导入一次

```python
from src.api.tasks import router as tasks_router
app.include_router(tasks_router)    # 一次把所有路由全挂上
```

### 类比

```
router = 一个文件夹
@router.get/post = 文件夹里的文件

tasks.py 的文件夹里有 5 个文件
health.py 的文件夹里有 1 个文件

main.py 问：有几个文件夹？
→ 从每个文件夹拿一次就行了，不用管里面有几个文件
```

---

## 十五、LangGraph 多 Agent 工作流

### 什么是 LangGraph？

用"画流程图"的方式写多 Agent 程序。核心概念就 3 个：

| 概念 | 作用 | 类比 |
|------|------|------|
| State | 节点之间流动的数据包 | 快递包裹 |
| Node | 做事的函数，读 state → 处理 → 返回更新的 state | 流水线上的工人 |
| Edge | 节点之间的连接，支持条件路由 | 传送带 |

### State 定义

```python
from typing import TypedDict

class AgentState(TypedDict):
    question: str                # 用户的问题
    question_type: str           # coordinator 判断的类型
    forward_answer: str          # 前瞻 Agent 的分析
    critical_answer: str         # 批判 Agent 的分析
    creative_answer: str         # 创造 Agent 的分析
    debate_critique: str         # 辩论质疑
    forward_revised: str         # 修正后的前瞻分析
    creative_revised: str        # 修正后的创造分析
    final_answer: str            # 最终综合总结
```

**TypedDict 的作用：** 让 Python 知道 state 有哪些字段、每个字段是什么类型。

### 节点函数的写法

```python
def forward_agent(state: AgentState) -> dict:
    """节点函数：接收 state，返回要更新的字段"""
    question = state["question"]
    answer = call_llm(f"请分析：{question}")
    return {"forward_answer": answer}    # 只返回要更新的字段
```

**关键规则：**
- 参数是 `state`（当前所有数据）
- 返回值是 `dict`（要写入 state 的字段）
- 不需要返回全部字段，只返回要更新的

### 构建图

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(AgentState)    # 创建图，指定 State 类型

graph.add_node("forward", forward_agent)    # 注册节点
graph.add_node("critical", critical_agent)

graph.set_entry_point("coordinator")        # 设置入口

graph.add_edge("forward", "critical")       # 普通边：forward 完了去 critical
graph.add_conditional_edges("coordinator", dispatcher)  # 条件边：根据函数返回值路由

app = graph.compile()            # 编译，生成可执行的应用
```

### 调用方式

```python
result = app.invoke({"question": "如果太阳消失了会怎样"})
print(result["final_answer"])
```

---

## 十六、Send API 并行执行

### 什么是 Send？

**Send 就是"同时把任务发给多个人"。**

```python
from langgraph.types import Send

# 没有 Send：一个一个跑（串行）
forward → critical → creative
总时间 = 10 + 10 + 10 = 30 秒

# 有 Send：同时跑（并行）
Send("forward", state)
Send("critical", state)
Send("creative", state)
总时间 = max(10, 10, 10) = 10 秒
```

### Send 的语法

```python
Send("节点名", state)
#     ↑        ↑
#     │        └─ 发给它的数据
#     └─ 要启动的节点
```

### 返回多个 Send = 同时启动多个节点

```python
def dispatcher(state: AgentState) -> list[Send]:
    return [
        Send("forward", state),     # 同时启动
        Send("critical", state),    # 同时启动
        Send("creative", state),    # 同时启动
    ]
```

### 用法：通过 add_conditional_edges

```python
graph.add_conditional_edges("coordinator", dispatcher)
# dispatcher 返回 [Send("A", s), Send("B", s)]
# → LangGraph 同时启动 A 和 B
```

---

## 十七、条件路由

### add_conditional_edges 的用法

```python
def route_by_type(state: AgentState) -> str:
    if state["question_type"] == "greeting":
        return "direct_answer"      # 返回下一个节点的名字
    else:
        return "forward"

graph.add_conditional_edges("coordinator", route_by_type)
# 根据 route_by_type 的返回值决定去哪个节点
```

### lambda 写法（简短路由）

```python
# 路由逻辑很短时，用 lambda 更简洁
graph.add_conditional_edges(
    "debate_reviewer",
    lambda s: [Send("forward_reviser", s), Send("creative_reviser", s)]
)
```

**lambda = 匿名函数，不取名字，用一次就丢。**

```python
# 普通函数
def add_one(x):
    return x + 1

# lambda（效果一样）
add_one = lambda x: x + 1
```

---

## 十八、辩论-共识协议

### 流程

```
三个 Agent 各自分析（并行）
    ↓
Round 1：debate_reviewer 审视前瞻和创造的分析，提出质疑
    ↓
Round 2：forward_reviser 和 creative_reviser 根据质疑修正（并行）
    ↓
aggregator 综合修正后的分析
```

### 为什么要辩论？

- 没有辩论：三个 Agent 各说各的，可能都有盲点
- 有辩论：批判 Agent 能发现其他 Agent 的错误，其他 Agent 能修正

### 代码示例

```python
def debate_reviewer(state: AgentState) -> dict:
    """Round 1：批判审查"""
    forward = state.get("forward_answer", "")
    creative = state.get("creative_answer", "")
    prompt = f"请审视以下分析，找出逻辑漏洞：\n{forward}\n{creative}"
    critique = call_llm(prompt)
    return {"debate_critique": critique}

def forward_reviser(state: AgentState) -> dict:
    """Round 2：根据质疑修正"""
    original = state.get("forward_answer", "")
    critique = state.get("debate_critique", "")
    prompt = f"你之前的分析：{original}\n批判质疑：{critique}\n请修正"
    revised = call_llm(prompt)
    return {"forward_revised": revised}
```

---

## 十九、sync_point 汇聚节点

### 为什么需要？

三个并行 Agent 速度不同，有的快有的慢。如果没有汇聚节点：
- debate_reviewer 可能被调用三次（每个 Agent 完成都触发一次）
- 浪费计算资源

### 怎么做？

```python
def sync_point(state: AgentState) -> dict:
    """什么都不做，只是等待所有并行任务完成"""
    return {}

# 三个 Agent 都先连到 sync_point
graph.add_edge("forward", "sync_point")
graph.add_edge("critical", "sync_point")
graph.add_edge("creative", "sync_point")

# sync_point 之后统一路由
graph.add_conditional_edges("sync_point", route_after_sync)
```

**类比：** sync_point 就像"集合点"，所有人到齐后再一起出发。

---

## 二十、异常处理

### call_llm 加 try-except

```python
def call_llm(prompt: str) -> str:
    try:
        client = ollama.Client(host=config["ollama"]["base_url"])
        response = client.chat(
            model=config["model"]["base_model"],
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"[模型调用失败: {e}]"
```

**为什么加：** Ollama 挂了、网络断了、模型没响应，不加 try-except 整个图会崩溃。加了之后返回错误信息，流程继续。

---

## 完整流程图

```
coordinator（分类）
    │
    ▼
dispatcher（Send 并行分发）
    │
    ├─ greeting → direct_answer → END
    ├─ factual  → critical → sync_point → aggregator → END
    └─ reasoning → [forward, critical, creative] 并行
                        │
                        ▼
                   sync_point（汇聚等待）
                        │
                        ▼
                   route_after_sync（统一路由）
                        │
                        ▼
                   debate_reviewer（批判审查）
                        │
                        ▼
                   [forward_reviser, creative_reviser] 并行修正
                        │
                        ▼
                   aggregator → END
```

---

## 二十一、LoRA 认知注入训练

### 什么是 LoRA？

不改模型本身，给模型加一个"插件"，让它学会新技能。

```
基座模型（qwen3:4b）= 通才，什么都会一点
LoRA adapter = 专业培训证书，让通才变成专家
```

### LoRA vs 全量微调

| 方式 | 改什么 | 显存需求 | 训练速度 |
|------|--------|---------|---------|
| 全量微调 | 模型所有参数 | ~60GB | 很慢 |
| LoRA | 只训练一个小矩阵 | ~6GB | 快 |

### QLoRA = 量化 + LoRA

```
普通 LoRA：模型用 float16 存储，需要 ~8GB 显存
QLoRA：模型用 4-bit 存储，需要 ~2GB 显存
```

RTX 3060 有 6GB 显存，QLoRA 刚好够用。

### 训练数据格式

```json
{
  "instruction": "你是一个前瞻性推理专家。请从短期、中期、长期分析。",
  "input": "某城市全面禁止燃油车",
  "output": "<reasoning>\n短期：...\n中期：...\n长期：...\n</reasoning>\n最终分析：..."
}
```

**关键：** output 里必须有推理过程，模型才能学会"怎么想"。

### 训练需要的库

```bash
pip install transformers peft bitsandbytes datasets accelerate
```

| 库 | 作用 |
|------|------|
| transformers | 加载和运行模型 |
| peft | LoRA 训练和加载 |
| bitsandbytes | 4-bit 量化（省显存） |
| datasets | 加载和处理训练数据 |
| accelerate | 训练加速 |

### LoRA 关键参数

| 参数 | 含义 | 推荐值 |
|------|------|--------|
| r | LoRA 的秩，越大越强但越慢 | 8-16 |
| alpha | 缩放因子，通常 = 2*r | 16-32 |
| target_modules | 注入 LoRA 的层 | q_proj, v_proj, k_proj, o_proj |

### 训练脚本模板

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
from datasets import load_dataset

# 1. 加载 4-bit 量化模型
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
model = AutoModelForCausalLM.from_pretrained("./models/qwen3-4b", quantization_config=bnb_config)

# 2. 注入 LoRA
lora_config = LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj", "k_proj", "o_proj"])
model = get_peft_model(model, lora_config)

# 3. 加载训练数据
dataset = load_dataset("json", data_files="data/forward_train.json")

# 4. 训练
trainer = SFTTrainer(model=model, train_dataset=dataset, ...)
trainer.train()

# 5. 保存 adapter
model.save_pretrained("./adapters/forward_lora")
```

### 训练后集成到 LangGraph

```python
from peft import PeftModel

# 加载基座模型
base_model = AutoModelForCausalLM.from_pretrained("./models/qwen3-4b", ...)

# 加载 LoRA
forward_model = PeftModel.from_pretrained(base_model, "./adapters/forward_lora")

# Agent 用对应模型生成
answer = forward_model.generate("请前瞻分析：...")
```

### 训练流程总结

```
Step 1: 下载 qwen3-4b HF 版本（约 8GB）
Step 2: 准备训练数据（3 个文件，每个 200-500 条）
Step 3: 写训练脚本
Step 4: 运行训练（每个 1-2 小时）
Step 5: 集成到 LangGraph
Step 6: 测试验证
```

---

## 二十二、train_forward.py 训练脚本（编写进度）

### 脚本整体结构

```python
# Step 2: 导入库
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer
from src.config import config

# Step 3: 量化配置（BitsAndBytesConfig）
# Step 4: 加载模型和分词器
# Step 5: LoRA 配置（从 config.yaml 读 forward 参数）
# Step 6: 加载训练数据
# Step 7: TrainingArguments 训练参数
# Step 8: format_prompt + SFTTrainer + 训练 + 保存（待完成）
```

### 已完成的部分（Step 2-7）

**量化配置** — 用 4-bit 量化省显存：
```python
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)
```

**模型加载** — 从本地路径加载，不从 HF 下载：
```python
MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True, padding_side="right")
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, quantization_config=bnb_config, device_map="auto")
model = prepare_model_for_kbit_training(model)
```

**LoRA 配置** — 从 config.yaml 读取 forward 的参数：
```python
lora_config_dict = config["model"]["lora"]["forward"]
lora_config = LoraConfig(
    r=lora_config_dict['r'],
    lora_alpha=lora_config_dict['alpha'],
    target_modules=lora_config_dict['target_modules'],
    lora_dropout=lora_config_dict['dropout'],
    bias='none',
    task_type='CAUSAL_LM'
)
model = get_peft_model(model, lora_config)
```

**训练数据** — 加载 forward_train.json（500 条）：
```python
dataset = load_dataset("json", data_files="data/forward_train.json", split="train")
```

**TrainingArguments** — 训练超参数：
```python
training_args = TrainingArguments(
    output_dir="./adapters/forward_lora",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,    # 等效 batch_size=16
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    bf16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="none",
)
```

### 待完成的部分（Step 8）

1. **format_prompt 函数** — 将 JSON 数据格式化为 qwen3 对话模板
2. **SFTTrainer 初始化** — 传入模型、数据、参数
3. **trainer.train()** — 开始训练
4. **model.save_pretrained()** — 保存 LoRA 适配器

### 为什么用 SFTTrainer 而不是普通 Trainer？

| Trainer | 用途 |
|---------|------|
| `Trainer` (transformers) | 通用训练，需要自己写数据处理 |
| `SFTTrainer` (trl) | 专门为对话/指令微调设计，自动处理数据格式化 |

SFTTrainer 接受 `formatting_func` 参数，自动把数据格式化成模型需要的格式。

### 训练脚本写完后

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行训练
python scripts/train_forward.py

# 训练完成后，adapters/forward_lora/ 目录下会有：
# - adapter_config.json
# - adapter_model.safetensors
# - checkpoint-xxx/（每个 epoch 的检查点）
```

---

## 二十三、train_forward.py 调试实录（11 个错误及修复）

### 错误 1：ModuleNotFoundError: No module named 'src'

**原因：** Python 找不到项目根目录的 `src` 包。

**修复：** 在脚本顶部加：
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

**为什么不用 `PYTHONPATH` 环境变量？** 写在脚本里更可靠，不需要每次手动设置。

---

### 错误 2：OSError: 页面文件太小

**原因：** 加载 8GB 模型到 16GB RAM 时，Windows 页面文件不够。

**修复 1：** 加 `low_cpu_mem_usage=True`（只载一个分片，不一次性全载入内存）
```python
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config=bnb_config,
    device_map="auto",
    low_cpu_mem_usage=True,    # 关键！
)
```

**修复 2：** 增大 Windows 页面文件（系统 → 高级系统设置 → 性能 → 虚拟内存）。

---

### 错误 3：TypeError: SFTTrainer got unexpected keyword argument 'tokenizer'

**原因：** trl 1.6.0 把参数名从 `tokenizer` 改成了 `processing_class`。

**修复：**
```python
# 旧版本（trl < 1.6.0）
trainer = SFTTrainer(model=model, tokenizer=tokenizer, ...)

# 新版本（trl >= 1.6.0）
trainer = SFTTrainer(model=model, processing_class=tokenizer, ...)
```

---

### 错误 4：CUDA OOM（显存不足）

**原因：** RTX 3060 只有 6GB 显存，`per_device_train_batch_size=4` 太大。

**修复：**
```python
per_device_train_batch_size=1,       # 6GB 显存：每次只喂 1 条
gradient_accumulation_steps=16,      # 累积 16 步 = 等效 batch_size=16
model.gradient_checkpointing_enable() # 用计算换显存
```

**gradient_accumulation_steps 占用显存吗？** 不占用。它只是在 GPU 里多算几次，最后一起更新权重。16 步累积 = 等效于 batch_size=16，但显存占用和 batch_size=1 一样。

---

### 错误 5：bf16 不支持（RTX 3060）

**错误信息：** `"_amp_foreach_non_finite_check_and_unscale_cuda" not implemented for 'BFloat16'`

**原因：** RTX 3060 不支持 bf16（只有 A100/H100 等高端卡支持）。同时用了两个 bf16 相关的配置：量化时用 bf16 compute dtype，TrainingArguments 又开了 bf16 AMP，导致冲突。

**修复：**
```python
# 1. bnb 配置：改用 float16
bnb_4bit_compute_dtype=torch.float16    # 不要 torch.bfloat16

# 2. TrainingArguments：删除 fp16=True（4-bit 量化内部处理精度）
# 不要加 fp16=True，会与量化冲突
```

**规则：** 4-bit 量化训练时，不需要在 TrainingArguments 里设置 fp16 或 bf16。量化层已经处理了精度转换。

---

### 错误 6：pad_token 缺失导致格式错误

**原因：** Qwen3 分词器默认没有 `pad_token`，训练时 SFTTrainer 需要它来填充不等长的句子。

**修复：**
```python
tokenizer.pad_token = tokenizer.eos_token    # 用 eos_token 充当 pad_token
```

**pad_token 是什么？** 一个 batch 里句子长度不同时，短的句子末尾补 pad_token，让所有句子等长。

```
句子A: 你好，请回答问题 [PAD] [PAD] [PAD]
句子B: 你好
→ pad_token_id 填充后长度一致
```

---

### 错误 7：Qwen3 对话模板格式错误

**错误格式（训练数据不可用）：**
```
Human: 你好
Assistant: 你好！
```

**正确格式（Qwen3 chat template）：**
```
<|im_start|>user
{instruction}
{input}
<|im_end|>
<|im_start|>assistant
{output}
<|im_end|>
```

**format_prompt 函数：**
```python
def format_prompt(sample):
    return f"""<|im_start|>user
{sample['instruction']}
{sample['input']}
<|im_end|>
<|im_start|>assistant
{sample['output']}
<|im_end|>"""
```

**核心规则：** 每条消息以 `<|im_start|>角色名` 开头，以 `<|im_end|>` 结尾。模型在训练时只看 `<|im_start|>assistant` 之后的内容来学习。

---

### 错误 8：训练过程不可见

**原因：** `logging_steps=10`，每 10 步才打印一次 loss。batch_size=1 时，训练几百步才看到一次输出。

**修复：**
```python
logging_steps=1    # 每步都打印 loss
```

同时加 `MetricsLogger` 回调，把每步的 loss、grad_norm、entropy、accuracy 存到 JSON 文件：
```python
class MetricsLogger(TrainerCallback):
    def __init__(self):
        self.history = []
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and 'loss' in logs:
            self.history.append(logs)

metrics_logger = MetricsLogger()
trainer.add_callback(metrics_logger)

# 训练结束后保存
json.dump(metrics_logger.history, open("training_log.json", "w"))
```

---

### 错误 9：SFTTrainer 没有显式指定损失函数和优化器

**问题：** 为什么看不到 Loss 和 Optimizer 的定义？

**答案：** SFTTrainer 自动处理了：

| 组件 | 默认值 | 说明 |
|------|--------|------|
| 损失函数 | 交叉熵损失（CrossEntropyLoss） | CausalLM 默认 |
| 优化器 | AdamW | TrainingArguments 传参，自动创建 |
| 学习率调度 | cosine（你在参数里指定的） | 自动管理 |

**如何自定义？**
```python
from torch.optim import SGD
trainer = SFTTrainer(model=model, optimizers=(SGD(...), None), ...)
```

---

### 错误 10：训练指标解读

**5 个 epoch 训练结果：**

| 指标 | Epoch 1 | Epoch 5 | 变化 | 含义 |
|------|---------|---------|------|------|
| loss | 2.55 | 1.47 | ↓42% | 模型越来越"确定"正确答案 |
| accuracy | 47.8% | 59% | ↑22% | Token 预测准确率提升 |
| grad_norm | 0.24-0.67 | 稳定 | — | 梯度健康，没有爆炸 |
| entropy | 1.33→2.28→1.52 | 先升后降 | — | 见下文 |

**entropy 为什么先升后降？**
```
阶段1: 模型瞎自信（entropy 低，实际预测是错的）
阶段2: 模型意识到自己不会（entropy 升高，开始探索）
阶段3: 模型学会了（entropy 回落，预测变准）
```

**grad_norm 在 epoch 边界震荡？** 正常——每个 epoch 结束时会更新权重，新 epoch 开始时梯度自然变大。只要不持续增大（爆炸），就是健康的。

---

### 错误 11：训练数据与 Ollama 的关系

**混淆点：** 训练用的本地 HF 模型和 Ollama 的 qwen3:4b 是否冲突？

**澄清：** 两条独立路径：
```
训练路径: train_forward.py → models/qwen3-4b/（本地 HF 文件） → adapters/forward_lora/
推理路径（旧）: graph.py → ollama API → Ollama 服务 → qwen3:4b（Ollama 管理的模型）
推理路径（新）: graph.py → lora_inference.py → 本地 HF 模型 + LoRA adapter
```

---

## 二十四、LoRA 参数计算

### 为什么 Forward LoRA 只有 ~500 万可训练参数？

**LoRA 原理：** 不直接改权重矩阵 W，在 W 旁边挂两个小矩阵 A 和 B。

```
y = W·x + B·(A·x)

W 形状: (2560, 2560)   ← 冻结，不训练
A 形状: (8, 2560)      ← 训练
B 形状: (2560, 8)      ← 训练
```

**计算：**
```
每层: 4 个模块 (q_proj, k_proj, v_proj, o_proj)
每模块: (8×2560) + (2560×8) = 40,960 参数
每层: 4 × 40,960 = 163,840 参数
Qwen3-4B 约 36 层: 36 × 163,840 ≈ 5,898,240

实际约 500 万+（因 GQA 机制，k_proj/v_proj 形状略小）
```

**占比：** 500 万 / 40 亿 ≈ 0.12%。用 0.12% 的参数引导模型风格。

---

## 二十五、LoRA 推理验证（test_lora.py）

### 为什么需要验证？

训练完不能直接集成——先确认 LoRA 真的改变了模型，否则集成后才发现问题是浪费时间。

### 验证策略

```
同一道题 → 基座模型（无 LoRA） → 答案 A
         → LoRA 模型             → 答案 B
         
对比 A 和 B：
  - LoRA 是否更结构化（分步骤/阶段）？
  - LoRA 是否有 "最终分析" 式总结句？
  - LoRA 是否更注重因果链推理？
```

### 关键注意：4-bit 模型不能 merge_and_unload

```python
# 错误！4-bit 量化模型调用 merge_and_unload() 会报错
lora_model.merge_and_unload()

# 正确：直接用 PeftModel 推理
lora_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
output = lora_model.generate(...)
```

---

## 二十六、LoRA 集成到 LangGraph（替换 Ollama）

### 核心挑战：6GB 显存不能同时跑两个模型

```
Ollama qwen3:4b:  ~4-5GB 显存
本地 4-bit 模型:  ~4GB 显存
同时跑:           ~8-9GB > 6GB → OOM
```

### 解决方案：一个模型，两种用法

```
基座模型（4-bit，~4GB） ──── 无 LoRA  ──→ 其他 Agent（与 Ollama 能力等同）
                        └── +LoRA   ──→ forward_agent / forward_reviser
```

### lora_inference.py 模块设计

```
全局单例（只加载一次）:
  _base_model   = 纯基座（不加任何 LoRA）
  _lora_models  = {"forward": PeftModel, "critical": ..., "creative": ...}

generate_base(prompt)           → 用 _base_model 生成
generate_lora(prompt, "forward") → 用 _lora_models["forward"] 生成
```

**为什么 PeftModel 不额外占显存？** 底层权重是共享的（同一个 Python 对象），LoRA 只加了几个小矩阵（几 MB）。

### call_llm 改造

```python
def call_llm(prompt: str, use_lora: str = None) -> str:
    """use_lora=None → 基座模型; "forward" → forward LoRA"""
    if use_lora:
        return generate_lora(prompt, use_lora)
    else:
        return generate_base(prompt)

# Agent 调用
forward_agent:     call_llm(prompt, use_lora="forward")  # 有 LoRA
forward_reviser:   call_llm(prompt, use_lora="forward")  # 有 LoRA
其他所有 Agent:     call_llm(prompt)                      # 无 LoRA
```

---

## 二十七、ML 模型部署的铁律（踩坑实录）

### 坑 1：CUDA 初始化必须在主线程

**现象：** 在 uvicorn 请求线程里加载模型 → 死锁，进度条永远 0%。

**根因：** PyTorch 的 CUDA 上下文绑定到创建它的线程。FastAPI 的同步请求运行在线程池子线程中，在线程池里创建 CUDA 上下文会和 PyTorch 主线程的部分初始化状态冲突。

```
✅ test_lora.py:    主线程 → from_pretrained() → 16 秒完成
❌ uvicorn 线程池:   子线程 → from_pretrained() → 死锁
```

**修复：** 在 FastAPI 创建之前加载模型：
```python
# main.py
from src.agents.lora_inference import preload
preload()    # ← 主线程执行，在 FastAPI 创建之前完成

app = FastAPI()
```

**铁律：启动时加载，请求时推理。** 永远不要让用户的请求触发模型加载。

---

### 坑 2：Ollama stop 不等于 Ollama 退出

**现象：** `ollama stop` 后模型卸载了，但加载本地模型仍然卡住。

**根因：** `ollama stop` 只卸载了模型权重，Ollama 进程还活着，持有着 CUDA 上下文。

```
ollama stop  → 卸载模型（释放显存），进程仍在（占用 CUDA 上下文）
ollama.exe   → 进程 + CUDA 上下文仍在
```

**修复：**
```powershell
taskkill /F /IM ollama.exe    # 彻底杀掉 Ollama 进程
```

---

### 坑 3：模型加载需要足够物理内存

**现象：** 加载到 41%（165/398）时进程崩溃。

**根因：** Qwen3-4B 的 safetensors 分片每个 ~3.8GB，即使 `low_cpu_mem_usage=True` 每次只载一个分片，单个分片也必须完全装入 RAM。

```
可用内存: 3.1GB
分片大小: 3.8GB  →  装不下 → 崩溃
```

**修复：**
- 关闭 Chrome（释放 ~1.5GB）
- 关闭 Docker Desktop / WSL（释放 ~440MB）
- 确保可用内存 > 4GB

**教训：** 加载大模型前，先检查可用内存。8GB 模型虽然是 4-bit 存 GPU，但加载过程需要把 fp16 分片读进内存再量化。

---

### 坑 4：Docker 容器重启后不会自动启动

**现象：** 之前 CRUD 操作正常，现在 `Connection refused`。

**根因：** Docker 容器默认不自动启动。电脑重启后 `cognitive_postgres` 和 `cognitive_redis` 退出。

```
docker ps -a    → STATUS: Exited (0) 5 days ago    ← 5 天前就停了
```

**修复：**
```powershell
docker start cognitive_postgres cognitive_redis
```

**如何设置开机自启：** 在 `docker-compose.yml` 里加 `restart: unless-stopped`。

---

## 二十八、完整 debug 方法论小结

```
排查流程：
  1. nvidia-smi              → 显存够吗？有残留进程吗？
  2. tasklist / 任务管理器    → 内存够吗？谁在吃内存？
  3. docker ps -a            → 数据库容器活着吗？
  4. 最小复现脚本             → 剥离 FastAPI/数据库等干扰
  5. 对比能跑的脚本           → 差异在哪？
```

**一个原则：** 出现奇怪问题时，先写最小复现脚本（如 `debug_uvicorn.py`），只包含最小逻辑。如果最小脚本都跑不通，问题一定在更底层。
