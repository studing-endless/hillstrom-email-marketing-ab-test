# 正式复现说明

## 1. 数据与运行环境

使用 Kevin Hillstrom 公开的邮件营销随机实验数据，共 64,000 行客户、12 个原始字段，三组为男装邮件、女装邮件和不发邮件，观察发送后两周的结果。原始 CSV 未随仓库分发；请按[数据获取说明](../data/README.md)从作者原始发布获取，保留行顺序并保存为 data/hillstrom.csv。[原始来源](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html)

全量分析、测试和两张图在 Windows PowerShell、Python 3.13.6 隔离环境中实际运行。核心版本如下，固定约束见 [requirements.txt](../requirements.txt)。

| 依赖 | 已验证版本 |
| --- | --- |
| NumPy | 2.2.6 |
| pandas | 2.2.3 |
| SciPy | 1.15.3 |
| statsmodels | 0.14.4 |
| Matplotlib | 3.10.7 |
| pytest | 8.3.5 |

Linux GitHub Actions 执行合成数据和图像输出测试。macOS 及 Python 3.10、3.11、3.12 的全量运行尚未验证。图中中文在 Windows 使用 Microsoft YaHei，Linux CI 安装 Noto CJK；macOS 可使用系统 PingFang SC。

## 2. 安装与运行

先安装稳定 Python 3.13，在仓库根目录执行。数据就位后可同时生成分析结果和两张 200 DPI PNG。每步直接调用虚拟环境 Python。

