"""
本地 LoRA 模型推理模块

作用：加载 4-bit 量化 Qwen3-4B + 指定的 LoRA adapter，
     提供本地推理能力，替代 Ollama API 调用。

设计：
  - 基座模型全局单例，只加载一次
  - LoRA adapter 懒加载，用到才加载
  - 基座模型和 LoRA 模型共享底层权重（不重复占显存）

用法：
  from src.agents.lora_inference import generate_lora, generate_base

  answer = generate_base(prompt)           # 基座模型（无 LoRA）
  answer = generate_lora(prompt, "forward") # 基座 + forward LoRA
"""
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ==================== 全局单例 ====================
_base_model = None       # 纯基座模型（不包含任何 LoRA）
_tokenizer = None
_lora_models = {}        # {"forward": PeftModel, "critical": PeftModel, ...}

# ==================== 路径配置 ====================
MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"
ADAPTER_DIR = Path(__file__).parent.parent.parent / "adapters"


def _ensure_base_loaded():
    """
    确保基座模型已加载（懒加载：第一次调用时才加载）

    为什么懒加载？
    - 如果只 import 这个模块但不推理，就不该占显存
    - 第一次推理会慢 ~30 秒（加载模型），后续调用秒出
    """
    global _base_model, _tokenizer

    if _base_model is None:
        print("[LoRA推理] 加载基座模型（4-bit）...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,   # RTX 3060 不支持 bf16
            bnb_4bit_use_double_quant=True,
        )

        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_PATH,
            trust_remote_code=True,
        )
        _tokenizer.pad_token = _tokenizer.eos_token  # Qwen3 默认没有 pad_token

        _base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            quantization_config=bnb_config,
            device_map="auto",           # 自动分配 GPU/CPU
            trust_remote_code=True,
            low_cpu_mem_usage=True,      # 省内存，避免爆页面文件
        )
        print("[LoRA推理] 基座模型加载完成")


def get_lora_model(adapter_name: str):
    """
    获取指定 LoRA adapter 的模型（懒加载 adapter）

    为什么 PeftModel 不额外占显存？
    - PeftModel.from_pretrained 只是在基座模型外面包一层
    - LoRA 权重只有几 MB（adapter_model.safetensors）
    - 底层基座权重是共享的，不会复制
    """
    _ensure_base_loaded()

    if adapter_name not in _lora_models:
        adapter_path = ADAPTER_DIR / f"{adapter_name}_lora"
        if not adapter_path.exists():
            raise FileNotFoundError(
                f"Adapter 不存在: {adapter_path}\n"
                f"请先运行训练脚本: python scripts/train_forward.py"
            )

        print(f"[LoRA推理] 加载 {adapter_name} LoRA adapter...")
        _lora_models[adapter_name] = PeftModel.from_pretrained(
            _base_model, str(adapter_path)
        )
        print(f"[LoRA推理] {adapter_name} adapter 加载完成")

    return _lora_models[adapter_name]


def _generate(model, prompt: str, max_new_tokens: int = 512) -> str:
    """
    内部生成函数：tokenize → generate → decode

    参数说明：
      - temperature=0.7: 控制随机性，越高越"有创意"，越低越"保守"
      - top_p=0.9: nucleus sampling，只从累积概率 >= 0.9 的词中采样
      - do_sample=True: 开启采样（否则是 greedy decoding，每次选概率最高的词）
    """
    inputs = _tokenizer(prompt, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=_tokenizer.eos_token_id,
        )

    # 只取生成的部分（去掉输入 prompt）
    generated = _tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return generated.strip()


def generate_lora(prompt: str, adapter_name: str, max_new_tokens: int = 512) -> str:
    """
    使用指定的 LoRA adapter 生成回答

    Args:
        prompt: 提示词
        adapter_name: LoRA adapter 名称（"forward" / "critical" / "creative"）
        max_new_tokens: 最多生成多少 token
    """
    model = get_lora_model(adapter_name)
    return _generate(model, prompt, max_new_tokens)


def generate_base(prompt: str, max_new_tokens: int = 512) -> str:
    """
    使用基座模型（无 LoRA）生成回答
    用于还没有训练 LoRA 的 Agent
    """
    _ensure_base_loaded()
    return _generate(_base_model, prompt, max_new_tokens)


def preload():
    """
    预加载基座模型和 forward LoRA（FastAPI 启动时调用）

    为什么需要这个？
    - 如果在请求线程里加载模型，容易出现 CUDA 初始化死锁
    - 启动时在主线程加载完，后续请求直接推理，既快又安全
    """
    print("[LoRA推理] 启动预加载...")
    _ensure_base_loaded()
    # 提前加载 forward adapter（后续加 critical/creative 也在这里）
    get_lora_model("forward")
    print("[LoRA推理] 预加载完成，所有 adapter 就绪")
