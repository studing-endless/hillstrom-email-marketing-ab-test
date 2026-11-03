# Hillstrom 邮件营销随机实验
*Hillstrom Email Marketing A/B/n Experiment*

邮件组发生的购买中，有多少原本也会发生？本项目利用 Kevin Hillstrom 公开的 64,000 名既有客户实验，对比男装邮件、女装邮件和不发邮件三种随机分配方案，追踪两周访问、购买及销售。随机分配让对照组为自然消费提供可比较的基准。[原始挑战](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)

**[阅读完整分析报告](docs/analysis-report.md)** · [统计口径](docs/methodology.md) · [字段字典](docs/data-dictionary.md) · [运行与审计](docs/verification.md)

| RPC 比较（美元/客户） | 增量 | Welch 单项 95% CI | 九项 Holm P |
| --- | ---: | --- | ---: |
| 男装－不发 | +0.7698 | [0.4851, 1.0545] | 5.82e−7 |
| 女装－不发 | +0.4244 | [0.1690, 0.6799] | 0.002259 |
| 男装－女装 | +0.3454 | [0.0326, 0.6583] | 0.030469 |

男装邮件的收入优势主要来自较高购买率。按 10 万名可比客户、30% 贡献毛益率、每客 $0.10 成本的假设，男装增量利润估计约 $13,095，女装约 $2,732，女装区间跨零。成本升到 $0.20 时，男装区间也跨零。历史购买品类的分群规则相对统一发男装仅增加 $0.0106/客户，探索性 Welch P = 0.9571。统一男装可作为新随机试点的优先候选，实际部署取决于当前客户响应、真实单位成本和毛益。

分析依次检查数据和基线、拆解访问至收入、量化不确定性、测算盈亏，再用 HC3 交互检验与内部样本拆分评价定向策略。方法包括比例 Z 检验、Newcombe、Welch、Bootstrap 和 Holm。实验年代、两周观测期和先看全量再拆分限制了外推及策略验证。

## 复现

使用 Python、pandas、NumPy、SciPy 和 statsmodels。按[数据获取说明](data/README.md)保存 CSV 到 data/hillstrom.csv。

```sh
python -m pip install -r requirements.txt
python -X utf8 analysis.py
```

也可将原始 CSV 路径作为脚本的第一个参数。analysis.py 包含五阶段与第 5.5 节，docs/ 保存报告、方法、字典和运行记录，data/ 保存下载指引。
