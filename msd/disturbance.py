"""扰动模块：定义外部扰动接口与实现。"""

from abc import ABC, abstractmethod
import numpy as np


class Disturbance(ABC):
    """扰动抽象基类。实现 __call__ 以兼容 Simulator 的 disturbance_fn 接口。"""

    @abstractmethod
    def __call__(self, t: float) -> float:
        """计算 t 时刻的扰动值。

        Args:
            t: 当前时间

        Returns:
            扰动力 d(t)
        """
        pass

    def reset(self):
        """重置内部状态（随机类扰动需要覆写此方法）。"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """扰动名称，用于标签和日志。"""
        pass


class SineDisturbance(Disturbance):
    """正弦扰动：d(t) = amplitude * sin(2π * frequency * t + phase)"""

    def __init__(
        self,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        phase: float = 0.0,
    ):
        """
        Args:
            amplitude: 幅值
            frequency: 频率 (Hz)
            phase: 初始相位 (rad)
        """
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase

    def __call__(self, t):
        return self.amplitude * np.sin(2 * np.pi * self.frequency * t + self.phase)

    @property
    def name(self):
        return f"Sine(A={self.amplitude}, f={self.frequency}Hz)"


class GaussianNoise(Disturbance):
    """高斯白噪声扰动：d(t) ~ N(mean, std²)"""

    def __init__(
        self,
        std: float = 1.0,
        mean: float = 0.0,
        seed: int | None = None,
    ):
        """
        Args:
            std: 标准差，控制噪声强度
            mean: 均值，通常为 0
            seed: 随机种子，None 则不固定
        """
        self.std = std
        self.mean = mean
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def __call__(self, t):
        return self._rng.normal(self.mean, self.std)

    def reset(self):
        """用相同 seed 重建随机数生成器，保证可复现。"""
        self._rng = np.random.default_rng(self.seed)

    @property
    def name(self):
        return f"GaussianNoise(σ={self.std})"


class CompositeDisturbance(Disturbance):
    """组合扰动：将多个扰动的输出相加。"""

    def __init__(self, disturbances: list[Disturbance]):
        """
        Args:
            disturbances: 子扰动列表
        """
        self.disturbances = disturbances

    def __call__(self, t):
        return sum(d(t) for d in self.disturbances)

    def reset(self):
        for d in self.disturbances:
            d.reset()

    @property
    def name(self):
        names = " + ".join(d.name for d in self.disturbances)
        return f"Composite({names})"
