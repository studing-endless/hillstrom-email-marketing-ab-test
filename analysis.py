import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import t, ttest_ind
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest

def welch_interval(a, b):
    """计算双侧 95% Welch–Satterthwaite 均值差区间。"""
    variance_a = a.var(ddof=1) / len(a)
    variance_b = b.var(ddof=1) / len(b)
    variance = variance_a + variance_b
    df = variance**2 / (
        variance_a**2 / (len(a) - 1) + variance_b**2 / (len(b) - 1)
    )
    half_width = t.ppf(0.975, df) * np.sqrt(variance)
    difference = a.mean() - b.mean()
    return difference - half_width, difference + half_width

parser = argparse.ArgumentParser(description="复现 Hillstrom 邮件实验分析")
parser.add_argument("csv", nargs="?", type=Path, default=Path(__file__).resolve().parent / "data" / "hillstrom.csv")
df = pd.read_csv(parser.parse_args().csv)
print(df.shape)

# 阶段 1｜数据质量与随机分组

# 1.1 数据质量：字段类型和缺失情况
# 1. 查看数据基本信息和每一列的数据类型
df.info()
print(df.isna().sum())

# 统计三个实验组各有多少名客户
print(df["segment"].value_counts())
# 计算每个实验组占总客户数的百分比
print(df["segment"].value_counts(normalize=True) * 100)

# 1.2 随机分组平衡描述：干预前的历史消费、购买偏好、地区和渠道等
#三个实验组的客户，在收到邮件之前，历史消费水平是否接近？
print(df.groupby("segment")["history"].mean().round(2))

# 计算三个实验组的平均最近购买间隔（月）
print(df.groupby("segment")["recency"].mean().round(2))

# 计算每个实验组的新客户占比（百分数）
print((df.groupby("segment")["newbie"].mean() * 100).round(2))

# 查看三个实验组的历史购买渠道分布
print(pd.crosstab(df["segment"],df["channel"]))

# 查看各实验组内部的购买渠道占比（%）
#示按照交叉表的每一行计算比例  normalize="index"
print(
    (pd.crosstab(df["segment"], df["channel"], normalize="index") * 100).round(2)
)

# 各实验组过去购买过男装的客户占比
print((df.groupby("segment")["mens"].mean() * 100).round(2))
print((df.groupby("segment")["womens"].mean() * 100).round(2))

print(
    (pd.crosstab(df['segment'], df['zip_code'],normalize = "index") * 100).round(2)
)

print(
    (pd.crosstab(df["segment"], df["history_segment"], normalize="index") * 100).round(2)
)

# 阶段 2｜营销业务指标：访问率、转化率、销售额和 RPC

# 2.1 网站访问指标

print(df.groupby("segment")["visit"].sum())
# 各实验组的网站访问率（百分比）
print((df.groupby("segment")["visit"].mean() * 100).round(2))

# 2.2 购买转化指标
print(df.groupby("segment")["conversion"].sum())
print((df.groupby("segment")["conversion"].mean() * 100).round(2))

# 2.3 销售额、RPC、付费客户平均消费

print(df.groupby("segment")["spend"].sum().round(2))
# 2. 计算三个实验组的客户平均消费金额
print(df.groupby("segment")["spend"].mean().round(2))

# 筛选实验后实际购买过商品的客户
buyers = df[df["conversion"] == 1]
# 计算三个实验组中购买客户的平均消费额
print(buyers.groupby("segment")["spend"].mean().round(2))

# 计算每组的客户平均销售额
rpc = df.groupby("segment")["spend"].mean()
# 取出不发邮件组的人均销售额
control_rpc = rpc["No E-Mail"]
print((rpc - control_rpc).round(4))

# 阶段 3｜统计推断：比例检验、均值检验、置信区间和多重比较

# 3.1 访问率：三组两两比例 Z 检验 + Newcombe 区间 + Holm 校正

#proportions_ztest()：比较两个独立样本的比例是否存在统计差异。
#confint_proportions_2indep()：计算两个独立比例之差的置信区间。

