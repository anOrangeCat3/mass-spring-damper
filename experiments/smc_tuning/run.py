"""SMC 调参实验：η/λ 参数扫描 + 切换函数对比。

使用方法：
    cd experiments/smc_tuning && python run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml
import numpy as np

from msd import SimConfig, run_from_config, Visualizer
from msd.metrics import compute_metrics, format_metrics_table


def _set_nested(d: dict, path: str, value):
    """设置嵌套字典中的值。"""
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def run_sweep(base_cfg: dict, sweep_name: str, sweep_def: dict,
              metric_names: list[str], results_dir: Path):
    """运行单个参数扫描。"""
    param_path = sweep_def["param_path"]
    values = sweep_def["values"]
    param_short = param_path.split(".")[-1]

    sweep_dir = results_dir / sweep_name
    sweep_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for val in values:
        cfg_dict = dict(base_cfg)
        _set_nested(cfg_dict, param_path, val)
        cfg_dict["label"] = f"{param_short}={val}"

        cfg = SimConfig.from_dict(cfg_dict)
        result = run_from_config(cfg)
        result.metrics = compute_metrics(result, metric_names)
        results.append(result)

        extra_arrays = {f"extra_{k}": v for k, v in result.extras.items()}
        np.savez(
            sweep_dir / f"data_{param_short}_{val}.npz",
            time=result.time, states=result.states,
            control=result.control, reference=result.reference,
            disturbance=result.disturbance, **extra_arrays,
        )

    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title=f"{sweep_name}: Time Series",
        save_path=str(sweep_dir / "timeseries.png"),
    )
    Visualizer.plot_metrics_vs_param(
        results,
        param_values=values,
        param_name=param_short,
        metric_names=metric_names,
        title=f"{sweep_name}: Metrics vs {param_short}",
        save_path=str(sweep_dir / "metrics.png"),
    )

    table = format_metrics_table(results, metric_names)
    print(f"\n=== {sweep_name} ===")
    print(table)
    with open(sweep_dir / "report.txt", "w") as f:
        f.write(f"Sweep: {sweep_name}\nParameter: {param_path}\nValues: {values}\n\n{table}")


def run_smoothing_comparison(base_cfg: dict, variants: list[dict],
                             metric_names: list[str], results_dir: Path):
    """运行切换函数对比。"""
    comp_dir = results_dir / "smoothing_comparison"
    comp_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for var in variants:
        cfg_dict = dict(base_cfg)
        params = dict(cfg_dict.get("controller_params", {}))
        params["smoothing"] = var.get("smoothing")
        if var.get("phi") is not None:
            params["phi"] = var["phi"]
        cfg_dict["controller_params"] = params
        cfg_dict["label"] = var["label"]

        cfg = SimConfig.from_dict(cfg_dict)
        result = run_from_config(cfg)
        result.metrics = compute_metrics(result, metric_names)
        results.append(result)

        extra_arrays = {f"extra_{k}": v for k, v in result.extras.items()}
        np.savez(
            comp_dir / f"data_{var['label'].replace(' ', '_')}.npz",
            time=result.time, states=result.states,
            control=result.control, reference=result.reference,
            disturbance=result.disturbance, **extra_arrays,
        )

    Visualizer.plot(
        results,
        items=["tracking", "control"],
        title="SMC Smoothing Comparison",
        save_path=str(comp_dir / "timeseries.png"),
    )
    Visualizer.plot(
        results,
        items=["sliding_surface"],
        title="SMC Sliding Surface Comparison",
        save_path=str(comp_dir / "sliding_surface.png"),
    )
    Visualizer.plot_metrics_bar(
        results, metric_names,
        title="SMC Smoothing: Metrics",
        save_path=str(comp_dir / "metrics.png"),
    )

    table = format_metrics_table(results, metric_names)
    print("\n=== Smoothing Comparison ===")
    print(table)
    with open(comp_dir / "report.txt", "w") as f:
        f.write(f"Smoothing Comparison\n\n{table}")


def main():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        full_config = yaml.safe_load(f)

    sweeps = full_config.get("sweeps", {})
    smoothing_variants = full_config.get("smoothing_comparison", [])
    metric_names = full_config.get("metrics", ["rmse", "max_control"])

    base_cfg = {k: v for k, v in full_config.items()
                if k not in ("sweeps", "smoothing_comparison", "metrics")}

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    for sweep_name, sweep_def in sweeps.items():
        run_sweep(base_cfg, sweep_name, sweep_def, metric_names, results_dir)

    if smoothing_variants:
        run_smoothing_comparison(base_cfg, smoothing_variants, metric_names, results_dir)

    print(f"\nAll results saved to {results_dir}")


if __name__ == "__main__":
    main()
