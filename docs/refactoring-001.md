# Refactoring #001：实验框架与代码重构

> 日期：2026-04-16
> 状态：设计中
> 目标：建立实验基础设施，分离测试与实验，支持参数扫描、控制器对比、定量分析

---

## 1. 现状问题

### 1.1 `tests/` 职责混乱

当前 `tests/` 中的脚本（`test_pid.py`、`test_smc.py` 等）既不是 pytest 单元测试，也不是正式实验。`test_kp_sweep()` 本质上是参数扫描实验，但放在 test 目录里、用 test 命名，且依赖 `sys.path.insert(0, "..")` 才能运行。

三个角色混在一起：

- **单元测试**（验证代码正确性）→ 当前不存在
- **开发验证**（开发时快速检查）→ 当前脚本的实际角色
- **正式实验**（出结论、写报告）→ 想做但缺少基础设施

### 1.2 `SimResult.metrics` 未实现

`result.py` 定义了 `metrics: dict` 字段，`architecture.md` 也提到了"超调量、调节时间、稳态误差、RMSE"，但从未实现计算逻辑。所有实验结果只有时域曲线图，没有任何定量结论。

### 1.3 参数扫描是手写循环

`test_pid.py` 和 `test_smc.py` 中的扫描逻辑（修改 dict → 循环 run）每次重写。只保存了第一个结果的 `config.yaml`，其余结果数据丢失。`architecture.md` 提到的 `BatchRunner` 未实现。

### 1.4 Visualizer 功能单一

只能画时域响应曲线（position / velocity / control / tracking）。不支持：

- 误差曲线 e(t)
- 性能指标对比图（柱状图 / 折线图）
- 相图 (x, v)
- 控制器内部信号（如 SMC 的滑模面 s(t)、PID 的各分量）

### 1.5 控制器内部信号不可观测

`Controller.compute()` 只返回控制力 u，无法获取内部诊断信号（SMC 的滑模面 s、PID 的 P/I/D 分量）。这些信号对调参和分析至关重要，但当前需要重新从 states 反算，且部分信号（如积分项）无法从外部重建。

### 1.6 实验可复现性不足

参数扫描只存了一组数据。没有实验级元信息（实验名称、全部参数组合、运行时间、结论汇总）。

---

## 2. 目标目录结构

```
mass_spring_damper/
├── msd/                            # 核心库
│   ├── plant.py
│   ├── controller/
│   │   ├── base.py                 # [修改] 新增 extras 机制
│   │   ├── step_input.py
│   │   ├── pid.py                  # [修改] compute 中记录 P/I/D 分量
│   │   ├── smc.py                  # [修改] compute 中记录 s(t)
│   │   └── cascade.py
│   ├── reference.py
│   ├── disturbance.py
│   ├── simulator.py                # [修改] 采集 controller extras
│   ├── result.py                   # [修改] 新增 extras 字段
│   ├── config.py
│   ├── metrics.py                  # [新增] 性能指标计算
│   ├── experiment.py               # [新增] 实验运行器
│   └── visualizer.py               # [增强] 新增图类型
├── experiments/                    # [新增] 正式实验脚本
│   ├── pid_tuning.py
│   ├── smc_tuning.py
│   ├── controller_comparison.py
│   └── trajectory_comparison.py
├── tests/                          # [重构] pytest 单元测试
│   ├── configs/                    # 保留
│   ├── test_plant.py
│   ├── test_simulator.py
│   ├── test_pid.py
│   └── test_smc.py
├── results/                        # 实验输出
├── docs/
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

---

## 3. 核心改动设计

### 3.1 Controller extras 机制

**目的**：让控制器在 `compute()` 过程中暴露内部诊断信号，供 Simulator 采集、SimResult 存储、Visualizer 绘图。

**设计**：

```python
# controller/base.py
class Controller(ABC):
    def __init__(self):
        self._extras: dict[str, float] = {}

    @abstractmethod
    def compute(self, state, t, reference=0.0) -> float:
        pass

    @property
    def extras(self) -> dict[str, float]:
        """当前步的诊断信号。由 compute() 内部填充，Simulator 在每步后读取。"""
        return self._extras
