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
import os
import torch
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ==================== 全局单例 ====================
_base_model = None       # 纯基座模型（不包含任何 LoRA）
_tokenizer = None
_lora_model = None       # PeftModel（包含所有 adapter，动态切换）
_lora_adapters = set()   # 已加载的 adapter 名称集合

# ==================== 路径配置 ====================
MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"
ADAPTER_DIR = Path(__file__).parent.parent.parent / "adapters_4090"


def _mock_enabled() -> bool:
    return os.getenv("COGNITIVEPROBE_MOCK_LLM", "0") == "1"


def _mock_response(prompt: str, adapter_name: str = "base") -> str:
    compact_prompt = " ".join(prompt.split())[:80]
    return f"[mock:{adapter_name}] {compact_prompt}"


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
    获取指定 LoRA adapter 的模型

    设计：只创建一个 PeftModel，用 load_adapter + set_adapter 动态切换
    避免多次 PeftModel.from_pretrained 导致的嵌套问题

    注意：adapter 名称不能用 "forward"，因为和 PyTorch 的 forward 方法冲突
    所以用 "lora_forward" / "lora_critical" / "lora_creative" 作为内部名称
    """
    global _lora_model, _lora_adapters

    _ensure_base_loaded()

    # 内部 adapter 名称（避免和 PyTorch forward 方法冲突）
    internal_name = f"lora_{adapter_name}"

    adapter_path = ADAPTER_DIR / f"{adapter_name}_lora"
    if not adapter_path.exists():
        raise FileNotFoundError(
            f"Adapter 不存在: {adapter_path}\n"
            f"请先运行训练脚本"
        )

    # 第一次调用时，用第一个 adapter 创建 PeftModel
    if _lora_model is None:
        print(f"[LoRA推理] 加载 {adapter_name} LoRA adapter（首次创建 PeftModel）...")
        _lora_model = PeftModel.from_pretrained(_base_model, str(adapter_path), adapter_name=internal_name)
        _lora_adapters.add(adapter_name)
        print(f"[LoRA推理] {adapter_name} adapter 加载完成")
    # 后续调用，用 load_adapter 加载新 adapter
    elif adapter_name not in _lora_adapters:
        print(f"[LoRA推理] 加载 {adapter_name} LoRA adapter...")
        _lora_model.load_adapter(str(adapter_path), adapter_name=internal_name)
        _lora_adapters.add(adapter_name)
        print(f"[LoRA推理] {adapter_name} adapter 加载完成")

    # 切换到指定 adapter
    _lora_model.set_adapter(internal_name)

    return _lora_model


def _clean_output(text: str) -> str:
    """
    清理模型输出，删除重复的总结和元指令

    问题：
    1. 模型会输出多个"### 最终分析"、"### 优化分析"等
    2. 模型会混入指令如"请用创造性推理专家的视角..."
    3. 模型会输出"```"代码块
    """
    import re

    # 1. 删除"```"代码块及其内容
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'```', '', text)

    # 2. 删除元指令行
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # 跳过元指令
        if re.match(r'^(请用|跳出|回归到问题|按照指定|答案简评|现在应用|修改润色|最后检查|确保|分析这两个)', stripped):
            continue
        # 跳过纯"答案"行
        if stripped in ['答案', '回答', '答案：', '回答：', '---']:
            continue
        # 跳过步骤说明行
        if re.match(r'^步骤[说明]*[：:]', stripped):
            continue
        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)

    # 3. 处理重复的"最终分析"
    # 如果有多个"最终分析：XXX"，只保留第一个完整的
    if '最终分析：' in text:
        parts = text.split('最终分析：')
        if len(parts) > 1:
            # 保留第一个"最终分析"及其后面的内容，直到遇到下一个标题
            first_part = parts[0]
            analysis_part = parts[1]

            # 找到分析部分中下一个标题的位置
            next_header = re.search(r'\n###|\n答案|\n回答', analysis_part)
            if next_header:
                analysis_part = analysis_part[:next_header.start()]

            text = first_part + '最终分析：' + analysis_part.strip()

    # 4. 删除连续空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 5. 删除尾部不完整的内容（以"，"或"、"结尾）
    text = re.sub(r'[，、]\s*$', '', text.strip())

    # 6. 限制最大长度（防止输出太长）
    max_chars = 800
    if len(text) > max_chars:
        # 在句号处截断
        cut_pos = text[:max_chars].rfind('。')
        if cut_pos > max_chars // 2:
            text = text[:cut_pos + 1]
        else:
            text = text[:max_chars] + '...'

    return text.strip()


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
            eos_token_id=_tokenizer.eos_token_id,
            repetition_penalty=1.2,
        )

    # 只取生成的部分（去掉输入 prompt）
    generated = _tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )

    # 后处理：清理输出
    generated = _clean_output(generated)

    return generated.strip()


def generate_lora(prompt: str, adapter_name: str, max_new_tokens: int = 400) -> str:
    if _mock_enabled():
        return _mock_response(prompt, adapter_name)

    """
    使用指定的 LoRA adapter 生成回答

    Args:
        prompt: 提示词
        adapter_name: LoRA adapter 名称（"forward" / "critical" / "creative"）
        max_new_tokens: 最多生成多少 token
    """
    model = get_lora_model(adapter_name)  # 会自动切换到对应 adapter
    return _generate(model, prompt, max_new_tokens)


def generate_base(prompt: str, max_new_tokens: int = 300) -> str:
    if _mock_enabled():
        return _mock_response(prompt, "base")

    """
    使用基座模型（无 LoRA）生成回答
    用于 coordinator、debate_reviewer、aggregator 等
    """
    _ensure_base_loaded()
    return _generate(_base_model, prompt, max_new_tokens)


def preload():
    if _mock_enabled():
        print("[LoRA推理] mock 模式：跳过模型和 adapter 预加载")
        return

    """
    预加载基座模型和所有 LoRA adapters（FastAPI 启动时调用）

    为什么需要这个？
    - 如果在请求线程里加载模型，容易出现 CUDA 初始化死锁
    - 启动时在主线程加载完，后续请求直接推理，既快又安全
    """
    print("[LoRA推理] 启动预加载...")
    _ensure_base_loaded()

    # 预加载所有 adapters
    for adapter_name in ["forward", "critical", "creative"]:
        try:
            get_lora_model(adapter_name)
        except FileNotFoundError as e:
            print(f"[LoRA推理] ⚠️ 跳过 {adapter_name}: {e}")

    print("[LoRA推理] 预加载完成，所有 adapter 就绪")
