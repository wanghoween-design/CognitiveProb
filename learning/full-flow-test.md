# CognitiveProbe 全流程自测题

> 按真实开发顺序排列：从创建项目到数据库增删改查
> 不给答案，做完找 Claude 批改
> 建议：先自己写，写不出来说明那个知识点没掌握，回去看笔记

---

## 阶段一：项目初始化（虚拟环境 + 依赖）

### 1. 在项目根目录创建虚拟环境，写出命令。
python -m .venv venv

### 2. 激活虚拟环境的命令是什么？（Windows）
.\venv\Scripts\Activate.ps1

### 3. 创建 `requirements.txt`，写入以下依赖：
- pyyaml，最低版本 6.0
- fastapi，最低版本 0.104.0
- uvicorn，最低版本 0.24.0
- ollama，最低版本 0.3.0
pyyaml>=6.0
fastapi>=0.104.0
uvicorn>=0.24.0
ollama>=0.3.0

### 4. 安装 requirements.txt 中所有依赖的命令是什么？
pip install -r requirements.txt

### 5. 为什么要用虚拟环境？不用会怎样？
隔离全局环境，避免冲突，不用的话会出现版本不兼容的情况

### 6. `torch==2.1.0` 和 `torch>=2.1.0` 的区别是什么？
第一个强制要求版本为2.1.0，第二个是不低于这个版本
---

## 阶段二：配置管理（config.yaml + config.py）

### 7. 创建 `configs/config.yaml`，包含以下配置：
- 模型名：qwen3:4b
- 嵌入模型名：nomic-embed-text
- Ollama 地址：http://localhost:11434
- Ollama 超时时间：120 秒
model:
    model_name: qwen3:4b
    embedding: nomic-embed-text
Ollama:
    url:http://localhost:11434
    time:120

### 8. 为什么不把模型名、端口号直接写在代码里，而要放在 YAML 文件中？
只需要维护yaml文件就可以了，很方便，而且不需要动源码
### 9. 创建 `src/config.py`，写一个配置加载器，要求：
- 能找到项目根目录下的 `configs/config.yaml`
- 解析 YAML 返回字典
- 创建全局配置实例
```python
from pathlib import Path
import yaml

ROOTDIR = Path(__file__).parent.parent
def load_config(path: str = None)-> dict:
    if path is None:
        path = ROOTDIR / "configs" / "config.yaml"
    with open(path, 'r', encoding = "utf-8") as f:
        return yaml.safeload(f)

config = load_config()

```

### 10. `Path(__file__).parent.parent` 中，`__file__` 是什么？`.parent.parent` 为什么要两次？
1.当前的文件夹2.二级父文件夹 ，能炸到当前项目中的所有文件夹

### 11. 为什么用全局变量 `config = load_config()` 而不是每次调用函数？
方便

### 12. 写一段代码，从 config 中读取模型名并打印。
```python
from src.configs import config
print(config['model']['name'])

```
---

## 阶段三：FastAPI 基础

### 13. 创建 `src/main.py`，写一个最小的 FastAPI 应用，只有一个 `/health` 接口返回 `{"status": "ok"}`。
```python 
from fastapi import FastAPI

app = FastAPI()
@app.get("/health")
def health():
    return {"status": "ok"}
```
### 14. 运行 FastAPI 的命令是什么？`--reload` 的作用是什么？
uvicorn main:app --reload 持续加载，就算修改代码也不影响运行

### 15. `@app.get("/health")` 中的 `@` 叫什么？它的作用是什么？
修饰器，作用是忘记了
### 16. 访问 `http://127.0.0.1:8000/docs` 会看到什么？为什么？
会看到一个网页，里面有所有的路由，可以进行测试
### 17. 在 main.py 中加一个 `/config` 接口，返回 config 的全部内容。
from src.configs import config

app = FastAPI()

@app.get("/config")
def get_config(config: str):
    return config

### 18. `return config` 时，FastAPI 做了什么转换？
不知道T。T
---

## 阶段四：Ollama 连接

### 19. 安装 ollama Python 库的命令是什么？
pip install Ollama

### 20. 写一段 Python 代码，调用 Ollama 的 qwen3:4b 模型，发送"你好"，打印回复。
client = Ollama.Client(host = "localhost:11434")
response = client.chat(model = "qwen3:4b", messages = [{"role": "user", "content": "你好"}])
print(response['message']['content'])

### 21. 创建客户端时，`host` 参数为什么不直接写 `"http://localhost:11434"`，而要从 config 读取？
不写死方便维护

### 22. `response["message"]["content"]` 中，为什么是 `message`（单数）而不是 `messages`（复数）？
message是response的参数，messages啥也不是

### 23. 把 Ollama 调用封装成一个 FastAPI 接口 `/test_llm`，写出来。
```python
from src.configs import config
from fastapi import APIRouter
import Ollama

router = APIRouter()

@router.get("/test_llm")
def test_llm():
    client = Ollama.Client(host = config['ollama']['url'] )
    response = client.chat(model = config['model']['name'],
                            message = [{"role":"user", "content":"你好"}])
    return {"response": response['message']['content']}

```
---