```

各控制器在 `compute()` 末尾更新 `self._extras`：

| 控制器 | extras 内容 |
|--------|-------------|
| PID | `{"error": e, "p_term": p, "i_term": i, "d_term": d}` |
| SMC | `{"s": s, "u_eq": u_eq, "u_sw": u_sw, "error": e}` |
| StepInput | `{}`（无内部状态） |

**Simulator 采集**：

```python
# simulator.py run() 循环中
u = self.controller.compute(y, t, reference=ref)
extras = self.controller.extras  # 读取本步诊断信号
# 记录到 extras_log
```

**SimResult 存储**：

```python
# result.py
@dataclass
class SimResult:
    # ... 现有字段 ...
    extras: dict[str, np.ndarray] = field(default_factory=dict)
    # extras["s"] -> shape (n,), extras["p_term"] -> shape (n,), ...
```

`save()` 中将 extras 写入 `data.npz`（key 加 `extra_` 前缀避免冲突）。`load()` 中反向解析。

### 3.2 Metrics 模块

**文件**：`msd/metrics.py`

**核心函数**：`compute_metrics(result: SimResult) -> dict`

**全量指标集**：

| 指标 | 公式/定义 | 适用场景 |
|------|-----------|----------|
| overshoot | (peak - target) / target × 100% | 阶跃 / 恒值参考 |
| settling_time | 首次进入 ±2% 带后不再离开的时刻 | 阶跃 / 恒值参考 |
| rise_time | 从 10% 到 90% 目标值的时间 | 阶跃 / 恒值参考 |
| steady_state_error | 最后 10% 时间段误差均值 | 阶跃 / 恒值 / 斜坡参考 |
| rmse | √(mean(e²)) | 全部 |
| iae | ∫\|e\|dt | 全部 |
| ise | ∫e²dt | 全部 |
| max_control | max(\|u\|) | 全部 |
| control_energy | ∫u²dt | 全部 |
| phase_lag | 互相关峰值对应的时间延迟 | 正弦参考 |

**指标选择策略**：

`compute_metrics` 始终计算所有指标并返回完整 dict。但部分指标对特定参考类型无意义（如正弦跟踪的 overshoot），这些指标值会被标记为 `NaN`。

实验层根据 `result.config["reference_type"]` 决定展示哪些指标：

```python
METRICS_BY_REFERENCE = {
    "Step":     ["overshoot", "settling_time", "rise_time", "steady_state_error", "rmse", "iae", "max_control", "control_energy"],
    "Constant": ["steady_state_error", "rmse", "iae", "max_control", "control_energy"],
    "Ramp":     ["steady_state_error", "rmse", "iae", "max_control", "control_energy"],
    "Sine":     ["rmse", "iae", "phase_lag", "max_control", "control_energy"],
}
```

这套映射随 Reference 类型的扩展同步更新。新增控制器不影响指标体系（指标只依赖 result 数据，不依赖控制器类型）。新增 Reference 类型时，需要在映射中添加对应条目。

**扩展性说明**：

实验框架的指标体系强依赖于 Reference 类型。当新增 Reference 子类时：
1. 在 `METRICS_BY_REFERENCE` 中添加对应条目
2. 如需新指标（如 Ramp 的斜率跟踪误差），在 `compute_metrics` 中新增计算逻辑

控制器的扩展不影响指标计算，但可能引入新的 extras 信号需要可视化。

### 3.3 Experiment 模块

**文件**：`msd/experiment.py`

#### 3.3.1 ParameterSweep

单参数扫描：固定其他参数，遍历一个参数的多个值。

```python
class ParameterSweep:
    def __init__(
        self,
        name: str,               # 实验名称，如 "pid_kp_sweep"
        base_config: SimConfig,   # 基础配置
        param_path: str,          # 参数路径，如 "controller_params.kp"
        values: list,             # 参数值列表
        labels: list[str] = None, # 图例标签，默认自动生成
    )

    def run(self) -> list[SimResult]:
        """运行扫描，返回带 metrics 的结果列表。"""

    def save(self, base_dir="results") -> Path:
        """保存全部结果到实验目录。"""
