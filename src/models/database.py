from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import config
from src.models.task import Base


db = config["database"]
DATABASE_URL = (
    f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['name']}"
                        #用户名：密码@地址：端口/库名
    )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)