## 阶段五：项目结构（路由拆分）

### 24. 为什么要用 `APIRouter` 把路由拆分到不同文件？不拆会怎样？
把不同功能的路由拆分到不同文件中便于查找和维护，不拆会很臃肿
### 25. `APIRouter()` 和 `FastAPI()` 的区别是什么？
APIRouter是子路由，有很多，但是FastAPI只有一个，负责统筹各个子路由
### 26. 创建 `src/api/health.py`，把 `/health` 接口从 main.py 搬过去。
```py
from fastapi import APIRouter

router = APIRputer()
@router.get("/health")
def health():
    return {"status":"health"}
```
### 27. 改写 `src/main.py`，让它只负责注册路由，不包含具体接口逻辑。
from src.api.health import router as health_router
from fastapi import FastAPI

app = FastAPI()
app.include_router(health_router)

### 28. `app.include_router(health_router)` 这行代码做了什么？
把子路由health_router集合到主路由中
### 29. 画出当前项目的目录结构，标注每个文件的职责。
src/main.py
src/api/health.py
---

## 阶段六：Git 版本控制

### 30. `.gitignore` 的作用是什么？
把不提交的文件或文件夹写进去，在提交的时候自动忽略
### 31. 写一个 `.gitignore`，排除以下内容：
- 虚拟环境
- Python 缓存
- 环境变量文件
- IDE 配置
- 训练产出

这个我只知道一点
.venv
__pycache__


### 32. 初始化 Git 仓库的命令是什么？
git init

### 33. 设置 Git 用户名和邮箱的命令是什么？
忘了
### 34. `git add .` 和 `git commit -m "说明"` 分别做了什么？能不能跳过 add？
不能跳过，git add .是把当前文件夹所有的文件都添加到待上传的状态，属于是缓冲区，git commit是真正要上传的
### 35. 把本地仓库推送到 GitHub 的完整命令序列是什么？
不记得了，不过以后有你，我让你提交
### 36. `.gitignore` 里写了 `.venv/`，但 `git status` 里还是出现了 `.venv/`，可能是什么原因？
不知道
---

## 阶段七：Docker Compose

### 37. 写一个 `docker-compose.yml`，包含：
- PostgreSQL 16，端口 5432，用户名 postgres，密码 postgres123，数据库名 cognitive_probe
- Redis 7，端口 6379
不会，这个以后都让你写
### 38. `ports: "5432:5432"` 中，左边和右边分别代表什么？
左边是本机的端口，右边是docker的端口
### 39. `volumes: - postgres_data:/var/lib/postgresql/data` 的作用是什么？不写会怎样？
卷，写了之后就算删掉容器也会保留记录
### 40. `docker compose up -d` 中 `-d` 的作用是什么？
后台运行
### 41. 查看 Docker 容器运行状态的命令是什么？
docker compose status
### 42. 停止所有容器的命令是什么？
忘了
### 43. 你的 `config.yaml` 和 `docker-compose.yml` 里都有数据库配置，为什么要写两遍？
一个是配置的参数，方便在程序中调用；另一个是给docker的约束，说明容器的版本
---

## 阶段八：SQLAlchemy ORM —— 定义模型

### 44. ORM 的全称是什么？它解决了什么问题？
对象关系映射，可以使用python调用数据库，方便高效
### 45. 创建 `src/models/task.py`，定义一个 `Task` 表，字段：
- id：主键
- question：字符串，不能为空
- status：字符串，默认 "pending"
- created_at：时间戳，自动填入当前时间
```python
from sqlalchemy import Integer, String, Column, Datetime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key = True)
    question = Column(String, nullable = False)
    status = Column(String, default = "pending")
    create_at = Column(Datetime, default = lambda: datetime.now(timezone.utc))

```
### 46. `Column(Integer, primary_key=True)` 中 `primary_key=True` 的作用是什么？
主键，唯一标识
### 47. `default=datetime.now(timezone.utc)` 和 `default=lambda: datetime.now(timezone.utc)` 的区别是什么？为什么必须用 lambda？
确保每个对象的时间是不一样的
### 48. `nullable=False` 和 `nullable=True` 的区别是什么？
是否允许为空
### 49. `DeclarativeBase` 的作用是什么？每个模型类为什么要继承它？
继承父类，因为他是python创建数据库表单的要求
### 50. `__tablename__ = "tasks"` 的作用是什么？不写会怎样？
表单名字，不写就没有名字了
---

## 阶段九：SQLAlchemy ORM —— 数据库连接

