"""控制器对比实验：PID vs SMC 在不同参考轨迹下的表现。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, ControllerComparison


def _make_pid_config(reference_type: str, reference_params: dict, label: str = "PID") -> SimConfig:
    """构建 PID 配置。"""
    return SimConfig.from_dict({
        "plant_type": "MassSpringDamper",
        "plant_params": {"m": 1.0, "c": 0.5, "k": 2.0},
        "controller_type": "PID",
        "controller_params": {"kp": 10.0, "ki": 5.0, "kd": 4.0},
        "reference_type": reference_type,
        "reference_params": reference_params,
        "dt": 0.01, "t_end": 10.0,
        "label": label,
    })


def _make_smc_config(reference_type: str, reference_params: dict, label: str = "SMC") -> SimConfig:
    """构建 SMC 配置（sat 平滑）。"""
    return SimConfig.from_dict({
        "plant_type": "MassSpringDamper",
        "plant_params": {"m": 1.0, "c": 0.5, "k": 2.0},
        "controller_type": "SMC",
        "controller_params": {
            "m": 1.0, "c": 0.5, "k": 2.0,
            "lambda_": 5.0, "eta": 1.0,
            "smoothing": "sat", "phi": 0.5,
        },
        "reference_type": reference_type,
        "reference_params": reference_params,
        "dt": 0.01, "t_end": 10.0,
        "label": label,
    })


def step_comparison():
    """阶跃参考下 PID vs SMC。"""
    ref_type, ref_params = "Step", {"value": 1.0, "t_step": 0.0}
    configs = [
        _make_pid_config(ref_type, ref_params, "PID"),
        _make_smc_config(ref_type, ref_params, "SMC"),
    ]
    comp = ControllerComparison(name="pid_vs_smc_step", configs=configs)
    comp.run_and_save("../results")


def sine_comparison():
    """正弦参考下 PID vs SMC。"""
    ref_type, ref_params = "Sine", {"amplitude": 1.0, "frequency": 0.5}
    configs = [
        _make_pid_config(ref_type, ref_params, "PID"),
        _make_smc_config(ref_type, ref_params, "SMC"),
    ]
    comp = ControllerComparison(name="pid_vs_smc_sine", configs=configs)
    comp.run_and_save("../results")


def ramp_comparison():
    """斜坡参考下 PID vs SMC。"""
    ref_type, ref_params = "Ramp", {"slope": 0.5, "t_start": 0.0}
    configs = [
        _make_pid_config(ref_type, ref_params, "PID"),
        _make_smc_config(ref_type, ref_params, "SMC"),
    ]
    comp = ControllerComparison(name="pid_vs_smc_ramp", configs=configs)
    comp.run_and_save("../results")


if __name__ == "__main__":
    print("=== Step: PID vs SMC ===")
    step_comparison()
    print("\n=== Sine: PID vs SMC ===")
    sine_comparison()
    print("\n=== Ramp: PID vs SMC ===")
    ramp_comparison()
