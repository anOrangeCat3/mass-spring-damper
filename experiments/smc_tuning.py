"""SMC 调参实验：η / λ 参数扫描 + 切换函数对比。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, ParameterSweep, ControllerComparison, Visualizer
from msd.metrics import compute_metrics, select_metrics, format_metrics_table


def eta_sweep():
    """η 趋近增益扫描，固定 λ=5, sign。"""
    base = SimConfig.from_yaml("../tests/configs/smc_step.yaml")
    sweep = ParameterSweep(
        name="smc_eta_sweep",
        base_config=base,
        param_path="controller_params.eta",
        values=[0.5, 1.0, 2.0, 5.0, 10.0],
        labels=[f"η={v}" for v in [0.5, 1.0, 2.0, 5.0, 10.0]],
    )
    sweep.run_and_save("../results")


def lambda_sweep():
    """λ 滑模面斜率扫描，固定 η=1, sign。"""
    base = SimConfig.from_yaml("../tests/configs/smc_step.yaml")
    sweep = ParameterSweep(
        name="smc_lambda_sweep",
        base_config=base,
        param_path="controller_params.lambda_",
        values=[1, 2, 5, 10, 20],
        labels=[f"λ={v}" for v in [1, 2, 5, 10, 20]],
    )
    sweep.run_and_save("../results")


def smoothing_comparison():
    """切换函数对比：sign / sat / tanh。包含滑模面 s(t) 图。"""
    base = SimConfig.from_yaml("../tests/configs/smc_step.yaml")

    variants = [
        (None,   None, "SMC sign"),
        ("sat",  0.5,  "SMC sat(φ=0.5)"),
        ("tanh", 0.5,  "SMC tanh(φ=0.5)"),
    ]

    configs = []
    for smoothing, phi, label in variants:
        params = dict(base.controller_params)
        params["smoothing"] = smoothing
        if phi is not None:
            params["phi"] = phi
        cfg = SimConfig.from_dict({
            **base.to_dict(),
            "controller_params": params,
            "label": label,
        })
        configs.append(cfg)

    comp = ControllerComparison(name="smc_smoothing_comparison", configs=configs)
    results = comp.run()
    exp_dir = comp._make_exp_dir("../results")

    # 保存数据
    for r in results:
        from msd.experiment import _sanitize_filename
        import numpy as np
        filename = f"data_{_sanitize_filename(r.label)}.npz"
        extra_arrays = {f"extra_{k}": v for k, v in r.extras.items()}
        np.savez(
            exp_dir / filename,
            time=r.time, states=r.states,
            control=r.control, reference=r.reference,
            disturbance=r.disturbance, **extra_arrays,
        )

    metric_names = select_metrics(results[0])
    comp._save_metrics_csv(results, metric_names, exp_dir)

    # 时域对比
    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title="SMC Smoothing Comparison",
        save_path=str(exp_dir / "timeseries.png"),
    )

    # 滑模面 s(t) 对比
    Visualizer.plot(
        results,
        items=["sliding_surface"],
        title="SMC Sliding Surface Comparison",
        save_path=str(exp_dir / "sliding_surface.png"),
    )

    # 指标柱状图
    Visualizer.plot_metrics_bar(
        results, metric_names,
        title="SMC Smoothing: Metrics Comparison",
        save_path=str(exp_dir / "metrics.png"),
    )

    # 报告
    comp._save_report(results, metric_names, exp_dir)

    # 控制台输出
    print(format_metrics_table(results, metric_names))
    print(f"Experiment saved to {exp_dir}")


if __name__ == "__main__":
    print("=== η Sweep ===")
    eta_sweep()
    print("\n=== λ Sweep ===")
    lambda_sweep()
    print("\n=== Smoothing Comparison ===")
    smoothing_comparison()
