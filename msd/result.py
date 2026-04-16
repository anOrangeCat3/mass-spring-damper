"""仿真结果数据类，含保存与加载功能。"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import numpy as np


@dataclass
class SimResult:
    """单次仿真的标准化输出。

    Attributes:
        config: 仿真配置信息（plant参数、控制器、仿真参数等）
        time: 时间序列, shape (n,)
        states: 状态矩阵, shape (n, n_states)
        control: 控制力序列, shape (n,)
        reference: 参考轨迹序列, shape (n,)
        disturbance: 扰动序列, shape (n,)
        extras: 控制器诊断信号, {"signal_name": shape (n,) array}
        metrics: 性能指标字典
    """
    config: dict
    time: np.ndarray
    states: np.ndarray
    control: np.ndarray
    reference: np.ndarray
    disturbance: np.ndarray
    extras: dict[str, np.ndarray] = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)

    @property
    def position(self):
        return self.states[:, 0]

    @property
    def velocity(self):
        return self.states[:, 1]

    @property
    def label(self) -> str:
        """自动生成图例标签。"""
        return self.config.get("label", "unnamed")

    def save(self, base_dir: str = "results") -> Path:
        """保存仿真结果到带时间戳的目录。

        目录结构：
            base_dir/YYYYMMDD_HHMMSS/
            ├── config.yaml    仿真配置
            └── data.npz       仿真数据（time, states, control, reference, disturbance）

        Args:
            base_dir: 结果根目录

        Returns:
            本次保存的目录路径，便于后续保存图片
        """
        import yaml

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = Path(base_dir) / timestamp
        result_dir.mkdir(parents=True, exist_ok=True)

        # 保存配置 (YAML, 保持字段顺序)
        config_to_save = self._build_save_config()
        with open(result_dir / "config.yaml", "w") as f:
            yaml.dump(
                config_to_save, f,
                default_flow_style=False, allow_unicode=True, sort_keys=False,
            )

        # 保存数据 (npz)，extras 以 extra_ 前缀存储
        extra_arrays = {f"extra_{k}": v for k, v in self.extras.items()}
        np.savez(
            result_dir / "data.npz",
            time=self.time,
            states=self.states,
            control=self.control,
            reference=self.reference,
            disturbance=self.disturbance,
            **extra_arrays,
        )

        print(f"Results saved to {result_dir}")
        return result_dir

    def _build_save_config(self) -> dict:
        """构建保存用的配置字典，区分有值和无值的字段。"""
        cfg = {}

        # 初始条件
        cfg["y0"] = self.config.get("y0", [])

        # 物理模型
        cfg["plant_type"] = self.config.get("plant_type", "")
        cfg["plant_params"] = self.config.get("plant_params", {})

        # 控制器（开环标记为 open_loop）
        ctrl_type = self.config.get("controller_type", "")
        cfg["controller_type"] = ctrl_type if ctrl_type else "open_loop"
        cfg["controller_params"] = self.config.get("controller_params", {})

        # 参考轨迹（None 表示无参考轨迹）
        ref_type = self.config.get("reference_type", None)
        cfg["reference_type"] = ref_type
        if ref_type:
            cfg["reference_params"] = self.config.get("reference_params", {})

        # 扰动（None 表示无扰动）
        dist_type = self.config.get("disturbance_type", None)
        cfg["disturbance_type"] = dist_type
        if dist_type:
            cfg["disturbance_params"] = self.config.get("disturbance_params", {})

        # 仿真参数
        cfg["dt"] = self.config.get("dt", 0.01)
        cfg["t_end"] = self.config.get("t_end", 10.0)
        cfg["method"] = self.config.get("method", "RK45")

        # 标签
        cfg["label"] = self.label

        return cfg

    @staticmethod
    def load(result_dir: str) -> "SimResult":
        """从保存目录加载仿真结果。

        Args:
            result_dir: 结果目录路径

        Returns:
            SimResult 对象
        """
        import yaml

        result_dir = Path(result_dir)

        with open(result_dir / "config.yaml") as f:
            config = yaml.safe_load(f)

        data = np.load(result_dir / "data.npz")

        # 还原 extras：提取 extra_ 前缀的数组
        extras = {k[6:]: data[k] for k in data.files if k.startswith("extra_")}

        return SimResult(
            config=config,
            time=data["time"],
            states=data["states"],
            control=data["control"],
            reference=data["reference"],
            disturbance=data["disturbance"],
            extras=extras,
        )
