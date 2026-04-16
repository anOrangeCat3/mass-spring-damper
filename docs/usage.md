# 使用方法

## 环境准备

```bash
git clone https://github.com/<your-username>/mass_spring_damper.git
cd mass_spring_damper
pip install -r requirements.txt
```

依赖：`numpy`, `scipy`, `matplotlib`, `pyyaml`。

## 基本工作流

所有仿真都遵循同一流程：**编写 YAML 配置 → 运行仿真 → 查看结果**。

### 方式一：使用测试脚本

```bash
cd tests

# 开环阶跃响应（含解析解对比）
python3 step_response.py

# PID 控制测试（含 Kp 参数扫描）
python3 test_pid.py

# SMC 控制测试（含切换函数对比和 η 扫描）
python3 test_smc.py

# 扰动测试
python3 test_disturbance.py
```

### 方式二：Python 脚本调用

最简单的用法——从 YAML 配置一键运行：

```python
from msd import SimConfig, run_from_config, Visualizer

# 加载配置并运行
config = SimConfig.from_yaml("tests/configs/pid_step.yaml")
result = run_from_config(config)

# 保存数据（config.yaml + data.npz）
result_dir = result.save("results")

# 绘图
Visualizer.plot(
    result,
    items=["tracking", "velocity", "control"],
    title="PID Step Response",
    save_path=str(result_dir / "plot.png"),
)
```

### 方式三：纯代码构建（不使用 YAML）

```python
from msd import (
    MassSpringDamper, PIDController, StepReference,
    Simulator, Visualizer,
)

# 构建各模块
plant = MassSpringDamper(m=1.0, c=0.5, k=2.0)
controller = PIDController(kp=10.0, ki=5.0, kd=4.0, dt=0.01)
reference = StepReference(value=1.0, t_step=0.0)

# 运行仿真
sim = Simulator(plant, controller, dt=0.01)
result = sim.run(t_end=10.0, y0=[0.0, 0.0], reference_fn=reference)

# 绘图
Visualizer.plot(result, items=["tracking", "control"])
```

## YAML 配置详解

一个完整的配置文件包含以下部分：

```yaml
# 初始条件 [位移, 速度]
y0: [0.0, 0.0]

# 仿真参数
dt: 0.01          # 控制周期 (s)
t_end: 10.0       # 仿真时长 (s)
method: RK45       # scipy 积分方法

# 物理模型
plant_type: MassSpringDamper
plant_params:
  m: 1.0           # 质量 (kg)
  c: 0.5           # 阻尼系数 (N·s/m)
  k: 2.0           # 弹簧刚度 (N/m)

# 控制器（下文详述）
controller_type: PID
controller_params:
  kp: 10.0
  ki: 5.0
  kd: 4.0

# 参考轨迹（可选，不填则恒为 0）
reference_type: Step
reference_params:
  value: 1.0
  t_step: 0.0

# 扰动（可选，不填则无扰动）
disturbance_type: Sine
disturbance_params:
  amplitude: 0.3
  frequency: 2.0

# 图例标签（可选，不填则自动生成）
label: "my experiment"
```

### 控制器配置

#### StepInput（开环）

```yaml
controller_type: StepInput
controller_params:
  amplitude: 1.0     # 阶跃幅值
  t_step: 0.0        # 阶跃时刻
```

#### PID

```yaml
controller_type: PID
controller_params:
  kp: 10.0           # 比例增益
  ki: 5.0            # 积分增益
  kd: 4.0            # 微分增益
  # dt 自动注入，无需填写
  # 以下为可选扩展：
  # state_index: 0               # 跟踪状态索引（0=位移, 1=速度）
  # derivative_on_measurement: true  # 微分作用于测量值
  # u_min: -50                   # 输出下限
  # u_max: 50                    # 输出上限
```

#### SMC

```yaml
controller_type: SMC
controller_params:
  m: 1.0             # 质量（需与 plant_params 一致）
  c: 0.5             # 阻尼系数
  k: 2.0             # 弹簧刚度
  lambda_: 5.0       # 滑模面斜率
  eta: 1.0           # 趋近增益
  # dt 自动注入，无需填写
  # 以下为可选扩展：
  # smoothing: tanh              # 抖振抑制（null/sat/tanh）
  # phi: 0.5                     # 边界层厚度
  # u_min: -50                   # 输出下限
  # u_max: 50                    # 输出上限
  # estimate_reference_derivative: true  # 差分估计参考导数
```

### 参考轨迹配置

