# Hillstrom 邮件营销随机实验
*Hillstrom Email Marketing A/B/n Experiment*

**发不发邮件，发哪封，给谁发？** 即使不发邮件，有些客户也会回来购买。要决定营销预算，先要把自然购买和邮件带来的增量分开。本项目使用 Kevin Hillstrom 公开的 64,000 名既有客户随机实验，比较男装邮件、女装邮件和不发邮件在随后两周带来的访问、购买与销售差异。[原始挑战](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)

## 从实验结果到投放决策

**邮件有没有创造收入？** 两封邮件都提高了访问率和购买率。女装邮件组的购买者平均花费更高，但男装邮件组的购买率更高，所以按全体分配客户计算，男装每客增量收入约为 0.77 美元，女装约为 0.42 美元。

**增加的收入够不够覆盖成本？** 假设投放给 10 万名可比客户、贡献毛益率为 30%、每客成本为 0.10 美元，男装与女装利润点估计约为 13,095 和 2,732 美元，女装利润区间跨零。成本升到 0.20 美元时，男装利润区间也跨零。

**按历史偏好换邮件值不值？** 同一训练集选出统一发男装和按品类投放两条规则，再用验证集原有的随机分组估计规则价值。分群规则只给仅买过女装的人换邮件，整体多 0.0106 美元/客户，探索性 Welch P = 0.9571，当前证据不足以支持切换规则。

**经营判断**　优先把统一男装邮件纳入新随机试点，保留不发邮件组，并用真实毛益和成本判断是否推广。历史实验仅跟踪两周，策略拆分前已探索全量数据。

### 核心收入证据

用对照差回答发不发，用两封邮件直接比较回答发哪封。下表保留三项比较的效应量与不确定性。

| RPC 比较（美元/客户） | 增量 | Welch 单项 95% CI | 九项 Holm P |
| --- | ---: | --- | ---: |
| 男装－不发 | +0.7698 | [0.4851, 1.0545] | 5.82e−7 |
| 女装－不发 | +0.4244 | [0.1690, 0.6799] | 0.002259 |
| 男装－女装 | +0.3454 | [0.0326, 0.6583] | 0.030469 |

两封邮件相对不发的收入证据在九项统一 Holm 校正后仍成立。男装相对女装的估计优势更不确定，区间下限接近每客三美分。

**[阅读完整分析报告](docs/analysis-report.md)**，沿着随机分组、收入拆解、统计推断、成本情景和分群策略的顺序查看完整证据。[统计口径](docs/methodology.md) · [字段字典](docs/data-dictionary.md) · [运行与审计](docs/verification.md)

## 复现

已在 Windows PowerShell、稳定版 Python 3.13.6 的隔离环境完成验证，核心依赖为 NumPy 2.2.6、pandas 2.2.3、SciPy 1.15.3、statsmodels 0.14.4。按[数据获取说明](data/README.md)保存 CSV 到 data/hillstrom.csv。

以下命令在仓库根目录执行，需要先安装稳定版 Python 3.13，并按上述说明下载数据。每一步都直接调用虚拟环境中的 Python。

**Windows PowerShell**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -X utf8 analysis.py data/hillstrom.csv
```

**macOS / Linux（bash 或 zsh）**

```sh
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q
./.venv/bin/python -X utf8 analysis.py data/hillstrom.csv
```

若尚未下载 CSV，可以先运行测试；全量数据集成项会明确跳过，分析命令需在数据就位后执行。本地全量复现环境为 Windows，Linux 合成测试由 GitHub Actions 验证，macOS 命令尚未实机执行。

也可将原始 CSV 路径作为脚本的第一个参数。analysis.py 包含五阶段与第 5.5 节，docs/ 保存报告、方法、字典和运行记录，data/ 保存下载指引。

## 质量检查与测试导航

[分析代码](analysis.py) 包含输入校验、1:1:1 SRM、原主分析和单元格内 Bootstrap 敏感性。[测试](tests/test_analysis.py) 使用合成数据覆盖指标、区间、Holm、SRM、标签、策略选择与多群体评价、随机种子和异常报错。本地原始 CSV 存在时另执行全量集成复现；缺少 CSV 时该项明确跳过。CI 使用合成测试，不能替代原始数据的集成验证。

[统计质量与敏感性审查](docs/statistical-quality.md) 列出消费分布和五项分层效果差区间。[验证记录](docs/verification.md) 保留历史与本次环境、命令和回归比较。跨平台命令以所选稳定 Python 已安装为前提，本次实际执行环境是 Windows。

主要限制包括历史人群和两周结果的可迁移性、假设成本与毛益、先看全量再拆分的探索性质，以及个别单元格少量非零消费。新增区间为单项敏感性结果，项目全部探索尚未统一控制错误率。
