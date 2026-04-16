"""滑模控制器（SMC）。"""

import numpy as np
from .base import Controller


class SMCController(Controller):
    """滑模控制器，基于线性滑模面 s = ė + λe。

    默认使用经典 sign(s) 切换函数。可选抖振抑制和输出限幅作为扩展。

    系统模型：m·x'' + c·x' + k·x = u + d
    滑模面：  s = (ẋ_ref - v) + λ·(x_ref - x)
    控制律：  u = u_eq + u_sw
      u_eq = k·x + (c - m·λ)·v + m·λ·ẋ_ref    等效控制
      u_sw = m·η·switching(s)                    切换控制

    Args:
        m: 质量（需与 plant_params 一致）
        c: 阻尼系数
        k: 弹簧刚度
        lambda_: 滑模面斜率 (> 0)，决定到达滑模面后误差的收敛速度
        eta: 趋近增益 (> 0)，需大于扰动上界以保证可达性
        dt: 控制周期，由 build_controller 自动注入
        smoothing: 切换函数类型。None=sign（经典），"sat"=饱和函数，"tanh"=双曲正切
        phi: 边界层厚度，仅 smoothing 非 None 时有效 (> 0)
        u_min: 控制输出下限（可选扩展，默认无限幅）
        u_max: 控制输出上限（可选扩展，默认无限幅）
        estimate_reference_derivative: 是否用差分估计参考轨迹导数，
                                       False 则假设 ẋ_ref=0（适用于阶跃/恒值参考）

    Returns:
        compute() 返回控制力 u (float)
    """

    def __init__(
        self,
        m: float = 1.0,
        c: float = 0.5,
        k: float = 2.0,
        lambda_: float = 5.0,
        eta: float = 1.0,
        dt: float = 0.01,
        smoothing: str | None = None,
        phi: float = 0.1,
        u_min: float = -np.inf,
        u_max: float = np.inf,
        estimate_reference_derivative: bool = False,
    ):
        self.m = m
        self.c = c
        self.k = k
        self.lambda_ = lambda_
        self.eta = eta
        self.dt = dt
        self.smoothing = smoothing
        self.phi = phi
        self.u_min = u_min
        self.u_max = u_max
        self.estimate_reference_derivative = estimate_reference_derivative

        self._prev_reference = None

    def _switching(self, s: float) -> float:
        """切换函数：根据 smoothing 参数选择 sign / sat / tanh。

        Args:
            s: 滑模面值

        Returns:
            切换函数输出，范围 [-1, 1]
        """
        if self.smoothing is None:
            return float(np.sign(s))
        elif self.smoothing == "sat":
            return float(np.clip(s / self.phi, -1.0, 1.0))
        elif self.smoothing == "tanh":
            return float(np.tanh(s / self.phi))
        else:
            raise ValueError(f"未知的 smoothing 类型: {self.smoothing}，"
                             f"可选: None, 'sat', 'tanh'")

    def compute(self, state, t, reference=0.0):
        """计算 SMC 控制输出。"""
        x, v = state[0], state[1]

        # 参考轨迹导数估计
        if self.estimate_reference_derivative and self._prev_reference is not None:
            ref_dot = (reference - self._prev_reference) / self.dt
        else:
            ref_dot = 0.0

        # 误差与滑模面
        e = reference - x
        s = (ref_dot - v) + self.lambda_ * e

        # 等效控制（基于系统模型的前馈补偿）
        u_eq = self.k * x + (self.c - self.m * self.lambda_) * v \
            + self.m * self.lambda_ * ref_dot

        # 切换控制（驱动系统到达并保持在滑模面上）
        u_sw = self.m * self.eta * self._switching(s)

        u = u_eq + u_sw

        # 可选输出限幅
        u = float(np.clip(u, self.u_min, self.u_max))

        self._prev_reference = reference
        return u

    def reset(self):
        """重置内部状态。"""
        self._prev_reference = None

    @property
    def name(self):
        smoothing_tag = self.smoothing or "sign"
        label = f"SMC(λ={self.lambda_}, η={self.eta}, {smoothing_tag})"
        if self.smoothing:
            label = f"SMC(λ={self.lambda_}, η={self.eta}, {smoothing_tag}, φ={self.phi})"
        return label
