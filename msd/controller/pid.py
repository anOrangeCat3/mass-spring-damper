"""PID 控制器。"""

import numpy as np
from .base import Controller


class PIDController(Controller):
    """位置式 PID 控制器。

    Args:
        kp: 比例增益
        ki: 积分增益
        kd: 微分增益
        dt: 控制周期 (s)，由 build_controller 自动注入
        state_index: 跟踪的状态量索引（0=位移, 1=速度），用于级联控制
        derivative_on_measurement: True 则微分作用于测量值（避免阶跃微分冲击），
                                   False 则作用于误差
        u_min: 控制输出下限（可选扩展，默认无限幅）
        u_max: 控制输出上限（可选扩展，默认无限幅）

    Returns:
        compute() 返回控制力 u (float)
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        dt: float = 0.01,
        state_index: int = 0,
        derivative_on_measurement: bool = True,
        u_min: float = -np.inf,
        u_max: float = np.inf,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.state_index = state_index
        self.derivative_on_measurement = derivative_on_measurement
        self.u_min = u_min
        self.u_max = u_max
        self._saturated = not (np.isinf(u_min) and np.isinf(u_max))

        self._integral = 0.0
        self._prev_error = None
        self._prev_measurement = None

    def compute(self, state, t, reference=0.0):
        """计算 PID 控制输出。"""
        measurement = state[self.state_index]
        error = reference - measurement

        # 比例项
        p_term = self.kp * error

        # 积分项（梯形积分 + clamping 抗饱和）
        self._integral += error * self.dt
        i_term = self.ki * self._integral

        # 微分项
        if self.derivative_on_measurement:
            if self._prev_measurement is None:
                d_term = 0.0
            else:
                d_term = -self.kd * (measurement - self._prev_measurement) / self.dt
        else:
            if self._prev_error is None:
                d_term = 0.0
            else:
                d_term = self.kd * (error - self._prev_error) / self.dt

        u = p_term + i_term + d_term

        # 可选输出限幅 + clamping 积分抗饱和
        if self._saturated:
            u_clipped = float(np.clip(u, self.u_min, self.u_max))
            if u_clipped != u:
                self._integral -= error * self.dt
            u = u_clipped

        # 更新历史值
        self._prev_error = error
        self._prev_measurement = measurement

        return float(u)

    def reset(self):
        """重置积分项和历史值。"""
        self._integral = 0.0
        self._prev_error = None
        self._prev_measurement = None

    @property
    def name(self):
        return f"PID(Kp={self.kp}, Ki={self.ki}, Kd={self.kd})"
