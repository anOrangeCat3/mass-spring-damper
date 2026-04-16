"""SMC 控制器验证：阶跃跟踪 + 切换函数对比。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, run_from_config, Visualizer


def test_smc_step():
    """经典 SMC 阶跃跟踪测试（sign 切换函数）。"""
    config = SimConfig.from_yaml("configs/smc_step.yaml")
    result = run_from_config(config)
    result_dir = result.save("../results")

    Visualizer.plot(
        result,
        items=["tracking", "velocity", "control"],
        title="SMC Step Response (sign)",
        save_path=str(result_dir / "plot.png"),
    )


def test_smoothing_comparison():
    """切换函数对比：sign vs sat vs tanh。"""
    base = SimConfig.from_yaml("configs/smc_step.yaml")

    variants = [
        (None,   None, "sign"),
        ("sat",  0.5,  "sat(φ=0.5)"),
        ("tanh", 0.5,  "tanh(φ=0.5)"),
    ]

    results = []
    for smoothing, phi, label in variants:
        params = dict(base.controller_params)
        params["smoothing"] = smoothing
        if phi is not None:
            params["phi"] = phi

        cfg = SimConfig.from_dict({
            **base.to_dict(),
            "controller_params": params,
            "label": f"SMC {label}",
        })
        results.append(run_from_config(cfg))

    result_dir = results[0].save("../results")

    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title="SMC Smoothing Comparison (λ=5, η=1)",
        save_path=str(result_dir / "smoothing_comparison.png"),
    )


def test_eta_sweep():
    """趋近增益 η 参数扫描。"""
    base = SimConfig.from_yaml("configs/smc_step.yaml")
    eta_values = [0.5, 1.0, 2.0, 5.0, 10.0]

    results = []
    for eta in eta_values:
        cfg = SimConfig.from_dict({
            **base.to_dict(),
            "controller_params": {**base.controller_params, "eta": eta},
            "label": f"η={eta}",
        })
        results.append(run_from_config(cfg))

    result_dir = results[0].save("../results")

    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title="SMC η Sweep (λ=5, sign)",
        save_path=str(result_dir / "eta_sweep.png"),
    )


if __name__ == "__main__":
    print("=== SMC Step Response ===")
    test_smc_step()
    print("\n=== Smoothing Comparison ===")
    test_smoothing_comparison()
    print("\n=== η Sweep ===")
    test_eta_sweep()
