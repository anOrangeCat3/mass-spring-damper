"""SMC 控制器单元测试。"""

from pathlib import Path

import numpy as np

from msd import SimConfig, run_from_config
from msd.metrics import compute_metrics

CONFIGS_DIR = Path(__file__).parent / "configs"


def test_smc_step_tracking():
    """SMC 阶跃跟踪：稳态误差 < 1%。"""
    config = SimConfig.from_yaml(str(CONFIGS_DIR / "smc_step.yaml"))
    result = run_from_config(config)
    result.metrics = compute_metrics(result)

    assert result.metrics["steady_state_error"] < 0.01


def test_smc_no_overshoot():
    """默认 SMC 参数应无超调（sign 切换函数）。"""
    config = SimConfig.from_yaml(str(CONFIGS_DIR / "smc_step.yaml"))
    result = run_from_config(config)
    result.metrics = compute_metrics(result)

    assert result.metrics["overshoot"] < 1.0


def test_smc_extras_sliding_surface():
    """SMC 应输出滑模面 s(t) 诊断信号。"""
    config = SimConfig.from_yaml(str(CONFIGS_DIR / "smc_step.yaml"))
    result = run_from_config(config)

    assert "s" in result.extras
    assert "u_eq" in result.extras
    assert "u_sw" in result.extras
    assert len(result.extras["s"]) == len(result.time)


def test_smc_sliding_surface_converges():
    """滑模面 s(t) 应收敛到 0 附近。"""
    config = SimConfig.from_yaml(str(CONFIGS_DIR / "smc_step.yaml"))
    result = run_from_config(config)

    s_tail = result.extras["s"][-100:]
    assert np.max(np.abs(s_tail)) < 0.1


def test_smc_smoothing_sat():
    """sat 平滑切换函数应减少控制力抖振。"""
    base = SimConfig.from_yaml(str(CONFIGS_DIR / "smc_step.yaml"))

    result_sign = run_from_config(base)

    params = dict(base.controller_params)
    params["smoothing"] = "sat"
    params["phi"] = 0.5
    cfg_sat = SimConfig.from_dict({**base.to_dict(), "controller_params": params})
    result_sat = run_from_config(cfg_sat)

    std_sign = np.std(np.diff(result_sign.control))
    std_sat = np.std(np.diff(result_sat.control))
    assert std_sat < std_sign
