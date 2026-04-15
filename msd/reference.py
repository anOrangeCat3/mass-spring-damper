"""参考轨迹模块：定义控制目标接口与实现。"""

from abc import ABC, abstractmethod
import numpy as np


class Reference(ABC):
    """参考轨迹抽象基类。实现 __call__ 以兼容 Simulator 的 reference_fn 接口。"""

    @abstractmethod
    def __call__(self, t: float) -> float:
        """返回 t 时刻的参考值（目标位置）。

        Args:
            t: 当前时间

        Returns:
            参考值 r(t)
        """
        pass

    def derivative(self, t: float) -> float:
        """返回 t 时刻参考值的导数 ṙ(t)，用于前馈或误差微分。

        默认返回 0。子类可覆写提供解析导数，避免数值微分噪声。

        Args:
            t: 当前时间

        Returns:
            参考值导数 ṙ(t)
        """
        return 0.0

    def reset(self):
        """重置内部状态（有状态的参考轨迹需要覆写）。"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """名称，用于标签和日志。"""
        pass


class ConstantReference(Reference):
    """恒定参考值：r(t) = value"""

    def __init__(self, value: float = 1.0):
        """
        Args:
            value: 目标值
        """
        self.value = value

    def __call__(self, t):
        return self.value

    @property
    def name(self):
        return f"Constant({self.value})"


class StepReference(Reference):
    """阶跃参考：t >= t_step 时输出 value，否则输出 initial。"""

    def __init__(
        self,
        value: float = 1.0,
        t_step: float = 0.0,
        initial: float = 0.0,
    ):
        """
        Args:
            value: 阶跃后的目标值
            t_step: 阶跃时刻
            initial: 阶跃前的值
        """
        self.value = value
        self.t_step = t_step
        self.initial = initial

    def __call__(self, t):
        return self.value if t >= self.t_step else self.initial

    @property
    def name(self):
        return f"Step({self.value}, t={self.t_step})"


class RampReference(Reference):
    """斜坡参考：r(t) = slope * max(0, t - t_start) + offset"""

    def __init__(
        self,
        slope: float = 1.0,
        t_start: float = 0.0,
        offset: float = 0.0,
    ):
        """
        Args:
            slope: 斜率 (单位/秒)
            t_start: 斜坡起始时刻
            offset: 初始偏移量
        """
        self.slope = slope
        self.t_start = t_start
        self.offset = offset

    def __call__(self, t):
        return self.slope * max(0.0, t - self.t_start) + self.offset

    def derivative(self, t):
        return self.slope if t >= self.t_start else 0.0

    @property
    def name(self):
        return f"Ramp(slope={self.slope})"


class SineReference(Reference):
    """正弦参考：r(t) = amplitude * sin(2π * frequency * t + phase) + offset"""

    def __init__(
        self,
        amplitude: float = 1.0,
        frequency: float = 1.0,
        phase: float = 0.0,
        offset: float = 0.0,
    ):
        """
        Args:
            amplitude: 幅值
            frequency: 频率 (Hz)
            phase: 初始相位 (rad)
            offset: 直流偏移量
        """
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase = phase
        self.offset = offset

    def __call__(self, t):
        return self.amplitude * np.sin(
            2 * np.pi * self.frequency * t + self.phase
        ) + self.offset

    def derivative(self, t):
        omega = 2 * np.pi * self.frequency
        return self.amplitude * omega * np.cos(omega * t + self.phase)

    @property
    def name(self):
        return f"Sine(A={self.amplitude}, f={self.frequency}Hz)"