### 51. 创建 `src/models/database.py`，写出：
- 从 config 读取数据库配置
- 拼接 DATABASE_URL
- 创建 engine
- 创建 SessionLocal
from src.configs import config
db = config['database']
DATABASE_URL = f"postgresql://{db['user']}:{db['password']@{db['host']}:{db['port']}/{db['name']}}"
engine = 后面的不会了，这里确实忘了
### 52. `create_engine(DATABASE_URL)` 的作用是什么？
忘了
### 53. `SessionLocal` 是什么？为什么叫"会话工厂"？
不会
### 54. 为什么每次操作数据库都要 `SessionLocal()` 开会话、`db.close()` 关会话？不关会怎样？
忘了
### 55. 为什么不在文件开头创建一个全局的 db，而是每个函数单独创建？
不会
---

## 阶段十：SQLAlchemy ORM —— CRUD 操作

### 56. 创建 `src/models/crud.py`，写 `create_task` 函数：
- 接收 question 参数
- 创建 Task 对象
- 存入数据库
- 返回 Task 对象
def create_task(question: str):
    task = Task(question = question)
    db = SessionLocal()
    db.add(task)
    db.commit()
    db.refresh(task)
    db.close()
    return task




### 57. 写 `get_task` 函数，根据 id 查询任务。`db.query(Task).filter(Task.id == task_id).first()` 中，`.first()` 的作用是什么？
def get_task(task_id: int)-> Task:
    db = SessionLocal()
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        db.close()
        return False
    db.close()
    return task
    
### 58. 写 `change_task` 函数，修改指定任务的 question 和 status。
def change_task(question: str, status: str, task_id: int)->Task:
    db = SessionLocal()
    task = db.query(Task).filter(task_id == Task.id).first()
    if task is None:
        db.close()
        return False
    task.question = question
    task.status = status
    db.commit()
    db.refresh(task)
    db.close()
    return task
### 59. 写 `delete_task` 函数，删除指定任务。为什么删之前要先查出来？
def delete_task(task_id: int)->bool:
    db=SessionLocal()
    task = db.query(Task).filter(task_id == Task.id).first()
    if task is None:
        db.close()
        return False
    db.delete(task)
    db.commit()
    db.close()
    return True
### 60. `db.add(task)` 之后，数据已经存入数据库了吗？还需要做什么？
没有，必须db.commit()
### 61. `db.delete(task)` 之后，数据已经从数据库删了吗？还需要做什么？
也需要commit？
### 62. CRUD 四个函数的共同结构是什么？（提示：开头和结尾）
开启和关闭对话db=SessionLocal()和db.close()
---

## 阶段十一：FastAPI 路由接入 CRUD

### 63. 创建 `src/api/tasks.py`，写出 4 个路由：
- POST /tasks — 创建任务
- GET /tasks/{task_id} — 查询任务
- PUT /tasks/{task_id} — 修改任务
- DELETE /tasks/{task_id} — 删除任务
@router.post("/tasks")
def create_task():

### 64. HTTP 的 POST、GET、PUT、DELETE 分别对应 CRUD 的哪个操作？
post是增，get是查，put是改，d是删除
### 65. 浏览器地址栏直接访问是 GET 还是 POST？为什么不能用浏览器测试创建任务？
get，不知道
### 66. 如何测试 POST、PUT、DELETE 接口？
我一般都在docs里测试
### 67. 在 main.py 中注册 tasks 路由，写出代码。
不会
---

## 阶段十二：端到端验证

### 68. 启动 Docker Compose（PostgreSQL + Redis）的命令是什么？
docker compose -d
### 69. 验证 tasks 表是否建好的命令是什么？
忘了
### 70. 启动 FastAPI 服务器的命令是什么？
uvicorn main:app --reload
### 71. 写出从创建任务到查询任务的完整测试流程（包括用什么工具、访问什么地址）。
好难
### 72. 如果访问 `/tasks/1` 返回 `{"error": "not found"}`，可能是什么原因？
1.没创建；2.删掉了
---

## 阶段十三：综合题

### 73. 从零开始，写出一个新表 `AgentLog` 的完整代码：
- 模型定义（agent_log.py）
- 数据库连接（可复用 database.py）
- CRUD 操作（create 和 get）
- FastAPI 路由（POST 和 GET）
- 在 main.py 中注册路由

### 74. 画出这个项目的完整调用链：用户发 POST 请求创建任务，从 main.py 到 PostgreSQL，经过了哪些文件和函数？

### 75. 画出项目的目录结构，标注每个文件只有 1-2 个职责。

### 76. 如果你要给项目加一个新功能"用户管理"，需要创建哪些文件？按什么顺序？

### 77. 面试官问："你的项目用了 SQLAlchemy ORM，为什么不直接写 SQL？"你怎么回答？

### 78. 面试官问："你的 FastAPI 项目是怎么组织代码的？为什么这样分层？"你怎么回答？

### 79. 面试官问："你的 docker-compose.yml 里为什么用 volumes？不写会有什么问题？"你怎么回答？

### 80. 面试官问："Git 的 add 和 commit 分别做了什么？为什么不能跳过 add？"你怎么回答？
