# Mass-Spring-Damper Simulation

弹簧-质量-阻尼器仿真框架，支持多种控制器、参考轨迹和外部扰动，通过 YAML 配置一键运行仿真。

## Features

- **模块化架构**：Plant / Controller / Reference / Disturbance / Simulator / Visualizer 各模块独立，通过注册表自由组合
- **控制器**：StepInput（开环阶跃）、PID（积分抗饱和 + 微分滤波）、SMC（滑模控制）、Cascade 预留
- **参考轨迹**：Constant / Step / Ramp / Sine
- **扰动模型**：正弦扰动、高斯噪声、复合扰动
- **YAML 配置驱动**：所有参数通过配置文件管理，无需修改代码
- **结果自动保存**：每次仿真自动保存 config.yaml + data.npz + plot.png

## Installation

```bash
git clone https://github.com/<your-username>/mass_spring_damper.git
cd mass_spring_damper
pip install -r requirements.txt
```

## Quick Start

```bash
# 运行阶跃响应仿真
python tests/step_response.py

# 运行 PID 控制测试（含 Kp 参数扫描）
python tests/test_pid.py

# 运行 SMC 控制测试（含切换函数对比和 η 扫描）
python tests/test_smc.py
```

也可以在 Python 中直接调用：

```python
from msd import run_from_config

result = run_from_config("tests/configs/pid_step.yaml")
```

## Project Structure

```
mass_spring_damper/
├── msd/                    # 核心库
│   ├── plant.py            # 被控对象（MassSpringDamper）
│   ├── controller/         # 控制器包
│   │   ├── base.py         # 控制器抽象基类
│   │   ├── step_input.py   # 开环阶跃输入
│   │   ├── pid.py          # PID 控制器
│   │   ├── smc.py          # 滑模控制器
│   │   └── cascade.py      # 级联控制器（占位）
│   ├── reference.py        # 参考轨迹
│   ├── disturbance.py      # 扰动模型
│   ├── simulator.py        # 仿真器
│   ├── visualizer.py       # 可视化
│   ├── result.py           # 仿真结果数据类
│   └── config.py           # 配置系统与工厂函数
├── tests/                  # 测试与示例脚本
│   └── configs/            # YAML 配置文件
├── docs/                   # 技术文档
├── results/                # 仿真输出（gitignored）
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

## License

MIT License. See [LICENSE](LICENSE) for details.
