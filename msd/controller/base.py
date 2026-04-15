"""控制器抽象基类。"""

from abc import ABC, abstractmethod
import numpy as np


class Controller(ABC):
    """控制器抽象基类。所有控制算法继承此类。"""

    @abstractmethod
    def compute(self, state: np.ndarray, t: float, reference: float = 0.0) -> float:
        """根据当前状态和参考值计算控制输入。

        Args:
            state: 当前状态向量 [位移, 速度, ...]
            t: 当前时间
            reference: 参考值（目标位置或目标速度，取决于控制器配置）

        Returns:
            控制输入 u
        """
        pass

    def reset(self):
        """重置控制器内部状态（积分项、历史值等）。

        无状态控制器无需覆写。有状态控制器（如 PID）必须覆写。
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """控制器名称，用于图例标签。"""
        pass
