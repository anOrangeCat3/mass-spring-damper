"""可视化模块：静态绘图与多结果对比。"""

import matplotlib.pyplot as plt
import numpy as np

from .result import SimResult


class Visualizer:
    """仿真结果可视化。支持单次结果绘图和多次结果对比。"""

    # 可绘制的状态量及其对应的数据提取方式
    PLOT_ITEMS = {
        "position": {"ylabel": "Position (m)", "extract": lambda r: r.position},
        "velocity": {"ylabel": "Velocity (m/s)", "extract": lambda r: r.velocity},
        "control": {"ylabel": "Control Force (N)", "extract": lambda r: r.control},
        "reference": {"ylabel": "Reference", "extract": lambda r: r.reference},
        "disturbance": {"ylabel": "Disturbance (N)", "extract": lambda r: r.disturbance},
        "tracking": {"ylabel": "Position (m)", "extract": lambda r: r.position},
    }

    @staticmethod
    def plot(
        results: SimResult | list[SimResult],
        items: list[str] = None,
        title: str = "Simulation Results",
        analytical: dict = None,
        save_path: str = None,
    ):
        """绘制仿真结果。

        Args:
            results: 单个或多个 SimResult
            items: 要绘制的状态量名称列表，默认 ["position", "velocity", "control"]
            title: 图表总标题
            analytical: 解析解字典 {"time": t, "position": x, ...}，用于验证
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
            info = Visualizer.PLOT_ITEMS[item_name]

            for result in results:
                ax.plot(result.time, info["extract"](result), label=result.label)

            # tracking 模式：叠加参考轨迹（取第一个 result 的 reference）
            if item_name == "tracking" and results:
                ax.plot(
                    results[0].time, results[0].reference,
                    "--k", label="reference", alpha=0.7, linewidth=1.5,
                )

            # 叠加解析解（如果有）
            if analytical and item_name in analytical:
                ax.plot(
                    analytical["time"],
                    analytical[item_name],
                    "--k",
                    label="analytical",
                    alpha=0.7,
                )

            ax.set_ylabel(info["ylabel"])
            ax.legend()
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle(title)
        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150)
            print(f"Figure saved to {save_path}")
            plt.close(fig)
        else:
            plt.show()
