"""实验运行器：参数扫描、控制器对比，自动保存结果和报告。"""

import csv
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from .config import SimConfig, run_from_config
from .metrics import compute_metrics, select_metrics, format_metrics_table
from .result import SimResult
from .visualizer import Visualizer


def _sanitize_filename(name: str) -> str:
    """将 label 转换为安全文件名。"""
    return re.sub(r'[^\w\-.]', '_', name)


def _set_nested(d: dict, path: str, value):
    """设置嵌套字典中的值，如 'controller_params.kp'。"""
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


class ParameterSweep:
    """单参数扫描实验。

    固定其他参数，遍历一个参数的多个值，运行仿真并自动计算指标。

    Args:
        name: 实验名称，如 "pid_kp_sweep"
        base_config: 基础配置
        param_path: 参数路径，如 "controller_params.kp"
        values: 参数值列表
        labels: 图例标签列表，默认自动从 param_path 和 values 生成
    """

    def __init__(
        self,
        name: str,
        base_config: SimConfig,
        param_path: str,
        values: list,
        labels: list[str] = None,
    ):
        self.name = name
        self.base_config = base_config
        self.param_path = param_path
        self.values = values
        self.labels = labels or [
            f"{param_path.split('.')[-1]}={v}" for v in values
        ]

    def run(self) -> list[SimResult]:
        """运行扫描，每个结果自动计算 metrics。"""
        results = []
        for val, label in zip(self.values, self.labels):
            cfg_dict = self.base_config.to_dict()
            _set_nested(cfg_dict, self.param_path, val)
            cfg_dict["label"] = label
            cfg = SimConfig.from_dict(cfg_dict)

            result = run_from_config(cfg)
            result.metrics = compute_metrics(result)
            results.append(result)

        return results

    def run_and_save(self, base_dir: str = "results") -> Path:
        """运行扫描并保存全部结果、图表、报告到实验目录。

        Args:
            base_dir: 结果根目录

        Returns:
            实验目录路径
        """
        results = self.run()
        exp_dir = self._make_exp_dir(base_dir)

        # 保存数据
        for r in results:
            filename = f"data_{_sanitize_filename(r.label)}.npz"
            self._save_single_result(r, exp_dir, filename)

        # 选择指标并保存
        metric_names = select_metrics(results[0])
        self._save_metrics_csv(results, metric_names, exp_dir)

        # 画图：时域对比
        Visualizer.plot(
            results,
            items=["tracking", "control"],
            title=f"{self.name}: Time Series",
            save_path=str(exp_dir / "timeseries.png"),
        )

        # 画图：指标随参数变化
        Visualizer.plot_metrics_vs_param(
            results,
            param_values=self.values,
            param_name=self.param_path.split(".")[-1],
            metric_names=metric_names,
            title=f"{self.name}: Metrics vs {self.param_path.split('.')[-1]}",
            save_path=str(exp_dir / "metrics.png"),
        )

        # 生成报告
        self._save_report(results, metric_names, exp_dir)

        print(f"Experiment saved to {exp_dir}")
        return exp_dir

    def _make_exp_dir(self, base_dir: str) -> Path:
        """创建实验目录。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        exp_dir = Path(base_dir) / f"{self.name}_{timestamp}"
        exp_dir.mkdir(parents=True, exist_ok=True)
        return exp_dir

    def _save_single_result(self, result: SimResult, exp_dir: Path, filename: str):
        """保存单个结果的 npz 数据。"""
        extra_arrays = {f"extra_{k}": v for k, v in result.extras.items()}
        np.savez(
            exp_dir / filename,
            time=result.time, states=result.states,
            control=result.control, reference=result.reference,
            disturbance=result.disturbance, **extra_arrays,
        )

    def _save_metrics_csv(self, results: list[SimResult], metric_names: list[str], exp_dir: Path):
        """保存指标汇总 CSV。"""
        with open(exp_dir / "metrics.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["label"] + metric_names)
            for r in results:
                row = [r.label] + [r.metrics.get(m, float("nan")) for m in metric_names]
                writer.writerow(row)

    def _save_report(self, results: list[SimResult], metric_names: list[str], exp_dir: Path):
        """生成 Markdown 实验报告。"""
        cfg = self.base_config.to_dict()
        lines = [
            f"# 实验：{self.name}",
            f"",
            f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- 实验类型：ParameterSweep",
            f"- 扫描参数：{self.param_path}",
            f"- 扫描值：{self.values}",
            f"",
            f"## 基础配置",
            f"",
            f"- Plant: {cfg.get('plant_type', 'N/A')}({cfg.get('plant_params', {})})",
            f"- Controller: {cfg.get('controller_type', 'N/A')}({cfg.get('controller_params', {})})",
            f"- Reference: {cfg.get('reference_type', 'None')}({cfg.get('reference_params', {})})",
            f"- Disturbance: {cfg.get('disturbance_type', 'None')}",
            f"- dt={cfg.get('dt', 0.01)}s, t_end={cfg.get('t_end', 10.0)}s",
            f"",
            f"## 性能指标",
            f"",
            f"```",
            format_metrics_table(results, metric_names),
            f"```",
            f"",
            f"## 图表",
            f"",
            f"- timeseries.png: 时域响应对比",
            f"- metrics.png: 性能指标随 {self.param_path.split('.')[-1]} 变化趋势",
            f"",
        ]

        with open(exp_dir / "report.md", "w") as f:
            f.write("\n".join(lines))


class ControllerComparison:
    """多控制器对比实验。

    同一 plant / reference / disturbance 下，对比多个控制器的表现。

    Args:
        name: 实验名称
        configs: 各控制器的 SimConfig 列表
    """

    def __init__(self, name: str, configs: list[SimConfig]):
        self.name = name
        self.configs = configs

    def run(self) -> list[SimResult]:
        """运行对比实验，每个结果自动计算 metrics。"""
        results = []
        for cfg in self.configs:
            result = run_from_config(cfg)
            result.metrics = compute_metrics(result)
            results.append(result)
        return results

    def run_and_save(self, base_dir: str = "results") -> Path:
        """运行对比并保存全部结果、图表、报告。

        Args:
            base_dir: 结果根目录

        Returns:
            实验目录路径
        """
        results = self.run()
        exp_dir = self._make_exp_dir(base_dir)

        # 保存数据
        for r in results:
            filename = f"data_{_sanitize_filename(r.label)}.npz"
            extra_arrays = {f"extra_{k}": v for k, v in r.extras.items()}
            np.savez(
                exp_dir / filename,
                time=r.time, states=r.states,
                control=r.control, reference=r.reference,
                disturbance=r.disturbance, **extra_arrays,
            )

        # 指标
        metric_names = select_metrics(results[0])
        self._save_metrics_csv(results, metric_names, exp_dir)

        # 画图：时域对比
        Visualizer.plot(
            results,
            items=["tracking", "error", "control"],
            title=f"{self.name}: Time Series",
            save_path=str(exp_dir / "timeseries.png"),
        )

        # 画图：指标柱状图
        Visualizer.plot_metrics_bar(
            results,
            metric_names=metric_names,
            title=f"{self.name}: Metrics Comparison",
            save_path=str(exp_dir / "metrics.png"),
        )

        # 报告
        self._save_report(results, metric_names, exp_dir)

        print(f"Experiment saved to {exp_dir}")
        return exp_dir

    def _make_exp_dir(self, base_dir: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        exp_dir = Path(base_dir) / f"{self.name}_{timestamp}"
        exp_dir.mkdir(parents=True, exist_ok=True)
        return exp_dir

    def _save_metrics_csv(self, results: list[SimResult], metric_names: list[str], exp_dir: Path):
        with open(exp_dir / "metrics.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["label"] + metric_names)
            for r in results:
                row = [r.label] + [r.metrics.get(m, float("nan")) for m in metric_names]
                writer.writerow(row)

    def _save_report(self, results: list[SimResult], metric_names: list[str], exp_dir: Path):
        cfg0 = self.configs[0].to_dict()
        ctrl_lines = []
        for c in self.configs:
            cd = c.to_dict()
            ctrl_lines.append(f"  - {cd.get('controller_type', '?')}({cd.get('controller_params', {})})")

        lines = [
            f"# 实验：{self.name}",
            f"",
            f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"- 实验类型：ControllerComparison",
            f"",
            f"## 配置",
            f"",
            f"- Plant: {cfg0.get('plant_type', 'N/A')}({cfg0.get('plant_params', {})})",
            f"- Reference: {cfg0.get('reference_type', 'None')}({cfg0.get('reference_params', {})})",
            f"- Disturbance: {cfg0.get('disturbance_type', 'None')}",
            f"- dt={cfg0.get('dt', 0.01)}s, t_end={cfg0.get('t_end', 10.0)}s",
            f"",
            f"### 对比控制器",
            f"",
            *ctrl_lines,
            f"",
            f"## 性能指标",
            f"",
            f"```",
            format_metrics_table(results, metric_names),
            f"```",
            f"",
            f"## 图表",
            f"",
            f"- timeseries.png: 时域响应对比（tracking + error + control）",
            f"- metrics.png: 性能指标柱状图",
            f"",
        ]

        with open(exp_dir / "report.md", "w") as f:
            f.write("\n".join(lines))
