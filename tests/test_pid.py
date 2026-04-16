"""PID 控制器单元测试。"""

import pytest

import sys
sys.path.insert(0, "..")

from msd import SimConfig, run_from_config, compute_metrics


def test_pid_step_tracking():
    """PID 阶跃跟踪：稳态误差 < 1%。"""
    config = SimConfig.from_yaml("configs/pid_step.yaml")
    result = run_from_config(config)
    result.metrics = compute_metrics(result)

    assert result.metrics["steady_state_error"] < 0.01


def test_pid_overshoot_bounded():
    """默认 PID 参数超调量 < 20%。"""
    config = SimConfig.from_yaml("configs/pid_step.yaml")
    result = run_from_config(config)
    result.metrics = compute_metrics(result)

    assert result.metrics["overshoot"] < 20.0


def test_pid_settling_time():
    """默认 PID 参数调节时间 < 5s。"""
    config = SimConfig.from_yaml("configs/pid_step.yaml")
    result = run_from_config(config)
    result.metrics = compute_metrics(result)

    assert result.metrics["settling_time"] < 5.0


def test_pid_extras_components():
    """PID 应输出 error, p_term, i_term, d_term 诊断信号。"""
    config = SimConfig.from_yaml("configs/pid_step.yaml")
    result = run_from_config(config)

    for key in ["error", "p_term", "i_term", "d_term"]:
        assert key in result.extras
        assert len(result.extras[key]) == len(result.time)
