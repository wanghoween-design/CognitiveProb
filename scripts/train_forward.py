import os

# ==================== 环境变量设置 ====================
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

import sys
import json
import math
import inspect
import torch
from pathlib import Path
from collections import Counter

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainerCallback,
    set_seed,
)

from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)

from trl import SFTTrainer, SFTConfig


# ==================== 项目配置导入 ====================
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import config


# ==================== 基础设置 ====================
SEED = 42
set_seed(SEED)

MODEL_PATH = r".\models\qwen3-4b\Qwen\Qwen3-4B"
DATA_PATH = "data/forward_train.json"
OUTPUT_DIR = "./adapters/forward_lora"

# RTX 3060 6GB：先用 1024，跑通后再尝试 1536 / 2048
MAX_LENGTH = 1024

# 如果你的 output 里没有 <think>...</think>，建议关闭 Qwen3 thinking
ENABLE_THINKING = False

NUM_TRAIN_EPOCHS = 4
PER_DEVICE_TRAIN_BATCH_SIZE = 1
GRADIENT_ACCUMULATION_STEPS = 16
LEARNING_RATE = 2e-4
WARMUP_RATIO_VALUE = 0.1


# ==================== CUDA 检查 ====================
if not torch.cuda.is_available():
    raise RuntimeError("当前没有检测到 CUDA。RTX 3060 训练需要 CUDA 环境。")

print(f"当前 GPU: {torch.cuda.get_device_name(0)}")

# TF32 只影响 fp32 matmul 性能，不会启用 bf16。
torch.backends.cuda.matmul.allow_tf32 = True


# ==================== dtype 工程检查工具 ====================
def print_parameter_dtype_summary(model, title, trainable_only=False):
    counter = Counter()
    total = 0

    for _, param in model.named_parameters():
        if trainable_only and not param.requires_grad:
            continue

        counter[str(param.dtype)] += param.numel()
        total += param.numel()

    print(f"\n{title}")

    if total == 0:
        print("  没有匹配的参数")
        return

    for dtype_name, numel in sorted(counter.items()):
        ratio = numel / total * 100
        print(f"  {dtype_name}: {numel:,} params ({ratio:.4f}%)")


def assign_buffer_by_name(module, buffer_name, new_tensor):
    parts = buffer_name.split(".")
    parent = module

    for part in parts[:-1]:
        parent = getattr(parent, part)

    parent._buffers[parts[-1]] = new_tensor


def force_trainable_params_to_fp32(model, verbose=True):
    """
    核心修复：
    所有 requires_grad=True 的参数必须转为 fp32。

    原因：
    RTX 3060 不支持 bf16 训练。
    你的日志已经证明 SFTTrainer 创建后，
    LoRA 的 lora_A/lora_B 可训练参数会重新变成 bf16。

    所以必须在：
        1. get_peft_model 之后修正一次；
        2. SFTTrainer 创建之后再修正一次；
        3. train() 开始前回调里兜底修正一次。

    LoRA 参数很小，用 fp32 稳定且显存增加可以接受。
    """
    converted = []

    for name, param in model.named_parameters():
        if param.requires_grad and param.dtype != torch.float32:
            old_dtype = str(param.dtype)
            param.data = param.data.to(torch.float32)

            if param.grad is not None:
                param.grad.data = param.grad.data.to(torch.float32)

            converted.append((name, old_dtype, str(param.dtype)))

    if verbose:
        print(f"\n可训练参数 fp32 归一：转换 {len(converted)} 个参数")

        for name, old_dtype, new_dtype in converted[:20]:
            print(f"  - {name}: {old_dtype} -> {new_dtype}")

        if len(converted) > 20:
            print(f"  ... 其余 {len(converted) - 20} 个省略")


def force_bf16_buffers_to_fp16(model, verbose=True):
    """
    兜底：
    如果有 bf16 buffer，则转成 fp16。
    """
    converted = []

    for name, buffer in list(model.named_buffers()):
        if torch.is_tensor(buffer) and buffer.dtype == torch.bfloat16:
            assign_buffer_by_name(model, name, buffer.to(torch.float16))
            converted.append(name)

    if verbose:
        print(f"bf16 buffer -> fp16：转换 {len(converted)} 个 buffer")

        for name in converted[:20]:
            print(f"  - {name}")

        if len(converted) > 20:
            print(f"  ... 其余 {len(converted) - 20} 个省略")


