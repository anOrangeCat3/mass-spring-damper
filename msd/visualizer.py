"""可视化模块：静态绘图、多结果对比、性能指标图表。"""

import matplotlib.pyplot as plt
import numpy as np

from .result import SimResult


class Visualizer:
    """仿真结果可视化。支持时域绘图、相图、extras 信号、指标对比。"""

    # 可绘制的状态量及其对应的数据提取方式
    PLOT_ITEMS = {
        "position": {"ylabel": "Position (m)", "extract": lambda r: r.position},
        "velocity": {"ylabel": "Velocity (m/s)", "extract": lambda r: r.velocity},
        "control": {"ylabel": "Control Force (N)", "extract": lambda r: r.control},
        "reference": {"ylabel": "Reference", "extract": lambda r: r.reference},
        "disturbance": {"ylabel": "Disturbance (N)", "extract": lambda r: r.disturbance},
        "tracking": {"ylabel": "Position (m)", "extract": lambda r: r.position},
        "error": {"ylabel": "Tracking Error", "extract": lambda r: r.reference - r.position},
    }

    # extras 中的信号也可直接作为 plot item
    EXTRAS_ITEMS = {
        "sliding_surface": {"ylabel": "Sliding Surface s(t)", "key": "s"},
        "p_term": {"ylabel": "P Term", "key": "p_term"},
        "i_term": {"ylabel": "I Term", "key": "i_term"},
        "d_term": {"ylabel": "D Term", "key": "d_term"},
        "u_eq": {"ylabel": "u_eq (Equivalent)", "key": "u_eq"},
        "u_sw": {"ylabel": "u_sw (Switching)", "key": "u_sw"},
    }

    @staticmethod
    def plot(
        results: SimResult | list[SimResult],
        items: list[str] = None,
        title: str = "Simulation Results",
        analytical: dict = None,
        save_path: str = None,
    ):
        """绘制仿真结果时域图。

        Args:
            results: 单个或多个 SimResult
            items: 要绘制的量名称列表，支持 PLOT_ITEMS 和 EXTRAS_ITEMS 中的名称
            title: 图表总标题
            analytical: 解析解字典 {"time": t, "position": x, ...}
            save_path: 图片保存路径，None 则调用 plt.show()
        """
        if isinstance(results, SimResult):
            results = [results]
        if items is None:
            items = ["position", "velocity", "control"]

        n = len(items)
        fig, axes = plt.subplots(n, 1, figsize=(10, 3 * n), sharex=True)
        if n == 1:
            axes = [axes]

        for ax, item_name in zip(axes, items):
            if item_name in Visualizer.PLOT_ITEMS:
                Visualizer._plot_standard_item(ax, results, item_name, analytical)
            elif item_name in Visualizer.EXTRAS_ITEMS:
                Visualizer._plot_extras_item(ax, results, item_name)
            else:
                ax.set_ylabel(item_name)
                ax.text(0.5, 0.5, f"Unknown item: {item_name}",
                        transform=ax.transAxes, ha="center")

            ax.legend()
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle(title)
        plt.tight_layout()

        Visualizer._save_or_show(fig, save_path)

    @staticmethod
    def plot_phase(
        results: SimResult | list[SimResult],
        title: str = "Phase Portrait",
        save_path: str = None,
    ):
        """绘制相图 (position vs velocity)。

        Args:
            results: 单个或多个 SimResult
            title: 图表标题
            save_path: 保存路径
        """
        if isinstance(results, SimResult):
            results = [results]

        fig, ax = plt.subplots(figsize=(8, 6))
        for r in results:
            ax.plot(r.position, r.velocity, label=r.label)
            ax.plot(r.position[0], r.velocity[0], "o", color="green", markersize=6)
            ax.plot(r.position[-1], r.velocity[-1], "s", color="red", markersize=6)

        ax.set_xlabel("Position (m)")
        ax.set_ylabel("Velocity (m/s)")
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        Visualizer._save_or_show(fig, save_path)

    @staticmethod
    def plot_metrics_bar(
        results: list[SimResult],
        metric_names: list[str],
        title: str = "Performance Metrics Comparison",
        save_path: str = None,
    ):
        """柱状图对比多组结果的性能指标。

        Args:
            results: SimResult 列表（需已填充 metrics）
            metric_names: 要展示的指标名列表
            title: 图表标题
            save_path: 保存路径
        """
        header_map = {
            "overshoot": "Overshoot (%)", "settling_time": "Settling Time (s)",
            "rise_time": "Rise Time (s)", "steady_state_error": "SSE",
            "rmse": "RMSE", "iae": "IAE", "ise": "ISE",
            "max_control": "Max Control", "control_energy": "Energy",
            "phase_lag": "Phase Lag (s)",
        }

        # 过滤掉全 NaN 的指标
        valid_metrics = []
        for m in metric_names:
            vals = [r.metrics.get(m, float("nan")) for r in results]
            if not all(np.isnan(v) for v in vals):
                valid_metrics.append(m)

        if not valid_metrics:
            return

        n = len(valid_metrics)
        fig, axes = plt.subplots(1, n, figsize=(3 * n, 4))
        if n == 1:
            axes = [axes]

        labels = [r.label for r in results]
        x = np.arange(len(labels))

        for ax, m in zip(axes, valid_metrics):
            vals = [r.metrics.get(m, float("nan")) for r in results]
            # NaN 替换为 0 以避免绘图警告
            plot_vals = [0.0 if np.isnan(v) else v for v in vals]
            bars = ax.bar(x, plot_vals, width=0.6)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
            ax.set_title(header_map.get(m, m))
            ax.grid(True, alpha=0.3, axis="y")

            for bar, v in zip(bars, vals):
                text = "N/A" if np.isnan(v) else f"{v:.3f}"
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        text, ha="center", va="bottom", fontsize=7)

        fig.suptitle(title)
        plt.tight_layout()

        Visualizer._save_or_show(fig, save_path)

    @staticmethod
    def plot_metrics_vs_param(
        results: list[SimResult],
        param_values: list[float],
        param_name: str,
        metric_names: list[str],
        title: str = "Metrics vs Parameter",
        save_path: str = None,
    ):
        """指标随参数变化的折线图，用于参数扫描。

        Args:
            results: SimResult 列表（需已填充 metrics）
            param_values: 参数值列表，与 results 一一对应
            param_name: 参数名称（x 轴标签）
            metric_names: 要展示的指标名列表
            title: 图表标题
            save_path: 保存路径
        """
        header_map = {
            "overshoot": "Overshoot (%)", "settling_time": "Settling Time (s)",
            "rise_time": "Rise Time (s)", "steady_state_error": "SSE",
            "rmse": "RMSE", "iae": "IAE", "ise": "ISE",
            "max_control": "Max Control", "control_energy": "Energy",
            "phase_lag": "Phase Lag (s)",
        }

        # 过滤掉全 NaN 的指标
        valid_metrics = []
        for m in metric_names:
            vals = [r.metrics.get(m, float("nan")) for r in results]
            if not all(np.isnan(v) for v in vals):
                valid_metrics.append(m)

        if not valid_metrics:
            return

        n = len(valid_metrics)
        fig, axes = plt.subplots(n, 1, figsize=(8, 3 * n), sharex=True)
        if n == 1:
            axes = [axes]

        for ax, m in zip(axes, valid_metrics):
            vals = [r.metrics.get(m, float("nan")) for r in results]
            ax.plot(param_values, vals, "o-", linewidth=1.5, markersize=5)
            ax.set_ylabel(header_map.get(m, m))
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel(param_name)
        fig.suptitle(title)
        plt.tight_layout()

        Visualizer._save_or_show(fig, save_path)

    # ============================================================
    # 内部方法
    # ============================================================

    @staticmethod
    def _plot_standard_item(ax, results, item_name, analytical):
        """绘制标准 PLOT_ITEMS 中的量。"""
        info = Visualizer.PLOT_ITEMS[item_name]

        for result in results:
            ax.plot(result.time, info["extract"](result), label=result.label)

        # tracking 模式：叠加参考轨迹
        if item_name == "tracking" and results:
            ax.plot(
                results[0].time, results[0].reference,
                "--k", label="reference", alpha=0.7, linewidth=1.5,
            )

        # 叠加解析解
        if analytical and item_name in analytical:
            ax.plot(
                analytical["time"], analytical[item_name],
                "--k", label="analytical", alpha=0.7,
            )

        ax.set_ylabel(info["ylabel"])

    @staticmethod
    def _plot_extras_item(ax, results, item_name):
        """绘制 EXTRAS_ITEMS 中的控制器诊断信号。"""
        info = Visualizer.EXTRAS_ITEMS[item_name]
        key = info["key"]

        for result in results:
            if key in result.extras:
                ax.plot(result.time, result.extras[key], label=result.label)

        ax.set_ylabel(info["ylabel"])

    @staticmethod
    def _save_or_show(fig, save_path):
        """保存图片或显示。"""
        if save_path:
            fig.savefig(save_path, dpi=150)
            print(f"Figure saved to {save_path}")
            plt.close(fig)
        else:
            plt.show()