```

#### 3.3.2 ControllerComparison

多控制器对比：同一 plant / reference / disturbance，不同控制器。

```python
class ControllerComparison:
    def __init__(
        self,
        name: str,                    # 实验名称
        configs: list[SimConfig],     # 各控制器配置
    )

    def run(self) -> list[SimResult]:
        """运行对比，返回带 metrics 的结果列表。"""

    def save(self, base_dir="results") -> Path:
        """保存全部结果到实验目录。"""
```

#### 3.3.3 实验目录结构

每个实验一个目录，命名格式：`{实验名}_{YYYYMMDD_HHMM}`

示例：

```
results/
├── pid_kp_sweep_20260416_1200/
│   ├── report.md                # 实验报告（文字总结）
│   ├── metrics.csv              # 指标汇总表
│   ├── data_Kp=2.npz            # 各组仿真数据
│   ├── data_Kp=5.npz
│   ├── data_Kp=10.npz
│   ├── data_Kp=20.npz
│   ├── timeseries.png           # 时域响应对比图
│   └── metrics.png              # 性能指标图
├── smc_vs_pid_step_20260416_1430/
│   ├── report.md
│   ├── metrics.csv
│   ├── data_PID.npz
│   ├── data_SMC.npz
│   ├── timeseries.png
│   └── metrics.png
```

#### 3.3.4 实验报告 (`report.md`)

自动生成，包含：

```markdown
# 实验：PID Kp 参数扫描
- 时间：2026-04-16 12:00
- 实验类型：ParameterSweep
- 扫描参数：controller_params.kp
- 扫描值：[2, 5, 10, 20, 50]

## 基础配置
- Plant: MassSpringDamper(m=1.0, c=0.5, k=2.0)
- Controller: PID(Ki=5, Kd=4)
- Reference: Step(value=1.0, t_step=0.0)
- 仿真时长: 10.0s, dt=0.01s

## 性能指标

| Label | Overshoot(%) | Settling(s) | Rise(s) | RMSE   | IAE    | Control Energy |
|-------|-------------|-------------|---------|--------|--------|----------------|
| Kp=2  | 0.0         | 4.21        | 2.34    | 0.0832 | 0.521  | 12.3           |
| Kp=5  | 3.2         | 1.87        | 0.92    | 0.0456 | 0.287  | 28.7           |
| ...   | ...         | ...         | ...     | ...    | ...    | ...            |

## 图表
- timeseries.png: 时域响应对比
- metrics.png: 性能指标随 Kp 变化趋势
```

### 3.4 Visualizer 增强

#### 3.4.1 新增绘图 item

在现有 `PLOT_ITEMS` 基础上新增：

| item 名称 | 数据来源 | 用途 |
|-----------|----------|------|
| `"error"` | `ref - position` | 跟踪误差时域曲线 |
| `"phase"` | `(position, velocity)` | 相图，不共享 x 轴 |
| `"sliding_surface"` | `extras["s"]` | SMC 滑模面，需要 extras |
| `"p_term"` / `"i_term"` / `"d_term"` | `extras[...]` | PID 各分量，需要 extras |

`phase` 需要特殊处理（x 轴是 position 而非 time），可能需要单独的绘图逻辑而非复用现有 subplot 框架。

#### 3.4.2 新增独立绘图方法

```python
class Visualizer:
    # 现有
    @staticmethod
    def plot(results, items, title, save_path): ...

    # 新增
    @staticmethod
    def plot_metrics_bar(results, metric_names, title, save_path):
        """柱状图对比多组结果的指标。用于控制器对比。"""

    @staticmethod
    def plot_metrics_vs_param(results, param_name, metric_names, title, save_path):
        """指标随参数变化的折线图。用于参数扫描。"""

    @staticmethod
    def print_metrics_table(results, metric_names):
        """在控制台输出对齐的 ASCII 表格。"""
