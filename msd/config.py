"""配置模块：集中管理所有可调参数，支持 YAML 加载和类型注册。"""

import inspect
from dataclasses import dataclass, field, asdict
from typing import Optional

from .plant import Plant, MassSpringDamper
from .controller import Controller, StepInput, PIDController
from .reference import Reference, ConstantReference, StepReference, RampReference, SineReference
from .disturbance import Disturbance, SineDisturbance, GaussianNoise, CompositeDisturbance
from .result import SimResult


@dataclass
class SimConfig:
    """仿真配置。所有可调参数集中管理，支持 YAML 文件加载。

    Attributes:
        y0: 初始状态 [位移, 速度]
        dt: 控制周期 (s)
        t_end: 仿真时长 (s)
        method: solve_ivp 积分方法
        plant_type: 物理模型类型名
        plant_params: 物理模型参数
        controller_type: 控制器类型名
        controller_params: 控制器参数
        label: 图例标签，None 则自动生成
    """

    # 初始条件
    y0: list = field(default_factory=lambda: [0.0, 0.0])

    # 仿真参数
    dt: float = 0.01
    t_end: float = 10.0
    method: str = "RK45"

    # 物理模型
    plant_type: str = "MassSpringDamper"
    plant_params: dict = field(default_factory=lambda: {"m": 1.0, "c": 0.5, "k": 2.0})

    # 控制器
    controller_type: str = "StepInput"
    controller_params: dict = field(
        default_factory=lambda: {"amplitude": 1.0, "t_step": 0.0}
    )

    # 参考轨迹（None 表示恒为 0）
    reference_type: Optional[str] = None
    reference_params: dict = field(default_factory=dict)

    # 扰动（None 表示无扰动）
    disturbance_type: Optional[str] = None
    disturbance_params: dict = field(default_factory=dict)

    # 图例标签
    label: Optional[str] = None

    @classmethod
    def from_yaml(cls, path: str) -> "SimConfig":
        """从 YAML 文件加载配置。"""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "SimConfig":
        """从字典创建配置，忽略未知字段。"""
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def to_dict(self) -> dict:
        """导出为字典。"""
        return asdict(self)


# ============================================================
# 类型注册表
# 新增 Plant / Controller 时，在对应字典中添加一行即可
# ============================================================

PLANT_REGISTRY: dict[str, type[Plant]] = {
    "MassSpringDamper": MassSpringDamper,
}

CONTROLLER_REGISTRY: dict[str, type[Controller]] = {
    "StepInput": StepInput,
    "PID": PIDController,
}

REFERENCE_REGISTRY: dict[str, type[Reference]] = {
    "Constant": ConstantReference,
    "Step": StepReference,
    "Ramp": RampReference,
    "Sine": SineReference,
}

DISTURBANCE_REGISTRY: dict[str, type[Disturbance]] = {
    "Sine": SineDisturbance,
    "GaussianNoise": GaussianNoise,
}


def build_plant(config: SimConfig) -> Plant:
    """根据配置创建 Plant 实例。"""
    cls = PLANT_REGISTRY[config.plant_type]
    return cls(**config.plant_params)


def build_controller(config: SimConfig) -> Controller:
    """根据配置创建 Controller 实例。自动注入 dt 给需要的控制器。"""
    cls = CONTROLLER_REGISTRY[config.controller_type]
    params = dict(config.controller_params)
    # 闭环控制器需要 dt，自动从仿真配置注入，避免用户重复填写
    sig = inspect.signature(cls.__init__)
    if "dt" in sig.parameters and "dt" not in params:
        params["dt"] = config.dt
    return cls(**params)


def build_reference(config: SimConfig) -> Reference | None:
    """根据配置创建 Reference 实例，None 表示无参考轨迹（恒为 0）。"""
    if config.reference_type is None:
        return None
    cls = REFERENCE_REGISTRY[config.reference_type]
    return cls(**config.reference_params)


def build_disturbance(config: SimConfig) -> Disturbance | None:
    """根据配置创建 Disturbance 实例，None 表示无扰动。

    支持两种格式：
      - 简单扰动：disturbance_type 为注册表中的类型名
      - 组合扰动：disturbance_type 为 "Composite"，
        disturbance_params.disturbances 为子扰动列表
    """
    if config.disturbance_type is None:
        return None

    if config.disturbance_type == "Composite":
        sub_configs = config.disturbance_params.get("disturbances", [])
        subs = []
        for item in sub_configs:
            cls = DISTURBANCE_REGISTRY[item["type"]]
            subs.append(cls(**item.get("params", {})))
        return CompositeDisturbance(subs)

    cls = DISTURBANCE_REGISTRY[config.disturbance_type]
    return cls(**config.disturbance_params)


def run_from_config(config: SimConfig) -> SimResult:
    """从配置一键运行仿真，返回 SimResult。"""
    from .simulator import Simulator

    plant = build_plant(config)
    controller = build_controller(config)
    reference = build_reference(config)
    disturbance = build_disturbance(config)
    sim = Simulator(plant, controller, dt=config.dt)
    result = sim.run(
        t_end=config.t_end,
        y0=config.y0,
        reference_fn=reference,
        disturbance_fn=disturbance,
        method=config.method,
    )

    # 用完整的 SimConfig 覆盖 result.config，便于保存和复现
    full_config = config.to_dict()
    full_config["label"] = config.label or controller.name
    result.config = full_config

    return result
