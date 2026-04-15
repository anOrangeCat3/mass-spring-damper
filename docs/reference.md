# Reference 参考轨迹模块

## 接口设计

```python
class Reference(ABC):
    def __call__(self, t: float) -> float: ...
    def derivative(self, t: float) -> float: ...
    def reset(self): ...
    def name(self) -> str: ...
```

`__call__` 返回 t 时刻的目标位置，使 Reference 对象直接兼容 `Simulator.run()` 的 `reference_fn: Callable[[float], float]` 参数。

`derivative()` 返回目标位置的导数 ṙ(t)，默认返回 0。子类提供解析导数，用于：

- **PID 微分项**：误差导数 d(r-x)/dt = ṙ - ẋ，变化的参考需要 ṙ 才能正确计算
- **前馈控制**：已知 ṙ 可计算前馈力，改善动态跟踪
- **速度参考近似**：对于光滑轨迹，ṙ(t) 可作为目标速度

`reset()` 用于重置有状态的参考轨迹。当前所有实现均为无状态，此方法为空操作。

## 已实现的参考类型

### ConstantReference

$$r(t) = \text{value}$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `value` | float | 1.0 | 目标值 |

最简单的参考轨迹，目标恒定不变。derivative 恒为 0。

### StepReference

$$r(t) = \begin{cases} \text{value} & t \geq t_{\text{step}} \\ \text{initial} & t < t_{\text{step}} \end{cases}$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `value` | float | 1.0 | 阶跃后目标值 |
| `t_step` | float | 0.0 | 阶跃时刻 |
| `initial` | float | 0.0 | 阶跃前的值 |

与 ConstantReference 的区别：支持延迟阶跃和非零初始值。derivative 恒为 0（阶跃点的 Dirac delta 不建模）。

### RampReference

$$r(t) = \text{slope} \cdot \max(0,\, t - t_{\text{start}}) + \text{offset}$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `slope` | float | 1.0 | 斜率（单位/秒） |
| `t_start` | float | 0.0 | 斜坡起始时刻 |
| `offset` | float | 0.0 | 初始偏移量 |

线性增长的目标。derivative 在 t ≥ t_start 时为 slope，否则为 0。

用途：匀速位移跟踪、斜坡测试（评估稳态跟踪误差）。

### SineReference

$$r(t) = A \sin(2\pi f t + \varphi) + \text{offset}$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `amplitude` | float | 1.0 | 幅值 $A$ |
| `frequency` | float | 1.0 | 频率 $f$（Hz） |
| `phase` | float | 0.0 | 初始相位 $\varphi$（rad） |
| `offset` | float | 0.0 | 直流偏移量 |

解析导数：

$$\dot{r}(t) = A \cdot 2\pi f \cdot \cos(2\pi f t + \varphi)$$

用途：周期轨迹跟踪、频率响应分析。

## YAML 配置

### 无参考轨迹（默认）

不写 `reference_type`，或显式设为 `null`，仿真中参考值恒为 0：

```yaml
reference_type: null
```

### 配置示例

```yaml
reference_type: Constant
reference_params:
  value: 1.0
```

```yaml
reference_type: Step
reference_params:
  value: 2.0
  t_step: 1.0
  initial: 0.0
```

```yaml
reference_type: Ramp
reference_params:
  slope: 0.5
  t_start: 0.0
  offset: 0.0
```

```yaml
reference_type: Sine
reference_params:
  amplitude: 1.0
  frequency: 0.5
  phase: 0.0
  offset: 1.0
```

## 与控制器的关系

Simulator 每个控制周期调用 `reference(t)` 获取目标值，传给 `controller.compute(state, t, reference=r)`。

| 控制器类型 | 如何使用 Reference |
|---|---|
| PID | error = r - x，内部维护积分和微分 |
| LQR | 状态误差 [r - x, 0 - ẋ]，计算最优控制 |
| MPC | 直接查询 reference(t_future) 获取未来轨迹 |

对于需要 Reference 对象本身的高级控制器（如 MPC），可在构造时注入 Reference 对象。

## 扩展指南

新增参考类型只需两步：

1. 在 `msd/reference.py` 继承 `Reference`，实现 `__call__`、`derivative` 和 `name`
2. 在 `msd/config.py` 的 `REFERENCE_REGISTRY` 添加一行映射

### 可能的扩展方向

| 类型 | 说明 |
|---|---|
| `CompositeReference` | 多个参考轨迹叠加 |
| `PiecewiseReference` | 分段定义，不同时段不同轨迹 |
| `CsvReference` | 从文件加载目标轨迹数据 |
| `PolynomialReference` | 多项式轨迹（用于最小 jerk 规划） |

### 速度控制拓展路径

当前 `__call__` 返回标量（位置目标）。未来若需速度控制：

- **方案 A**：新增 `VelocityReference`，Controller 同时持有 position 和 velocity reference
- **方案 B**：`derivative()` 方法本身就是目标速度的解析来源，无需额外模块
