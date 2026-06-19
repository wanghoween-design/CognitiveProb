from src.models.database import SessionLocal
from src.models.task import Task


def create_task(question: str) -> Task:
    """创建一个任务存储到数据库"""
    db = SessionLocal()
    task = Task(question=question)
    db.add(task)
    db.commit()
    db.refresh(task)
    db.close()
    return task


def get_task(task_id: int) ->Task:
    """根据id查任务"""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id==task_id).first()
    db.close()
    return task

def delete_task(task_id: int) -> bool:
    """根据id删除"""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        db.close()
        return False
    db.delete(task)
    db.commit()
    db.close()
    return True

def change_task(task_id: int, question: str) -> Task:
    """根据id修改"""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        db.close()
        return None
    task.question = question
    task.status = "done"
    db.commit()
    db.refresh(task)
    db.close()
    return task