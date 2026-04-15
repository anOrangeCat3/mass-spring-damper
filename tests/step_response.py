"""阶跃响应验证：从 YAML 配置加载参数，与解析解对比，保存结果。"""

import numpy as np
import sys
sys.path.insert(0, "..")

from msd import SimConfig, run_from_config, MassSpringDamper, Visualizer


def analytical_step_response(plant, amplitude, t):
    """计算质量-弹簧-阻尼器的阶跃响应解析解（零初始条件）。

    Args:
        plant: MassSpringDamper 对象
        amplitude: 阶跃幅值
        t: 时间数组

    Returns:
        (position, velocity) 解析解元组
    """
    wn = plant.natural_frequency
    zeta = plant.damping_ratio
    x_ss = amplitude / plant.k

    if zeta < 1.0:
        wd = wn * np.sqrt(1 - zeta**2)
        position = x_ss * (
            1 - np.exp(-zeta * wn * t) * (
                np.cos(wd * t) + (zeta / np.sqrt(1 - zeta**2)) * np.sin(wd * t)
            )
        )
        velocity = x_ss * np.exp(-zeta * wn * t) * (
            wn / np.sqrt(1 - zeta**2)
        ) * np.sin(wd * t)
    elif zeta == 1.0:
        position = x_ss * (1 - (1 + wn * t) * np.exp(-wn * t))
        velocity = x_ss * wn**2 * t * np.exp(-wn * t)
    else:
        s1 = -wn * (zeta + np.sqrt(zeta**2 - 1))
        s2 = -wn * (zeta - np.sqrt(zeta**2 - 1))
        position = x_ss * (1 + (s1 * np.exp(s2 * t) - s2 * np.exp(s1 * t)) / (s2 - s1))
        velocity = x_ss * s1 * s2 * (np.exp(s2 * t) - np.exp(s1 * t)) / (s2 - s1)

    return position, velocity


def main():
    # 从 YAML 加载配置
    config = SimConfig.from_yaml("configs/step_response.yaml")

    # 运行仿真
    result = run_from_config(config)

    # 打印系统信息
    plant = MassSpringDamper(**config.plant_params)
    print(f"Plant: {plant}")
    print(f"  Natural frequency: {plant.natural_frequency:.4f} rad/s")
    print(f"  Damping ratio:     {plant.damping_ratio:.4f}")

    # 保存配置 + 数据
    result_dir = result.save("../results")

    # 解析解
    amplitude = config.controller_params["amplitude"]
    t_analytical = np.linspace(0, config.t_end, 2000)
    pos_a, vel_a = analytical_step_response(plant, amplitude, t_analytical)
    analytical = {"time": t_analytical, "position": pos_a, "velocity": vel_a}

    # 保存效果图到同一目录
    Visualizer.plot(
        result,
        items=["position", "velocity", "control"],
        title=f"Step Response ({plant})",
        analytical=analytical,
        save_path=str(result_dir / "plot.png"),
    )


if __name__ == "__main__":
    main()