# 1. 取出男装邮件组和对照组
mens = df[df["segment"] == "Mens E-Mail"]
control = df[df["segment"] == "No E-Mail"]

# 2. 统计访问人数和总人数
x1 = mens["visit"].sum()
n1=len(mens)

x0 = control["visit"].sum()
n0 = len(control)

# 3. 双样本比例 Z 检验
z_stat,p_value = proportions_ztest(
    [x1,x0],[n1, n0],
    alternative="two-sided"
)

# 4. 计算比例差异的 95% 置信区间
low, high = confint_proportions_2indep(
    x1, n1, x0, n0,
    compare="diff",
    method="newcomb"
)

print("访问率差异：",round((x1/n1 - x0/n0)*100,2))
print("P值: ",p_value)
print("95%置信区间：",round(low*100, 2),round(high*100, 2))

womens = df[df["segment"] == "Womens E-Mail"]

x_w = womens["visit"].sum()
n_w = len(womens)
x_c = control["visit"].sum()
n_c = len(control)

z_w, p_w = proportions_ztest(
    [x_w, x_c], [n_w,n_c],
    alternative="two-sided"
)

low_w, high_w = confint_proportions_2indep(
    x_w, n_w, x_c, n_c,
    compare="diff",
    method="newcomb"
)

print("访问率差异：",round((x_w/n_w - x_c/n_c)*100, 2))
print("P 值：",p_w)
print("95%置信区间：",round(low_w*100,2), round(high_w*100,2))

# 第三次比较：男装邮件 vs 女装邮件
# 统计男装邮件组的访问人数和总人数
x_m = mens["visit"].sum()
n_m = len(mens)

# 进行双侧比例 Z 检验
z_mw,p_mw = proportions_ztest(
    [x_m,x_w],[n_m,n_w],
    alternative = "two-sided"
)

low_mw, high_mw = confint_proportions_2indep(
    x_m, n_m,x_w,n_w,
    compare = "diff",
    method = "newcomb"
)

print("访问率差异：",round((x_m/n_m - x_w/n_w)*100, 2))
print("P值:",p_mw)
print("95%置信区间：",round(low_mw*100,2),round(high_mw*100,2))

#当我们同时检验多个假设时，不能忽视反复寻找显著差异所带来的假阳性风险。

p_values = [p_value, p_w,p_mw]

# Holm 多重比较校正
#这个函数会返回四个结果，我们当前只需要前两个。
#- reject：每个检验是否拒绝原假设，True 表示拒绝。
#- p_adjusted：经过 Holm 校正后的 P 值。
reject, p_adjusted, _, _ = multipletests(
    p_values,
    alpha = 0.05,
    method = "holm"
)

print("校正后的P值：",p_adjusted)
print("是否拒绝原假设：", reject)

# 3.2 转化率：三组两两比例 Z 检验 + Newcombe 区间 + Holm 校正

# 1. 定义需要比较的三个组别组合
pairs = [
    ("Mens E-Mail", "No E-Mail"),
    ("Womens E-Mail","No E-Mail"),
    ("Mens E-Mail","Womens E-Mail")
]

results = []

# 2. 循环进行三次检验
for group1, group2 in pairs:

    a = df[df["segment"] == group1]["conversion"]
    b = df[df["segment"] == group2]["conversion"]

    x1, n1 = a.sum(), len(a)
    x2, n2 = b.sum(), len(b)

    z, p = proportions_ztest(
        [x1,x2], [n1,n2],
        alternative = "two-sided"
    )

    lower, upper = confint_proportions_2indep(
        x1, n1, x2, n2,
        compare = "diff",
        method = "newcomb"
    )

    results.append([
        f"{group1} vs {group2}",
        (x1/n1 - x2/n2) * 100,
        lower *100,
        upper *100,
        p
    ])

summary = pd.DataFrame(
    results,
    columns=["比较", "差异(pp)", "95%下限(pp)", "95%上限(pp)", "原始P"]
)

# 4. 对转化率的三个比较统一做 Holm 校正
#从函数返回的多个结果中，取出第 2 个结果( 校正后的 P 值。
summary["Holm校正P"] = multipletests(
    summary["原始P"],
    method="holm"
)[1]
summary["校正后显著"] = summary["Holm校正P"] < 0.05
print("\n转化率三组两两比较：")
print(summary.to_string(index=False))

