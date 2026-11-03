# 复现与代码审计

在 Windows PowerShell 上用 Python 3.9.0rc2、NumPy 1.24.1、pandas 1.5.3、SciPy 1.10.0、statsmodels 0.14.4 验证。工作区只有 analysis.py，整理前备份到本地 analysis.original.py。

运行 `python analysis.py (Get-ChildItem *.csv).Name`，退出码 0，执行到第 5.5 节 Holm 输出。复跑确认 64,000 × 12、无缺失，男装、女装、对照人数为 21,307、21,387、21,306。相对对照 RPC 增量 +0.769827、+0.424412。品类整体和仅邮件交互 P 分别为 0.141812、0.041738。B−A = 0.010612，Welch P = 0.957054。newbie 与 channel 原始 P 为 0.051584、0.315287，校正后 0.103168、0.315287。均与任务参考和原稿对应数值在显示精度内一致。

- 修复第 5.5.4 节 Wald 索引中的多余空格，读取 C(segment):C(channel)。
- 首次运行在第 3.3 节遇到 SciPy 1.10 缺少置信区间接口。改用 Welch–Satterthwaite 自由度和 t 临界值计算同一双侧区间，原 Welch P 值计算保留。
- 路径改为可传参，默认定位到脚本旁 data/hillstrom.csv。集中导入，去除未使用的 matplotlib 与重复的交互检验调用。保留种子、样本和检验口径。
- 策略点估计使用未舍入均值，分别显示四位小数的 A、B 直接相减可能相差 0.0001。
