# Simulator 仿真器模块

## 核心策略：分段积分 + 零阶保持

仿真器模拟真实数字控制系统的工作方式：控制器以固定周期 `dt` 采样，计算一次控制量，该控制量在下一个采样周期到来之前保持不变。

```
时间轴:  |--- dt ---|--- dt ---|--- dt ---|
控制输入:    u₀          u₁          u₂        ← 每段内恒定
ODE 积分:  solve_ivp   solve_ivp   solve_ivp  ← 每段独立调用
```

### 为什么不直接一次性积分？

如果将整个仿真时间跨度一次性交给 `solve_ivp`，控制输入 $u(t)$ 必须作为时间的连续函数传入。但实际数字控制器的输出是**离散的**——只在采样时刻更新，期间保持不变。分段积分精确还原了这一行为。

### 单步流程

每个控制周期内的执行顺序：

1. **采样**：读取当前状态 $\mathbf{y}$、参考值 $r(t)$、扰动 $d(t)$
2. **计算**：控制器根据状态和参考值计算 $u = \text{controller.compute}(\mathbf{y}, t, r)$
3. **记录**：将 $t, \mathbf{y}, u, r, d$ 写入日志数组
4. **积分**：调用 `solve_ivp`，在 $[t, t+dt]$ 上求解 ODE，$u$ 和 $d$ 在此区间内为常数
5. **更新**：$\mathbf{y} \leftarrow$ 积分终点状态，$t \leftarrow t + dt$

### 积分方法

默认使用 `RK45`（4/5 阶 Runge-Kutta，自适应步长）。`solve_ivp` 在每个 $dt$ 区间内自动选择子步长以满足误差容限。

可通过配置 `method` 字段切换其他方法（`RK23`, `DOP853`, `Radau`, `BDF` 等）。对于刚性系统可选用 `Radau` 或 `BDF`。

## 数据记录

所有时间序列预分配为 numpy 数组，避免动态追加的性能开销：

| 数组 | shape | 内容 |
|---|---|---|
| `time_log` | $(n,)$ | 采样时刻 |
| `state_log` | $(n, n_{states})$ | 状态向量（位移、速度） |
| `control_log` | $(n,)$ | 控制输入 |
| `reference_log` | $(n,)$ | 参考轨迹 |
| `disturbance_log` | $(n,)$ | 扰动值 |

其中 $n = \lceil t_{end} / dt \rceil$。

## 接口兼容性

`disturbance_fn` 和 `reference_fn` 的类型签名均为 `Callable[[float], float] | None`。`Disturbance` 类通过 `__call__` 实现此接口，因此可以直接传入，不需要适配层。

## 注意事项

- 最后一步的 `dt_actual` 可能小于 `dt`，以精确到达 `t_end`
- 控制输入和扰动在每个 `dt` 区间内为**常数**，即使 `solve_ivp` 内部使用了多个子步也是如此
- 仿真器不持有 Disturbance 或 Reference 对象的引用，而是通过函数参数传入，保持松耦合
