"""PID 控制器验证：阶跃跟踪 + Kp 参数扫描对比。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, run_from_config, Visualizer


def test_pid_step():
    """单组 PID 阶跃跟踪测试。"""
    config = SimConfig.from_yaml("configs/pid_step.yaml")
    result = run_from_config(config)
    result_dir = result.save("../results")

    Visualizer.plot(
        result,
        items=["tracking", "velocity", "control"],
        title="PID Step Response",
        save_path=str(result_dir / "plot.png"),
    )


def test_kp_sweep():
    """Kp 参数扫描：固定 Ki, Kd，对比不同 Kp 的响应。"""
    base = SimConfig.from_yaml("configs/pid_step.yaml")
    kp_values = [2, 5, 10, 20, 50]

    results = []
    for kp in kp_values:
        cfg = SimConfig.from_dict({
            **base.to_dict(),
            "controller_params": {**base.controller_params, "kp": kp},
            "label": f"Kp={kp}",
        })
        results.append(run_from_config(cfg))

    # 保存第一个结果的目录用于存图
    result_dir = results[0].save("../results")

    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title="PID Kp Sweep (Ki=5, Kd=4)",
        save_path=str(result_dir / "kp_sweep.png"),
    )


if __name__ == "__main__":
    print("=== PID Step Response ===")
    test_pid_step()
    print("\n=== Kp Sweep ===")
    test_kp_sweep()
