"""轨迹对比实验：同一控制器在 Step / Ramp / Sine 参考下的表现。

使用方法：
    cd experiments/trajectory_comparison && python run.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml
import numpy as np

from msd import SimConfig, run_from_config, Visualizer
from msd.metrics import compute_metrics, format_metrics_table


def run_trajectory_test(base_cfg: dict, ctrl_name: str, ctrl_def: dict,
                        references: dict, results_dir: Path):
    """对一种控制器，遍历所有参考轨迹。"""
    ctrl_dir = results_dir / ctrl_name.lower()
    ctrl_dir.mkdir(parents=True, exist_ok=True)

    results = []
    all_metric_names = set()

    for ref_type, ref_def in references.items():
        ref_params = ref_def["reference_params"]
        metric_names = ref_def.get("metrics", ["rmse", "max_control"])
        all_metric_names.update(metric_names)

        cfg_dict = dict(base_cfg)
        cfg_dict["controller_type"] = ctrl_def["controller_type"]
        cfg_dict["controller_params"] = dict(ctrl_def["controller_params"])
        cfg_dict["reference_type"] = ref_type
        cfg_dict["reference_params"] = ref_params
        cfg_dict["label"] = f"{ctrl_name}+{ref_type}"

        # SMC 对时变参考需开启导数估计
        if ctrl_def["controller_type"] == "SMC" and ref_type in ("Ramp", "Sine"):
            cfg_dict["controller_params"]["estimate_reference_derivative"] = True

        cfg = SimConfig.from_dict(cfg_dict)
        result = run_from_config(cfg)
        result.metrics = compute_metrics(result, metric_names)
        results.append(result)

        extra_arrays = {f"extra_{k}": v for k, v in result.extras.items()}
        np.savez(
            ctrl_dir / f"data_{ref_type}.npz",
            time=result.time, states=result.states,
            control=result.control, reference=result.reference,
            disturbance=result.disturbance, **extra_arrays,
        )

    Visualizer.plot(
        results,
        items=["tracking", "error", "control"],
        title=f"{ctrl_name} Trajectory Comparison",
        save_path=str(ctrl_dir / "timeseries.png"),
    )

    common_metrics = ["rmse", "iae", "max_control", "control_energy"]
    Visualizer.plot_metrics_bar(
        results, common_metrics,
        title=f"{ctrl_name}: Common Metrics",
        save_path=str(ctrl_dir / "metrics.png"),
    )

    table = format_metrics_table(results, list(all_metric_names))
    print(f"\n=== {ctrl_name} Trajectory Comparison ===")
    print(table)
    with open(ctrl_dir / "report.txt", "w") as f:
        f.write(f"{ctrl_name} Trajectory Comparison\n\n{table}")


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

    for ctrl_name, ctrl_def in controllers.items():
        run_trajectory_test(base_cfg, ctrl_name, ctrl_def, references, results_dir)

    print(f"\nAll results saved to {results_dir}")


if __name__ == "__main__":
    main()
