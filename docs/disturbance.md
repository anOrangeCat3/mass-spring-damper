# Disturbance 扰动模块

## 接口设计

```python
class Disturbance(ABC):
    def __call__(self, t: float) -> float: ...
    def reset(self): ...
    def name(self) -> str: ...
```

关键决策：用 `__call__` 而非 `compute`。这使扰动对象本身成为 callable，直接兼容 `Simulator.run()` 的 `disturbance_fn: Callable[[float], float]` 参数，Simulator 代码无需修改。

`reset()` 用于重置随机类扰动的内部状态（重建 RNG）。确定性扰动（如 Sine）的 `reset()` 为空操作，不需要覆写。

## 已实现的扰动类型

### SineDisturbance

$$d(t) = A \sin(2\pi f t + \varphi)$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `amplitude` | float | 1.0 | 幅值 $A$ |
| `frequency` | float | 1.0 | 频率 $f$（Hz） |
| `phase` | float | 0.0 | 初始相位 $\varphi$（rad） |

用途：模拟周期性外力，如发动机振动、路面周期激励。

### GaussianNoise

$$d(t) \sim \mathcal{N}(\mu,\, \sigma^2)$$

| 参数 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `std` | float | 1.0 | 标准差 $\sigma$，控制噪声强度 |
| `mean` | float | 0.0 | 均值 $\mu$ |
| `seed` | int \| None | None | 随机种子，固定后仿真可复现 |

内部使用 `np.random.default_rng(seed)` 生成随机数。`reset()` 用相同 seed 重建 Generator，保证多次运行结果一致。

注意：该实现是**离散白噪声**——每个控制周期独立采样一次，噪声值在该周期内保持不变（与 Simulator 的 ZOH 策略一致）。噪声的功率谱密度与控制周期 `dt` 有关。

### CompositeDisturbance

$$d(t) = \sum_{i} d_i(t)$$

接受 `list[Disturbance]`，`__call__` 时对所有子扰动求和。`reset()` 会逐个调用子扰动的 `reset()`。

用途：组合多种扰动。例如"正弦 + 高斯噪声"模拟带随机抖动的周期激励。

## YAML 配置

### 无扰动（默认）

不写 `disturbance_type`，或显式设为 `null`：

```yaml
disturbance_type: null
```

### 单一扰动

```yaml
disturbance_type: Sine
disturbance_params:
  amplitude: 0.3
  frequency: 2.0
  phase: 0.0
```

```yaml
disturbance_type: GaussianNoise
disturbance_params:
  std: 0.2
  mean: 0.0
  seed: 42
```

### 组合扰动

```yaml
disturbance_type: Composite
disturbance_params:
  disturbances:
    - type: Sine
      params: {amplitude: 0.5, frequency: 1.0}
    - type: GaussianNoise
      params: {std: 0.1, seed: 42}
```

`build_disturbance()` 对 `Composite` 类型特殊处理：遍历 `disturbances` 列表，逐个从 `DISTURBANCE_REGISTRY` 查表构建，最后包装为 `CompositeDisturbance`。

## 扩展指南

新增扰动类型只需两步：

1. 在 `msd/disturbance.py` 继承 `Disturbance`，实现 `__call__` 和 `name`
2. 在 `msd/config.py` 的 `DISTURBANCE_REGISTRY` 添加一行映射

不需要修改 Simulator、Visualizer 或其他模块。

### 可能的扩展方向

| 类型 | 说明 |
|---|---|
| `StepDisturbance` | 阶跃扰动，模拟突加载荷 |
| `PulseDisturbance` | 脉冲扰动，仅在短时间窗口内施加 |
| `UniformNoise` | 均匀分布噪声 |
| `ChirpDisturbance` | 扫频正弦，频率随时间线性变化 |
| `CsvDisturbance` | 从文件加载实测扰动数据 |
| `WindowedDisturbance` | 通用包装器，限制扰动仅在 $[t_0, t_1]$ 内生效 |