def normalize_for_rtx3060(model, where):
    """
    3060 dtype 总入口。

    注意：
    不要对整个 model 调用 model.to(fp16)，
    避免破坏 bitsandbytes 的 4bit 模块。
    """
    print(f"\n========== dtype 归一位置：{where} ==========")

    # 防止后续模块继续根据 config 创建 bf16 权重。
    if hasattr(model, "config"):
        model.config.torch_dtype = torch.float16
        model.config.use_cache = False

    force_trainable_params_to_fp32(model, verbose=True)
    force_bf16_buffers_to_fp16(model, verbose=True)

    print_parameter_dtype_summary(
        model,
        f"{where}：可训练参数 dtype 分布",
        trainable_only=True,
    )


def assert_trainable_no_bf16(model, where):
    bad = []

    for name, param in model.named_parameters():
        if param.requires_grad and param.dtype == torch.bfloat16:
            bad.append(name)

    if bad:
        lines = [f"{where}：仍检测到 bf16 可训练参数，禁止开始训练："]

        for name in bad[:200]:
            lines.append(f"  - {name}")

        if len(bad) > 200:
            lines.append(f"  ... 其余 {len(bad) - 200} 个省略")

        raise RuntimeError("\n".join(lines))

    print(f"{where}：检查通过，没有 bf16 可训练参数。")


class DTypeGuardCallback(TrainerCallback):
    """
    训练开始前最后一道保险。

    如果 Trainer / Accelerate 在内部又改了 dtype，
    这里会再转回 fp32。
    """
    def on_train_begin(self, args, state, control, model=None, **kwargs):
        if model is not None:
            normalize_for_rtx3060(model, "on_train_begin")
            assert_trainable_no_bf16(model, "on_train_begin")


# ==================== 版本兼容工具 ====================
def build_sft_config(**kwargs):
    """
    兼容不同 transformers / trl 版本。

    1. 新版本可能使用 eval_strategy；
       老版本可能使用 evaluation_strategy。

    2. 新版本使用 max_length；
       老版本可能使用 max_seq_length。

    3. loss_type 只在当前版本支持时传入；
       不支持则自动跳过，避免 TypeError。
    """
    sig = inspect.signature(SFTConfig.__init__)
    valid_keys = set(sig.parameters.keys())

    if "eval_strategy" not in valid_keys and "evaluation_strategy" in valid_keys:
        if "eval_strategy" in kwargs:
            kwargs["evaluation_strategy"] = kwargs.pop("eval_strategy")

    if "max_length" not in valid_keys and "max_seq_length" in valid_keys:
        if "max_length" in kwargs:
            kwargs["max_seq_length"] = kwargs.pop("max_length")

    filtered = {
        key: value
        for key, value in kwargs.items()
        if key in valid_keys
    }

    dropped = sorted(set(kwargs.keys()) - set(filtered.keys()))

    if dropped:
        print(f"当前 TRL/SFTConfig 不支持这些参数，已跳过: {dropped}")

    return SFTConfig(**filtered)


# ==================== 量化配置 ====================
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)


# ==================== 加载分词器 ====================
print("加载分词器...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True,
    padding_side="right",
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token


# ==================== 加载 4bit 量化模型 ====================
print("加载 4bit 量化模型...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    quantization_config=bnb_config,
    device_map={"": 0},
    trust_remote_code=True,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float16,
)

model.config.torch_dtype = torch.float16
model.config.use_cache = False
model.config.pad_token_id = tokenizer.pad_token_id

if hasattr(model, "generation_config"):
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    model.generation_config.eos_token_id = tokenizer.eos_token_id


# ==================== k-bit 训练准备 ====================
try:
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
    )
except TypeError:
    model = prepare_model_for_kbit_training(model)

model.config.torch_dtype = torch.float16
model.config.use_cache = False
model.config.pad_token_id = tokenizer.pad_token_id

if hasattr(model, "enable_input_require_grads"):
    model.enable_input_require_grads()

print("模型加载完成")

print_parameter_dtype_summary(
    model,
    "LoRA 注入前：全部参数 dtype",
    trainable_only=False,
)


# ==================== LoRA 配置 ====================
print("配置 LoRA...")

lora_config_dict = config["model"]["lora"]["forward"]

default_target_modules = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]

target_modules = lora_config_dict.get(
    "target_modules",
    default_target_modules,
)

lora_config = LoraConfig(
    r=lora_config_dict.get("r", 8),
    lora_alpha=lora_config_dict.get("alpha", 16),
    target_modules=target_modules,
    lora_dropout=lora_config_dict.get("dropout", 0.05),
    bias="none",
    task_type="CAUSAL_LM",
)

# 注意：
# 这里显式关闭 autocast_adapter_dtype。
# 你的环境中 SFTTrainer 后 adapter 会变成 bf16，
# 所以 adapter dtype 我们自己控制。
try:
    model = get_peft_model(
        model,
        lora_config,
        autocast_adapter_dtype=False,
    )
except TypeError:
    model = get_peft_model(
        model,
        lora_config,
    )