```

### 3.5 tests/ 重构为 pytest 单元测试

将现有开发验证脚本重写为 pytest 测试，用 assert 验证正确性：

```python
# tests/test_pid.py（重构后）
def test_pid_step_tracking():
    """PID 阶跃跟踪：稳态误差 < 1%。"""
    config = SimConfig.from_yaml("tests/configs/pid_step.yaml")
    result = run_from_config(config)
    metrics = compute_metrics(result)
    assert metrics["steady_state_error"] < 0.01

def test_pid_no_overshoot_with_low_kp():
    """低 Kp 时无超调。"""
    ...
    assert metrics["overshoot"] < 1.0
```

不再需要 `sys.path.insert`，通过项目根目录 `pip install -e .` 或 `PYTHONPATH` 解决导入。

---

## 4. 画图策略

### 4.1 通用原则

| 原则 | 说明 |
|------|------|
| 同一物理量叠加 | 不同参数/控制器的 position 曲线放同一 subplot |
| 时域图和指标图分开 | 时域曲线一张图，指标图单独一张 |
| subplot 上限 4 个 | 超过 4 个拆分为多张图 |
| 命名规范 | `{图类型}.png`，如 `timeseries.png`、`metrics.png` |

### 4.2 各类实验的标准图集

#### 参数扫描（ParameterSweep）

| 图 | 内容 | subplot 数 |
|----|------|-----------|
| `timeseries.png` | tracking + control 时域对比 | 2 |
| `metrics.png` | overshoot / settling_time / rmse vs 参数值（折线图） | 3 |

共 2 张图。

#### 控制器对比（ControllerComparison）

| 图 | 内容 | subplot 数 |
|----|------|-----------|
| `timeseries.png` | tracking + error + control 时域对比 | 3 |
| `metrics.png` | 各指标柱状图（side-by-side） | 1 |

共 2 张图。

#### SMC 专项（切换函数对比、抖振分析）

| 图 | 内容 | subplot 数 |
|----|------|-----------|
| `timeseries.png` | tracking + control 时域对比 | 2 |
| `sliding_surface.png` | s(t) 对比 | 1 |
| `metrics.png` | 指标柱状图 | 1 |

共 3 张图。

---

## 5. 实验规划

### 5.1 PID 调参实验 (`experiments/pid_tuning.py`)

| 子实验 | 扫描参数 | 固定参数 | 输出 |
|--------|----------|----------|------|
| Kp 扫描 | Kp = [2, 5, 10, 20, 50] | Ki=5, Kd=4 | 2 张图 + 表格 |
| Ki 扫描 | Ki = [0, 1, 5, 10, 20] | Kp=10, Kd=4 | 2 张图 + 表格 |
| Kd 扫描 | Kd = [0, 1, 4, 8, 16] | Kp=10, Ki=5 | 2 张图 + 表格 |

### 5.2 SMC 调参实验 (`experiments/smc_tuning.py`)

| 子实验 | 扫描参数 | 固定参数 | 输出 |
|--------|----------|----------|------|
| η 扫描 | η = [0.5, 1, 2, 5, 10] | λ=5, sign | 2 张图 + 表格 |
| λ 扫描 | λ = [1, 2, 5, 10, 20] | η=1, sign | 2 张图 + 表格 |
| 切换函数对比 | sign / sat(φ=0.5) / tanh(φ=0.5) | λ=5, η=1 | 3 张图 + 表格 |

### 5.3 PID vs SMC 对比 (`experiments/controller_comparison.py`)

| 子实验 | 对比对象 | 参考轨迹 | 输出 |
|--------|----------|----------|------|
| 阶跃对比 | PID(10,5,4) vs SMC(λ=5,η=1,sat) | Step(1.0) | 2 张图 + 表格 |
| 正弦对比 | 同上 | Sine(A=1, f=0.5Hz) | 2 张图 + 表格 |
| 斜坡对比 | 同上 | Ramp(slope=0.5) | 2 张图 + 表格 |

### 5.4 轨迹对比 (`experiments/trajectory_comparison.py`)

同一控制器，不同参考轨迹下的表现：

| 子实验 | 控制器 | 参考轨迹 | 输出 |
|--------|--------|----------|------|
| PID 多轨迹 | PID(10,5,4) | Step / Ramp / Sine | 每种轨迹 1 张图 + 汇总表 |
| SMC 多轨迹 | SMC(λ=5,η=1,sat) | Step / Ramp / Sine | 同上 |

---

## 6. 执行计划

按依赖关系分阶段执行：

### 阶段 A：核心基础设施（3 个改动）

| 步骤 | 内容 | 修改文件 | 依赖 |
|------|------|----------|------|
| A1 | Controller extras 机制 | `base.py`, `pid.py`, `smc.py`, `simulator.py`, `result.py` | 无 |
| A2 | Metrics 模块 | `metrics.py`（新建）| A1（需要 extras 中的 error） |
| A3 | Visualizer 增强 | `visualizer.py` | A1（需要 extras）、A2（需要 metrics） |

### 阶段 B：实验框架（2 个改动）

| 步骤 | 内容 | 修改文件 | 依赖 |
|------|------|----------|------|
| B1 | Experiment 运行器 | `experiment.py`（新建）| A2 |
| B2 | 实验报告生成 | 集成在 `experiment.py` 中 | B1 |

### 阶段 C：实验脚本（4 个脚本）

| 步骤 | 内容 | 修改文件 | 依赖 |
|------|------|----------|------|
| C1 | PID 调参实验 | `experiments/pid_tuning.py` | B1 |
| C2 | SMC 调参实验 | `experiments/smc_tuning.py` | B1 |
| C3 | 控制器对比实验 | `experiments/controller_comparison.py` | B1 |
| C4 | 轨迹对比实验 | `experiments/trajectory_comparison.py` | B1 |

### 阶段 D：测试与收尾

| 步骤 | 内容 | 修改文件 | 依赖 |
|------|------|----------|------|
| D1 | 重构 tests/ 为 pytest | `tests/test_*.py` | A2 |
| D2 | 更新文档 | `README.md`, `docs/architecture.md`, `CHANGELOG.md` | 全部完成 |

---

## 7. 注意事项

### 7.1 向后兼容

- `Controller.compute()` 的返回值不变（仍然只返回 `float`），extras 通过属性读取，不破坏现有接口
- `SimResult` 新增 `extras` 字段使用默认值 `{}`，旧的 `load()` 不会报错
- `Visualizer.plot()` 现有 items 行为不变，新 items 为可选

### 7.2 扩展性关联

| 新增内容 | 需要同步更新 |
|----------|-------------|
| 新 Controller | `base.py` extras 自动兼容，无需改动 metrics；如需新 extras 信号，在该控制器中自行填充 |
| 新 Reference | `metrics.py` 的 `METRICS_BY_REFERENCE` 需添加条目 |
| 新指标 | `metrics.py` 的 `compute_metrics` 添加计算逻辑 |
| 新 Visualizer item | `visualizer.py` 的 `PLOT_ITEMS` 添加条目 |

### 7.3 `data.npz` 文件命名

实验目录中的 npz 文件按 `result.label` 命名：`data_{label}.npz`。label 中的特殊字符（`/`、`\`、空格）替换为 `_`。
