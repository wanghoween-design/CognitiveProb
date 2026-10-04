from src.models.database import SessionLocal
from src.models.task import Task


def create_task(question: str) -> Task:
    """创建一个任务存储到数据库"""
    db = SessionLocal()
    try:
        task = Task(question=question)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


def get_task(task_id: int) -> Task:
    """根据id查任务"""
    db = SessionLocal()
    try:
        return db.query(Task).filter(Task.id == task_id).first()
    finally:
        db.close()


def delete_task(task_id: int) -> bool:
    """根据id删除"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return False
        db.delete(task)
        db.commit()
        return True
    finally:
        db.close()


def change_task(task_id: int, question: str) -> Task:
    """根据id修改问题"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return None
        task.question = question
        task.status = "pending"
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


def finish_task(task_id: int, status: str, result: dict | None = None) -> None:
    """推理结束后回写状态和结果（数据库不可用时静默跳过，不影响推理本身）"""
    try:
        db = SessionLocal()
    except Exception:
        return
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return
        task.status = status
        if result is not None:
            task.result = result
        db.commit()
    except Exception as e:
        print(f"[CRUD] 回写任务 {task_id} 状态失败: {e}")
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def list_tasks(limit: int = 20) -> list[dict]:
    """按时间倒序列出最近的任务，用于前端历史记录"""
    db = SessionLocal()
    try:
        tasks = (
            db.query(Task)
            .order_by(Task.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": t.id,
                "question": t.question,
                "status": t.status,
                "has_result": t.result is not None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    finally:
        db.close()
