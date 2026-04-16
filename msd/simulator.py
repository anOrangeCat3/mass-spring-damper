"""仿真器模块：组合各模块执行仿真主循环。"""

from typing import Callable, Optional
import numpy as np
from scipy.integrate import solve_ivp

from .plant import Plant
from .controller import Controller
from .result import SimResult


class Simulator:
    """仿真器：分段积分 + 零阶保持。

    每个控制周期调用一次 solve_ivp，控制输入在周期内保持不变，
    真实反映数字控制器的离散采样行为。
    """

    def __init__(self, plant: Plant, controller: Controller, dt: float = 0.001):
        """
        Args:
            plant: 物理模型
            controller: 控制器
            dt: 控制周期（秒）
        """
        self.plant = plant
        self.controller = controller
        self.dt = dt

    def run(
        self,
        t_end: float,
        y0: list[float],
        reference_fn: Optional[Callable[[float], float]] = None,
        disturbance_fn: Optional[Callable[[float], float]] = None,
        method: str = "RK45",
    ) -> SimResult:
        """执行仿真。

        Args:
            t_end: 仿真结束时间
            y0: 初始状态
            reference_fn: 参考轨迹函数 ref(t) -> float，默认恒为 0
            disturbance_fn: 扰动函数 d(t) -> float，默认恒为 0
            method: solve_ivp 积分方法

        Returns:
            SimResult 对象
        """
        ref_fn = reference_fn or (lambda t: 0.0)
        dist_fn = disturbance_fn or (lambda t: 0.0)

        t = 0.0
        y = np.array(y0, dtype=float)
        n_steps = int(np.ceil(t_end / self.dt))

        # 预分配数组
        time_log = np.zeros(n_steps)
        state_log = np.zeros((n_steps, len(y0)))
        control_log = np.zeros(n_steps)
        reference_log = np.zeros(n_steps)
        disturbance_log = np.zeros(n_steps)
        extras_log: dict[str, list[float]] = {}

        for i in range(n_steps):
            ref = ref_fn(t)
            d = dist_fn(t)
            u = self.controller.compute(y, t, reference=ref)

            # 采集控制器诊断信号
            for key, val in self.controller.extras.items():
                if key not in extras_log:
                    extras_log[key] = [0.0] * i
                extras_log[key].append(val)

            # 记录当前步数据
            time_log[i] = t
            state_log[i] = y
            control_log[i] = u
            reference_log[i] = ref
            disturbance_log[i] = d

            # 分段积分：控制输入在本周期内保持不变
            dt_actual = min(self.dt, t_end - t)
            sol = solve_ivp(
                lambda t_, y_: self.plant.derivatives(t_, y_, u, d),
                (t, t + dt_actual),
                y,
                method=method,
            )
            y = sol.y[:, -1]
            t += dt_actual

        # 转换 extras 为 numpy 数组
        extras = {k: np.array(v) for k, v in extras_log.items()}

        config = {
            "plant": repr(self.plant),
            "controller": self.controller.name,
            "dt": self.dt,
            "t_end": t_end,
            "y0": list(y0),
            "method": method,
            "label": self.controller.name,
        }

        return SimResult(
            config=config,
            time=time_log,
            states=state_log,
            control=control_log,
            reference=reference_log,
            disturbance=disturbance_log,
            extras=extras,
        )
