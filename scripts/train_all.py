"""
接力训练：Forward → Critical → Creative
用法：python scripts/train_all.py
"""

import subprocess
import sys
import time
from pathlib import Path

# 训练脚本列表（按顺序执行）
TRAIN_SCRIPTS = [
    ("Forward LoRA", "scripts/train_forward.py"),
    ("Critical LoRA", "scripts/train_critical.py"),
    ("Creative LoRA", "scripts/train_creative.py"),
]


def run_training(name, script_path):
    """运行单个训练脚本"""
    print(f"\n{'='*60}")
    print(f"开始训练: {name}")
    print(f"脚本: {script_path}")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    start_time = time.time()

    # 运行训练脚本
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=str(Path(__file__).parent.parent),  # 项目根目录
    )

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    if result.returncode == 0:
        print(f"\n✅ {name} 训练完成! 耗时: {minutes}分{seconds}秒")
    else:
        print(f"\n❌ {name} 训练失败! 返回码: {result.returncode}")

    return result.returncode


def main():
    print("=" * 60)
    print("接力训练：Forward → Critical → Creative")
    print("=" * 60)
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"预计总耗时: 2-4 小时")

    total_start = time.time()
    results = []

    for name, script in TRAIN_SCRIPTS:
        if not Path(script).exists():
            print(f"\n⚠️ 跳过 {name}: 脚本不存在 {script}")
            results.append((name, -1))
            continue

        returncode = run_training(name, script)
        results.append((name, returncode))

        # 如果失败，询问是否继续
        if returncode != 0:
            print(f"\n⚠️ {name} 失败，是否继续训练下一个？")
            response = input("输入 y 继续，其他任意键退出: ")
            if response.lower() != 'y':
                print("训练中止")
                break

    # 汇总
    total_elapsed = time.time() - total_start
    minutes = int(total_elapsed // 60)
    seconds = int(total_elapsed % 60)

    print("\n" + "=" * 60)
    print("训练汇总")
    print("=" * 60)
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {minutes}分{seconds}秒")
    print()

    for name, returncode in results:
        status = "✅ 成功" if returncode == 0 else "❌ 失败"
        print(f"  {name}: {status}")

    print("\n训练完成的 adapter 保存在:")
    print("  adapters/forward_lora/")
    print("  adapters/critical_lora/")
    print("  adapters/creative_lora/")


if __name__ == '__main__':
    main()
