"""扰动功能验证：对比无扰动、正弦扰动、高斯噪声三种情况。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, run_from_config, Visualizer


def main():
    # 加载三组配置
    configs = {
        "no_disturbance": SimConfig.from_yaml("configs/step_response.yaml"),
        "sine": SimConfig.from_yaml("configs/step_with_disturbance.yaml"),
        "gaussian": SimConfig.from_yaml("configs/step_with_noise.yaml"),
    }

    # 分别运行仿真
    results = []
    for name, cfg in configs.items():
        print(f"Running: {name}")
        result = run_from_config(cfg)
        results.append(result)

    # 保存带扰动的结果
    result_dir = results[1].save("../results")

    # 多结果对比绘图
    Visualizer.plot(
        results,
        items=["position", "velocity", "control", "disturbance"],
        title="Step Response: No Disturbance vs Sine vs Gaussian",
        save_path=str(result_dir / "comparison.png"),
    )


if __name__ == "__main__":
    main()
