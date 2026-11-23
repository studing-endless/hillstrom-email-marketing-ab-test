"""Hillstrom 五阶段随机实验。导入模块不会读取数据或执行分析。"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chisquare, t, ttest_ind
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest

ARMS = ("Mens E-Mail", "Womens E-Mail", "No E-Mail")
PAIRS = ((ARMS[0], ARMS[2]), (ARMS[1], ARMS[2]), (ARMS[0], ARMS[1]))
FIELDS = ("recency", "history_segment", "history", "mens", "womens", "zip_code",
          "newbie", "channel", "segment", "visit", "conversion", "spend")


def purchase_groups(df):
    mapping = {(1, 0): "仅买过男装", (0, 1): "仅买过女装", (1, 1): "两类都买过"}
    labels = pd.Series([mapping.get(pair) for pair in zip(df["mens"], df["womens"])],
                       index=df.index, name="purchase_group")
    if labels.isna().any():
        raise ValueError("历史购买品类存在未覆盖的组合")
    return labels


def validate_data(df):
    """报告异常并停止，保留全部原始记录。"""
    if df.empty or set(df.columns) != set(FIELDS) or len(df.columns) != 12:
        raise ValueError("数据必须非空且恰含 12 个原始字段")
    if df.isna().any().any():
        raise ValueError("存在缺失值：" + str(df.isna().sum().loc[lambda x: x > 0].to_dict()))
    if set(df["segment"]) != set(ARMS):
        raise ValueError("segment 必须包含且只包含三个合法实验组")
    for field in ("visit", "conversion", "mens", "womens", "newbie"):
        if not df[field].isin([0, 1]).all():
            raise ValueError(f"{field} 必须为 0/1")
    for field in ("history", "recency", "spend"):
        if not pd.api.types.is_numeric_dtype(df[field]) or not np.isfinite(df[field]).all():
            raise ValueError(f"{field} 必须为有限数值")
        if (df[field] < 0).any():
            raise ValueError(f"{field} 含负数")
    if ((df["conversion"] == 1) != (df["spend"] > 0)).any():
        raise ValueError("conversion 与 spend>0 不一致")
    for field in ("channel", "zip_code", "history_segment"):
        if df[field].astype(str).str.strip().eq("").any():
            raise ValueError(f"{field} 存在空分类")
    groups = purchase_groups(df)
    required_levels = {
        "purchase_group": (groups, {"仅买过男装", "仅买过女装", "两类都买过"}),
        "newbie": (df["newbie"], {0, 1}),
        "channel": (df["channel"], {"Phone", "Web", "Multichannel"}),
    }
    for feature, (values, expected) in required_levels.items():
        if set(values) != expected:
            raise ValueError(f"{feature} 缺少必要分群或包含未知类别")
    return df


def load_data(path):
    return validate_data(pd.read_csv(path))


def srm_test(df):
    counts = df["segment"].value_counts().reindex(ARMS, fill_value=0)
    if df.empty or not df["segment"].isin(ARMS).all():
        raise ValueError("SRM 需要非空且合法的实验分配")
    expected = np.repeat(len(df) / 3, 3)
    test = chisquare(counts.to_numpy(), f_exp=expected)
    return pd.DataFrame({"observed": counts, "expected": expected}), float(test.statistic), float(test.pvalue)


def business_metrics(df):
    if df.empty or set(df["segment"]) != set(ARMS):
        raise ValueError("业务指标需要三个非空实验组")
    table = df.groupby("segment").agg(
        n=("spend", "size"), visitors=("visit", "sum"), visit_rate=("visit", "mean"),
        buyers=("conversion", "sum"), conversion_rate=("conversion", "mean"),
        revenue=("spend", "sum"), rpc=("spend", "mean"))
    table["buyer_spend"] = table["revenue"] / table["buyers"].replace(0, np.nan)
    table["uplift"] = table["rpc"] - table.loc["No E-Mail", "rpc"]
    return table


def holm(pvalues):
    values = np.asarray(pvalues, dtype=float)
    if values.size == 0 or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Holm 需要非空且位于 [0,1] 的有限 P 值")
    return multipletests(values, method="holm")[1]


def welch_result(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if min(a.size, b.size) < 2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Welch 每组至少需要两个有限观测")
    va, vb = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    variance = va + vb
    if variance == 0:
        raise ValueError("Welch 总方差为零，无法推断")
    degrees = variance**2 / (va**2 / (a.size - 1) + vb**2 / (b.size - 1))
    diff = a.mean() - b.mean()
    width = t.ppf(0.975, degrees) * np.sqrt(variance)
    return dict(diff=float(diff), low=float(diff - width), high=float(diff + width),
                p=float(ttest_ind(a, b, equal_var=False).pvalue))


def welch_interval(a, b):
    result = welch_result(a, b)
    return result["low"], result["high"]


def proportion_result(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if min(a.size, b.size) == 0 or not np.isin(a, [0, 1]).all() or not np.isin(b, [0, 1]).all():
        raise ValueError("比例比较需要非空二元观测")
    if a.sum() + b.sum() in (0, a.size + b.size):
        raise ValueError("合并比例为 0 或 1，Z 检验无法推断")
    low, high = confint_proportions_2indep(a.sum(), a.size, b.sum(), b.size,
                                         compare="diff", method="newcomb")
    return dict(diff=float(a.mean() - b.mean()), low=float(low), high=float(high),
                p=float(proportions_ztest([a.sum(), b.sum()], [a.size, b.size])[1]))


def comparisons(df):
    rows = []
    for metric in ("visit", "conversion", "spend"):
        for arm_a, arm_b in PAIRS:
            a = df.loc[df["segment"] == arm_a, metric]
            b = df.loc[df["segment"] == arm_b, metric]
            result = welch_result(a, b) if metric == "spend" else proportion_result(a, b)
            rows.append(dict(metric=metric, comparison=f"{arm_a} vs {arm_b}", **result))
    table = pd.DataFrame(rows)
    table["holm_metric"] = table.groupby("metric")["p"].transform(holm)
    table["holm_nine"] = holm(table["p"])
    return table


def bootstrap_rpc(df, repetitions=3000, seed=42):
    """保持历史逐对逐次的抽样顺序，与新增敏感性分析使用独立随机流。"""
    rng = np.random.default_rng(seed)
    rows = []
    for arm_a, arm_b in PAIRS:
        a = df.loc[df["segment"] == arm_a, "spend"].to_numpy()
        b = df.loc[df["segment"] == arm_b, "spend"].to_numpy()
        draws = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean()
                 for _ in range(repetitions)]
        low, high = np.percentile(draws, [2.5, 97.5])
        rows.append(dict(comparison=f"{arm_a} vs {arm_b}", low=low, high=high))
    return pd.DataFrame(rows)


def cell_values(df, feature, minimum=2):
    cells = {}
    if df.empty or df[feature].isna().any():
        raise ValueError(f"{feature} 分群为空或缺失")
    for group in sorted(df[feature].unique()):
        for arm in ARMS:
            values = df.loc[(df[feature] == group) & (df["segment"] == arm), "spend"].to_numpy()
            if len(values) < minimum:
                raise ValueError(f"{feature}={group}, {arm} 单元格至少需要 {minimum} 人")
            cells[group, arm] = values
    return cells


def interaction_test(df, feature, emails_only=False):
    cell_values(df, feature)
    data = df[df["segment"].isin(ARMS[:2])] if emails_only else df
    model = smf.ols(f"spend ~ C(segment) * C({feature})", data=data).fit(cov_type="HC3")
    row = model.wald_test_terms(scalar=True).table.loc[f"C(segment):C({feature})"]
    return float(row["pvalue"])


def select_policies(train):
    cell_values(train, "purchase_group")
    means = train.groupby(["purchase_group", "segment"])["spend"].mean().unstack()
    return train.groupby("segment")["spend"].mean().idxmax(), means.idxmax(axis=1)


def evaluate_policies(valid, strategy_a, strategy_b):
    """固定群体权重；独立单元格均值的加权方差及 Satterthwaite 近似。"""
    cells = cell_values(valid, "purchase_group")
    weights = valid["purchase_group"].value_counts(normalize=True)
    if strategy_a not in ARMS or set(strategy_b.index) != set(weights.index) or not strategy_b.isin(ARMS).all():
        raise ValueError("策略须覆盖全部验证群体并选择合法方案")
    value_a = sum(weights[g] * cells[g, strategy_a].mean() for g in weights.index)
    value_b = sum(weights[g] * cells[g, strategy_b[g]].mean() for g in weights.index)
    terms, denominator = [], 0.0
    for group, weight in weights.items():
        if strategy_b[group] == strategy_a:
            continue
        for arm in (strategy_b[group], strategy_a):
            values = cells[group, arm]
            term = weight**2 * values.var(ddof=1) / len(values)
            terms.append(term)
            denominator += term**2 / (len(values) - 1)
    diff = value_b - value_a
    variance = sum(terms)
    if not terms:
        return dict(value_a=float(value_a), value_b=float(value_b), diff=0.0, low=0.0, high=0.0, p=None)
    if variance == 0:
        raise ValueError("策略差异总方差为零，无法推断")
    degrees = variance**2 / denominator
    width = t.ppf(0.975, degrees) * np.sqrt(variance)
    return dict(value_a=float(value_a), value_b=float(value_b), diff=float(diff),
                low=float(diff - width), high=float(diff + width),
                p=float(2 * t.sf(abs(diff) / np.sqrt(variance), degrees)))


def diagnostics(df, feature):
    return df.groupby([feature, "segment"])["spend"].agg(
        n="size", nonzero=lambda x: (x > 0).sum(), nonzero_rate=lambda x: (x > 0).mean(),
        mean="mean", skew="skew", p99=lambda x: x.quantile(0.99), maximum="max")


def bootstrap_interactions(df, repetitions=3000, seed=42):
    """分层估计两邮件效果差的群体间差值，单项区间不充当整体交互检验。"""
    rng = np.random.default_rng(seed)
    rows = []
    for feature in ("purchase_group", "newbie", "channel"):
        cells = cell_values(df, feature)
        groups = sorted(df[feature].unique())
        reference = groups[0]
        effects = {}
        for group in groups:
            a, b = cells[group, ARMS[0]], cells[group, ARMS[1]]
            effects[group] = np.array([
                rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean()
                for _ in range(repetitions)])
        for group in groups[1:]:
            point = (cells[group, ARMS[0]].mean() - cells[group, ARMS[1]].mean()
                     - cells[reference, ARMS[0]].mean() + cells[reference, ARMS[1]].mean())
            low, high = np.percentile(effects[group] - effects[reference], [2.5, 97.5])
            rows.append(dict(feature=feature, group=str(group), reference=str(reference),
                             diff=point, low=low, high=high))
    return pd.DataFrame(rows)


def run_analysis(df, repetitions=3000):
    validate_data(df)
    data = df.copy()
    data["purchase_group"] = purchase_groups(data)
    print("\n阶段 1｜数据质量、SRM 与描述性基线")
    counts, statistic, pvalue = srm_test(data)
    print(counts.to_string())
    print(f"SRM chi2={statistic:.9f}, p={pvalue:.9f}")
    print(data.groupby("segment")[["history", "recency", "newbie", "mens", "womens"]].mean())
    for feature in ("history_segment", "channel", "zip_code"):
        print(pd.crosstab(data["segment"], data[feature], normalize="index").to_string())
    print("\n阶段 2｜业务指标（金额为美元，比例为 0–1）")
    metrics = business_metrics(data)
    print(metrics.to_string())
    print("\n阶段 3｜双侧比较、单项 95% CI 与 Holm")
    tests = comparisons(data)
    print(tests.to_string(index=False))
    bootstrap = bootstrap_rpc(data, repetitions)
    print(bootstrap.to_string(index=False))
    print("\n阶段 4｜10 万客户假设情景；成本、毛益均为假设")
    scenarios = []
    for arm in ARMS[:2]:
        uplift = metrics.loc[arm, "uplift"]
        ci = tests.loc[(tests.metric == "spend") & (tests.comparison == f"{arm} vs No E-Mail")].iloc[0]
        print(arm, "增量销售额", uplift * 100000, "30% 毛益盈亏平衡成本", uplift * 0.3)
        for margin in (0.2, 0.3, 0.4):
            for cost in (0.1, 0.2):
                scenarios.append(dict(arm=arm, margin=margin, cost=cost,
                                      per_customer=uplift * margin - cost,
                                      profit=(uplift * margin - cost) * 100000,
                                      low=(ci.low * margin - cost) * 100000,
                                      high=(ci.high * margin - cost) * 100000))
    print(pd.DataFrame(scenarios).to_string(index=False))
    print("\n阶段 5｜历史品类与探索性策略；5.5 新老客户、历史渠道")
    interactions = {}
    for feature in ("purchase_group", "newbie", "channel"):
        print(feature)
        print(diagnostics(data, feature).to_string())
        means = data.groupby([feature, "segment"])["spend"].mean().unstack()
        print(means.to_string())
        print(means.loc[:, list(ARMS[:2])].sub(means["No E-Mail"], axis=0).to_string())
        interactions[feature] = interaction_test(data, feature)
    interactions["emails"] = interaction_test(data, "purchase_group", emails_only=True)
    print("HC3 原始 P", interactions)
    print("5.5 两项 Holm", holm([interactions["newbie"], interactions["channel"]]))
    train = data.sample(frac=0.7, random_state=42)
    valid = data.drop(train.index)
    strategy_a, strategy_b = select_policies(train)
    print("训练总体 RPC", train.groupby("segment")["spend"].mean().to_dict())
    print("训练群体 RPC", train.groupby(["purchase_group", "segment"])["spend"].mean().unstack())
    print("验证群体 RPC", valid.groupby(["purchase_group", "segment"])["spend"].mean().unstack())
    print("验证权重", valid["purchase_group"].value_counts(normalize=True))
    policy = evaluate_policies(valid, strategy_a, strategy_b)
    print("A", strategy_a, "B", strategy_b.to_dict(), "验证结果", policy)
    sensitivity = bootstrap_interactions(data, repetitions)
    print("分层 Bootstrap 单项敏感性区间")
    print(sensitivity.to_string(index=False))
    return dict(n=len(data), counts=counts["observed"].to_dict(), rpc=metrics["rpc"].to_dict(),
                p_all=interactions["purchase_group"], p_emails=interactions["emails"],
                policy_difference=policy["diff"], policy_p=policy["p"],
                p_newbie=interactions["newbie"], p_channel=interactions["channel"],
                srm=dict(statistic=statistic, p=pvalue),
                bootstrap_rpc=bootstrap.to_dict("records"),
                sensitivity=sensitivity.to_dict("records"))


def main():
    parser = argparse.ArgumentParser(description="复现 Hillstrom 五阶段邮件实验")
    parser.add_argument("csv", nargs="?", type=Path, default=Path(__file__).resolve().parent / "data/hillstrom.csv")
    parser.add_argument("--output-json", type=Path, help="可选本地机器可读验证结果")
    args = parser.parse_args()
    result = run_analysis(load_data(args.csv))
    if args.output_json:
        args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
