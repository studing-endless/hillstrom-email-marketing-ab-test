# 复现与代码审计

在 Windows PowerShell 上用 Python 3.9.0rc2、NumPy 1.24.1、pandas 1.5.3、SciPy 1.10.0、statsmodels 0.14.4 验证。工作区只有 analysis.py，整理前备份到本地 analysis.original.py。

运行 `python analysis.py (Get-ChildItem *.csv).Name`，退出码 0，执行到第 5.5 节 Holm 输出。复跑确认 64,000 × 12、无缺失，男装、女装、对照人数为 21,307、21,387、21,306。相对对照 RPC 增量 +0.769827、+0.424412。品类整体和仅邮件交互 P 分别为 0.141812、0.041738。B−A = 0.010612，Welch P = 0.957054。newbie 与 channel 原始 P 为 0.051584、0.315287，校正后 0.103168、0.315287。均与任务参考和原稿对应数值在显示精度内一致。

- 修复第 5.5.4 节 Wald 索引中的多余空格，读取 C(segment):C(channel)。
- 首次运行在第 3.3 节遇到 SciPy 1.10 缺少置信区间接口。改用 Welch–Satterthwaite 自由度和 t 临界值计算同一双侧区间，原 Welch P 值计算保留。
- 路径改为可传参，默认定位到脚本旁 data/hillstrom.csv。集中导入，去除未使用的 matplotlib 与重复的交互检验调用。保留种子、样本和检验口径。
- 策略点估计使用未舍入均值，分别显示四位小数的 A、B 直接相减可能相差 0.0001。

## 2026-11-23 最终整改验证

修改前基准为 0589a963891be690032a8184a25eb219a82e6172。修改前 main 与 origin/main 同步，只有用户未跟踪的 .vscode 目录。本次分支为 improve/statistical-quality；原始 Word、CSV 与已发布提交保留。旧脚本先在历史环境运行，stdout 及关键值保存在本地忽略目录 .local-audit，未提交原始数据或运行日志。

### 实际环境与执行命令

实际执行环境为 Windows PowerShell，Python 3.13.6 隔离虚拟环境。本机没有 Python 3.11，因此选用已安装的稳定 Python 3.13。核心依赖为 NumPy 2.2.6、pandas 2.2.3、SciPy 1.15.3、statsmodels 0.14.4、pytest 8.3.5。

其余实际安装版本为 colorama 0.4.6、iniconfig 2.3.1、packaging 26.3、patsy 1.0.3、pluggy 1.7.0、python-dateutil 4.0.0、pytz 2026.6、tzdata 2026.6。requirements.txt 固定核心计算和测试依赖，以上记录补足本次完整环境，间接依赖仍由安装工具解析。

以下为本次在 Windows 实际执行的命令。CSV 路径通过 PowerShell 获取，读者可改为普通文件路径。

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m compileall -q analysis.py tests
.venv/Scripts/python -m pytest -q
.venv/Scripts/python analysis.py (Get-ChildItem *.csv).Name --output-json .local-audit/after.json
.venv/Scripts/python -m pip check
```

语法检查和 pip check 通过。最终本地 pytest 为 35 passed，其中 34 项合成/单元验证和 1 项全量 CSV 集成复现。另把代码和测试复制到没有 CSV 的隔离目录执行，得到 34 passed、1 skipped；跳过信息明确说明未执行 64,000 行验证。GitHub Actions 在公开仓库执行合成测试与语法检查，原始数据不在仓库中，该环境全量集成项应跳过。

### 回归比较

| 项目 | 修改前 | 修改后 |
| --- | ---: | ---: |
| 行数 | 64,000 | 64,000 |
| 男装 / 女装 / 不发人数 | 21,307 / 21,387 / 21,306 | 21,307 / 21,387 / 21,306 |
| 男装增量 RPC | 0.769827156 | 0.769827156 |
| 女装增量 RPC | 0.424412216 | 0.424412216 |
| 品类三方案交互 P | 0.141811990 | 0.141811990 |
| 品类两封邮件交互 P | 0.041738011 | 0.041738011 |
| 策略 B−A | 0.010612019 | 0.010612019 |
| 策略 P | 0.957054219 | 0.957054219 |
| newbie 交互 P | 0.051584048 | 0.051584048 |
| channel 交互 P | 0.315287321 | 0.315287321 |
| 第 5.5 节 Holm | 0.103168096 / 0.315287321 | 0.103168096 / 0.315287321 |

关键值与修改前基准在绝对误差 1e-12 下相符。另在新环境重新运行基准提交脚本，逐项比较九个原始 P、九项 Holm 值及三项 RPC Welch 区间，均在同一误差阈值内相符。原有三对 Bootstrap 区间显示精度保持一致。

新增 SRM χ²=0.202531250、P=0.903692958。新增五项分层 Bootstrap 区间及完整单元格诊断见[质量审查](statistical-quality.md)。单变化群体策略区间为 [−0.375690200, 0.396914238]，与原 Welch 权重换算一致。多个变化群体用独立单元格均值方差求和与 Satterthwaite 近似实现，已用合成数据和手算方差核验。

### 实际缺陷与审查判断

修复了导入时立即执行、缺少输入校验及 SRM、重复计算和输出、多个变化群体缺少统计推断、缺少自动测试、历史预发布 Python 环境不足以支撑当前复现等问题。数据加载、指标汇总、比例比较、Welch、Holm、分群、交互检验、策略选择与评价均有可导入函数，main 串联原五阶段和第 5.5 节。

消费右偏本身不构成否定 Welch、Bootstrap 或 OLS+HC3 的理由，分析目标是全体客户平均增量。SRM 未发现异常也不能证明随机化完整无误；基线采用描述性检查。没有发现需要改写历史检验结果的实际算术错误。新分层区间反映部分邮件相对优势差异，同时保留跨零结果及探索限制，未增加预测模型、异常值筛除或新的营销实验。

### 身份与发布范围

仓库级作者配置为 studing-endless，邮箱为 257683604+studing-endless@users.noreply.github.com。该身份来自本地 Olist 正式仓库提交 d10c3a4，账号 ID 与 GitHub 连接器返回的 257683604 一致。GitHub 私有邮箱设置页未读取，因此不声称检查了所有已验证邮箱。全局配置未修改，历史 Codex 提交保留。

About Description 和五项 Topics 已通过 GitHub API 更新并回读确认。仓库目前无 LICENSE，未自行选择开源许可证。原始 CSV 的再分发许可仍未确认，读者按来源获取数据。本次仅推送独立分支，供进一步审阅。
