"""Plant 模块单元测试。"""

import numpy as np
import pytest

import sys
sys.path.insert(0, "..")

from msd import MassSpringDamper


def test_derivatives_at_rest():
    """静止状态无外力时导数为零。"""
    plant = MassSpringDamper(m=1.0, c=0.5, k=2.0)
    dy = plant.derivatives(0, np.array([0.0, 0.0]), u=0.0, d=0.0)
    np.testing.assert_array_almost_equal(dy, [0.0, 0.0])


def test_derivatives_with_force():
    """施加单位力时加速度 = F/m。"""
    plant = MassSpringDamper(m=2.0, c=0.0, k=0.0)
    dy = plant.derivatives(0, np.array([0.0, 0.0]), u=1.0, d=0.0)
    assert dy[0] == 0.0
    assert dy[1] == pytest.approx(0.5)


def test_natural_frequency():
    """固有频率 ωn = sqrt(k/m)。"""
    plant = MassSpringDamper(m=1.0, c=0.0, k=4.0)
    assert plant.natural_frequency == pytest.approx(2.0)


def test_damping_ratio():
    """阻尼比 ζ = c / (2*sqrt(m*k))。"""
    plant = MassSpringDamper(m=1.0, c=2.0, k=4.0)
    assert plant.damping_ratio == pytest.approx(0.5)


def test_state_names():
    plant = MassSpringDamper()
    assert plant.state_names == ["position", "velocity"]
