"""控制器对比实验：PID vs SMC 在不同参考轨迹下的表现。

使用方法：
    cd experiments/controller_comparison && python run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml
import numpy as np

from msd import SimConfig, run_from_config, Visualizer
from msd.metrics import compute_metrics, format_metrics_table


def run_comparison(base_cfg: dict, controllers: dict, ref_name: str,
                   ref_def: dict, results_dir: Path):
    """对一种参考轨迹，运行所有控制器对比。"""
    metric_names = ref_def.get("metrics", ["rmse", "max_control"])
    comp_dir = results_dir / ref_name
    comp_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for ctrl_name, ctrl_def in controllers.items():
        cfg_dict = dict(base_cfg)
        cfg_dict["controller_type"] = ctrl_def["controller_type"]
        cfg_dict["controller_params"] = dict(ctrl_def["controller_params"])
        cfg_dict["reference_type"] = ref_def["reference_type"]
        cfg_dict["reference_params"] = dict(ref_def["reference_params"])
        cfg_dict["label"] = ctrl_name

        cfg = SimConfig.from_dict(cfg_dict)
        result = run_from_config(cfg)
        result.metrics = compute_metrics(result, metric_names)
        results.append(result)

        extra_arrays = {f"extra_{k}": v for k, v in result.extras.items()}
        np.savez(
            comp_dir / f"data_{ctrl_name}.npz",
            time=result.time, states=result.states,
            control=result.control, reference=result.reference,
            disturbance=result.disturbance, **extra_arrays,
        )

    Visualizer.plot(
        results,
        items=["tracking", "error", "control"],
        title=f"Controller Comparison ({ref_name})",
        save_path=str(comp_dir / "timeseries.png"),
    )
    Visualizer.plot_metrics_bar(
        results, metric_names,
        title=f"Metrics Comparison ({ref_name})",
        save_path=str(comp_dir / "metrics.png"),
    )

    table = format_metrics_table(results, metric_names)
    print(f"\n=== {ref_name} ===")
    print(table)
    with open(comp_dir / "report.txt", "w") as f:
        f.write(f"Controller Comparison: {ref_name}\n\n{table}")


def main():
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        full_config = yaml.safe_load(f)

    controllers = full_config.get("controllers", {})
    references = full_config.get("references", {})

    base_cfg = {
        "y0": full_config.get("y0", [0.0, 0.0]),
        "dt": full_config.get("dt", 0.01),
        "t_end": full_config.get("t_end", 10.0),
        "method": full_config.get("method", "RK45"),
        "plant_type": full_config.get("plant_type", "MassSpringDamper"),
        "plant_params": full_config.get("plant_params", {}),
    }

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    for ref_name, ref_def in references.items():
        run_comparison(base_cfg, controllers, ref_name, ref_def, results_dir)

    print(f"\nAll results saved to {results_dir}")


if __name__ == "__main__":
    main()
