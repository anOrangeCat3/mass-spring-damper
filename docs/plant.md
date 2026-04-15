# Plant 物理模型模块

## 接口设计

```python
class Plant(ABC):
    def derivatives(self, t: float, state: np.ndarray, u: float, d: float) -> np.ndarray: ...
    def state_names(self) -> list[str]: ...
```

`derivatives()` 返回状态导数向量 $\dot{\mathbf{y}}$，供 `solve_ivp` 调用。签名中显式包含 `u`（控制输入）和 `d`（扰动），使 Plant 作为纯粹的动力学模型，不关心输入来源。

`state_names` 用于 Visualizer 和 SimResult 中的标签映射。

## MassSpringDamper 实现

### 动力学方程

$$m\ddot{x} + c\dot{x} + kx = u(t) + d(t)$$

状态空间形式（令 $y_1 = x$，$y_2 = \dot{x}$）：

$$\dot{y}_1 = y_2$$

$$\dot{y}_2 = \frac{u + d - c \cdot y_2 - k \cdot y_1}{m}$$

### 参数

| 参数 | 符号 | 默认值 | 单位 | 含义 |
|---|---|---|---|---|
| `m` | $m$ | 1.0 | kg | 质量 |
| `c` | $c$ | 0.5 | N·s/m | 阻尼系数 |
| `k` | $k$ | 2.0 | N/m | 弹簧刚度 |

### 推导属性

**固有频率**（无阻尼自由振动频率）：

$$\omega_n = \sqrt{\frac{k}{m}}$$

**阻尼比**（表征系统衰减快慢）：

$$\zeta = \frac{c}{2\sqrt{mk}}$$

| $\zeta$ 范围 | 分类 | 响应特征 |
|---|---|---|
| $0 < \zeta < 1$ | 欠阻尼 | 振荡衰减，有超调 |
| $\zeta = 1$ | 临界阻尼 | 最快无振荡收敛 |
| $\zeta > 1$ | 过阻尼 | 缓慢无振荡收敛 |

默认参数下：$\omega_n = \sqrt{2} \approx 1.414$ rad/s，$\zeta = \frac{0.5}{2\sqrt{2}} \approx 0.177$（欠阻尼）。

### 阶跃响应解析解

对 $u(t) = A \cdot \mathbf{1}(t)$（单位阶跃），零初始条件，稳态值为 $x_{ss} = A/k$。

**欠阻尼**（$\zeta < 1$）：

$$x(t) = x_{ss}\left[1 - e^{-\zeta\omega_n t}\left(\cos\omega_d t + \frac{\zeta}{\sqrt{1-\zeta^2}}\sin\omega_d t\right)\right]$$

其中阻尼振荡频率 $\omega_d = \omega_n\sqrt{1-\zeta^2}$。

该解析解在 `tests/step_response.py` 中用于验证数值仿真的正确性。

## 扩展

新增物理模型只需继承 `Plant`，实现 `derivatives()` 和 `state_names`，然后在 `PLANT_REGISTRY` 中注册。

可能的扩展：非线性弹簧（$k(x)$）、库伦摩擦、多自由度系统。