# 3.3 RPC：Welch t 检验 + 均值差置信区间 + Holm 校正

pairs = [
    ("Mens E-Mail", "No E-Mail"),
    ("Womens E-Mail", "No E-Mail"),
    ("Mens E-Mail", "Womens E-Mail")
]

results = []
for group1, group2 in pairs:
    a = df[df["segment"] == group1]["spend"]
    b = df[df["segment"] == group2]["spend"]

    #Welch t检验
    test = ttest_ind(a, b, equal_var = False)

    # 均值差异的95%置信区间
    ci_low, ci_high = welch_interval(a, b)

    results.append([
        f"{group1} vs {group2}",
        a.mean() - b.mean(),
        ci_low,
        ci_high,
        test.pvalue
    ])

# 3. 整理结果
summary = pd.DataFrame(
    results,
    columns=["比较", "人均差异", "CI下限", "CI上限", "原始P"]
)

# 4. Holm校正
summary["Holm校正P"] = multipletests(
    summary["原始P"],
    method="holm"
)[1]

summary["是否显著"] = summary["Holm校正P"] < 0.05

print(summary.to_string(index=False))

# 3.4 RPC：Bootstrap 百分位置信区间（每次重抽样 3000 次）
# 设置随机种子，保证结果可复现  建一个随机数生成器
rng = np.random.default_rng(42)

pairs = [
    ("Mens E-Mail", "No E-Mail"),
    ("Womens E-Mail", "No E-Mail"),
    ("Mens E-Mail", "Womens E-Mail")
]

for group1, group2 in pairs:
    a = df[df["segment"] == group1]["spend"].to_numpy()
    b = df[df["segment"] == group2]["spend"].to_numpy()

    diffs = []
    for _ in range(3000):
        #从 a 中有放回抽样，抽取与原来相同数量的记录
         sample_a = rng.choice(a, size = len(a), replace = True)
         sample_b = rng.choice(b, size = len(b), replace = True)

         diff = sample_a.mean() - sample_b.mean()
         diffs.append(diff)

    # 计算95% Bootstrap置信区间
    low, high = np.percentile(diffs, [2.5, 97.5])
    print(f"\n{group1} vs {group2}")
    print(f"均值差：{a.mean() - b.mean():.4f}")
    print(f"Bootstrap 95% CI: [{low:.4f}, {high:.4f}]")

# 3.5 汇总访问率/转化率/RPC 共 9 个比较，并统一 Holm 校正

# 三个指标
metrics = ["visit", "conversion", "spend"]

# 三组比较
pairs = [
    ("Mens E-Mail", "No E-Mail"),
    ("Womens E-Mail", "No E-Mail"),
    ("Mens E-Mail", "Womens E-Mail")
]

results = []
for metric in metrics:
    for group1, group2 in pairs:
        a = df[df["segment"] == group1][metric]
        b = df[df["segment"] == group2][metric]

        if metric in ["visit", "conversion"]:
             # 二分类指标：比例Z检验
             _, p = proportions_ztest(
                 [a.sum(), b.sum()],[len(a), len(b)]
             )

             diff = (a.mean() - b.mean()) * 100
        else:
             # 消费金额：Welch t检验
             p = ttest_ind(a, b, equal_var = False).pvalue
             diff = a.mean() - b.mean()

        results.append([
            metric, f"{group1} vs {group2}", diff, p
        ])

# 整理九次比较结果
report = pd.DataFrame(
    results,
    columns=["指标", "比较", "差异", "原始P"]
)

# 对九个P值统一进行Holm校正
reject, p_adjusted, _, _ = multipletests(
    report["原始P"],
    alpha = 0.05,
    method = "holm"
)

report["Holm校正P"] = p_adjusted
report["是否显著"] = reject
print(report.to_string(index=False))

# 阶段 4｜营销经济价值：增量收入、假设利润、盈亏平衡与敏感性分析

