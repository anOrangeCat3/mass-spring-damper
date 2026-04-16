"""性能指标计算模块。

从 SimResult 中提取跟踪误差、超调量、调节时间等控制性能指标。
"""

import numpy as np

from .result import SimResult


# 各 Reference 类型适用的指标集
METRICS_BY_REFERENCE: dict[str, list[str]] = {
    "Step": [
        "overshoot", "settling_time", "rise_time",
        "steady_state_error", "rmse", "iae", "ise",
        "max_control", "control_energy",
    ],
    "Constant": [
        "steady_state_error", "rmse", "iae", "ise",
        "max_control", "control_energy",
    ],
    "Ramp": [
        "steady_state_error", "rmse", "iae", "ise",
        "max_control", "control_energy",
    ],
    "Sine": [
        "rmse", "iae", "ise", "phase_lag",
        "max_control", "control_energy",
    ],
}

# 所有指标名称（全量）
ALL_METRICS = [
    "overshoot", "settling_time", "rise_time",
    "steady_state_error", "rmse", "iae", "ise",
    "max_control", "control_energy", "phase_lag",
]


def compute_metrics(result: SimResult) -> dict:
    """计算全量性能指标，不适用的指标值为 NaN。

    Args:
        result: SimResult 对象，需包含 time, position, reference, control

    Returns:
        指标字典 {指标名: float}
    """
    t = result.time
    x = result.position
    ref = result.reference
    u = result.control
    dt = t[1] - t[0] if len(t) > 1 else 1.0

    error = ref - x
    target = ref[-1]
    has_step = not np.allclose(ref, ref[0])

    metrics = {}

    # 超调量 (%)：仅对阶跃/恒值参考有意义
    if abs(target) > 1e-12 and not _is_oscillating_reference(ref):
        peak = np.max(x) if target > 0 else np.min(x)
        overshoot = (peak - target) / abs(target) * 100.0
        metrics["overshoot"] = max(0.0, overshoot)
    else:
        metrics["overshoot"] = float("nan")

    # 调节时间 (s)：首次进入 ±2% 带后不再离开
    if abs(target) > 1e-12 and not _is_oscillating_reference(ref):
        band = 0.02 * abs(target)
        settled = np.abs(x - target) <= band
        metrics["settling_time"] = _find_settling_time(t, settled)
    else:
        metrics["settling_time"] = float("nan")

    # 上升时间 (s)：从 10% 到 90% 目标值
    if abs(target) > 1e-12 and not _is_oscillating_reference(ref):
        metrics["rise_time"] = _find_rise_time(t, x, target)
    else:
        metrics["rise_time"] = float("nan")

    # 稳态误差：最后 10% 时间段的平均绝对误差
    tail = max(1, len(t) // 10)
    metrics["steady_state_error"] = float(np.mean(np.abs(error[-tail:])))

    # RMSE
    metrics["rmse"] = float(np.sqrt(np.mean(error ** 2)))

    # IAE: ∫|e|dt
    metrics["iae"] = float(np.sum(np.abs(error)) * dt)

    # ISE: ∫e²dt
    metrics["ise"] = float(np.sum(error ** 2) * dt)

    # 最大控制力
    metrics["max_control"] = float(np.max(np.abs(u)))

    # 控制能量: ∫u²dt
    metrics["control_energy"] = float(np.sum(u ** 2) * dt)

    # 相位延迟：通过互相关估计（正弦跟踪）
    if _is_oscillating_reference(ref):
        metrics["phase_lag"] = _estimate_phase_lag(t, x, ref)
    else:
        metrics["phase_lag"] = float("nan")

    return metrics


def select_metrics(result: SimResult) -> list[str]:
    """根据 result.config 中的 reference_type 选择适用的指标名称。

    Args:
        result: SimResult 对象

    Returns:
        指标名称列表
    """
    ref_type = result.config.get("reference_type", None)
    if ref_type and ref_type in METRICS_BY_REFERENCE:
        return METRICS_BY_REFERENCE[ref_type]
    return ["steady_state_error", "rmse", "iae", "max_control", "control_energy"]


def format_metrics_table(results: list[SimResult], metric_names: list[str] = None) -> str:
    """将多个 SimResult 的指标格式化为 ASCII 表格。

    Args:
        results: SimResult 列表，每个需要已填充 metrics
        metric_names: 要展示的指标名。None 则自动选择

    Returns:
        格式化的表格字符串
    """
    if not results:
        return ""
    if metric_names is None:
        metric_names = select_metrics(results[0])

    # 表头
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

    # 计算列宽
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
# 内部辅助函数
# ============================================================

def _is_oscillating_reference(ref: np.ndarray, threshold: float = 0.1) -> bool:
    """判断参考信号是否为振荡型（如正弦），通过检查过零次数。"""
    centered = ref - np.mean(ref)
    if np.max(np.abs(centered)) < threshold:
        return False
    sign_changes = np.sum(np.diff(np.sign(centered)) != 0)
    return sign_changes > 4


def _find_settling_time(t: np.ndarray, settled: np.ndarray) -> float:
    """找到首次进入稳态带后不再离开的时刻。"""
    for i in range(len(settled) - 1, -1, -1):
        if not settled[i]:
            if i < len(t) - 1:
                return float(t[i + 1])
            return float("nan")
    return float(t[0])


def _find_rise_time(t: np.ndarray, x: np.ndarray, target: float) -> float:
    """从 10% 到 90% 目标值的时间。"""
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


def _estimate_phase_lag(t: np.ndarray, x: np.ndarray, ref: np.ndarray) -> float:
    """通过互相关估计输出相对于参考的相位延迟（秒）。"""
    dt = t[1] - t[0]
    # 去除前 20% 的瞬态
    skip = len(t) // 5
    x_ss = x[skip:] - np.mean(x[skip:])
    ref_ss = ref[skip:] - np.mean(ref[skip:])

    if np.std(x_ss) < 1e-12 or np.std(ref_ss) < 1e-12:
        return float("nan")

    corr = np.correlate(x_ss, ref_ss, mode="full")
    lags = np.arange(-len(ref_ss) + 1, len(ref_ss)) * dt
    peak_idx = np.argmax(corr)
    return float(lags[peak_idx])
