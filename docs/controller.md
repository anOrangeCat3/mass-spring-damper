# Controller 控制器模块

## 概述

控制器模块以 Python 包形式组织（`msd/controller/`），每种控制算法独立一个文件，通过 `__init__.py` 统一导出。

```
msd/controller/
├── __init__.py        统一导出
├── base.py            Controller 抽象基类
├── step_input.py      开环阶跃输入
├── pid.py             PID 控制器
├── smc.py             滑模控制器
└── cascade.py         级联控制器（预留）
```

新增控制算法只需：① 新建文件实现 `Controller` 子类 → ② `__init__.py` 加一行导出 → ③ `config.py` 注册表加一行。

## Controller 抽象基类

```python
class Controller(ABC):
    def compute(self, state: np.ndarray, t: float, reference: float = 0.0) -> float
    def reset(self)       # 重置内部状态，无状态控制器无需覆写
    def name(self) -> str # 图例标签（@property）
```

| 参数 | 类型 | 说明 |
|---|---|---|
| state | np.ndarray | 当前状态向量 [位移, 速度, ...] |
| t | float | 当前时间 |
| reference | float | 参考值（目标位置或目标速度） |
| **返回值** | float | 控制输入 u |

## PIDController

位置式 PID 控制器，公式：

$$u(t) = K_p e(t) + K_i \int_0^t e(\tau) d\tau + K_d \frac{d}{dt}[\cdot]$$

### 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| kp | float | 1.0 | 比例增益 |
| ki | float | 0.0 | 积分增益 |
| kd | float | 0.0 | 微分增益 |
| dt | float | 0.01 | 控制周期，由 `build_controller` 自动从 SimConfig 注入 |
| state_index | int | 0 | 跟踪的状态量索引（0=位移, 1=速度），用于级联控制 |
| derivative_on_measurement | bool | True | 微分项作用对象（见下文） |
| u_min | float | -inf | 控制输出下限（可选扩展，默认无限幅） |
| u_max | float | +inf | 控制输出上限（可选扩展，默认无限幅） |

### 设计要点

**微分项策略**：默认微分作用于测量值（`-Kd * dPV/dt`），而非误差（`Kd * de/dt`）。当参考值发生阶跃变化时，误差的导数会产生瞬时脉冲（derivative kick），导致控制输出剧烈跳变。作用于测量值可避免此问题。可通过 `derivative_on_measurement=False` 切换为传统模式。

**积分抗饱和（可选扩展）**：当配置了输出限幅（`u_min` / `u_max`）时自动启用 clamping 抗饱和。输出饱和时回退本次积分累积量，防止积分项在饱和期间持续增长（windup）。未配置限幅时不触发任何饱和逻辑。

**dt 自动注入**：PID 需要控制周期 `dt` 来计算积分和微分，但 `dt` 本质上是仿真层参数。`build_controller()` 通过 `inspect` 检测构造函数签名，自动将 `SimConfig.dt` 注入给需要的控制器，用户无需在 YAML 中重复填写。

### YAML 配置示例

```yaml
controller_type: PID
controller_params:
  kp: 10.0
  ki: 5.0
  kd: 4.0
  # dt 无需填写，自动注入
  # 以下为可选扩展：
  # state_index: 0                    # 跟踪状态索引
  # derivative_on_measurement: true   # 微分作用于测量值
  # u_min: -50                        # 输出限幅
  # u_max: 50
```

## StepInput

开环阶跃输入，用于系统辨识和基准测试，不使用反馈。

```yaml
controller_type: StepInput
controller_params:
  amplitude: 1.0
  t_step: 0.0
```

## SMCController

滑模控制器（Sliding Mode Control），基于系统模型的非线性鲁棒控制方法。

### 原理

对于质量-弹簧-阻尼器系统 $m\ddot{x} + c\dot{x} + kx = u + d$，定义：

- 位置误差 $e = x_{\text{ref}} - x$
- 线性滑模面 $s = \dot{e} + \lambda e$

控制律由两部分组成：

$$u = \underbrace{kx + (c - m\lambda)v + m\lambda\dot{x}_{\text{ref}}}_{u_{\text{eq}}（等效控制）} + \underbrace{m\eta \cdot \text{switching}(s)}_{u_{\text{sw}}（切换控制）}$$