# 4.1 增量销售额：将人均 uplift 外推到假设的 10 万客户
# 1. 计算三个组的客户平均销售额
rpc = df.groupby("segment")["spend"].mean()

# 2. 获取对照组的人均销售额
control_rpc = rpc["No E-Mail"]

# 3. 假设未来投放10万名客户
target_n = 100000

# 4. 分别估计两种邮件方案的增量销售额
for group in ["Mens E-Mail", "Womens E-Mail"]:
    ## 增量提升。
    uplift = rpc[group] - control_rpc
    incremental_revenue = uplift * target_n

    print(f"{group}")
    print(f"每名客户增量销售额：${uplift:.4f}")

    #,：显示千位分隔符   .2f：保留小数点后两位。
    print(f"10万名客户预计增量销售额：${incremental_revenue:,.2f}")

# 4.2 基础利润情景与盈亏平衡成本
margin = 0.30
cost_per_customer = 0.10
# 3. 分别计算两种邮件方案的经济效果
for group in ["Mens E-Mail", "Womens E-Mail"]:
    uplift = rpc[group] - control_rpc

    # 每名客户的增量利润
    profit_per_customer = uplift * margin - cost_per_customer

    # 总增量利润
    total_profit = profit_per_customer * target_n

    # 盈亏平衡时允许的最高营销成本
    break_even_cost = uplift * margin

    print(f"\n方案：{group}")
    print(f"人均增量利润：${profit_per_customer:.4f}")
    print(f"10万客户增量利润：${total_profit:,.2f}")
    print(f"盈亏平衡营销成本：${break_even_cost:.4f}")

# 4.3 多种毛益率和单位营销成本的敏感性分析
## 1. 计算两种邮件的人均增量销售额
rpc = df.groupby("segment")["spend"].mean()

uplift_m = rpc["Mens E-Mail"] - rpc["No E-Mail"]
uplift_w = rpc["Womens E-Mail"] - rpc["No E-Mail"]

# 2. 设置假设条件
margins = [0.20, 0.30, 0.40]
costs = [0.10, 0.20]
target_n = 100000

results = []

# 3. 遍历不同的成本情景
for margin in margins:
    for cost in costs:
        profit_m = (uplift_m * margin - cost) * target_n
        profit_w = (uplift_w * margin - cost) * target_n
        results.append([
                   f"{margin:.0%}", cost,
                   round(profit_m, 2),
                   round(profit_w, 2)
               ])

scenario_df = pd.DataFrame(
    results,
    columns=["毛益率", "单位营销成本", "男装利润", "女装利润"]
)

print(scenario_df.to_string(index=False))

# 1. 对照组的消费数据
control = df[df["segment"] == "No E-Mail"]["spend"]

# 2. 设定假设条件
margin = 0.30
target_n = 100000
costs = [0.10, 0.20]

# 3. 分别分析两种邮件方案
for group in ["Mens E-Mail", "Womens E-Mail"]:

    a = df[df["segment"] == group]["spend"]

    # 计算人均增量销售额
    uplift = a.mean() - control.mean()

    # Welch均值差的95%置信区间
    ci_low, ci_high = welch_interval(a, control)

    for cost in costs:

        # 利润点估计
        profit = (uplift * margin - cost) * target_n

        # 利润置信区间
        low = (ci_low * margin - cost) * target_n
        high = (ci_high * margin - cost) * target_n

        print(f"\n方案：{group}，成本：${cost}")
        print(f"预计利润：${profit:,.2f}")
        print(f"95%区间：[${low:,.2f}, ${high:,.2f}]")

# 阶段 5｜客户分群、异质性检验与探索性营销策略评价
# 注意：
# 本阶段属于探索性策略评价。
# 因为此前已经分析过全量数据，
# 当前验证集不构成完全独立的确认性验证。
# 不应据此宣称分群策略具有稳定的因果增益。
# 5.1 定义历史购买品类分群并检查样本数

# 1. 定义三种客户分群条件
conditions = [
    (df["mens"] == 1) & (df["womens"] == 0),
    (df["mens"] == 0) & (df["womens"] == 1),
    (df["mens"] == 1) & (df["womens"] == 1)
]

