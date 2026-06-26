# CognitiveProbe

基于 LoRA 认知注入的 Multi-Agent 协作推理系统。

通过三个具有不同认知风格（前瞻、批判、创造）的 Agent 协作分析问题，经**辩论-共识协议**互相质疑和修正，由 **Coordinator 智能路由**分发任务，最终由 **Aggregator** 综合生成高质量回答。每个 Agent 使用独立的 **QLoRA adapter** 进行认知风格微调。

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
    │     ┌──────────┐  ┌─────────────────────┐
    │     │ 批判 Agent│  │ 前瞻/批判/创造 Agent │
    │     └────┬─────┘  │   三个并行执行       │
    │          │        └────────┬────────────┘
    │          │                 │
    │          │                 ▼
    │          │        ┌─────────────────┐
    │          │        │  sync_point     │
    │          │        │  汇聚等待        │
    │          │        └────────┬────────┘
    │          │                 │
    │          │                 ▼
    │          │        ┌─────────────────┐
    │          │        │ debate_reviewer  │
    │          │        │ 批判审查其他分析  │
    │          │        └────────┬────────┘
    │          │                 │
    │          │                 ▼
    │          │     ┌───────────────────────┐
    │          │     │ forward_reviser       │
    │          │     │ creative_reviser      │
    │          │     │ 两个并行修正          │
    │          │     └───────────┬───────────┘
    │          │                 │
    │          │                 ▼
    │          │        ┌─────────────────┐
    │          │        │  sync_point_2   │
    │          │        └────────┬────────┘
    │          │                 │
    ▼          ▼                 ▼
┌─────────────────────────────────────────┐
│            汇总 Agent                    │
│   综合所有分析，提取共识与分歧，写总结    │
└─────────────────────────────────────────┘
                 │
                 ▼
            最终回答
```

### 三个 Agent 的认知分工

| Agent | 认知风格 | LoRA 秩 | 训练状态 | 分析角度 |
|-------|---------|---------|---------|---------|
| 前瞻 Agent | Forward-looking | r=8 | ✅ 已完成 | 短期→中期→长期因果链推演 |
| 批判 Agent | Critical | r=12 | ⏳ 待训练 | 逻辑漏洞、反例、谬误识别 |
| 创造 Agent | Creative | r=16 | ⏳ 待训练 | 跨领域类比，创新视角 |

### Coordinator 路由逻辑

| 问题类型 | 示例 | 路由路径 | 模型调用次数 |
|---------|------|---------|------------|
| 简单问候 | "你好"、"你是谁" | 直接回答 | 2 次 |
| 简单事实 | "Python是什么" | 批判→汇总 | 3 次 |
| 复杂推理 | "太阳消失了会怎样" | 3 Agent 并行→辩论→修正→汇总 | 8 次 |

### 辩论-共识协议

```
Round 1: 三个 Agent 各自分析（并行）
    ↓
Round 2: 批判 Agent 审视前瞻和创造的分析，提出质疑
    ↓
Round 3: 前瞻和创造 Agent 根据质疑修正自己的观点（并行）
    ↓