model.print_trainable_parameters()

print_parameter_dtype_summary(
    model,
    "LoRA 注入后：可训练参数 dtype 修正前",
    trainable_only=True,
)

normalize_for_rtx3060(
    model,
    "get_peft_model 之后",
)

assert_trainable_no_bf16(
    model,
    "get_peft_model 之后",
)

try:
    memory_gb = model.get_memory_footprint() / 1024 ** 3
    print(f"模型显存/内存占用估计: {memory_gb:.2f} GB")
except Exception:
    pass


# ==================== 加载训练数据 ====================
print("加载训练数据...")

raw_dataset = load_dataset(
    "json",
    data_files=DATA_PATH,
    split="train",
)

print(f"原始训练数据条数: {len(raw_dataset)}")

if len(raw_dataset) == 0:
    raise RuntimeError("训练数据为空，请检查 data/forward_train.json")

required_columns = {
    "instruction",
    "input",
    "output",
}

missing_columns = required_columns - set(raw_dataset.column_names)

if missing_columns:
    raise RuntimeError(f"训练数据缺少字段: {sorted(missing_columns)}")

print("数据格式示例:")
print(f"  instruction: {str(raw_dataset[0]['instruction'])[:80]}...")
print(f"  input: {str(raw_dataset[0]['input'])[:80]}...")
print(f"  output: {str(raw_dataset[0]['output'])[:120]}...")


# ==================== Qwen3 Chat Template 工具函数 ====================
def apply_qwen_template(messages, add_generation_prompt):
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
            enable_thinking=ENABLE_THINKING,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )


def build_user_content(sample):
    instruction = str(sample.get("instruction", "")).strip()
    input_text = str(sample.get("input", "")).strip()

    if input_text:
        return f"{instruction}\n\n{input_text}"

    return instruction


def to_prompt_completion(sample):
    user_content = build_user_content(sample)
    assistant_content = str(sample.get("output", "")).strip()

    if not user_content:
        raise ValueError("发现空 prompt，请检查 instruction/input 字段。")

    if not assistant_content:
        raise ValueError("发现空 completion，请检查 output 字段。")

    user_messages = [
        {
            "role": "user",
            "content": user_content,
        }
    ]

    full_messages = [
        {
            "role": "user",
            "content": user_content,
        },
        {
            "role": "assistant",
            "content": assistant_content,
        },
    ]

    prompt = apply_qwen_template(
        user_messages,
        add_generation_prompt=True,
    )

    full_text = apply_qwen_template(
        full_messages,
        add_generation_prompt=False,
    )

    if full_text.startswith(prompt):
        completion = full_text[len(prompt):]
    else:
        assistant_marker = "<|im_start|>assistant\n"
        pos = full_text.rfind(assistant_marker)

        if pos == -1:
            print("prompt 示例：")
            print(prompt[:1000])
            print("full_text 示例：")
            print(full_text[:1000])
            raise ValueError("无法在 chat template 中找到 assistant 起始标记。")

        prompt = full_text[:pos + len(assistant_marker)]
        completion = full_text[pos + len(assistant_marker):]

    if not completion.strip():
        raise ValueError("发现空 completion，请检查训练数据 output 字段。")

    return {
        "prompt": prompt,
        "completion": completion,
    }


# ==================== 转换数据集格式 ====================
print("转换为 prompt-completion 格式...")

dataset = raw_dataset.map(
    to_prompt_completion,
    remove_columns=raw_dataset.column_names,
)

print("模板化后的样例 prompt:")
print(dataset[0]["prompt"][:500])

print("模板化后的样例 completion:")
print(dataset[0]["completion"][:500])


# ==================== 过滤超长样本 ====================
def add_token_length(sample):
    text = sample["prompt"] + sample["completion"]

    tokenized = tokenizer(
        text,
        add_special_tokens=False,
    )

    return {
        "n_tokens": len(tokenized["input_ids"]),
    }


print("统计 token 长度...")

dataset = dataset.map(add_token_length)

num_before = len(dataset)

dataset = dataset.filter(
    lambda x: x["n_tokens"] <= MAX_LENGTH,
)

num_after = len(dataset)

print(f"长度过滤: {num_before} -> {num_after}")
print(f"被过滤样本数: {num_before - num_after}")

if num_after == 0:
    raise RuntimeError(
        f"所有样本都超过 MAX_LENGTH={MAX_LENGTH}。"
        f"请增大 MAX_LENGTH，或者缩短训练数据。"
    )

dataset = dataset.remove_columns(["n_tokens"])


# ==================== 划分训练集 / 验证集 ====================
if len(dataset) >= 20:
    split_dataset = dataset.train_test_split(
        test_size=0.1,
        seed=SEED,
    )

    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]
    use_eval = True