# 2. 定义对应的客户群体名称
labels = ["仅买过男装", "仅买过女装", "两类都买过"]

# 3. 给每个客户添加分群标签  pandas 数据表增加一列。
df["purchase_group"] = np.select(
    conditions,labels,default="待检查"
)

# 4. 统计各群体人数
print(df["purchase_group"].value_counts())

# 5. 检查各群体在三个实验组中的人数
print(pd.crosstab(df["purchase_group"],df["segment"]))

# 5.2 分群平均销售额与相对不发邮件的增量
# 1. 按客户分群和实验组计算平均销售额
avg_spend = df.groupby(["purchase_group", "segment"])["spend"].mean().unstack()

print("各组客户平均销售额：")
print(avg_spend.round(4))

# 2. 计算各分群内的增量销售额
uplift = pd.DataFrame({
     "男装邮件增量": avg_spend["Mens E-Mail"] - avg_spend["No E-Mail"],
      "女装邮件增量": avg_spend["Womens E-Mail"] - avg_spend["No E-Mail"]
})

print("\n各客户群体的增量销售额：")
print(uplift.round(4))

# 5.3 交互效应：检验邮件效果是否随客户历史购买群体而变化
# 1. 定义包含交互效应的统计模型
formula = "spend ~ C(segment) * C(purchase_group)"

# 2. 检验三种营销方案的整体交互效应
model_all = smf.ols(formula, data = df).fit(cov_type = "HC3")
table_all = model_all.wald_test_terms(scalar=True).table

print("三种营销方案的整体交互检验：")
print(table_all.loc["C(segment):C(purchase_group)"])

# 3. 只比较男装邮件与女装邮件
emails = df[df["segment"].isin(["Mens E-Mail", "Womens E-Mail"])]
model_emails = smf.ols(formula, data=emails).fit(cov_type="HC3")
table_emails = model_emails.wald_test_terms(scalar=True).table
print("\n男装邮件 vs 女装邮件的交互检验：")
print(table_emails.loc["C(segment):C(purchase_group)"])

# 5.4 统一策略 A 与分群策略 B 的探索性离线比较
# A：训练集总体 RPC 最高的一种实验方案，全体客户采用同一选择。
# B：训练集中按历史购买群体分别挑选 RPC 最高的实验方案。

# 1. 划分训练集与验证集
train = df.sample(frac = 0.7,random_state = 42)

##排除训练集中的行，剩下的作为验证集
valid = df.drop(train.index)

# 2. 策略A：从训练集选出最好的统一营销方案
train_overall = train.groupby("segment")["spend"].mean()
strategy_a = train_overall.idxmax()
print("训练集各邮件方案的总体人均销售额：")
print(train_overall)
print("策略A选择：", strategy_a)

# 3. 策略B：从同一训练集为每类客户选择方案
train_mean = train.groupby(
    ["purchase_group","segment"]
)["spend"].mean().unstack()

strategy_b = train_mean.idxmax(axis = 1)
print("\n训练集各群体的平均销售额：")
print(train_mean)
print("\n策略B选择：")
print(strategy_b)

# 4. 验证集计算各群体、各邮件方案的平均销售额
valid_mean = valid.groupby(
    ["purchase_group", "segment"]
)["spend"].mean().unstack()

# 5. 验证集中各客户群体的占比
weights = valid["purchase_group"].value_counts(normalize = True)

# 6. 按照训练集确定的A规则，评价统一策略

value_a = sum(
    weights[g] * valid_mean.loc[g, strategy_a]
    for g in weights.index
)

# 7. 按照训练集确定的B规则，评价分群策略
value_b = sum(
    weights[g] * valid_mean.loc[g, strategy_b[g]]
    for g in weights.index
)

print(f"策略A的RPC：${value_a:.4f}")
print(f"策略B的RPC：${value_b:.4f}")
print(f"B-A：${value_b-value_a:.4f}")

# 检查A和B在哪些群体的选择不同
changed = strategy_b[
    strategy_b != strategy_a
].index

