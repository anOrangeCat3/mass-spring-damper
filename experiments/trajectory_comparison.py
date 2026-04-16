"""轨迹对比实验：同一控制器在 Step / Ramp / Sine 参考下的表现。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, ControllerComparison


TRAJECTORIES = [
    ("Step",    {"value": 1.0, "t_step": 0.0}),
    ("Ramp",    {"slope": 0.5, "t_start": 0.0}),
    ("Sine",    {"amplitude": 1.0, "frequency": 0.5}),
]


def pid_trajectory():
    """PID 在不同轨迹下的表现。"""
    configs = []
    for ref_type, ref_params in TRAJECTORIES:
        cfg = SimConfig.from_dict({
            "plant_type": "MassSpringDamper",
            "plant_params": {"m": 1.0, "c": 0.5, "k": 2.0},
            "controller_type": "PID",
            "controller_params": {"kp": 10.0, "ki": 5.0, "kd": 4.0},
            "reference_type": ref_type,
            "reference_params": ref_params,
            "dt": 0.01, "t_end": 10.0,
            "label": f"PID+{ref_type}",
        })
        configs.append(cfg)

    comp = ControllerComparison(name="pid_trajectory", configs=configs)
    comp.run_and_save("../results")


def smc_trajectory():
    """SMC 在不同轨迹下的表现。"""
    configs = []
    for ref_type, ref_params in TRAJECTORIES:
        estimate_deriv = ref_type in ("Ramp", "Sine")
        cfg = SimConfig.from_dict({
            "plant_type": "MassSpringDamper",
            "plant_params": {"m": 1.0, "c": 0.5, "k": 2.0},
            "controller_type": "SMC",
            "controller_params": {
                "m": 1.0, "c": 0.5, "k": 2.0,
                "lambda_": 5.0, "eta": 1.0,
                "smoothing": "sat", "phi": 0.5,
                "estimate_reference_derivative": estimate_deriv,
            },
            "reference_type": ref_type,
            "reference_params": ref_params,
            "dt": 0.01, "t_end": 10.0,
            "label": f"SMC+{ref_type}",
        })
        configs.append(cfg)

    comp = ControllerComparison(name="smc_trajectory", configs=configs)
    comp.run_and_save("../results")


if __name__ == "__main__":
    print("=== PID Trajectory Comparison ===")
    pid_trajectory()
    print("\n=== SMC Trajectory Comparison ===")
    smc_trajectory()
