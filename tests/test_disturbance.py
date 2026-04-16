"""扰动模块单元测试。"""

import pytest
import numpy as np

import sys
sys.path.insert(0, "..")

from msd import SineDisturbance, GaussianNoise, CompositeDisturbance
from msd import SimConfig, run_from_config


def test_sine_disturbance_amplitude():
    """正弦扰动幅值正确。"""
    d = SineDisturbance(amplitude=2.0, frequency=1.0)
    vals = [d(t) for t in np.linspace(0, 10, 1000)]
    assert max(vals) == pytest.approx(2.0, abs=0.05)
    assert min(vals) == pytest.approx(-2.0, abs=0.05)


def test_gaussian_noise_statistics():
    """高斯噪声均值和标准差近似正确。"""
    d = GaussianNoise(std=0.5, seed=42)
    vals = np.array([d(t) for t in range(10000)])
    assert abs(np.mean(vals)) < 0.05
    assert np.std(vals) == pytest.approx(0.5, abs=0.05)


def test_composite_disturbance():
    """组合扰动 = 各子扰动之和。"""
    d1 = SineDisturbance(amplitude=1.0, frequency=1.0)
    d2 = SineDisturbance(amplitude=0.5, frequency=2.0)
    comp = CompositeDisturbance([d1, d2])

    for t in [0.0, 0.5, 1.0]:
        assert comp(t) == pytest.approx(d1(t) + d2(t))


def test_disturbance_affects_response():
    """有扰动的响应应与无扰动不同。"""
    cfg_clean = SimConfig.from_yaml("configs/step_response.yaml")
    cfg_noisy = SimConfig.from_yaml("configs/step_with_disturbance.yaml")

    result_clean = run_from_config(cfg_clean)
    result_noisy = run_from_config(cfg_noisy)

    diff = np.max(np.abs(result_clean.position - result_noisy.position))
    assert diff > 0.01