print("策略不同的客户群体：", list(changed))
if len(changed) == 0:
    print("A和B完全相同，无需进行差异检验")
elif len(changed) == 1:
    g = changed[0]

    a = valid.loc[
        (valid["purchase_group"] == g) &
        (valid["segment"] == strategy_b[g]),
        "spend"
    ]

    b = valid.loc[
        (valid["purchase_group"] == g) &
        (valid["segment"] == strategy_a),
        "spend"
    ]

    test = ttest_ind(a, b, equal_var=False)
    ci_low, ci_high = welch_interval(a, b)
    print("Welch检验P值：", test.pvalue)
    print("整体策略差异：", weights[g] * (a.mean()-b.mean()))
    print("95%置信区间：",
          weights[g] * ci_low,
          weights[g] * ci_high)

else:
    print("多个群体的方案不同，需要联合估计策略差异及其不确定性")

# 5.5 客户特征与营销效果异质性分析
# 5.5.1 新老客户的邮件增量销售额
# 1. 检查各类客户在三个实验组中的人数
print(pd.crosstab(df["newbie"], df["segment"]))

# 2. 分别计算每个群体的RPC
newbie_rpc = df.groupby(
    ["newbie", "segment"]
)["spend"].mean().unstack()

print("\n新老客户各实验组RPC：")
print(newbie_rpc.round(4))

# 3. 计算相对于不发邮件的增量RPC
newbie_uplift = pd.DataFrame({
    "男装邮件增量":(
        newbie_rpc["Mens E-Mail"] - newbie_rpc["No E-Mail"]
    ),
    "女装邮件增量":(
        newbie_rpc["Womens E-Mail"] - newbie_rpc["No E-Mail"]
    )
})
print("\n新老客户的增量RPC：")
print(newbie_uplift.round(4))

# 5.5.2 新老客户的营销效果交互检验

# 1. 建立包含交互效应的模型
model_newbie = smf.ols(
    "spend ~ C(segment) * C(newbie)",
    data = df
).fit(cov_type="HC3")

# 2. 检验营销方案与新老客户身份的交互效应
interaction = model_newbie.wald_test_terms(
    scalar = True
).table.loc["C(segment):C(newbie)"]

print("新老客户交互效应检验：")
print(interaction)

# 5.5.3 历史购买渠道的营销增量分析

# 1. 检查各渠道在三个实验组的人数
print(pd.crosstab(df["channel"], df["segment"]))

# 2. 计算各渠道、各实验组的RPC
channel_rpc = df.groupby(
    ["channel", "segment"]
)["spend"].mean().unstack()
print("\n各渠道的RPC：")
print(channel_rpc.round(4))

# 3. 计算相对于不发邮件的增量RPC
channel_uplift = pd.DataFrame({
    "男装邮件增量": (
        channel_rpc["Mens E-Mail"] - channel_rpc["No E-Mail"]
    ),
    "女装邮件增量": (
        channel_rpc["Womens E-Mail"] - channel_rpc["No E-Mail"]
    )
})

print("\n各渠道增量RPC：")
print(channel_uplift.round(4))

# 5.5.4 历史购买渠道的交互效应检验
model_channel = smf.ols(
    "spend ~ C(segment) * C(channel)",
    data = df
).fit(cov_type = "HC3")

channel_test = model_channel.wald_test_terms(
    scalar = True
).table.loc["C(segment):C(channel)"]

print("历史购买渠道交互效应检验：")
print(channel_test)

# 5.5.5 两项交互效应检验的Holm校正
# 1. 提取新老客户交互检验的P值
p_newbie = interaction["pvalue"]

# 2. 提取历史渠道交互检验的P值
p_channel = channel_test["pvalue"]

# 3. 整理结果
interaction_report = pd.DataFrame({
    "客户特征": ["newbie", "channel"],
    "原始P": [p_newbie, p_channel]
})

# 4. Holm校正
interaction_report["Holm校正P"] = multipletests(
    interaction_report["原始P"],
    method="holm"
)[1]

interaction_report["是否显著"] = (
    interaction_report["Holm校正P"] < 0.05
)

print(interaction_report.to_string(index=False))