**Windows PowerShell**

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -X utf8 analysis.py data/hillstrom.csv
.\.venv\Scripts\python.exe -X utf8 plot_figures.py data/hillstrom.csv
```

**macOS / Linux（bash 或 zsh）**

```sh
python3.13 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m pytest -q
./.venv/bin/python -X utf8 analysis.py data/hillstrom.csv
./.venv/bin/python -X utf8 plot_figures.py data/hillstrom.csv
```

绘图需要系统中文字体。Ubuntu/Debian 可运行 `sudo apt-get install fonts-noto-cjk`。脚本会检查可用字体，缺少时明确报错。Windows 使用系统微软雅黑，macOS 可使用 PingFang SC，后者尚未实机执行。

主分析和绘图脚本都接受第一个位置参数指定 CSV 路径。plot_figures.py 调用 analysis.py 的正式比较、业务指标和利润情景函数，绘图过程不重复执行 Bootstrap。两张 PNG 默认输出到 figures/。

## 3. 自动化测试

本地原有 35 项测试全部通过，含 64,000 行 CSV 的完整集成复现。展示版另增 2 项测试，分别核对利润参数与全部情景值，以及绘图输入、PNG 格式、尺寸、DPI 和中文缺字警告，共 37 项通过。语法检查与依赖一致性检查也已通过。

公开 Linux CI 已实际通过 36 项测试，1 项预期跳过，包含两项展示测试。唯一跳过项是需要原始 CSV 的全量集成验证，其跳过原因由测试明确输出。最终执行结果可在 [GitHub Actions](https://github.com/studing-endless/hillstrom-email-marketing-ab-test/actions/workflows/tests.yml) 查看。合成样本验证公式及程序路径，无法替代原始实验数据的复现。

如需单独运行语法与依赖检查，可在所选虚拟环境中执行 `python -m compileall -q analysis.py plot_figures.py tests` 和 `python -m pip check`。[测试源码](../tests/test_analysis.py)

## 4. 核心统计结果复核

### 样本、分配与增量

| 项目 | 实际复核结果 |
| --- | --- |
| 数据规模 | 64,000 × 12 |
| 男装 / 女装 / 不发人数 | 21,307 / 21,387 / 21,306 |
| 男装邮件增量 RPC | +0.769827156 美元/客户 |
| 女装邮件增量 RPC | +0.424412216 美元/客户 |
| 1:1:1 SRM | χ²=0.202531250，P=0.903692958 |

SRM 使用真实预期比例和原始人数，未发现明显比例异常。它无法证明随机化与数据记录的每个环节均正确。

### 九项双侧比较

行为差异以百分点计，RPC 差异以美元/客户计。指标内 Holm 针对每项指标的三次比较，九项 Holm 将三指标的九个原始 P 值共同校正。区间为未同时调整的单项 95% 区间。

| 指标 | 前者减后者 | 差异 | 单项 95% CI | 原始 P | 指标内 Holm P | 九项 Holm P |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| 访问 | 男装－不发 | 7.6590 | [6.9953, 8.3227] | 5.68517e-112 | 1.70555e-111 | 5.11665e-111 |
| 访问 | 女装－不发 | 4.5233 | [3.8894, 5.1574] | 3.1824e-44 | 6.36481e-44 | 2.54592e-43 |
| 访问 | 男装－女装 | 3.1356 | [2.4284, 3.8428] | 3.80217e-18 | 3.80217e-18 | 2.66152e-17 |
| 购买 | 男装－不发 | 0.6805 | [0.5014, 0.8641] | 1.52322e-13 | 4.56967e-13 | 9.13934e-13 |
| 购买 | 女装－不发 | 0.3111 | [0.1502, 0.4745] | 0.000157105 | 0.00031421 | 0.000628421 |
| 购买 | 男装－女装 | 0.3694 | [0.1746, 0.5663] | 0.000205154 | 0.00031421 | 0.000628421 |
| RPC | 男装－不发 | 0.7698 | [0.4851, 1.0545] | 1.16381e-07 | 3.49144e-07 | 5.81907e-07 |
| RPC | 女装－不发 | 0.4244 | [0.1690, 0.6799] | 0.0011294 | 0.00225879 | 0.00225879 |
| RPC | 男装－女装 | 0.3454 | [0.0326, 0.6583] | 0.0304687 | 0.0304687 | 0.0304687 |

比例区间用 Newcombe，RPC 区间用 Welch。九项共同校正后结论保持一致，两邮件直接比较的收入证据相对较弱。原有 3,000 次 RPC Bootstrap 区间依次为 [0.4807, 1.0461]、[0.1877, 0.6902]、[0.0344, 0.6582]，未增加抽样次数。

### 异质性与固定策略评价

| 项目 | 实际复核结果 |
| --- | --- |
| 历史品类三方案 HC3 交互 P | 0.141811990 |
| 历史品类两封邮件 HC3 交互 P | 0.041738011 |
| 规则 A 验证 RPC | 1.540340151 美元/客户 |
| 规则 B 验证 RPC | 1.550952170 美元/客户 |
| B−A / 双侧 Welch P | +0.010612019 / 0.957054219 |
| B−A 单项 95% CI | [−0.375690200, 0.396914238] |
| newbie 交互原始 P / 两项 Holm P | 0.051584048 / 0.103168096 |
| channel 交互原始 P / 两项 Holm P | 0.315287321 / 0.315287321 |

种子 42 保持原训练/验证划分，A 统一选男装，B 仅在仅买过女装群体改选女装。评价使用固定规则与同一验证客户构成。当前证据不足以支持 B 替代 A。历史品类的名义 P 值属于探索结果，不能当作整个项目已统一校正的结论。[检验族与统计口径](methodology.md)

### 图表数值与情景范围

RPC 图完全使用上表的三项收入比较。利润图完全使用主分析的 100,000 人、20%/30%/40% 毛益率和 0.10/0.20 美元单位成本，共 12 项方案情景，展示利润点估计。与图表生成前的正式计算比较，全部结构化主结果及 12 项利润、区间和参数保持一致。

在 30% 假设毛益率下，男装/女装在 0.10 美元成本时的利润点估计为 13,094.81 / 2,732.37 美元；成本升至 0.20 美元时为 3,094.81 / −7,267.63 美元。全部情景和不确定性解释见[完整报告](analysis-report.md)。[RPC 图](../figures/rpc_uplift_ci.png) · [利润图](../figures/profit_sensitivity.png) · [绘图源码](../plot_figures.py)

## 5. 复现范围与局限

历史实验来自 2008 年既有购买客户，只有两周观察窗口。随机化支持该实验条件下的平均分配效果，未来客户、长期响应和真实财务条件仍需重新评价。利润为假设情景，并未测量企业实际利润。

此前已观察全量数据，后续训练/验证只能视为探索性的内部评价。消费零值多、右尾明显，单元格内 Bootstrap 仅反映当前样本经验分布。新增敏感性区间为单项区间，未对全部探索作项目级同时覆盖调整。[统计质量报告](statistical-quality.md)

公开仓库保留代码、报告、测试和由汇总结果生成的图片。原始 CSV 需另行获取；代码许可和数据再分发权限分别处理。合成 CI 的通过与实机全量复现分别报告。
