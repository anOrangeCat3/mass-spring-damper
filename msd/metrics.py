"""性能指标计算模块。

每个指标是独立函数，接收 SimResult 返回 float。
实验脚本按需调用所需指标，不依赖预设的指标集。
"""

import numpy as np

from .result import SimResult


# ============================================================
# 独立指标函数
# 每个函数签名统一：(result: SimResult) -> float
# ============================================================

def overshoot(result: SimResult) -> float:
    """超调量 (%)，仅对非振荡参考有意义。

    Args:
        result: SimResult，需包含 position 和 reference

    Returns:
        超调百分比，无超调返回 0.0，不适用返回 NaN
    """
    ref = result.reference
    x = result.position
    target = ref[-1]

    if abs(target) < 1e-12 or _is_oscillating_reference(ref):
        return float("nan")

    peak = np.max(x) if target > 0 else np.min(x)
    os = (peak - target) / abs(target) * 100.0
    return max(0.0, os)


def settling_time(result: SimResult, band: float = 0.02) -> float:
    """调节时间 (s)，首次进入 ±band 带后不再离开。

    Args:
        result: SimResult
        band: 误差带比例，默认 2%

    Returns:
        调节时间 (s)，不适用返回 NaN
    """
    ref = result.reference
    x = result.position
    t = result.time
    target = ref[-1]

    if abs(target) < 1e-12 or _is_oscillating_reference(ref):
        return float("nan")

    threshold = band * abs(target)
    settled = np.abs(x - target) <= threshold

    for i in range(len(settled) - 1, -1, -1):
        if not settled[i]:
            return float(t[i + 1]) if i < len(t) - 1 else float("nan")
    return float(t[0])


def rise_time(result: SimResult) -> float:
    """上升时间 (s)，从 10% 到 90% 目标值。

    Args:
        result: SimResult

    Returns:
        上升时间 (s)，不适用返回 NaN
    """
    ref = result.reference
    x = result.position
    t = result.time
    target = ref[-1]

    if abs(target) < 1e-12 or _is_oscillating_reference(ref):
        return float("nan")

    low, high = 0.1 * target, 0.9 * target
    if target < 0:
        low, high = high, low

    t_low = t_high = None
    for i in range(len(x)):
        if t_low is None and x[i] >= low:
            t_low = t[i]
        if t_high is None and x[i] >= high:
            t_high = t[i]
            break

    if t_low is not None and t_high is not None:
        return float(t_high - t_low)
    return float("nan")


def steady_state_error(result: SimResult, tail_ratio: float = 0.1) -> float:
    """稳态误差，最后 tail_ratio 时间段的平均绝对误差。

    Args:
        result: SimResult
        tail_ratio: 取末尾多大比例的数据，默认 10%

    Returns:
        稳态误差 (float)
    """
    error = result.reference - result.position
    tail = max(1, int(len(error) * tail_ratio))
    return float(np.mean(np.abs(error[-tail:])))


def rmse(result: SimResult) -> float:
    """均方根误差 RMSE。"""
    error = result.reference - result.position
    return float(np.sqrt(np.mean(error ** 2)))


def iae(result: SimResult) -> float:
    """积分绝对误差 IAE = ∫|e|dt。"""
    error = result.reference - result.position
    dt = result.time[1] - result.time[0] if len(result.time) > 1 else 1.0
    return float(np.sum(np.abs(error)) * dt)


def ise(result: SimResult) -> float:
    """积分平方误差 ISE = ∫e²dt。"""
    error = result.reference - result.position
    dt = result.time[1] - result.time[0] if len(result.time) > 1 else 1.0
    return float(np.sum(error ** 2) * dt)


def max_control(result: SimResult) -> float:
    """最大控制力 |u|_max。"""
    return float(np.max(np.abs(result.control)))


def control_energy(result: SimResult) -> float:
    """控制能量 ∫u²dt。"""
    dt = result.time[1] - result.time[0] if len(result.time) > 1 else 1.0
    return float(np.sum(result.control ** 2) * dt)


