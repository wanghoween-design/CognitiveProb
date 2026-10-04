from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config


db = config["database"]
DATABASE_URL = (
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
                        #用户名：密码@地址：端口/库名
    )

# pool_pre_ping：每次取连接前先探活，避免 PostgreSQL 重启后的残留失效连接
# connect_timeout=1：本机 Docker PostgreSQL，未启动时快速失败，
# 避免 /health、任务接口每个请求都卡在 TCP 连接上（实测会挂 4 秒）
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 1},
)
SessionLocal = sessionmaker(bind=engine)

# 注意：建表（create_all）不在 import 时执行，改由 main.py 启动时统一处理。
# 之前在这里执行，会导致 PostgreSQL 未启动时 import 本模块直接崩溃，
# 连 /reason 等不依赖数据库的接口也全部起不来。