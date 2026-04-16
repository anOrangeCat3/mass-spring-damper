"""Simulator 模块单元测试。"""

import numpy as np
import pytest

import sys
sys.path.insert(0, "..")

from msd import MassSpringDamper, StepInput, Simulator


def test_simulation_runs():
    """仿真能正常执行并返回正确长度的数据。"""
    plant = MassSpringDamper()
    ctrl = StepInput(amplitude=1.0)
    sim = Simulator(plant, ctrl, dt=0.01)
    result = sim.run(t_end=1.0, y0=[0.0, 0.0])

    assert len(result.time) == 100
    assert result.states.shape == (100, 2)
    assert len(result.control) == 100


def test_step_response_converges():
    """阶跃输入后系统最终应收敛到稳态值 F/k。"""
    plant = MassSpringDamper(m=1.0, c=0.5, k=2.0)
    ctrl = StepInput(amplitude=1.0)
    sim = Simulator(plant, ctrl, dt=0.01)
    result = sim.run(t_end=20.0, y0=[0.0, 0.0])

    expected_ss = 1.0 / 2.0
    assert result.position[-1] == pytest.approx(expected_ss, abs=0.01)


def test_extras_populated():
    """使用 PID 时 extras 应包含诊断信号。"""
    from msd import PIDController
    plant = MassSpringDamper()
    ctrl = PIDController(kp=10, ki=5, kd=4, dt=0.01)
    sim = Simulator(plant, ctrl, dt=0.01)
    result = sim.run(t_end=1.0, y0=[0.0, 0.0],
                     reference_fn=lambda t: 1.0)

    assert "error" in result.extras
    assert "p_term" in result.extras
    assert len(result.extras["error"]) == len(result.time)