**等效控制**：基于系统模型的前馈补偿，使系统在滑模面上运动时维持 $\dot{s} = 0$。

**切换控制**：驱动系统到达滑模面。当系统处于滑模面上时（$s = 0$），误差以 $\dot{e} = -\lambda e$ 指数衰减。

### 切换函数

| 类型 | `smoothing` | 公式 | 特点 |
|------|-------------|------|------|
| sign（经典） | `None`（默认） | $\text{sign}(s)$ | 理论最优鲁棒性，存在抖振 |
| sat（饱和函数） | `"sat"` | $\text{sat}(s/\phi)$ | 边界层内线性，边界层外等于 sign |
| tanh（双曲正切） | `"tanh"` | $\tanh(s/\phi)$ | 全局光滑，无切换点 |

$\phi$ 为边界层厚度，越小越接近经典 sign（抖振越大），越大越平滑（鲁棒性下降）。仅当 `smoothing` 非 `None` 时有效。

### 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| m | float | 1.0 | 质量（需与 plant_params 一致） |
| c | float | 0.5 | 阻尼系数 |
| k | float | 2.0 | 弹簧刚度 |
| lambda_ | float | 5.0 | 滑模面斜率 (> 0) |
| eta | float | 1.0 | 趋近增益 (> 0) |
| dt | float | 0.01 | 控制周期，由 `build_controller` 自动注入 |
| smoothing | str\|None | None | 切换函数类型（可选扩展） |
| phi | float | 0.1 | 边界层厚度（可选扩展） |
| u_min | float | -inf | 控制输出下限（可选扩展） |
| u_max | float | +inf | 控制输出上限（可选扩展） |
| estimate_reference_derivative | bool | False | 是否差分估计 $\dot{x}_{\text{ref}}$（可选扩展） |

### 设计要点

**模型依赖**：与 PID 不同，SMC 的等效控制项需要系统模型参数 (m, c, k)。用户需在 `controller_params` 中填入与 `plant_params` 一致的值。模型参数偏差会降低等效控制的精度，但切换控制项可以补偿一定范围内的不确定性。

**η 的选取**：趋近增益 η 需大于系统扰动的上界才能保证可达条件 $s \cdot \dot{s} < 0$。η 越大到达滑模面越快，但经典 sign 下抖振越严重。

**参考轨迹导数**：默认假设 $\dot{x}_{\text{ref}} = 0$，适用于阶跃和恒值参考。对于 Ramp、Sine 等时变参考，启用 `estimate_reference_derivative=True` 可用差分法估计导数，提高跟踪精度。

### YAML 配置示例

经典 SMC（sign 切换函数）：

```yaml
controller_type: SMC
controller_params:
  m: 1.0
  c: 0.5
  k: 2.0
  lambda_: 5.0
  eta: 1.0
```

带抖振抑制的 SMC：

```yaml
controller_type: SMC
controller_params:
  m: 1.0
  c: 0.5
  k: 2.0
  lambda_: 5.0
  eta: 1.0
  smoothing: tanh       # 或 "sat"
  phi: 0.5
```

### SMC vs PID 对比

| 特性 | SMC | PID |
|------|-----|-----|
| 模型依赖 | 需要系统参数 | 无需系统参数 |
| 鲁棒性 | 对匹配不确定性具有不变性 | 依赖增益整定 |
| 控制信号 | 经典 sign 不连续，可能抖振 | 连续平滑 |
| 参数数量 | 2 个核心参数 (λ, η) | 3 个核心参数 (Kp, Ki, Kd) |
| 稳态误差 | 无需积分项即可消除 | 需要积分项 |

## 级联控制（预留）

`CascadeController` 将外环和内环控制器组合。外环输出作为内环的参考值，通过 `state_index` 区分各环跟踪的状态量。

```
外环 PID (state_index=0, 跟踪位移)
  → 输出速度参考 →
    内环 PID (state_index=1, 跟踪速度)
      → 输出控制力 u
```

从 Simulator 视角，CascadeController 与普通 Controller 接口一致，仿真器无需修改。
