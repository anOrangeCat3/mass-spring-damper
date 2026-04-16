"""开环阶跃输入控制器。"""

from .base import Controller


class StepInput(Controller):
    """开环阶跃输入：在 t >= t_step 时输出固定幅值。"""

    def __init__(self, amplitude: float = 1.0, t_step: float = 0.0):
        super().__init__()
        self.amplitude = amplitude
        self.t_step = t_step

    def compute(self, state, t, reference=0.0):
        return self.amplitude if t >= self.t_step else 0.0

    @property
    def name(self):
        return f"Step(A={self.amplitude})"
