# Controller 控制器模块

## 概述

控制器模块以 Python 包形式组织（`msd/controller/`），每种控制算法独立一个文件，通过 `__init__.py` 统一导出。

```
msd/controller/
├── __init__.py        统一导出
├── base.py            Controller 抽象基类
├── step_input.py      开环阶跃输入
├── pid.py             PID 控制器
├── smc.py             滑模控制器（预留）
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
| u_min | float | -inf | 控制输出下限 |
| u_max | float | +inf | 控制输出上限 |
| derivative_on_measurement | bool | True | 微分项作用对象（见下文） |

### 设计要点

**微分项策略**：默认微分作用于测量值（`-Kd * dPV/dt`），而非误差（`Kd * de/dt`）。当参考值发生阶跃变化时，误差的导数会产生瞬时脉冲（derivative kick），导致控制输出剧烈跳变。作用于测量值可避免此问题。可通过 `derivative_on_measurement=False` 切换为传统模式。

**积分抗饱和**：采用 clamping 方式。当控制输出超过 `[u_min, u_max]` 限幅范围时，回退本次积分累积量，防止积分项在饱和期间持续增长（windup）。

**dt 自动注入**：PID 需要控制周期 `dt` 来计算积分和微分，但 `dt` 本质上是仿真层参数。`build_controller()` 通过 `inspect` 检测构造函数签名，自动将 `SimConfig.dt` 注入给需要的控制器，用户无需在 YAML 中重复填写。

### YAML 配置示例

```yaml
controller_type: PID
controller_params:
  kp: 10.0
  ki: 5.0
  kd: 4.0
  # dt 无需填写，自动注入
  # state_index: 0        # 可选，默认跟踪位移
  # u_min: -50             # 可选，限幅
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

## 级联控制（预留）

`CascadeController` 将外环和内环控制器组合。外环输出作为内环的参考值，通过 `state_index` 区分各环跟踪的状态量。

```
外环 PID (state_index=0, 跟踪位移)
  → 输出速度参考 →
    内环 PID (state_index=1, 跟踪速度)
      → 输出控制力 u
```

从 Simulator 视角，CascadeController 与普通 Controller 接口一致，仿真器无需修改。
