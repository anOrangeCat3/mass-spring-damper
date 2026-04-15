# Architecture

## Overview

Mass-spring-damper simulation system for verifying control algorithms.

**Dynamics:**

$$m\ddot{x} + c\dot{x} + kx = u(t) + d(t)$$

- $u(t)$: control input
- $d(t)$: external disturbance

## Module Structure

```
Plant           物理模型（m, c, k，支持非线性扩展）
Controller      控制算法（PID / LQR / MPC / 自定义）
Reference       目标轨迹生成器（阶跃 / 正弦 / 任意函数）
Disturbance     外部扰动（脉冲 / 噪声 / 周期力）
Solver          ODE 积分器（封装 scipy.integrate.solve_ivp）
Simulator       主循环，组合上述模块，输出 SimResult
BatchRunner     批量运行多组配置，返回 list[SimResult]
Visualizer      静态绘图 / 交互可视化 / 动画 / 多结果对比
```

## Key Design Decisions

### Extensibility

每个模块通过**抽象基类（ABC）**定义接口，新增实现只需继承并实现接口方法，无需修改其他代码。

### Simulation Method

采用 `scipy.integrate.solve_ivp`（默认 RK45），**分段积分**策略：

1. 每个控制周期调用一次 `solve_ivp`
2. 控制输入在周期内保持不变（零阶保持 ZOH）
3. 真实反映数字控制器的离散采样行为

### Data Flow

```
Config ──→ Simulator.run() ──→ SimResult
                                    │
[Config, ...] ──→ BatchRunner ──→ [SimResult, ...]
                                        │
                                  Visualizer.compare()
```

### SimResult

单次仿真的标准化输出，包含：

| 字段 | 内容 |
|---|---|
| config | 完整仿真参数（Plant / Controller / Reference / Disturbance） |
| time | 时间序列 |
| states | 状态量（位移、速度） |
| control | 控制力序列 |
| reference | 参考轨迹序列 |
| disturbance | 扰动序列 |
| metrics | 性能指标（超调量、调节时间、稳态误差、RMSE 等） |

## Directory Layout

```
mass_spring_damper/
├── docs/                   技术文档
├── msd/                    源代码包
│   ├── plant.py
│   ├── controller/         控制器包（每种算法独立文件）
│   │   ├── base.py         Controller 抽象基类
│   │   ├── step_input.py   开环阶跃输入
│   │   ├── pid.py          PID 控制器
│   │   ├── smc.py          滑模控制器（预留）
│   │   └── cascade.py      级联控制器（预留）
│   ├── reference.py
│   ├── disturbance.py
│   ├── config.py           配置管理 + 类型注册表
│   ├── simulator.py
│   ├── batch_runner.py
│   ├── result.py           SimResult 数据类（含 save/load）
│   └── visualizer.py
├── tests/                  测试 / 验证脚本
│   └── configs/            YAML 配置文件
├── results/                仿真结果（按时间戳组织）
│   └── YYYYMMDD_HHMMSS/
│       ├── config.yaml     仿真配置
│       ├── data.npz        仿真数据
│       └── plot.png        效果图
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

## Future Plans

- Web demo（Streamlit）
- Manim 教学动画
- 多自由度扩展
