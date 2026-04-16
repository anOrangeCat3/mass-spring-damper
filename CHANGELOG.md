# Changelog

## [0.0.5] - 2026-04-16

### Summary

新增 SMC 滑模控制器，统一 PID/SMC 输出限幅为可选扩展，新增使用方法文档。

### Added

- SMCController 实现（`msd/controller/smc.py`）：基于线性滑模面 s = ė + λe，等效控制 + 切换控制
  - 默认经典 sign(s) 切换函数
  - 可选抖振抑制扩展：`smoothing="sat"` 饱和函数、`smoothing="tanh"` 双曲正切，通过 `phi` 控制边界层厚度
  - 可选输出限幅扩展：`u_min` / `u_max`
  - 可选参考轨迹导数估计：`estimate_reference_derivative=True` 支持时变参考跟踪
- `CONTROLLER_REGISTRY` 注册 SMC 类型
- SMC 测试配置（`tests/configs/smc_step.yaml`）及测试脚本（`tests/test_smc.py`，含切换函数对比和 η 参数扫描）
- 技术文档：`docs/usage.md` 使用方法文档（工作流、YAML 配置详解、参数扫描、可视化、结果保存加载、新增控制器指南）
- 技术文档：`docs/controller.md` 更新 SMC 章节

### Changed

- PIDController 输出限幅改为可选扩展：`u_min` / `u_max` 默认 ±inf（无限幅），仅显式配置时才执行 clip 和 clamping 积分抗饱和
- `docs/controller.md` PID 章节更新，限幅和抗饱和标注为可选扩展

## [0.0.4] - 2026-04-15

### Summary

新增 PID 闭环控制器，Controller 模块重构为包结构，Visualizer 新增 tracking 绘图模式。

### Added

- Controller 模块从单文件重构为包（`msd/controller/`），每种算法独立文件，便于维护和扩展
- Controller 基类新增 `reset()` 方法，支持有状态控制器（PID 积分项等）在多次仿真间重置
- PIDController 实现（`msd/controller/pid.py`）：位置式 PID，支持 `state_index` 级联预留、输出限幅、clamping 积分抗饱和、微分作用于测量值（避免 derivative kick）
- `build_controller()` 通过 `inspect` 自动注入 `dt`，闭环控制器无需在 YAML 中重复填写控制周期
- `CONTROLLER_REGISTRY` 注册 PID 类型
- Visualizer 新增 `"tracking"` 绘图项：在同一子图上绘制实际位置与参考轨迹，便于评估控制效果
- SMC 滑模控制器和 CascadeController 级联控制器占位文件（`smc.py`, `cascade.py`）
- PID 测试配置（`tests/configs/pid_step.yaml`）及测试脚本（`tests/test_pid.py`，含 Kp 参数扫描对比）
- 技术文档：`docs/controller.md`

### Changed

- `docs/architecture.md` 目录结构更新为 controller 包结构
- `docs/config.md` 注册表和 `build_controller` 说明更新

## [0.0.3] - 2026-04-15

### Summary

新增 Reference 参考轨迹模块，支持 Constant / Step / Ramp / Sine 四种目标轨迹，可通过 YAML 配置。

### Added

- Reference 抽象基类及 ConstantReference、StepReference、RampReference、SineReference 实现（`msd/reference.py`）
- Reference 基类提供 `derivative()` 方法，返回目标的解析导数，为 PID 微分项和前馈控制预留拓展性
- SimConfig 新增 `reference_type` / `reference_params` 字段，支持 YAML 配置参考轨迹
- `REFERENCE_REGISTRY` 类型注册表及 `build_reference()` 工厂函数（`msd/config.py`）
- `run_from_config()` 自动构建 Reference 对象并传入仿真器
- 技术文档：`docs/reference.md`

### Fixed

- `result.py` 的 `_build_save_config()` 正确保存 `reference_type` 和 `reference_params`（旧版仅保存一个占位字段）

## [0.0.2] - 2026-04-15

### Summary

新增 Disturbance 扰动模块，支持正弦扰动和高斯噪声，可通过 YAML 配置开关和参数。

### Added

- Disturbance 抽象基类及 SineDisturbance、GaussianNoise、CompositeDisturbance 实现（`msd/disturbance.py`）
- SimConfig 新增 `disturbance_type` / `disturbance_params` 字段，支持 YAML 配置扰动
- `DISTURBANCE_REGISTRY` 类型注册表及 `build_disturbance()` 工厂函数（`msd/config.py`）
- `run_from_config()` 自动构建扰动对象并传入仿真器
- 扰动测试脚本及配置文件（`tests/test_disturbance.py`，`tests/configs/step_with_disturbance.yaml`，`tests/configs/step_with_noise.yaml`）
- 技术文档：`docs/disturbance.md`（扰动模块）、`docs/plant.md`（物理模型）、`docs/simulator.md`（仿真器）、`docs/config.md`（配置系统）

### Fixed

- SimResult 保存的 config.yaml 字段按字母排序导致逻辑分组混乱，改用 `sort_keys=False` 保持插入顺序

## [0.0.1] - 2026-04-15

### Summary

实现核心仿真框架，完成阶跃响应验证，加入配置系统与结果保存。

### Added

- Plant 抽象基类及 MassSpringDamper 模型（`msd/plant.py`）
- Controller 抽象基类及 StepInput 开环控制（`msd/controller.py`）
- Simulator 分段积分仿真器 + SimResult 数据类（`msd/simulator.py`, `msd/result.py`）
- Visualizer 静态绘图，支持多结果对比与解析解叠加（`msd/visualizer.py`）
- SimConfig 配置系统，支持 YAML 文件加载和类型注册表（`msd/config.py`）
- `run_from_config()` 便捷函数，从配置一键运行仿真
- SimResult `save()` / `load()` 方法，按时间戳保存 config.yaml + data.npz + plot.png
- 阶跃响应测试脚本及配置文件（`tests/step_response.py`, `tests/configs/step_response.yaml`）
- pyyaml 依赖

### Fixed

- Visualizer `plt.show()` 在无图形界面环境下阻塞，新增 `save_path` 参数支持直接保存文件
- `examples/` 重命名为 `tests/`，更准确反映目录用途

## [0.0.0] - 2026-04-15

### Summary

项目初始化，完成架构设计与可行性分析。

### Details

- 确定项目架构：Plant / Controller / Reference / Disturbance / Solver / Simulator / BatchRunner / Visualizer
- 确定仿真方法：scipy.integrate.solve_ivp，分段积分 + 零阶保持
- 确定可视化方案：matplotlib（静态图 + 交互 + 动画），Manim 作为后续可选
- 确定 Web 部署方案：Streamlit 优先
- 确定开发环境：Python 3.12.3, numpy 1.26.4, scipy 1.11.4, matplotlib 3.6.3
- 定义 SimResult 数据结构，支持批量运行与多结果对比
- 建立项目目录结构与文档规范