def phase_lag(result: SimResult) -> float:
    """相位延迟 (s)，通过互相关估计，适用于振荡参考。

    Args:
        result: SimResult

    Returns:
        相位延迟 (s)，非振荡参考返回 NaN
    """
    ref = result.reference
    x = result.position
    t = result.time

    if not _is_oscillating_reference(ref):
        return float("nan")

    dt = t[1] - t[0]
    skip = len(t) // 5
    x_ss = x[skip:] - np.mean(x[skip:])
    ref_ss = ref[skip:] - np.mean(ref[skip:])

    if np.std(x_ss) < 1e-12 or np.std(ref_ss) < 1e-12:
        return float("nan")

    corr = np.correlate(x_ss, ref_ss, mode="full")
    lags = np.arange(-len(ref_ss) + 1, len(ref_ss)) * dt
    peak_idx = np.argmax(corr)
    return float(lags[peak_idx])


# ============================================================
# 便捷函数：批量计算
# ============================================================

# 指标名 -> 函数 的映射表
METRIC_FUNCTIONS: dict[str, callable] = {
    "overshoot": overshoot,
    "settling_time": settling_time,
    "rise_time": rise_time,
    "steady_state_error": steady_state_error,
    "rmse": rmse,
    "iae": iae,
    "ise": ise,
    "max_control": max_control,
    "control_energy": control_energy,
    "phase_lag": phase_lag,
}


def compute_metrics(result: SimResult, names: list[str] = None) -> dict:
    """批量计算指标。

    Args:
        result: SimResult
        names: 要计算的指标名列表，None 则计算全部

    Returns:
        {指标名: float} 字典
    """
    if names is None:
        names = list(METRIC_FUNCTIONS.keys())
    return {name: METRIC_FUNCTIONS[name](result) for name in names if name in METRIC_FUNCTIONS}


def format_metrics_table(results: list[SimResult], metric_names: list[str]) -> str:
    """将多个 SimResult 的指标格式化为 ASCII 表格。

    Args:
        results: SimResult 列表，每个需已填充 metrics
        metric_names: 要展示的指标名

    Returns:
        格式化表格字符串
    """
    if not results:
        return ""

    header_map = {
        "overshoot": "Overshoot(%)",
        "settling_time": "Settling(s)",
        "rise_time": "Rise(s)",
        "steady_state_error": "SSE",
        "rmse": "RMSE",
        "iae": "IAE",
        "ise": "ISE",
        "max_control": "MaxCtrl",
        "control_energy": "Energy",
        "phase_lag": "PhaseLag(s)",
    }

    headers = ["Label"] + [header_map.get(m, m) for m in metric_names]

    rows = []
    for r in results:
        row = [r.label]
        for m in metric_names:
            val = r.metrics.get(m, float("nan"))
            if np.isnan(val):
                row.append("N/A")
            else:
                row.append(f"{val:.4f}")
        rows.append(row)

    col_widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]

    def format_row(cells):
        return "│ " + " │ ".join(c.rjust(w) for c, w in zip(cells, col_widths)) + " │"

    sep_top = "┌─" + "─┬─".join("─" * w for w in col_widths) + "─┐"
    sep_mid = "├─" + "─┼─".join("─" * w for w in col_widths) + "─┤"
    sep_bot = "└─" + "─┴─".join("─" * w for w in col_widths) + "─┘"

    lines = [sep_top, format_row(headers), sep_mid]
    for row in rows:
        lines.append(format_row(row))
    lines.append(sep_bot)

    return "\n".join(lines)


# ============================================================
# 内部辅助
# ============================================================

def _is_oscillating_reference(ref: np.ndarray, threshold: float = 0.1) -> bool:
    """判断参考信号是否为振荡型（如正弦），通过过零次数检测。"""
    centered = ref - np.mean(ref)
    if np.max(np.abs(centered)) < threshold:
        return False
    sign_changes = np.sum(np.diff(np.sign(centered)) != 0)
    return sign_changes > 4
