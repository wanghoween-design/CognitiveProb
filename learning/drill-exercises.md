# 薄弱点专项练习

> 针对 5 个薄弱点，每个 3-5 题，做完对照答案自查

---

## 专项 1：SQLAlchemy Column 写法

### 1.1 判断对错，错的改正

```python
# A
name = Column(String, nullable=False)

# B
age = Column(Integer, nullable = False)

# C
email = Column(String, nullable=True, default="unknown")

# D
id = Column(Integer, primary_key=True)

# E
created_at = Column(Datetime, default=lambda: datetime.now(timezone.utc))
```

### 1.2 补全代码
```python
class User(Base):
    __tablename__ = "users"

    id = _Column(Integer, primary_key = True)___                        # 主键
    username = _Column(String, nullable = False)___                  # 字符串，不能为空
    email = _Column(String, nullable = True)___                     # 字符串，可以为空
    is_active = _Column(bool, nullable = True)___                 # 布尔，默认 True
    created_at = _Column(DateTime, datetime = lambda: datetime.now(timezone.utc))___                # 时间戳，自动填入当前时间
```

### 1.3 从零写一个完整模型
写一个 `Product` 表，字段：
- id：主键
- name：字符串，不能为空
- price：整数
- in_stock：布尔，默认 True
- created_at：时间戳
class Base(DeclarativeBase):
  pass

class Product(Base):
  __tablename__ = "product"

  id = Column(Integer, primary_key = True)
  name = Column(String, nullable = False)
  price = Column(Integer, nullable = False)
  in_stock = Column(bool, defaut = True)
  create_at = Column(DateTime, datetime = lambda: datetime.now(timezone.utc))

### 1.4 找出所有错误
```python
from sqlalchemy import Column, Integer, String, Datetime
from sqlalchemy.orm import Declarativebase
from Datetime import datetime

class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key = True)
    product_name = Column(String, nullable = False)
    quantity = Column(Integer, default = 1)
    order_date = Column(Datetime, datetime = datetime.now(timezone.utc))
```

---

## 专项 2：lambda 延迟执行

### 2.1 判断输出
```python
# 场景 A
import time
default_time = time.time()

class ModelA:
    t = default_time

a1 = ModelA()
time.sleep(1)
a2 = ModelA()
print(a1.t == a2.t)  # 输出什么？为什么？输出True,因为只执行了一次
```

```python
# 场景 B
import time

class ModelB:
    t = lambda: time.time()

b1 = ModelB()
time.sleep(1)
b2 = ModelB()
print(b1.t() == b2.t())  # 输出什么？为什么？False,执行了两次
```

### 2.2 选择题
什么时候需要用 lambda？B
```python
# A. 固定默认值
default = "pending"

# B. 当前时间
default = datetime.now(timezone.utc)

# C. 随机数
default = random.randint(1, 100)
```

### 2.3 改错
```python
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```
哪行有问题？为什么？
created_at = Column(DateTime, default=datetime.now(timezone.utc))应该改成created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc))
---

## 专项 3：Docker Compose 配置

### 3.1 补全配置
```yaml
services:
  redis:
    image: _postgres16___
    container_name: _cognitiveprob___
    ports:
      - __5432:5432__
    volumes:
      - __券的声明我真的记不住__
```

### 3.2 解释含义
```yaml
ports:
  - "5432:3306"
```
访问 `localhost:5432` 会连到容器里的哪个端口？3306

### 3.3 判断对错
```yaml
# A
volumes:
  - postgres_data:/var/lib/postgresql/data

# B
volumes:
  - /var/lib/postgresql/data:postgres_data
```
哪个对？
真不知道，记不住啊啊啊啊啊啊啊啊啊

### 3.4 补全完整配置
写一个 docker-compose.yml，包含：
- PostgreSQL 16，端口 5432，数据库名 mydb，密码 123456
- Redis 7，端口 6379
记不住记不住哭了
---

## 专项 4：CRUD 写法

### 4.1 补全 create 函数
```python
def create_book(title: str, author: str) -> Book:
    db = _SessionLocal()___
    book = Task____(title=_db.title___, author=_db.author___)
    db._add___(book)
    db._commit___()
    db._refresh___(book)
    db._close___()
    return book
```

### 4.2 补全 get 函数
```python
def get_book(book_id: int) -> Book:
    db = _SessionLocal()___
    book = db._query___(Book)._filter___(Book.id == book_id)._first___()
    db._close___()
    return book
```
补充一个问题，我很想知道这里的first是什么作用
### 4.3 补全 delete 函数
```python
def delete_book(book_id: int) -> bool:
    db = _SessionLocal()___
    book = db._query___(Book)._filter___(Book.id == book_id)._first___()
    if book is _Nose___
        db._close___()
        return False
    db.delete___(book)
    db._commit___()
    db._close___()
    return True
```

### 4.4 写完整 CRUD
为一个 `Comment` 表（字段：id, content, author）写完整的 4 个 CRUD 函数。
```python
def create_comment(content: str, author: str) -> Comment:
  db = SessionLocal()
  comment = Comment(content = content, author = author)
  db.add(comment)
  db.commit()
  db.refresh(comment)
  db.close()
  return comment

def update_comment(comment_id: int, content: str)-> Comment:
  db = SessionLocal()
  comment = db.query(Comment).filter(Comment.id == comment_id).first()
  if comment is None:
    db.close()
    return False
  comment.content = content
  db.commit()
  db.refresh(comment)
  db.close()
  return comment

def get_comment(comment_id: int) -> Comment:
  db = SessionLocal()
  comment = db.query(Comment).filter(Comment.id == comment_id).first()
  if comment is None:
    db.close()
    return False
  db.close()
  return comment

def delete_comment(comment_id: int) -> bool:
  db = SessionLocal()
  comment = db.query(Comment).filter(Comment.id == comment_id).first()
  if comment is None:
    db.close()
    return False
  db.delete(comment)
  db.commit()
  db.close()
  return True

```
---

