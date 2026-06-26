# CognitiveProbe 自测题

> 覆盖：虚拟环境、requirements.txt、配置管理、FastAPI、Docker、Git、SQLAlchemy
> 建议：先自己想，想不起来再看笔记，不要直接翻答案

---

## 第一部分：基础题（填空 / 选择）

### Q1. 虚拟环境
创建虚拟环境的命令是 `______python -m venv .venv__________`，激活命令是 `____.venv/Scripts/Activate.ps1____________`。

### Q2. 虚拟环境
为什么需要虚拟环境？（多选）BC
- A. 让代码跑得更快
- B. 隔离不同项目的依赖
- C. 防止包版本冲突
- D. 自动安装所有依赖

### Q3. requirements.txt
`torch==2.1.0` 和 `torch>=2.1.0` 的区别是什么？第一个是必须等于这个版本，第二个是这个版本及以上

### Q4. requirements.txt
安装 requirements.txt 中所有依赖的命令是 `___pip install -r requirements.txt_____________`。

### Q5. 配置管理
`config.py` 中 `ROOT_DIR = Path(__file__).parent.parent` 的作用是什么？为什么要 `.parent.parent`？
file地址的二级父地址，这样能包含项目所有代码
### Q6. 配置管理
为什么用全局变量 `config = load_config()` 而不是每次调用 `load_config()`？
方便，调用一次即可
### Q7. FastAPI
`@app.get("/health")` 中的 `@` 符号叫什么？它的作用是什么？
修饰器，我也不直到
### Q8. FastAPI
`APIRouter()` 和 `FastAPI()` 的区别是什么？为什么要把路由拆分到单独的文件？
应该是看上去更简洁更方便
### Q9. FastAPI
运行 FastAPI 的命令是 `__uvicorn main：app --reload______________`，`--reload` 参数的作用是 `___持续加载_____________`。

### Q10. Ollama
在 Python 中调用 Ollama 模型，创建客户端的代码是：
```python
client = ollama.Client(host=__127.0.0.1：11434______________)
```
这里应该填什么？为什么不直接写 `"http://localhost:11434"`？
不知道
### Q11. Ollama
`response["message"]["content"]` 中，为什么是 `message`（单数）而不是 `messages`（复数）？
因为message是response的参数，messages是我们自己定义变量
### Q12. Docker
`docker compose up -d` 中 `-d` 的作用是什么？
忘了
### Q13. Docker
`ports: "5432:5432"` 中，左边的 5432 和右边的 5432 分别代表什么？
左边表示本机的端口，右边表示docker的端口，做了个映射
### Q14. Docker
`volumes: - postgres_data:/var/lib/postgresql/data` 的作用是什么？不写会怎样？
忘了
### Q15. Git
`git add .` 和 `git commit -m "说明"` 的区别是什么？能不能跳过 `git add` 直接 `git commit`？
一个是准备阶段，一个是提交，必须把想要提交的文件修改成待提交的状态才能提交
### Q16. Git
`.gitignore` 的作用是什么？如果 `.gitignore` 里写了 `.venv/`，但你已经 `git add .venv/` 了，`.gitignore` 还生效吗？
1.忽略不想提交的文件2.不会
### Q17. SQLAlchemy
ORM 的全称是什么？它解决了什么问题？
对象关系映射？可以直接使用python操作数据库
### Q18. SQLAlchemy
`Column(Integer, primary_key=True)` 中 `primary_key=True` 的作用是什么？
应该是主键，具体我也不知道
### Q19. SQLAlchemy
为什么 `default=datetime.now(timezone.utc)` 要写成 `default=lambda: datetime.now(timezone.utc)`？
不知道
### Q20. SQLAlchemy
`db.add(task)` 之后，数据已经存入数据库了吗？还需要做什么？
db.commit() db.refresh(task) db.close()
---

## 第二部分：代码阅读题

### Q21. 读代码，写输出
```python
from src.config import config
print(config["model"]["base_model"])
print(config["ollama"]["base_url"])
```
假设 config.yaml 内容如下，输出是什么？qwen3:4b http://localhost:11434
```yaml
model:
  base_model: "qwen3:4b"
ollama:
  base_url: "http://localhost:11434"
```

### Q22. 读代码，找错误
```python
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    question = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
```
这段代码有一个问题，是什么？怎么改？datetime.now(timezone.utc)应该改成lambda，但是我不会

### Q23. 读代码，找错误
```python
def create_task(question: str) -> Task:
    db = SessionLocal()
    task = Task(question)
    db.add(task)
    db.close()
    return task
```
这段代码有 2 个错误，分别是什么？task = Task(question=question) db.commit() db.refresh(task)

### Q24. 读代码，找错误
```python
def delete_task(task_id: int) -> bool:
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        return False
    task = db.delete(task)
    db.commit()
    db.close()
    return True
```
这段代码有 1 个错误，是什么？
task = db.delete(task) 删除task=
### Q25. 读代码，写输出
```python
@app.get("/config")
def get_config():
    return config
```
访问 `http://127.0.0.1:8000/config` 会返回什么？（提示：config 是一个 Python 字典）
输出配置的参数
---

## 第三部分：代码补全题

### Q26. 补全 FastAPI 路由
补全下面的代码，让它成为一个能返回 `{"status": "ok"}` 的健康检查接口：
```python
from fastapi import __FastAPI__

app = __FastAPI（）__

@app._get___("/health")
def health():
    return _{"status": "ok"}___
```

