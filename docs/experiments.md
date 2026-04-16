# 实验框架

## 目录结构

每个实验是 `experiments/` 下的独立目录，包含配置和运行脚本：

```
experiments/
├── pid_tuning/                 PID 调参（Kp/Ki/Kd 扫描）
│   ├── config.yaml             实验参数
│   ├── run.py                  运行脚本
│   └── results/                结果（gitignored）
│       ├── kp_sweep/
│       │   ├── timeseries.png
│       │   ├── metrics.png
│       │   ├── data_kp_*.npz
│       │   └── report.txt
│       ├── ki_sweep/
│       └── kd_sweep/
├── smc_tuning/                 SMC 调参（η/λ 扫描 + 切换函数对比）
│   ├── config.yaml
│   ├── run.py
│   └── results/
├── controller_comparison/      PID vs SMC 控制器对比
│   ├── config.yaml
│   ├── run.py
│   └── results/
└── trajectory_comparison/      不同参考轨迹对比
    ├── config.yaml
    ├── run.py
    └── results/
```

## 运行方式

```bash
cd experiments/<实验名> && python run.py
```

每个实验从同目录的 `config.yaml` 读取参数，结果保存到同目录的 `results/`。

## 复现

Git 仓库保留 `run.py` 和 `config.yaml`，`results/` 被 gitignored。克隆后运行即可复现：

```bash
git clone <repo>
cd mass_spring_damper
pip install -r requirements.txt
cd experiments/pid_tuning && python run.py
```

## 新建实验

1. 在 `experiments/` 下创建新目录
2. 编写 `config.yaml`（定义实验参数）
3. 编写 `run.py`（从 config 读取参数，调用 `msd` 库运行仿真，保存结果到 `results/`）
4. 运行 `python run.py` 验证

`run.py` 不依赖任何实验框架类，直接调用 `msd` 库的基础 API：

```python
from msd import SimConfig, run_from_config, Visualizer
from msd.metrics import compute_metrics, format_metrics_table
```

## 结果内容

每个实验的 `results/` 目录包含：

| 文件 | 内容 |
|---|---|
| `data_*.npz` | 仿真原始数据（time, states, control, reference, disturbance, extras） |
| `timeseries.png` | 时域响应对比图 |
| `metrics.png` | 性能指标图（柱状图或参数扫描曲线） |
| `report.txt` | 指标汇总表 |

## 指标系统

`msd/metrics.py` 提供独立的指标计算函数，每个函数接收 `SimResult` 返回 `float`：

```python
from msd.metrics import overshoot, settling_time, rmse, iae, phase_lag

# 按需调用单个指标
os = overshoot(result)
st = settling_time(result, band=0.02)

# 批量计算
from msd.metrics import compute_metrics
metrics = compute_metrics(result, names=["rmse", "iae", "max_control"])
```

可用指标：`overshoot`, `settling_time`, `rise_time`, `steady_state_error`, `rmse`, `iae`, `ise`, `max_control`, `control_energy`, `phase_lag`。

每个实验在 `config.yaml` 中定义需要的指标列表，`run.py` 按需调用。

## 与 tests/ 的区别

| | tests/ | experiments/ |
|---|---|---|
| 目的 | 代码正确性验证 | 控制效果实验与分析 |
| 运行方式 | `pytest` | `python run.py` |
| 结果 | pass/fail | 数据 + 图表 + 报告 |
| Git 跟踪 | 全部跟踪 | 仅跟踪 run.py + config.yaml |
