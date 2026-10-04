import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SKIP_MODEL_PRELOAD", "1")
os.environ.setdefault("COGNITIVEPROBE_MOCK_LLM", "1")
os.environ.setdefault("SKIP_DB_INIT", "1")


class LightweightTests(unittest.TestCase):
    def test_coordinator_parses_json_route(self):
        from src.agents import graph

        with patch.object(graph, "call_llm", return_value='{"type": 2}'):
            self.assertEqual(
                graph.coordinator({"question": "What is Python?"}),
                {"question_type": "simple_factual"},
            )

    def test_coordinator_falls_back_to_last_route_number(self):
        from src.agents import graph

        with patch.object(graph, "call_llm", return_value="analysis result type is 3"):
            self.assertEqual(
                graph.coordinator({"question": "What are the effects of a four-day work week?"}),
                {"question_type": "complex_reasoning"},
            )

    def test_mock_generation_does_not_load_model(self):
        from src.agents.lora_inference import generate_base, generate_lora

        self.assertTrue(generate_base("hello").startswith("[mock:base]"))
        self.assertTrue(generate_lora("hello", "critical").startswith("[mock:critical]"))

    def test_app_import_skips_preload(self):
        from src.main import app

        self.assertEqual(app.title, "CognitiveProbe")


class ApiTests(unittest.TestCase):
    """接口层测试：Mock LLM + 跳过数据库，验证 /health 与 /reason/stream"""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from src.main import app
        cls.client = TestClient(app)

    def test_health_reports_components(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["mock_llm"])
        self.assertIn("db", data)
        self.assertIn("loaded_adapters", data)

    def test_reason_stream_emits_node_events(self):
        resp = self.client.post(
            "/reason/stream", json={"question": "如果太阳消失了地球会怎样？"}
        )
        self.assertEqual(resp.status_code, 200)
        events = [json.loads(line) for line in resp.text.splitlines() if line.strip()]

        kinds = [e["event"] for e in events]
        self.assertEqual(kinds[0], "start")
        self.assertEqual(kinds[-1], "end")
        self.assertNotIn("error", kinds)

        # 复杂推理路径应包含三个并行 Agent 与辩论节点
        nodes = [e["node"] for e in events if e["event"] == "node"]
        for expected in ("coordinator", "forward", "critical", "creative",
                         "debate_reviewer", "forward_reviser", "creative_reviser",
                         "aggregator"):
            self.assertIn(expected, nodes)

        # end 事件携带完整响应，结构与 /reason 一致
        end_data = events[-1]["data"]
        for field in ("question", "question_type", "forward", "critical",
                      "creative", "debate_critique", "final"):
            self.assertIn(field, end_data)

    def test_reason_rejects_empty_question(self):
        resp = self.client.post("/reason", json={"question": "   "})
        self.assertEqual(resp.status_code, 422)

    def test_tasks_unavailable_returns_503(self):
        resp = self.client.post("/tasks", json={"question": "测试"})
        self.assertEqual(resp.status_code, 503)


class CrudPersistenceTests(unittest.TestCase):
    """用 SQLite 验证任务持久化逻辑（不依赖 PostgreSQL）"""

    def test_result_roundtrip_and_list(self):
        import tempfile
        from unittest.mock import patch

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.models import crud
        from src.models.task import Base

        with tempfile.TemporaryDirectory() as tmp:
            engine = create_engine(f"sqlite:///{tmp}/t.db")
            Base.metadata.create_all(bind=engine)
            factory = sessionmaker(bind=engine)
            with patch.object(crud, "SessionLocal", factory):
                task = crud.create_task(question="测试问题")
                self.assertIsNotNone(task.id)

                crud.finish_task(task.id, status="done", result={"final": "结论", "forward": "分析"})
                detail = crud.get_task(task.id)
                self.assertEqual(detail.status, "done")
                self.assertEqual(detail.result["final"], "结论")

                rows = crud.list_tasks(limit=5)
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0]["has_result"])
                self.assertEqual(rows[0]["question"], "测试问题")

                # 失败路径回写
                t2 = crud.create_task(question="失败任务")
                crud.finish_task(t2.id, status="failed")
                self.assertEqual(crud.get_task(t2.id).status, "failed")

                engine.dispose()   # Windows 下需先释放 SQLite 文件句柄才能清理临时目录


if __name__ == "__main__":
    unittest.main()