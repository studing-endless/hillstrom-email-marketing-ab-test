"""从原始 CSV 复用正式分析函数生成两张展示图，不执行 Bootstrap。"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
import numpy as np

from analysis import ARMS, business_metrics, comparisons, load_data, profit_scenarios


def configure_style():
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = ("Microsoft YaHei", "SimHei", "PingFang SC", "Heiti SC",
                  "Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei")
    selected = next((name for name in candidates if name in available), None)
    if selected is None:
        raise RuntimeError("需要中文字体。请安装 Noto Sans CJK SC 后重新运行绘图。")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [selected],
        "axes.unicode_minus": False, "font.size": 11,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#cbd2d8", "text.color": "#263746",
        "axes.labelcolor": "#263746", "xtick.color": "#52616b",
        "ytick.color": "#263746", "savefig.facecolor": "white",
    })
    return selected


def plot_rpc(table, path):
    rpc = table.loc[table["metric"] == "spend"].reset_index(drop=True)
    labels = ["男装邮件 − 不发邮件", "女装邮件 − 不发邮件", "男装邮件 − 女装邮件"]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    fig.subplots_adjust(left=0.25, right=0.66, top=0.76, bottom=0.24)
    fig.text(0.06, 0.91, "邮件是否带来额外收入", fontsize=17, weight="bold")
    fig.text(0.06, 0.83, "点估计与 Welch 单项 95% 置信区间", fontsize=11)
    for index, row in rpc.iterrows():
        y = 2 - index
        ax.errorbar(row["diff"], y,
                    xerr=[[row["diff"] - row["low"]], [row["high"] - row["diff"]]],
                    fmt="o", color=("#326482", "#4f8178", "#6d7180")[index],
                    markersize=7, capsize=5, linewidth=2)
        ax.text(1.04, y, f'{row["diff"]:+.4f}  [{row["low"]:.4f}, {row["high"]:.4f}]',
                transform=ax.get_yaxis_transform(), va="center", fontsize=10)
    ax.axvline(0, color="#6b7280", linestyle="--", linewidth=1)
    ax.set(yticks=[2, 1, 0], yticklabels=labels, ylim=(-0.5, 2.5), xlim=(-0.1, 1.15),
           xlabel="人均增量销售额（美元/客户）")
    ax.set_xticks(np.arange(0, 1.2, 0.2))
    ax.grid(axis="x", color="#e5e9ec")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=12)
    fig.text(0.06, 0.06, "区间未作同时覆盖校正；第三项直接比较两封邮件。", fontsize=10, color="#52616b")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def plot_profit(scenarios, path):
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.subplots_adjust(left=0.10, right=0.80, top=0.72, bottom=0.26, wspace=0.36)
    fig.text(0.06, 0.92, "额外销售能否覆盖营销成本", fontsize=17, weight="bold")
    fig.text(0.06, 0.84, "假设 10 万名可比客户 · 增量利润点估计（美元）", fontsize=11)
    limit = float(scenarios["profit"].abs().max())
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    cmap = LinearSegmentedColormap.from_list("profit", ["#b76e64", "#f7f8f8", "#4a8079"])
    for ax, arm, title in zip(axes, ARMS[:2], ["男装邮件", "女装邮件"]):
        values = scenarios.loc[scenarios["arm"] == arm].pivot(
            index="margin", columns="cost", values="profit")
        image = ax.imshow(values.to_numpy(), cmap=cmap, norm=norm, aspect="auto")
        ax.set(title=title, xticks=[0, 1], xticklabels=["$0.10", "$0.20"],
               yticks=[0, 1, 2], yticklabels=["20%", "30%", "40%"],
               xlabel="假设每客邮件成本（美元）")
        for (row, col), value in np.ndenumerate(values.to_numpy()):
            color = "white" if abs(value) > limit * 0.65 else "#263746"
            ax.text(col, row, f"{value:+,.2f}", ha="center", va="center", color=color, fontsize=11)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    axes[0].set_ylabel("假设贡献毛益率")
    color_ax = fig.add_axes([0.85, 0.26, 0.025, 0.46])
    fig.colorbar(image, cax=color_ax, label="增量利润（美元）")
    fig.text(0.06, 0.07, "颜色表示利润点估计，统计不确定性见完整报告。", fontsize=10, color="#52616b")
    fig.savefig(path, dpi=200)
    plt.close(fig)


def generate_figures(df, output_dir):
    font = configure_style()
    table = comparisons(df)
    scenarios = profit_scenarios(business_metrics(df), table)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_rpc(table, output_dir / "rpc_uplift_ci.png")
    plot_profit(scenarios, output_dir / "profit_sensitivity.png")
    return table, scenarios, font


def main():
    parser = argparse.ArgumentParser(description="生成 Hillstrom 两张核心分析图")
    parser.add_argument("csv", nargs="?", type=Path,
                        default=Path(__file__).resolve().parent / "data/hillstrom.csv")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "figures")
    args = parser.parse_args()
    table, scenarios, font = generate_figures(load_data(args.csv), args.output_dir)
    print("中文字体", font)
    print(table.loc[table.metric == "spend"].to_string(index=False))
    print(scenarios[["arm", "margin", "cost", "profit"]].to_string(index=False))
    print("PNG 已保存到", args.output_dir)


if __name__ == "__main__":
    main()
