"""PID 调参实验：Kp / Ki / Kd 参数扫描。"""

import sys
sys.path.insert(0, "..")

from msd import SimConfig, ParameterSweep


def kp_sweep():
    """Kp 参数扫描，固定 Ki=5, Kd=4。"""
    base = SimConfig.from_yaml("../tests/configs/pid_step.yaml")
    sweep = ParameterSweep(
        name="pid_kp_sweep",
        base_config=base,
        param_path="controller_params.kp",
        values=[2, 5, 10, 20, 50],
        labels=[f"Kp={v}" for v in [2, 5, 10, 20, 50]],
    )
    sweep.run_and_save("../results")


def ki_sweep():
    """Ki 参数扫描，固定 Kp=10, Kd=4。"""
    base = SimConfig.from_yaml("../tests/configs/pid_step.yaml")
    sweep = ParameterSweep(
        name="pid_ki_sweep",
        base_config=base,
        param_path="controller_params.ki",
        values=[0, 1, 5, 10, 20],
        labels=[f"Ki={v}" for v in [0, 1, 5, 10, 20]],
    )
    sweep.run_and_save("../results")


def kd_sweep():
    """Kd 参数扫描，固定 Kp=10, Ki=5。"""
    base = SimConfig.from_yaml("../tests/configs/pid_step.yaml")
    sweep = ParameterSweep(
        name="pid_kd_sweep",
        base_config=base,
        param_path="controller_params.kd",
        values=[0, 1, 4, 8, 16],
        labels=[f"Kd={v}" for v in [0, 1, 4, 8, 16]],
    )
    sweep.run_and_save("../results")


if __name__ == "__main__":
    print("=== Kp Sweep ===")
    kp_sweep()
    print("\n=== Ki Sweep ===")
    ki_sweep()
    print("\n=== Kd Sweep ===")
    kd_sweep()
