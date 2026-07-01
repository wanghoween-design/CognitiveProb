import torch
import sys
import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments, TrainerCallback
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config



#==================== 量化配置 ====================

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,                          # 启用 4-bit 量化,	核心开关，不开就不是 QLoRA
    bnb_4bit_quant_type="nf4",                  # NF4 量化类型（比 FP4 效果好）NF4 是专门为神经网络设计的量化格式，比 FP4 效果好
    bnb_4bit_compute_dtype=torch.float16,      # RTX 3060 不支持 bf16，用 float16 做量化计算
    bnb_4bit_use_double_quant=True,              # 双重量化，再省一点显存 对量化参数再量化一次，额外省 ~0.4GB 显存,
    # bnb_4bit_quant_storage_dtype=torch.uint8
)

# ==================== 加载模型和分词器 ====================

MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"

print("加载分词器...")
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,                     # qwen3 需要执行自定义代码
    padding_side="right"                        # 填充方向设为右边（训练时用）训练时文本右对齐，这样模型能看到完整的上下文
    )
tokenizer.pad_token = tokenizer.eos_token       # Qwen3 默认没有 pad_token，用 eos_token 充当填充标记

print("加载量化模型...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config = bnb_config,
    device_map="auto",                          # 用上面的 4-bit 量化配置
    trust_remote_code=True,                      # 自动分配 GPU（有几卡用几卡）
    low_cpu_mem_usage= True                      # 以更省内存的方式加载，避免爆页面文件
)

# 准备模型进行量化训练
model = prepare_model_for_kbit_training(model)  #冻结大部分参数，只训练 LoRA 部分
model.gradient_checkpointing_enable()           # 用计算换显存，RTX 3060 6GB 必备
print("模型加载完成")

#==================== LoRA 配置 ===================

lora_config_dict = config["model"]["lora"]["creative"]

lora_config = LoraConfig(
    r=lora_config_dict['r'],                                ## LoRA 的秩（rank），越大学习能力越强，但越慢
    lora_alpha=lora_config_dict['alpha'],                   # 缩放因子，通常 = 2*r
    target_modules=lora_config_dict['target_modules'],      # 把 LoRA 注入到哪些层
    lora_dropout=lora_config_dict['dropout'],
    bias='none',
    task_type='CAUSAL_LM'
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ==================== 加载训练数据 ====================
print("加载训练数据...")
dataset = load_dataset("json", data_files="data/creative_train.json", split="train")
print(f"训练数据条数: {len(dataset)}")
print(f"数据格式示例:")
print(f"  instruction: {dataset[0]['instruction'][:50]}...")
print(f"  input: {dataset[0]['input'][:50]}...")
print(f"  output: {dataset[0]['output'][:100]}...")


# ==================== 训练参数 ===================

training_args = TrainingArguments(
    output_dir="./adapters/creative_lora",    # 训练结果保存到这里
    num_train_epochs=4,                       # 训练 3 轮（Creative 参数多，过拟合风险高，Epoch 3 最优）
    per_device_train_batch_size=1,            # RTX 3060 6GB：每次只喂 1 条数据
    gradient_accumulation_steps=16,            # 累积 16 步 = 等效 batch_size=16
    learning_rate=2e-4,                       # 学习率，太大模型学不好，太小学得慢 QLoRA 推荐值，太大模型会"忘记"原来的知识
    lr_scheduler_type="cosine",               # 学习率调度：余弦退火（先大后小）学习率先大后小，避免后期震荡
    warmup_ratio=0.1,                         # 前 10% 的步数用来预热（学习率从小慢慢升）前 10% 步数学习率从 0 慢慢升到 2e-4
    weight_decay=0.01,                        # 权重衰减，防止过拟合轻微正则化，防止过拟合
    max_grad_norm=1.0,                        # 梯度裁剪，防止梯度爆炸 梯度裁剪，防止梯度爆炸导致训练崩溃
    logging_steps=1,                          # 每 1 步打印一次 loss
    save_strategy="epoch",                    # 每个 epoch 保存一次 checkpoint
    report_to="none",                         # 不上报到 wandb 等平台
)

# ==================== 开始训练 ====================
print("开始训练 Creative Agent LoRA...")

def format_prompt(sample):
    """将数据格式化为模型能理解的格式"""
    return f"""<|im_start|>user
{sample['instruction']}
{sample['input']}
<|im_end|>
<|im_start|>assistant
{sample['output']}
<|im_end|>"""

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    formatting_func=format_prompt,  # 【关键】将格式化函数传入这里
    processing_class=tokenizer,            # 传入 tokenizer 以便 SFTTrainer 正确截断和填充
)

# 注册日志回调，把每步的训练指标存下来，后续画图用
class MetricsLogger(TrainerCallback):
    def __init__(self):
        self.history = []
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs and 'loss' in logs:
            self.history.append(logs)

metrics_logger = MetricsLogger()
trainer.add_callback(metrics_logger)

trainer.train()

# 保存训练日志到 JSON，供画图脚本使用
log_path = Path(training_args.output_dir) / "training_log.json"
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(metrics_logger.history, f, ensure_ascii=False, indent=2)
print(f"训练日志已保存: {log_path}")

# ==================== 保存 Adapter ====================
print("训练完成，保存 Adapter...")
trainer.save_model(training_args.output_dir)
print(f"✅ Creative Agent LoRA 训练完成！")
print(f"Adapter 保存在: {training_args.output_dir}")