最终: 综合修正后的分析，生成总结
```

---

## 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| API 框架 | FastAPI | REST API 接口 |
| Agent 编排 | LangGraph | 多 Agent 工作流状态图 |
| 基座模型 | Qwen3-4B（本地 HF 格式） | 本地 LLM 推理引擎 |
| 训练框架 | PEFT + QLoRA + SFTTrainer | LoRA 认知注入训练 |
| 量化 | bitsandbytes (4-bit NF4) | 省显存，适配消费级显卡 |
| 数据库 | PostgreSQL 16 | 任务持久化存储 |
| 缓存 | Redis 7 | 缓存（待集成） |
| ORM | SQLAlchemy | 数据库操作 |
| 容器化 | Docker Compose | 服务编排 |

---

## 项目结构

```
Multi-Agent/
├── configs/
│   └── config.yaml                  # 全局配置（模型、数据库、LoRA 参数）
├── src/
│   ├── api/                         # 路由层
│   │   ├── health.py                # 健康检查
│   │   ├── config_route.py          # 配置查看
│   │   ├── test_llm.py              # LLM 调用测试
│   │   ├── tasks.py                 # 任务 CRUD + 端到端问答
│   │   └── agents.py                # 多 Agent 推理接口
│   ├── agents/                      # Agent 层
│   │   ├── graph.py                 # LangGraph 工作流定义
│   │   └── lora_inference.py        # 本地模型推理模块（替代 Ollama）
│   ├── models/                      # 数据层
│   │   ├── task.py                  # Task 表模型
│   │   ├── database.py              # 数据库连接
│   │   └── crud.py                  # 增删改查
│   ├── config.py                    # 配置加载器
│   └── main.py                      # 应用入口（启动时预加载模型）
├── data/                            # LoRA 训练数据
│   ├── forward_train.json           # 前瞻推理训练数据（500条）
│   ├── critical_train.json          # 批判推理训练数据（500条）
│   └── creative_train.json          # 创造推理训练数据（500条）
├── models/                          # 基座模型（Qwen3-4B HF 版本，不提交 Git）
├── adapters/                        # 已训练的 LoRA adapter
│   └── forward_lora/                # Forward Agent LoRA
│       ├── adapter_model.safetensors  # LoRA 权重（~11.5MB）
│       ├── adapter_config.json        # LoRA 配置
│       └── training_log.json          # 训练日志（loss/accuracy/entropy）
├── scripts/                         # 训练 & 工具脚本
│   ├── train_forward.py             # Forward LoRA 训练脚本
│   ├── test_lora.py                 # LoRA 推理验证（基座 vs LoRA 对比）
│   ├── plot_training.py             # 训练指标 3D 瀑布图
│   └── debug_uvicorn.py             # 最小复现调试脚本
├── learning/                        # 学习笔记
│   └── project-setup-notes.md       # 项目搭建完整笔记（53KB）
├── docker-compose.yml               # PostgreSQL + Redis
├── requirements.txt                 # Python 依赖
└── README.md
```

---

## API 接口

| 方法 | 路径 | 功能 | 说明 |
|------|------|------|------|
| GET | `/health` | 健康检查 | 返回 `{"status": "ok"}` |
| GET | `/config` | 查看配置 | 返回 config.yaml 内容 |
| GET | `/test_llm` | LLM 测试 | 测试模型连接 |
| POST | `/tasks` | 创建任务 | 参数：question |
| GET | `/tasks/{id}` | 查询任务 | 返回任务详情 |
| PUT | `/tasks/{id}` | 修改任务 | 参数：question |
| DELETE | `/tasks/{id}` | 删除任务 | 删除指定任务 |
| POST | `/ask` | 端到端问答 | 提问→模型回答→存库 |
| POST | `/reason` | 多 Agent 推理 | Coordinator 路由→辩论→修正→综合 |

### /reason 返回示例

```json
{
  "question": "如果中国全面推行四天工作制，会带来什么影响？",
  "question_type": "complex_reasoning",
  "forward": "<reasoning>\n步骤1：短期影响（1-3年）...\n步骤2：中期影响（4-10年）...\n</reasoning>\n最终分析：...",
  "critical": "问题中'普遍'一词过度泛化...",
  "creative": "学制延长如同生态修复期...",
  "debate_critique": "前瞻分析中关于生产率的假设缺乏数据支撑...",
  "forward_revised": "修正后的前瞻分析：考虑到批判指出的证据不足问题...",
  "creative_revised": "修正后的创造分析：保留类比但修正了不合理的推断...",
  "final": "综合三个视角：四天工作制应分行业渐进推行..."
}
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Docker Desktop（PostgreSQL + Redis）
- GPU（RTX 3060 6GB+，用于本地模型推理和 LoRA 训练）
- 系统内存 >= 16GB（加载模型需要 ~4GB 可用内存）

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

# 4. 启动 API 服务（启动时会自动加载模型，约 16 秒）
uvicorn src.main:app --host 127.0.0.1 --port 8000

# 5. 访问 API 文档
# http://127.0.0.1:8000/docs
```

**启动时控制台输出：**
```
==========================================================
预加载本地模型（主线程）...
==========================================================
[LoRA推理] 启动预加载...
[LoRA推理] 加载基座模型（4-bit）...
Loading weights: 100%|████████| 398/398 [00:16<00:00, 23.51it/s]
[LoRA推理] 加载 forward LoRA adapter...
[LoRA推理] 预加载完成，所有 adapter 就绪
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 关键注意事项

1. **模型加载在启动阶段完成**（不在请求时），确保首次请求不会超时
2. **首次启动需要 ~16 秒加载模型**，后续请求直接推理
3. **确保可用内存 > 4GB**（模型分片每个 3.8GB，需要足够内存读入再量化）
4. **数据库启动失败不影响 /reason 接口**（try/except 容错）

---

## 训练 LoRA Adapter

### 训练流程

```
Step 1: 准备训练数据（data/forward_train.json，500条）
Step 2: 编辑 config.yaml 中的 LoRA 参数
Step 3: 运行训练脚本
Step 4: 验证 adapter 效果
Step 5: 集成到 graph.py
```

### 运行训练

```bash
# 训练 Forward Agent LoRA
python scripts/train_forward.py

# 验证训练效果
python scripts/test_lora.py

# 可视化训练指标
python scripts/plot_training.py
```

### Forward LoRA 训练结果

| 指标 | 初始 | 最终 | 变化 |
|------|------|------|------|
| Loss | 2.55 | 1.47 | ↓42% |
| Accuracy | 47.8% | 59.0% | ↑22% |
| Grad Norm | 0.24 | 0.67 | 稳定，无爆炸 |
| 可训练参数 | 5,898,240 (0.12% of 4B) | — | — |

训练详情见 [learning/project-setup-notes.md](learning/project-setup-notes.md) 第二十三节。

