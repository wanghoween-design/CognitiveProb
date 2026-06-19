# CognitiveProbe

基于 LoRA 认知注入的 Multi-Agent 协作推理系统。

通过多个具有不同认知风格的 Agent（前瞻、批判、创造）协作分析问题，由 Coordinator 智能路由，最终综合生成高质量回答。

---

## 系统架构

```
用户提问
    │
    ▼
┌─────────────────────────────────────────┐
│           Coordinator Agent             │
│     判断问题类型，决定调用哪些 Agent      │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
 简单问候    简单事实问题    复杂推理问题
 (直接回答)  (1个Agent)    (3个Agent并行)
    │            │            │
    │            ▼            ▼
    │     ┌──────────┐  ┌──────────┐
    │     │ 批判 Agent│  │ 前瞻 Agent│
    │     │ 找逻辑漏洞│  │ 预测后果  │
    │     └────┬─────┘  └────┬─────┘
    │          │              │
    │          │              ▼
    │          │       ┌──────────┐
    │          │       │ 批判 Agent│
    │          │       └────┬─────┘
    │          │            │
    │          │            ▼
    │          │       ┌──────────┐
    │          │       │ 创造 Agent│
    │          │       │ 跨领域类比│
    │          │       └────┬─────┘
    │          │            │
    ▼          ▼            ▼
┌─────────────────────────────────────────┐
│            汇总 Agent                    │
│   综合所有分析，提取共识与分歧，写总结    │
└─────────────────────────────────────────┘
                 │
                 ▼
            最终回答
```

### 三个 Agent 的认知分工

| Agent | 认知风格 | 分析角度 | 输出特点 |
|-------|---------|---------|---------|
| 前瞻 Agent | Forward-looking | 短期→中期→长期 | 时间线推演，因果链分析 |
| 批判 Agent | Critical | 逻辑漏洞、反例、谬误 | 质疑假设，找边界条件 |
| 创造 Agent | Creative | 跨领域类比 | 用其他领域的案例类比回答 |

### Coordinator 路由逻辑

| 问题类型 | 示例 | 路由路径 | 模型调用次数 |
|---------|------|---------|------------|
| 简单问候 | "你好"、"你是谁" | 直接回答 | 2 次 |
| 简单事实 | "Python是什么" | 批判→汇总 | 3 次 |
| 复杂推理 | "太阳消失了会怎样" | 前瞻→批判→创造→汇总 | 5 次 |

---

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| API 框架 | FastAPI | REST API 接口 |
| Agent 编排 | LangGraph | 多 Agent 工作流状态图 |
| 基座模型 | Qwen3 (Ollama) | 本地 LLM 推理 |
| 数据库 | PostgreSQL 16 | 任务持久化存储 |
| 缓存 | Redis 7 | 缓存（待集成） |
| ORM | SQLAlchemy | 数据库操作 |
| 容器化 | Docker Compose | 服务编排 |

---

## 项目结构

```
Multi-Agent/
├── configs/
│   └── config.yaml              # 全局配置（模型、数据库、Ollama）
├── src/
│   ├── api/                     # 路由层
│   │   ├── health.py            # 健康检查
│   │   ├── config_route.py      # 配置查看
│   │   ├── test_llm.py          # LLM 调用测试
│   │   ├── tasks.py             # 任务 CRUD + 端到端问答
│   │   └── agents.py            # 多 Agent 推理接口
│   ├── agents/                  # Agent 层
│   │   └── graph.py             # LangGraph 工作流定义
│   ├── models/                  # 数据层
│   │   ├── task.py              # Task 表模型
│   │   ├── database.py          # 数据库连接
│   │   └── crud.py              # 增删改查
│   ├── config.py                # 配置加载器
│   └── main.py                  # 应用入口
├── docker-compose.yml           # PostgreSQL + Redis
├── requirements.txt             # Python 依赖
└── learning/                    # 学习笔记（不提交 Git）
```

---

## API 接口

| 方法 | 路径 | 功能 | 说明 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 返回 `{"status": "ok"}` |
| GET | `/config` | 查看配置 | 返回 config.yaml 内容 |
| GET | `/test_llm` | LLM 测试 | 测试 Ollama 连接 |
| POST | `/tasks` | 创建任务 | 参数：question |
| GET | `/tasks/{id}` | 查询任务 | 返回任务详情 |
| PUT | `/tasks/{id}` | 修改任务 | 参数：question |
| DELETE | `/tasks/{id}` | 删除任务 | 删除指定任务 |
| POST | `/ask` | 端到端问答 | 提问→模型回答→存库 |
| POST | `/reason` | 多 Agent 推理 | Coordinator 路由→Agent 协作→综合总结 |

### /reason 返回示例

```json
{
  "question": "如果太阳消失了会怎样",
  "question_type": "complex_reasoning",
  "forward": "短期：光照滞后8分钟...(前瞻分析)",
  "critical": "问题存在时间参数缺失...(批判分析)",
  "creative": "太阳如同分布式系统的主服务器...(创造分析)",
  "final": "综合三个视角：太阳消失是一场...(综合总结)"
}
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Docker Desktop
- Ollama（已安装 qwen3 模型）

### 启动步骤

```bash
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # Linux/Mac

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动数据库服务
docker compose up -d

# 4. 启动 API 服务
uvicorn src.main:app --reload

# 5. 访问 API 文档
# http://127.0.0.1:8000/docs
```

---

## 工作原理

### LangGraph 状态图

系统基于 LangGraph 构建，核心是一个状态图（State Graph）：

- **State**：共享数据包，在节点之间流动
- **Node**：处理函数，读取 state → 处理 → 返回更新后的 state
- **Edge**：节点之间的连接，支持条件路由

### 调用链路

```
POST /reason?question=xxx
    │
    ▼
agents.py（接收请求）
    │
    ▼
graph.py（LangGraph 工作流）
    │
    ├─ coordinator：调用模型判断问题类型
    │
    ├─ 根据类型路由到不同 Agent
    │
    ├─ aggregator：调用模型综合所有分析
    │
    ▼
返回 JSON 结果
```

### 数据流

```
User Question
    ↓
[coordinator] → question_type, coordinator_answer
    ↓
[forward_agent] → forward_answer        (仅复杂推理)
    ↓
[critical_agent] → critical_answer
    ↓
[creative_agent] → creative_answer      (仅复杂推理)
    ↓
[aggregator] → final_answer
    ↓
Response JSON
```

---

## 开发状态

### 已完成

- [x] 项目骨架与配置管理
- [x] FastAPI 应用 + 路由拆分
- [x] Ollama 本地模型调用
- [x] Docker Compose（PostgreSQL + Redis）
- [x] SQLAlchemy ORM（Task 表 CRUD）
- [x] 端到端问答接口（/ask）
- [x] LangGraph 多 Agent 工作流
- [x] Coordinator 智能路由
- [x] 3 个认知 Agent（前瞻/批判/创造）
- [x] Aggregator 综合总结
- [x] 模型输出清洗（特殊标记、重复内容）
- [x] Git 版本控制 + GitHub

### 待开发

- [ ] Agent 并行执行（Send API 提速）
- [ ] 辩论-共识协议（Agent 间互相质疑）
- [ ] LoRA 认知注入训练
- [ ] Milvus 向量检索集成
- [ ] Langfuse 可观测性
- [ ] 评估框架（LogiQA 2.0）
- [ ] Streamlit 前端界面
