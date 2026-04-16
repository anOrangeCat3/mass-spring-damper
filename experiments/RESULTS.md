# 实验索引

| 实验 | 说明 | 配置要点 |
|------|------|----------|
| [pid_tuning](pid_tuning/) | PID Kp/Ki/Kd 参数扫描 | Step 参考，无扰动 |
| [smc_tuning](smc_tuning/) | SMC η/λ 参数扫描 | Step 参考，Sine 扰动(A=0.5,f=1Hz)，经典 sign，无限幅 |
| [controller_comparison](controller_comparison/) | PID vs SMC 对比 | Step/Sine/Ramp 三种参考 |
| [trajectory_comparison](trajectory_comparison/) | 同一控制器不同轨迹对比 | PID 和 SMC 分别测 Step/Ramp/Sine |

运行：`cd <实验目录> && python run.py`，结果在各自 `results/` 下。