---

## 工作原理

### 模型调用架构

系统使用**本地 HuggingFace Qwen3-4B + LoRA adapter**替代 Ollama API，实现"一模型多风格"：

```
call_llm(prompt)
    ├─ use_lora="forward"  → base_model + forward LoRA  → forward_agent
    │                                                      forward_reviser
    └─ use_lora=None       → base_model（无 LoRA）       → 其他所有 Agent
```

**设计要点：**
- 基座模型只加载一次（全局单例）
- LoRA adapter 懒加载，底层权重共享（不额外占显存）
- 总显存占用约 4GB（适配 RTX 3060 6GB）
- 模型在 FastAPI 创建前的主线程中加载（避免 CUDA 死锁）

### LangGraph 状态图

- **State**：共享数据包，在节点之间流动
- **Node**：处理函数，读取 state → 处理 → 返回部分更新
- **Edge**：节点之间的连接，支持条件路由
- **Send**：并行分发，同时启动多个节点
- **sync_point**：汇聚节点，等待所有并行任务完成

### State 数据结构

```python
class AgentState(TypedDict):
    question: str              # 用户的问题
    question_type: str         # coordinator 判断的类型
    forward_answer: str        # 前瞻 Agent 的分析
    critical_answer: str       # 批判 Agent 的分析
    creative_answer: str       # 创造 Agent 的分析
    debate_critique: str       # 辩论质疑
    forward_revised: str       # 修正后的前瞻分析
    creative_revised: str      # 修正后的创造分析
    final_answer: str          # 最终综合总结
```

### 完整调用链

```
POST /reason?question=xxx
    │
    ▼
agents.py（接收请求）
    │
    ▼
graph.py（LangGraph 工作流）
    │
    ├─ coordinator：分类问题
    ├─ dispatcher：Send 并行分发
    ├─ 3 个 Agent 并行执行
    ├─ sync_point：汇聚等待
    ├─ debate_reviewer：批判审查
    ├─ 2 个 reviser 并行修正
    ├─ sync_point_2：汇聚等待
    ├─ aggregator：综合总结
    │
    ▼
返回 JSON（含辩论中间结果）
```

---

## 开发状态

### 已完成

- [x] 项目骨架与配置管理
- [x] FastAPI 应用 + 路由拆分
- [x] Docker Compose（PostgreSQL + Redis）
- [x] SQLAlchemy ORM（Task 表 CRUD）
- [x] 端到端问答接口（/ask）
- [x] LangGraph 多 Agent 工作流
- [x] Coordinator 智能路由
- [x] 3 个认知 Agent（前瞻/批判/创造）
- [x] Send API 并行执行 + sync_point 汇聚
- [x] 辩论-共识协议（批判审查→并行修正）
- [x] Aggregator 综合总结
- [x] 异常处理（所有 Agent 节点 try-except 容错）
- [x] 训练数据准备（1500条，每种风格500条）
- [x] **Forward Agent QLoRA 训练**（loss↓42%, accuracy↑22%）
- [x] **LoRA adapter 集成到 LangGraph**（本地模型替代 Ollama）
- [x] **lora_inference.py 推理模块**（一模型多风格，~4GB 显存）
- [x] LoRA 推理验证脚本（test_lora.py）
- [x] 训练指标可视化（3D 瀑布图）
- [x] 完整学习笔记（project-setup-notes.md，28 章节）

### 进行中

- [ ] **模型加载环境优化**（解决 16GB 内存临界问题）
- [ ] Critical Agent LoRA 训练
- [ ] Creative Agent LoRA 训练

### 待开发

- [ ] 三 LoRA adapter 全部集成到 LangGraph
- [ ] Milvus 向量检索集成
- [ ] Langfuse 可观测性
- [ ] 评估框架（LogiQA 2.0）
- [ ] Streamlit 前端界面
- [ ] 三角互评（critical 也被质疑）

---

## 踩坑记录（关键教训）

| 坑 | 现象 | 根因 | 解决 |
|----|------|------|------|
| CUDA 线程安全 | 请求中加载模型卡死 | PyTorch CUDA 上下文只能在主线程初始化 | 启动时主线程预加载 |
| Ollama 残留 | ollama stop 后仍无法加载 | 进程未退出，占用 CUDA 上下文 | `taskkill /F /IM ollama.exe` |
| 内存不足 | 加载 41% 崩溃 | 单个分片 3.8GB > 可用内存 3.1GB | 关 Chrome/Docker，确保 >4GB 可用 |
| bf16 不支持 | `CUBLAS_STATUS_EXECUTION_FAILED` | RTX 3060 不支持 bf16 | 改用 `torch.float16` |
| 4-bit + fp16 冲突 | `_amp_foreach...` 错误 | 量化训练内部已处理精度 | 删除 TrainingArguments 中的 fp16 |
| Docker 不启动 | 数据库 Connection refused | 容器重启后默认不自动启动 | `docker start cognitive_postgres` |

---

## License

MIT