### Q27. 补全数据库连接
补全 database.py，从 config 读取数据库配置：
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config

db = config[__“database”__]
DATABASE_URL = f"postgresql://{db[_“user”___]}:{db[_“password”___]}@{db[__？？？__]}:{db[_“port”___]}/{db[__“name”__]}"

engine = create_engine____(DATABASE_URL)
SessionLocal = __sessionmaker__(bind=engine)
```

### Q28. 补全 CRUD 函数
补全 `get_task` 函数：
```python
def get_task(task_id: int) -> Task:
    db = _SessionLocal___()
    task = db._query___(Task)._filter___(Task.id == task_id).__first__()
    db._close___()
    return task
```

### Q29. 补全 FastAPI 路由
补全 DELETE 接口，调用 `delete_task` 函数：
```python
from fastapi import APIRouter
from src.models.crud import delete_task

router = APIRouter()

@router._delete___("/tasks/{task_id}")
def delete(_task_id___: int):
    success = _delete_task___(task_id)
    if success:
        return {"message": "deleted"}
    return {"error": "not found"}
```

### Q30. 补全 docker-compose.yml
补全 PostgreSQL 服务配置：
```yaml
services:
  postgres:
    image: ____
    container_name: ____
    environment:
      POSTGRES_USER: ____
      POSTGRES_PASSWORD: ____
      POSTGRES_DB: ____
    ports:
      - __5432__
    volumes:
      - ____
```
全忘了
---

## 第四部分：简答题

### Q31.
画出这个项目的调用链：用户发一个 POST 请求创建任务，经过了哪些文件、哪些函数？从 `main.py` 开始到 PostgreSQL 结束。
用户请求-main-router-crud-数据库

### Q32.
`config.yaml` 和 `docker-compose.yml` 里都有数据库的配置，为什么要写两遍？它们各自给谁用？
一个是配置的变量，主要用python加载，第二个是docker的变量，两者需一致
### Q33.
解释 `SessionLocal` 是什么，为什么每次操作数据库都要 `SessionLocal()` 开会话、`db.close()` 关会话？
创建一个数据库的对话，每次都要手动开启和关闭
### Q34.
为什么 `crud.py` 里的每个函数都要单独 `SessionLocal()` 和 `db.close()`，而不是在文件开头创建一个全局的 db？
有次数限制，必须用的时候再开启，否则容易崩溃
### Q35.
`.gitignore` 里写了 `__pycache__/`，但你发现 `git status` 里还是出现了 `__pycache__` 文件，可能是什么原因？（提示：拼写）
不知道
---

## 第五部分：实战题（手写代码）

### Q36.
从零开始创建一个新的表 `AgentLog`，字段如下：
- `id`：主键
- `agent_name`：字符串，不能为空
- `input_text`：字符串，不能为空
- `output_text`：字符串
- `duration_ms`：整数
- `created_at`：时间戳

写出 `agent_log.py` 的完整代码。
from sqlalchemy import Integer, String, Column, Datetime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

class AgentLog(Base):
    __tablename__ = "agentlog"

    id = Column(Integer, primay_key = True)
    agent_name = (String, allow_none = False)
    input = (String, allow_none = False)
    output = (String)
    duration_ms = (Integer)
    created_at = (Datetime)
### Q37.
为 Q36 的 `AgentLog` 表写 `create_agent_log` 和 `get_agent_log` 两个 CRUD 函数。
def create_agent_log(question: str):
    agentlog = AgentLog(input = question)
    db = SessionLocal()
    db.add(agentlog)
    db.commit()
    db.refresh(agentlog)
    db.close()
    return {"id": agentlog.id, "input":agentlog.input}

def get_agent_log(agent_id: int):
    agentlog = AgentLog()
    不确定了

### Q38.
为 Q37 的 CRUD 函数写 FastAPI 路由，包含创建和查询两个接口。

### Q39.
写一个完整的 `docker-compose.yml`，包含：
- PostgreSQL（端口 5432）
- Redis（端口 6379）
- 自定义网络

### Q40.
写一个 `config.yaml`，包含以下配置：
- 模型名：qwen3:4b
- Ollama 地址：http://localhost:11434
- 数据库连接信息（host, port, user, password, name）
- 三个 LoRA Agent 的 rank 配置（forward: 8, critical: 12, creative: 16）

---

## 附加：面试模拟题

### Q41.
面试官问："你的项目用了 SQLAlchemy ORM，为什么不直接写 SQL？"
使用python操作数据库不仅直观，而且方便，ide可以进行提示
### Q42.
面试官问："你的 FastAPI 项目是怎么组织代码的？为什么这样分层？"
main里主要是各个路由的router，把不同的router放到不同的任务中，这样更直观，修改也方便
### Q43.
面试官问："你的 docker-compose.yml 里为什么用 volumes？不写会有什么问题？"
不会
### Q44.
面试官问："你的项目配置是怎么管理的？换环境怎么办？"
主要通过维护config.yaml进行管理，换个环境只需要重新下载requirements.txt文件和config.yaml就可以，或是用docker上传
### Q45.
面试官问："Git 的 add 和 commit 分别做了什么？为什么不能跳过 add？"
add主要把要提交的文件进入准备状态，相当于做一个本地的缓冲。为什么不知道