else:
    train_dataset = dataset
    eval_dataset = None
    use_eval = False

print(f"训练集条数: {len(train_dataset)}")

if use_eval:
    print(f"验证集条数: {len(eval_dataset)}")
else:
    print("数据量较少，不划分验证集")


# ==================== warmup_steps 计算 ====================
steps_per_epoch = math.ceil(
    len(train_dataset)
    / (
        PER_DEVICE_TRAIN_BATCH_SIZE
        * GRADIENT_ACCUMULATION_STEPS
    )
)

total_optimization_steps = steps_per_epoch * NUM_TRAIN_EPOCHS

warmup_steps = int(total_optimization_steps * WARMUP_RATIO_VALUE)

if WARMUP_RATIO_VALUE > 0 and warmup_steps == 0:
    warmup_steps = 1

print(f"每个 epoch 优化步数: {steps_per_epoch}")
print(f"总优化步数: {total_optimization_steps}")
print(f"warmup_steps: {warmup_steps}")


# ==================== 训练参数 ====================
sft_kwargs = dict(
    output_dir=OUTPUT_DIR,

    num_train_epochs=NUM_TRAIN_EPOCHS,
    per_device_train_batch_size=PER_DEVICE_TRAIN_BATCH_SIZE,
    gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,

    learning_rate=LEARNING_RATE,
    lr_scheduler_type="cosine",
    warmup_steps=warmup_steps,
    weight_decay=0.0,
    max_grad_norm=1.0,

    # RTX 3060：禁用 bf16，只启用 fp16 AMP。
    fp16=True,
    bf16=False,

    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={
        "use_reentrant": False,
    },

    # Windows + 3060：adamw_torch 最稳。
    optim="adamw_torch",

    max_length=MAX_LENGTH,
    packing=False,
    completion_only_loss=True,
    assistant_only_loss=False,

    # 如果当前版本支持则固定当前 loss 行为；
    # 不支持会被 build_sft_config 自动跳过。
    loss_type="nll",

    logging_steps=1,
    logging_first_step=True,
    report_to="none",

    save_strategy="epoch",
    save_total_limit=2,

    eval_strategy="epoch" if use_eval else "no",
    per_device_eval_batch_size=1,

    load_best_model_at_end=True if use_eval else False,
    metric_for_best_model="eval_loss" if use_eval else None,
    greater_is_better=False if use_eval else None,

    dataloader_num_workers=0,
)

training_args = build_sft_config(**sft_kwargs)


# ==================== 日志回调 ====================
class MetricsLogger(TrainerCallback):
    def __init__(self):
        self.history = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs:
            return

        record = {
            "step": int(state.global_step),
            "epoch": float(state.epoch) if state.epoch is not None else None,
        }

        for key, value in logs.items():
            if isinstance(value, torch.Tensor):
                record[key] = value.detach().cpu().item()
            elif isinstance(value, (int, float, str)) or value is None:
                record[key] = value
            else:
                try:
                    record[key] = float(value)
                except Exception:
                    record[key] = str(value)

        self.history.append(record)


metrics_logger = MetricsLogger()
dtype_guard = DTypeGuardCallback()


# ==================== 创建 Trainer ====================
print("创建 SFTTrainer...")

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    processing_class=tokenizer,
    callbacks=[
        metrics_logger,
        dtype_guard,
    ],
)

# 关键修复：
# SFTTrainer 创建后，某些版本会把 LoRA 权重重新放回 bf16。
# 你的最新日志已经证明了这一点。
# 因此这里必须再次修正，而不是只检查。
print_parameter_dtype_summary(
    trainer.model,
    "SFTTrainer 创建后：可训练参数 dtype 修正前",
    trainable_only=True,
)

normalize_for_rtx3060(
    trainer.model,
    "SFTTrainer 创建后",
)

assert_trainable_no_bf16(
    trainer.model,
    "SFTTrainer 创建后",
)


# ==================== 开始训练 ====================
print("开始训练 Forward Agent LoRA...")

trainer.train()


# ==================== 保存训练日志 ====================
output_path = Path(training_args.output_dir)
output_path.mkdir(parents=True, exist_ok=True)

log_path = output_path / "training_log.json"

with open(log_path, "w", encoding="utf-8") as f:
    json.dump(
        metrics_logger.history,
        f,
        ensure_ascii=False,
        indent=2,
    )

print(f"训练日志已保存: {log_path}")


# ==================== 保存 Adapter 和 tokenizer ====================
print("训练完成，保存 Adapter...")

trainer.save_model(training_args.output_dir)
tokenizer.save_pretrained(training_args.output_dir)

print("✅ Forward Agent LoRA 训练完成！")
print(f"Adapter 保存在: {training_args.output_dir}")