| 类型 | `reference_type` | 关键参数 | 公式 |
|------|------------------|----------|------|
| 恒定值 | `Constant` | `value` | r(t) = value |
| 阶跃 | `Step` | `value`, `t_step`, `initial` | t ≥ t_step 时 value，否则 initial |
| 斜坡 | `Ramp` | `slope`, `t_start`, `offset` | slope × max(0, t - t_start) + offset |
| 正弦 | `Sine` | `amplitude`, `frequency`, `phase`, `offset` | A·sin(2πft + φ) + offset |

### 扰动配置

```yaml
# 正弦扰动
disturbance_type: Sine
disturbance_params:
  amplitude: 0.3
  frequency: 2.0

# 高斯噪声
disturbance_type: GaussianNoise
disturbance_params:
  std: 0.1
  seed: 42           # 可选，固定随机种子

# 组合扰动
disturbance_type: Composite
disturbance_params:
  disturbances:
    - type: Sine
      params: { amplitude: 0.3, frequency: 2.0 }
    - type: GaussianNoise
      params: { std: 0.1 }
```

## 参数扫描（多组对比）

在 Python 脚本中修改配置字典即可批量运行：

```python
from msd import SimConfig, run_from_config, Visualizer

base = SimConfig.from_yaml("tests/configs/pid_step.yaml")

results = []
for kp in [2, 5, 10, 20, 50]:
    cfg = SimConfig.from_dict({
        **base.to_dict(),
        "controller_params": {**base.controller_params, "kp": kp},
        "label": f"Kp={kp}",
    })
    results.append(run_from_config(cfg))

# 多结果对比绘图
Visualizer.plot(
    results,
    items=["tracking", "control"],
    title="PID Kp Sweep",
)
```

`Visualizer.plot()` 接受列表时会在同一子图上叠加所有结果，用 `label` 区分图例。

## 可视化

### 可绘制项

| `items` 值 | 说明 |
|-------------|------|
| `"position"` | 位移曲线 |
| `"velocity"` | 速度曲线 |
| `"control"` | 控制力曲线 |
| `"reference"` | 参考轨迹曲线 |
| `"disturbance"` | 扰动曲线 |
| `"tracking"` | 位移 + 参考轨迹叠加（推荐用于闭环控制评估） |

### Visualizer.plot() 参数

```python
Visualizer.plot(
    results,                           # SimResult 或 list[SimResult]
    items=["tracking", "control"],     # 绘制项列表
    title="My Plot",                   # 图标题
    analytical={"time": t, "position": x},  # 可选，叠加解析解
    save_path="output.png",            # 可选，保存路径（不填则 plt.show()）
)
```

## 结果保存与加载

### 保存

```python
result_dir = result.save("results")
# 生成目录：results/YYYYMMDD_HHMMSS/
#   ├── config.yaml    仿真配置（可复现）
#   └── data.npz       仿真数据
```

### 加载

```python
from msd import SimResult

result = SimResult.load("results/20260416_102045")
print(result.time.shape, result.position.shape)
```

### 直接访问数据

```python
result.time          # 时间序列 (n,)
result.states        # 状态矩阵 (n, 2)
result.position      # 位移 (n,)    等价于 states[:, 0]
result.velocity      # 速度 (n,)    等价于 states[:, 1]
result.control       # 控制力 (n,)
result.reference     # 参考轨迹 (n,)
result.disturbance   # 扰动 (n,)
result.config        # 配置字典
result.label         # 图例标签
```

## 新增控制器

三步即可扩展新的控制算法：

**第一步**：在 `msd/controller/` 下新建文件，继承 `Controller` 基类：

```python
from .base import Controller

class MyController(Controller):
    def __init__(self, gain=1.0, dt=0.01):
        self.gain = gain
        self.dt = dt

    def compute(self, state, t, reference=0.0):
        error = reference - state[0]
        return self.gain * error

    def reset(self):
        pass

    @property
    def name(self):
        return f"MyController(gain={self.gain})"
```

**第二步**：在 `msd/controller/__init__.py` 添加导出：

```python
from .my_controller import MyController
```

**第三步**：在 `msd/config.py` 注册表添加一行：

```python
CONTROLLER_REGISTRY = {
    ...
    "MyCtrl": MyController,
}
```

之后即可在 YAML 中使用：

```yaml
controller_type: MyCtrl
controller_params:
  gain: 5.0
  # dt 自动注入
```

`build_controller()` 会自动检测构造函数中的 `dt` 参数并注入，无需手动配置。
