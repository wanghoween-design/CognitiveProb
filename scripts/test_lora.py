"""
验证 Forward LoRA 是否真的改变了模型的推理风格
用法: python scripts/test_lora.py
"""
import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ==================== 配置 ====================
MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"
ADAPTER_PATH = r".\adapters\forward_lora"

# 测试题目：3 道典型的前瞻推理题
TEST_QUESTIONS = [
    "如果全球主要国家在2030年前全面禁止燃油车，预测这对汽车行业和就业市场会产生哪些连锁影响？请从短期、中期、长期三个维度分析。",
    "假设量子计算在未来五年内实用化，预测这将如何改变网络安全行业。请分阶段推理。",
    "如果远程办公成为永久常态，分析这对城市规划和房地产市场的长期影响。",
]

# ==================== 加载模型 ====================
print("加载基座模型（4-bit）...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    low_cpu_mem_usage=True,
)

print("加载 Forward LoRA adapter...")
lora_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
# 注意：4-bit 量化模型不能 merge_and_unload，直接用 PeftModel 推理即可

# ==================== 推理函数 ====================
def generate(model, question: str, max_new_tokens: int = 512) -> str:
    prompt = f"""<|im_start|>user
你是一个forward推理专家。请按照指定的推理风格回答。
{question}
<|im_end|>
<|im_start|>assistant
"""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
        )
    # 只取生成的部分（去掉输入 prompt）
    generated = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return generated.strip()

# ==================== 对比测试 ====================
print("\n" + "=" * 80)
print("开始对比测试：有 LoRA vs 无 LoRA")
print("=" * 80)

for i, question in enumerate(TEST_QUESTIONS, 1):
    print(f"\n{'─' * 80}")
    print(f"题目 {i}: {question[:50]}...")
    print(f"{'─' * 80}")

    print("\n【无 LoRA — 基座模型回答】")
    base_answer = generate(base_model, question)
    print(base_answer[:])
    # if len(base_answer) > 400:
    #     print("...(截断)")

    print("\n【有 LoRA — Forward Agent 回答】")
    lora_answer = generate(lora_model, question)
    print(lora_answer[:])
    # if len(lora_answer) > 400:
    #     print("...(截断)")

    print()

print("=" * 80)
print("对比完成。观察要点：")
print("  1. LoRA 回答是否更倾向于 短期→中期→长期 的因果链推理？")
print("  2. LoRA 回答是否更结构化（分步骤/阶段）？")
print("  3. LoRA 回答是否更有'最终分析'式的总结句？")
print("  4. 如果以上 3 点有明显差异，说明 LoRA 认知注入成功 ✅")
