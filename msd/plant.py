"""物理模型模块：定义系统动力学方程。"""

from abc import ABC, abstractmethod
import numpy as np


class Plant(ABC):
    """物理模型抽象基类。"""

    @abstractmethod
    def derivatives(self, t: float, state: np.ndarray, u: float, d: float) -> np.ndarray:
        """计算状态导数 dy/dt。

        Args:
            t: 当前时间
            state: 状态向量
            u: 控制输入
            d: 外部扰动

        Returns:
            状态导数向量
        """
        pass

    @property
    @abstractmethod
    def state_names(self) -> list[str]:
        """状态量名称列表。"""
        pass


class MassSpringDamper(Plant):
    """质量-弹簧-阻尼器模型：m*x'' + c*x' + k*x = u + d"""

    def __init__(self, m: float = 1.0, c: float = 0.5, k: float = 2.0):
        self.m = m
        self.c = c
        self.k = k

    def derivatives(self, t, state, u, d):
        x, v = state
        dxdt = v
        dvdt = (u + d - self.c * v - self.k * x) / self.m
        return np.array([dxdt, dvdt])

    @property
    def state_names(self):
        return ["position", "velocity"]

    @property
    def natural_frequency(self):
        """固有频率 ωn = sqrt(k/m)"""
        return np.sqrt(self.k / self.m)

    @property
    def damping_ratio(self):
        """阻尼比 ζ = c / (2*sqrt(m*k))"""
        return self.c / (2 * np.sqrt(self.m * self.k))

    def __repr__(self):
        return f"MassSpringDamper(m={self.m}, c={self.c}, k={self.k})"
