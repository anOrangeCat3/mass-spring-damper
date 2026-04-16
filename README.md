# Mass-Spring-Damper Simulation

弹簧-质量-阻尼器仿真框架，支持多种控制器、参考轨迹和外部扰动，通过 YAML 配置一键运行仿真。

## Features

- **模块化架构**：Plant / Controller / Reference / Disturbance / Simulator / Visualizer 各模块独立，通过注册表自由组合
- **控制器**：StepInput（开环阶跃）、PID（积分抗饱和 + 微分滤波）、SMC（滑模控制）、Cascade 预留
- **参考轨迹**：Constant / Step / Ramp / Sine
- **扰动模型**：正弦扰动、高斯噪声、复合扰动
- **YAML 配置驱动**：所有参数通过配置文件管理，无需修改代码
- **性能指标**：自动计算超调量、调节时间、RMSE、控制能量等指标
- **实验框架**：参数扫描、控制器对比，自动生成图表和报告
- **结果自动保存**：每次仿真/实验自动保存 config + data + 图表 + 报告

## Installation

```bash
git clone https://github.com/<your-username>/mass_spring_damper.git
cd mass_spring_damper
pip install -r requirements.txt
```

## Quick Start

### 运行单元测试

```bash
cd tests && python3 -m pytest -v
```

### 运行实验

```bash
# PID 调参实验（Kp/Ki/Kd 参数扫描）
cd experiments && python3 pid_tuning.py

# SMC 调参实验（η/λ 扫描 + 切换函数对比）
cd experiments && python3 smc_tuning.py

# PID vs SMC 控制器对比
cd experiments && python3 controller_comparison.py

# 不同轨迹对比
cd experiments && python3 trajectory_comparison.py
```

### Python API

```python
from msd import SimConfig, run_from_config, compute_metrics, ParameterSweep

# 单次仿真
config = SimConfig.from_yaml("tests/configs/pid_step.yaml")
result = run_from_config(config)
result.metrics = compute_metrics(result)

# 参数扫描实验
sweep = ParameterSweep(
    name="pid_kp_sweep",
    base_config=config,
    param_path="controller_params.kp",
    values=[2, 5, 10, 20, 50],
)
sweep.run_and_save("results")
```

## Project Structure

```
mass_spring_damper/
├── msd/                    # 核心库
│   ├── plant.py            # 被控对象（MassSpringDamper）
│   ├── controller/         # 控制器包
│   │   ├── base.py         # 控制器抽象基类（含 extras 机制）
│   │   ├── step_input.py   # 开环阶跃输入
│   │   ├── pid.py          # PID 控制器
│   │   ├── smc.py          # 滑模控制器
│   │   └── cascade.py      # 级联控制器（占位）
│   ├── reference.py        # 参考轨迹
│   ├── disturbance.py      # 扰动模型
│   ├── simulator.py        # 仿真器
│   ├── visualizer.py       # 可视化（时域图、相图、指标图）
│   ├── result.py           # 仿真结果数据类
│   ├── metrics.py          # 性能指标计算
│   ├── experiment.py       # 实验运行器（参数扫描、控制器对比）
│   └── config.py           # 配置系统与工厂函数
├── experiments/            # 实验脚本
│   ├── pid_tuning.py       # PID 调参
│   ├── smc_tuning.py       # SMC 调参
│   ├── controller_comparison.py  # 控制器对比
│   └── trajectory_comparison.py  # 轨迹对比
├── tests/                  # pytest 单元测试
│   ├── configs/            # YAML 配置文件
│   ├── test_plant.py
│   ├── test_simulator.py
│   ├── test_pid.py
│   ├── test_smc.py
│   └── test_disturbance.py
├── docs/                   # 技术文档
├── results/                # 实验输出（gitignored）
├── requirements.txt
└── CHANGELOG.md
```

## Documentation

详细文档见 [`docs/`](docs/) 目录：

- [使用方法](docs/usage.md)
- [架构概览](docs/architecture.md)
- [配置系统](docs/config.md)
- [物理模型](docs/plant.md)
- [控制器](docs/controller.md)
- [参考轨迹](docs/reference.md)
- [扰动模型](docs/disturbance.md)
- [仿真器](docs/simulator.md)
- [重构计划](docs/refactoring-001.md)

## License

MIT License. See [LICENSE](LICENSE) for details.