## 专项 5：装饰器 @ 和路由

### 5.1 选择题
下面哪个是正确的路由定义？C
```python
# A
@app("/health")
def health(): ...

# B
@app.get("/health")
def health(): ...

# C
@app.route("/health")
def health(): ...

# D
@get("/health")
def health(): ...
```

### 5.2 补全路由
```python
router = APIRouter()

# 定义一个 GET /users 路由
@router._get___("/users")
def list_users():
    return {"users": []}

# 定义一个 POST /users 路由
@router._post___("/users")
def create_user():
    return {"id": 1}

# 定义一个 DELETE /users/{user_id} 路由
@router._delete___("/users/{user_id}")
def delete_user(user_id: int):
    return {"deleted": user_id}
```

### 5.3 选择题
`APIRouter()` 和 `FastAPI()` 的区别是什么？
```python
# A
app = FastAPI()        # 作用是？运行整个fastapi
router = APIRouter()   # 作用是？把不同任务拆分出去

# B
# 什么时候用 app.include_router(router)？使用了APIRouter后需要对他们聚合

# C
# 能不能有两个 FastAPI() 实例？为什么？不能，唯一的
```

---

# 答案

## 专项 1 答案

### 1.1
```
A. 错。缺 Column → name = Column(String, nullable=False)
B. 对。
C. 对。
D. 错。primay → primary → id = Column(Integer, primary_key=True)
E. 错。Datetime → DateTime
```

### 1.2
```python
id = Column(Integer, primary_key=True)
username = Column(String, nullable=False)
email = Column(String, nullable=True)
is_active = Column(Boolean, default=True)
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### 1.3
```python
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Integer)
    in_stock = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### 1.4
```
1. import column, integer, string, datetime → Column, Integer, String, DateTime（大写）
2. import datetime 和 from datetime import datetime 冲突 → 去掉第一个
3. declarativebase → DeclarativeBase
4. class base → class Base
5. __tablename__ = "Order" → "orders"（表名小写）
6. column → Column
7. integer → Integer
8. primary_key = true → primary_key = True
9. (string, nullable = false) → Column(String, nullable=False)
10. datetime → DateTime
11. datetime.now(timezone.utc) 缺 lambda → lambda: datetime.now(timezone.utc)
```

## 专项 2 答案

### 2.1
```
场景 A: True。a1.t 和 a2.t 都是同一个 default_time 值。
场景 B: False。b1.t() 和 b2.t() 各自调用 time.time()，时间不同。
```

### 2.2
```
A. 不需要 lambda（固定值，不会变）
B. 需要 lambda（当前时间，每次要新的）
C. 需要 lambda（随机数，每次要新的）
```

### 2.3
```
created_at 那行有问题。
datetime.now(timezone.utc) 没有 lambda，会在定义类时执行一次，所有记录用同一个时间。
应该改成 default=lambda: datetime.now(timezone.utc)
updated_at 那行是对的。
```

## 专项 3 答案

### 3.1
```yaml
services:
  redis:
    image: redis:7
    container_name: cognitive_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

### 3.2
```
访问 localhost:5432 会连到容器里的 3306 端口。
因为 ports 格式是 "电脑端口:容器端口"。
```

### 3.3
```
A 对。格式是 "卷名:容器路径"
B 错。顺序反了。
```

### 3.4
```yaml
services:
  postgres:
    image: postgres:16
    container_name: my_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: "123456"
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app_network

  redis:
    image: redis:7
    container_name: my_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - app_network

volumes:
  postgres_data:
  redis_data:

networks:
  app_network:
```

## 专项 4 答案

### 4.1
```python
def create_book(title: str, author: str) -> Book:
    db = SessionLocal()
    book = Book(title=title, author=author)
    db.add(book)
    db.commit()
    db.refresh(book)
    db.close()
    return book
```

### 4.2
```python
def get_book(book_id: int) -> Book:
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    db.close()
    return book
```

### 4.3
```python
def delete_book(book_id: int) -> bool:
    db = SessionLocal()
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        db.close()
        return False
    db.delete(book)
    db.commit()
    db.close()
    return True
```

### 4.4
```python
def create_comment(content: str, author: str) -> Comment:
    db = SessionLocal()
    comment = Comment(content=content, author=author)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.close()
    return comment

def get_comment(comment_id: int) -> Comment:
    db = SessionLocal()
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    db.close()
    return comment

def change_comment(comment_id: int, content: str) -> Comment:
    db = SessionLocal()
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment is None:
        db.close()
        return None
    comment.content = content
    db.commit()
    db.refresh(comment)
    db.close()
    return comment

def delete_comment(comment_id: int) -> bool:
    db = SessionLocal()
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment is None:
        db.close()
        return False
    db.delete(comment)
    db.commit()
    db.close()
    return True
```

## 专项 5 答案

### 5.1
```
B 正确。FastAPI 用 @app.get() 语法。
A 错。缺少 HTTP 方法。
C 错。@app.route 是 Flask 语法，不是 FastAPI。
D 错。缺少 app。
```

### 5.2
```python
@router.get("/users")
@router.post("/users")
@router.delete("/users/{user_id}")
```

### 5.3
```
A: FastAPI() 是主应用，只能有一个，负责启动服务器。
   APIRouter() 是子路由，可以有很多个，负责分组管理接口。

B: 在 main.py 里，把子路由挂到主应用上：
   app.include_router(router)

C: 不能。一个应用只能有一个 FastAPI() 实例，多个会冲突。
   用 APIRouter() 来分组，最后都挂到同一个 FastAPI() 上。
```
