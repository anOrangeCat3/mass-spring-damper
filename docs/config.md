# Config 配置系统

## SimConfig

`@dataclass`，集中管理一次仿真的所有可调参数。支持三种创建方式：

```python
# 1. 直接构造
cfg = SimConfig(plant_params={"m": 2.0}, t_end=5.0)

# 2. 从字典构造（忽略未知字段）
cfg = SimConfig.from_dict({"plant_type": "MassSpringDamper", "unknown_key": 123})

# 3. 从 YAML 文件加载
cfg = SimConfig.from_yaml("configs/step_response.yaml")
```

### 字段一览

| 分组 | 字段 | 类型 | 默认值 |
|---|---|---|---|
| 初始条件 | `y0` | list | [0.0, 0.0] |
| 仿真参数 | `dt` | float | 0.01 |
| | `t_end` | float | 10.0 |
| | `method` | str | "RK45" |
| 物理模型 | `plant_type` | str | "MassSpringDamper" |
| | `plant_params` | dict | {m: 1.0, c: 0.5, k: 2.0} |
| 控制器 | `controller_type` | str | "StepInput" |
| | `controller_params` | dict | {amplitude: 1.0, t_step: 0.0} |
| 参考轨迹 | `reference_type` | str \| None | None |
| | `reference_params` | dict | {} |
| 扰动 | `disturbance_type` | str \| None | None |
| | `disturbance_params` | dict | {} |
| 标签 | `label` | str \| None | None（自动生成） |

## 类型注册表

字符串名 → 类的映射，将 YAML 中的类型名解析为实际的 Python 类：

```python
PLANT_REGISTRY = {"MassSpringDamper": MassSpringDamper}
CONTROLLER_REGISTRY = {"StepInput": StepInput, "PID": PIDController}
REFERENCE_REGISTRY = {"Constant": ConstantReference, "Step": StepReference, "Ramp": RampReference, "Sine": SineReference}
DISTURBANCE_REGISTRY = {"Sine": SineDisturbance, "GaussianNoise": GaussianNoise}
```

新增实现时只需在对应 registry 添加一行，`build_*()` 函数自动支持新类型。

### 工厂函数

| 函数 | 输入 | 输出 |
|---|---|---|
| `build_plant(config)` | SimConfig | Plant |
| `build_controller(config)` | SimConfig | Controller |
| `build_reference(config)` | SimConfig | Reference \| None |
| `build_disturbance(config)` | SimConfig | Disturbance \| None |

`build_controller` 的特殊处理：通过 `inspect.signature` 检测控制器构造函数，自动将 `SimConfig.dt` 注入给需要 `dt` 参数的控制器（如 PID），用户无需在 YAML 中重复填写。

`build_disturbance` 的特殊处理：`disturbance_type` 为 `None` 时返回 `None`（无扰动）；为 `"Composite"` 时递归构建子扰动列表。

## run_from_config()

一键运行的便捷函数，完整调用链：

```
SimConfig
  → build_plant()       → Plant
  → build_controller()  → Controller
  → build_reference()   → Reference | None
  → build_disturbance() → Disturbance | None
  → Simulator(plant, controller, dt)
  → Simulator.run(t_end, y0, reference_fn, disturbance_fn, method)
  → SimResult
```

运行完成后，将 `SimConfig.to_dict()` 的完整配置写入 `result.config`，确保保存的结果包含完整的复现信息。

## YAML 配置文件格式

推荐按以下顺序组织字段（与 `_build_save_config()` 的输出顺序一致）：

```yaml
# 初始条件
y0: [0.0, 0.0]

# 仿真参数
dt: 0.01
t_end: 10.0
method: RK45

# 物理模型
plant_type: MassSpringDamper
plant_params:
  m: 1.0
  c: 0.5
  k: 2.0

# 控制器
controller_type: StepInput
controller_params:
  amplitude: 1.0
  t_step: 0.0

# 参考轨迹（可选，不写则恒为 0）
reference_type: Step
reference_params:
  value: 1.0
  t_step: 0.0

# 扰动（可选，不写则无扰动）
disturbance_type: Sine
disturbance_params:
  amplitude: 0.3
  frequency: 2.0

# 标签（可选）
label: "my simulation"
```

`from_dict()` 会自动忽略未知字段，因此 YAML 中可以添加注释性字段而不影响解析。

## SimResult 保存

`SimResult.save()` 将配置和数据分别保存为 `config.yaml` 和 `data.npz`。

`config.yaml` 使用 `sort_keys=False` 确保字段按逻辑分组输出，而非按字母排序。`_build_save_config()` 控制输出字段和顺序，扰动配置仅在 `disturbance_type` 不为 `None` 时才包含 `disturbance_params`。
